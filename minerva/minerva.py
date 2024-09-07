from typing import Dict, cast

from openai import AsyncOpenAI

from telegram import Update, Message as TelegramMessage, User as TelegramUser
from telegram.constants import MessageEntityType, ChatType, ChatMemberStatus, ChatAction
from telegram.ext import Application, ContextTypes, MessageHandler, filters, ChatMemberHandler

from minerva.markdown_splitter import split_markdown
from minerva.message_history import Message, MessageHistory
from minerva.prompt import USERNAMELESS_ID_PREFIX

MAX_TELEGRAM_MESSAGE_LENGTH_CHAR = 2000
RESPONSE_MAX_TOKENS = 1512


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
    self.chat_histories: Dict[int, MessageHistory] = {}
    self.openai = AsyncOpenAI(api_key=openai_api_key)
    self.openai_model = openai_model

  async def initialize(self) -> None:
    self.me = cast(TelegramUser, await self.application.bot.get_me())
    self.username_with_mention = f"@{self.me.username}"
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
      self.chat_histories[topic_id] = MessageHistory(self.me.username)
    chat_history = self.chat_histories[topic_id]
    chat_history.add(Message(
        message.from_user.username or f"{USERNAMELESS_ID_PREFIX}{message.from_user.id}",
        message.text,
    ))

    if not self._is_reply_to_me(message) and not self._is_mentioned(message):
      return

    await message.chat.send_chat_action(ChatAction.TYPING, message_thread_id=topic_id)
    try:
      response = await self.openai.chat.completions.create(
          model=self.openai_model,
          messages=[
              {"role": "system", "content": chat_history.format_prompt()},
          ],
          temperature=0.8,
          frequency_penalty=0.7,
          presence_penalty=0.3,
          max_tokens=RESPONSE_MAX_TOKENS,
          user=f"telegram-{message.from_user.id}",
      )
      answer = response.choices[0].message.content  # type: ignore
    except Exception as err:
      print("OpenAI API error:", err)
      answer = (
          "I'm sorry, I'm having trouble understanding you right now."
          " Could you please rephrase your question?"
      )

    chat_history.add(Message(self.me.username, answer))

    for response in split_markdown(answer, MAX_TELEGRAM_MESSAGE_LENGTH_CHAR):
      await message.reply_markdown(response)

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
