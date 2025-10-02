from typing import Optional
from io import BytesIO
from openai import AsyncOpenAI
from telegram import Bot, InputFile
from minerva.llm_session import LlmSession
from minerva.markdown_splitter import split_markdown
from minerva.message_history import Message, trim_by_token_size
from minerva.prompt import ModelAction, parse_model_message
from telegram.constants import ParseMode

from minerva.tool_utils import GenericToolFn, format_tool_username, parse_tool_call


class CreateMessageCallInfo:
  tool_use_count: int = 0
  retry_count: int = 0


class ChatSession:
  def __init__(
    self,
    bot: Bot,
    ai_username: str,
    openai_client: AsyncOpenAI,
    openai_model_name: str,
    max_completion_tokens: int,
    max_history_tokens: int,
    max_create_response_retry_count: int,
    max_create_response_tool_use_count: int,
    max_telegram_message_length_char: int,
    max_tool_response_tokens: int,
    tools: dict[str, GenericToolFn],
    prompt: str,
    chat_id: int,
    topic_id: int,
  ):
    self.ai_username = ai_username
    self.bot = bot
    self.chat_id = chat_id
    self.topic_id = topic_id
    self.max_create_response_retry_count = max_create_response_retry_count
    self.max_create_response_tool_use_count = max_create_response_tool_use_count
    self.max_telegram_message_length_char = max_telegram_message_length_char
    self.max_tool_response_tokens = max_tool_response_tokens
    self.tools: dict[str, GenericToolFn] = tools

    self.llm_session = LlmSession(
      ai_username=ai_username,
      openai_client=openai_client,
      openai_model_name=openai_model_name,
      max_completion_tokens=max_completion_tokens,
      max_history_tokens=max_history_tokens,
      prompt=prompt,
    )

  def add_message(self, message: Message):
    self.llm_session.add_message(message)

  def create_response(self, user_id: str, reply_to_message_id: Optional[int] = None):
    return self._create_response(user_id=user_id, reply_to_message_id=reply_to_message_id)

  async def _create_response(
    self,
    user_id: str,
    reply_to_message_id: Optional[int] = None,
    call_info: Optional[CreateMessageCallInfo] = None,
  ) -> None:
    if call_info is None:
      call_info = CreateMessageCallInfo()

    try:
      answer = await self.llm_session.create_response(user_id=user_id)
      print(f"OpenAI response:\n{answer}\n\n")
    except Exception as err:
      print("OpenAI API error:", err)
      answer = (
        f"Action: {ModelAction.RESPOND}\n"
        "I'm sorry, I'm having trouble understanding you right now."
        " Could you please rephrase your question?"
      )
      self.llm_session.add_message(Message(self.ai_username, answer))

    try:
      model_message = parse_model_message(answer)
    except Exception as err:
      if call_info.retry_count >= self.max_create_response_retry_count:
        answer = "I'm sorry, I'm having trouble understanding you right now. Could you please rephrase your question?"
        self.llm_session.add_message(
          Message(self.ai_username, f"Action: {ModelAction.RESPOND}\n{answer}")
        )
        await self._send_message(answer, reply_to_message_id)
        return

      call_info.retry_count += 1
      self.llm_session.add_message(Message("ERROR", str(err)))
      await self._create_response(
        user_id=user_id,
        reply_to_message_id=reply_to_message_id,
        call_info=call_info,
      )
      return

    match model_message.action:
      case ModelAction.RESPOND:
        for response in split_markdown(
          model_message.content, self.max_telegram_message_length_char
        ):
          await self._send_message(response, reply_to_message_id)

      case ModelAction.USE_TOOL:
        call_info.tool_use_count += 1

        # Minerva reached the tool use limit, tell her to reply to the user
        if call_info.tool_use_count == self.max_create_response_tool_use_count:
          self.llm_session.add_message(
            Message(
              format_tool_username("ERROR"),
              f"You've used tools more than {self.max_create_response_tool_use_count} times in a row. Reply to the user.",
            )
          )
          await self._create_response(
            user_id=user_id,
            reply_to_message_id=reply_to_message_id,
            call_info=call_info,
          )
          return

        # Minerva is past the tool use limit and ignored our request to reply to the user
        # Reply to the user instead of her
        if call_info.tool_use_count > self.max_create_response_tool_use_count:
          max_tool_count_reached_response = (
            "I'm sorry, I can't help you with that. Please ask something else."
          )
          self.llm_session.add_message(
            Message(
              self.ai_username,
              f"Action: {ModelAction.RESPOND}\n{max_tool_count_reached_response}",
            )
          )
          await self._send_message(max_tool_count_reached_response, reply_to_message_id)
          return

        try:
          tool_call = parse_tool_call(model_message.content, self.tools)
        except Exception as err:
          self.llm_session.add_message(
            Message(format_tool_username("ERROR"), f"ERROR: {repr(err)}")
          )
          await self._create_response(
            user_id=user_id,
            reply_to_message_id=reply_to_message_id,
            call_info=call_info,
          )
          return

        try:
          # Special handling for file sending
          if tool_call.tool_name == "send_text_file":
            filename, content = tool_call.args  # type: ignore[misc]
            data = content.encode("utf-8")
            input_file = InputFile(BytesIO(data), filename=filename)
            await self.bot.send_document(
              chat_id=self.chat_id,
              document=input_file,
              message_thread_id=self.topic_id,
              reply_to_message_id=reply_to_message_id,
            )

          tool_response = await self.tools[tool_call.tool_name](*tool_call.args)
          # Ensure we won't blow up the conversation history with a huge tool response
          truncated_tool_response = trim_by_token_size(
            tool_response,
            self.max_tool_response_tokens,
            "...TRUNCATED",
          )
          self.llm_session.add_message(
            Message(
              format_tool_username(tool_call.tool_name),
              truncated_tool_response,
            )
          )
        except Exception as err:
          self.llm_session.add_message(
            Message(
              format_tool_username(tool_call.tool_name),
              f"ERROR: {repr(err)}",
            )
          )

        await self._create_response(
          user_id=user_id,
          reply_to_message_id=reply_to_message_id,
          call_info=call_info,
        )

      case _:
        print("Unknown action:", model_message.action)

  def _send_message(
    self,
    text: str,
    reply_to_message_id: Optional[int] = None,
  ):
    return self.bot.send_message(
      chat_id=self.chat_id,
      text=text,
      message_thread_id=self.topic_id,
      reply_to_message_id=reply_to_message_id,
      parse_mode=ParseMode.MARKDOWN,
    )
