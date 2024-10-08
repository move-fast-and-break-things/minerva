from typing import cast

from openai import AsyncOpenAI

from telegram import Update, Message as TelegramMessage, User as TelegramUser
from telegram.constants import MessageEntityType, ChatType, ChatMemberStatus, ChatAction
from telegram.ext import Application, ContextTypes, MessageHandler, filters, ChatMemberHandler

from minerva.config import AI_NAME, CALENDAR_ICS_URL
from minerva.markdown_splitter import split_markdown
from minerva.message_history import Message, MessageHistory, trim_by_token_size
from minerva.prompt import USERNAMELESS_ID_PREFIX, ModelAction, Prompt, parse_model_message
from minerva.tools.fetch_html import fetch_html
from minerva.tool_utils import format_tool_username, parse_tool_call

MAX_TELEGRAM_MESSAGE_LENGTH_CHAR = 2000
OPENAI_RESPONSE_MAX_TOKENS = 1512
TOOL_RESPONSE_MAX_TOKENS = 2048

MAX_TOOL_USE_COUNT = 5
MAX_RETRY_COUNT = 3


class ReplyToMessageCallInfo:
  tool_use_count: int = 0
  retry_count: int = 0


class Minerva:
  def __init__(
      self,
      application: Application,
      chat_id: int,
      openai_api_key: str,
      openai_model: str,
  ):
    self.application = application
    self.chat_id = chat_id
    self.chat_histories: dict[int, MessageHistory] = {}
    self.openai = AsyncOpenAI(api_key=openai_api_key)
    self.openai_model = openai_model
    self.tools: dict[str, callable] = {
        "fetch_html": fetch_html,
    }

    if CALENDAR_ICS_URL:
      from minerva.tools.calendar import CalendarTool
      calendar_tool = CalendarTool(CALENDAR_ICS_URL)
      self.tools["query_calendar"] = calendar_tool.query

  async def initialize(self) -> None:
    self.me = cast(TelegramUser, await self.application.bot.get_me())
    self.username_with_mention = f"@{self.me.username}"
    self.prompt = Prompt(ai_name=AI_NAME, ai_username=self.me.username, tools=self.tools)

    print("Starting Minerva with prompt:\n", self.prompt)

    self.application.add_handler(MessageHandler(filters.TEXT, self.on_message))
    self.application.add_handler(ChatMemberHandler(
        self.on_chat_member_update, chat_member_types=ChatMemberHandler.MY_CHAT_MEMBER))

    print(
        f"Minerva is ready to chat in chat {self.chat_id}. Minerva username is {self.me.username}.")

  async def on_chat_member_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.my_chat_member:
      return

    if update.my_chat_member.chat.id == self.chat_id:
      return

    if update.my_chat_member.new_chat_member.user.id != self.me.id:
      return

    if update.my_chat_member.new_chat_member.status != ChatMemberStatus.MEMBER:
      return

    await update.my_chat_member.chat.send_message("I'm sorry, I can't talk to you here.")
    await update.my_chat_member.chat.leave()

  async def on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message:
      return

    if not message.text:
      # Minerva only support text messages
      return

    if message.chat.id != self.chat_id:
      await message.reply_text("I'm sorry, I can't talk to you here.")
      if message.chat.type != ChatType.PRIVATE:
        await message.chat.leave()
      return

    topic_id = self._get_topic_id(message)
    # Add message to chat history
    if topic_id not in self.chat_histories:
      self.chat_histories[topic_id] = MessageHistory(str(self.prompt))
    chat_history = self.chat_histories[topic_id]
    chat_history.add(Message(
        message.from_user.username or f"{USERNAMELESS_ID_PREFIX}{message.from_user.id}",
        message.text,
    ))

    if not self._is_reply_to_me(message) and not self._is_mentioned(message):
      return

    await message.chat.send_chat_action(ChatAction.TYPING, message_thread_id=topic_id)
    await self._reply_to_message(message, chat_history)

  async def _reply_to_message(
      self,
      message: TelegramMessage,
      chat_history: MessageHistory,
      call_info: ReplyToMessageCallInfo = None,
  ) -> None:
    if call_info is None:
      call_info = ReplyToMessageCallInfo()

    try:
      prompt = self.prompt.format(chat_history)
      print(f"OpenAPI prompt:\n{prompt}\n\n")

      response = await self.openai.chat.completions.create(
          model=self.openai_model,
          messages=[
              {"role": "system", "content": prompt},
          ],
          temperature=0.8,
          frequency_penalty=0.7,
          presence_penalty=0.3,
          max_tokens=OPENAI_RESPONSE_MAX_TOKENS,
          user=f"telegram-{message.from_user.id}",
      )
      answer = response.choices[0].message.content  # type: ignore
      print(f"OpenAI response:\n{answer}\n\n")
    except Exception as err:
      print("OpenAI API error:", err)
      answer = (
          f"Action: {ModelAction.RESPOND}\n"
          "I'm sorry, I'm having trouble understanding you right now."
          " Could you please rephrase your question?"
      )

    chat_history.add(Message(self.me.username, answer))

    try:
      model_message = parse_model_message(answer)
    except Exception as err:
      if call_info.retry_count >= MAX_RETRY_COUNT:
        answer = (
            "I'm sorry, I'm having trouble understanding you right now."
            " Could you please rephrase your question?"
        )
        chat_history.add(Message(self.me.username, f"Action: {ModelAction.RESPOND}\n{answer}"))
        await message.reply_markdown(answer)
        return

      call_info.retry_count += 1
      chat_history.add(Message("ERROR", str(err)))
      await self._reply_to_message(message, chat_history, call_info)
      return

    match model_message.action:
      case ModelAction.RESPOND:
        for response in split_markdown(model_message.content, MAX_TELEGRAM_MESSAGE_LENGTH_CHAR):
          await message.reply_markdown(response)

      case ModelAction.USE_TOOL:
        call_info.tool_use_count += 1

        # Minerva reached the tool use limit, tell her to reply to the user
        if call_info.tool_use_count == MAX_TOOL_USE_COUNT:
          chat_history.add(Message(
              format_tool_username("ERROR"),
              f"You've used tools more than {MAX_TOOL_USE_COUNT} times in a row."
              " Reply to the user.",
          ))
          await self._reply_to_message(message, chat_history, call_info)
          return

        # Minerva is past the tool use limit and ignored our request to reply to the user
        # Reply to the user instead of her
        if call_info.tool_use_count > MAX_TOOL_USE_COUNT:
          message = "I'm sorry, I can't help you with that. Please ask something else."
          chat_history.add(Message(self.me.username, f"Action: {ModelAction.RESPOND}\n{message}"))
          await message.reply_markdown(message)
          return

        try:
          tool_call = parse_tool_call(model_message.content, self.tools)
        except Exception as err:
          chat_history.add(Message(format_tool_username("ERROR"), f"ERROR: {repr(err)}"))
          await self._reply_to_message(message, chat_history, call_info)
          return

        try:
          tool_response = await self.tools[tool_call.tool_name](*tool_call.args)
          # ensure we won't blow up the conversation history with a huge tool response
          truncated_tool_response = trim_by_token_size(
              tool_response, TOOL_RESPONSE_MAX_TOKENS, "...TRUNCATED",
          )
          chat_history.add(Message(format_tool_username(
              tool_call.tool_name), truncated_tool_response))
        except Exception as err:
          chat_history.add(Message(format_tool_username(
              tool_call.tool_name), f"ERROR: {repr(err)}"))

        await self._reply_to_message(message, chat_history, call_info)

      case _:
        print("Unknown action:", model_message.action)

  def _get_topic_id(self, message: TelegramMessage) -> int:
    return message.message_thread_id

  def _is_reply_to_me(self, message: TelegramMessage) -> bool:
    if not message.reply_to_message:
      return False
    return message.reply_to_message.from_user.id == self.me.id

  def _is_mentioned(self, message: TelegramMessage) -> bool:
    for entity in message.entities:
      if (
          entity.type == MessageEntityType.MENTION
          and message.parse_entity(entity) == self.username_with_mention
      ):
        return True
    return False
