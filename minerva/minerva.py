from typing import cast

from openai import AsyncOpenAI

from telegram import (
  Update,
  Message as TelegramMessage,
  User as TelegramUser,
  Bot,
)
from telegram.constants import MessageEntityType, ChatType, ChatMemberStatus, ChatAction
from telegram.ext import (
  Application,
  ContextTypes,
  MessageHandler,
  filters,
  ChatMemberHandler,
)

from minerva.chat_session import ChatSession
from minerva.get_image_from_telegram_photo import get_image_from_telegram_photo
from minerva.config import AI_NAME, CALENDAR_ICS_URL
from minerva.message_history import ImageContent, Message
from minerva.prompt import USERNAMELESS_ID_PREFIX, Prompt
from minerva.tools.fetch_html import fetch_html
from minerva.tool_utils import GenericToolFn

MAX_TELEGRAM_MESSAGE_LENGTH_CHAR = 2000
OPENAI_RESPONSE_MAX_TOKENS = 1512
TOOL_RESPONSE_MAX_TOKENS = 2048

MAX_TOOL_USE_COUNT = 5
MAX_RETRY_COUNT = 3
HISTORY_MAX_TOKENS = 16384


class Minerva:
  def __init__(
    self,
    application: Application,
    chat_id: int,
    openai_api_key: str,
    openai_base_url: str,
    openai_model: str,
  ):
    self.application = application
    self.chat_id = chat_id
    self.chat_sessions: dict[int, ChatSession] = {}
    self.openai = AsyncOpenAI(api_key=openai_api_key, base_url=openai_base_url)
    self.openai_model = openai_model
    self.tools: dict[str, GenericToolFn] = {
      "fetch_html": fetch_html,
    }

    if CALENDAR_ICS_URL:
      from minerva.tools.calendar.get_query_calendar import get_query_calendar

      query_calendar = get_query_calendar(CALENDAR_ICS_URL)
      self.tools["query_calendar"] = query_calendar

      from minerva.tools.calendar.meeting_reminderer import setup_meeting_reminderer

      async def send_reminder(message: str) -> None:
        await cast(Bot, self.application.bot).send_message(
          chat_id=self.chat_id, text=message, message_thread_id=0
        )

      setup_meeting_reminderer(
        send_reminder,
        CALENDAR_ICS_URL,
      )

  async def initialize(self) -> None:
    self.me = cast(TelegramUser, await self.application.bot.get_me())
    if not self.me.username:
      raise ValueError("Unexpected: Minerva bot doesn't have a username")
    self.username = self.me.username
    self.username_with_mention = f"@{self.me.username}"
    self.prompt = Prompt(ai_name=AI_NAME, ai_username=self.me.username, tools=self.tools)

    print("Starting Minerva with prompt:\n", self.prompt)

    self.application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, self.on_message))
    self.application.add_handler(
      ChatMemberHandler(
        self.on_chat_member_update,
        chat_member_types=ChatMemberHandler.MY_CHAT_MEMBER,
      )
    )

    print(
      f"Minerva is ready to chat in chat {self.chat_id}. Minerva username is {self.me.username}."
    )

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

    if not message.text and not message.photo:
      # Only text and photo messages are supported
      return

    if not message.from_user:
      raise ValueError("Unexpected: message.from_user is None")

    if message.chat.id != self.chat_id:
      await message.reply_text("I'm sorry, I can't talk to you here.")
      if message.chat.type != ChatType.PRIVATE:
        await message.chat.leave()
      return

    topic_id = self._get_topic_id(message)
    should_respond = self._is_reply_to_me(message) or self._is_mentioned(message)
    if should_respond:
      # Send typing notification before starting to download the images because
      # downloading may take some time and we want to let the user that we
      # started processing their request
      await message.chat.send_chat_action(ChatAction.TYPING, message_thread_id=topic_id)

    message_author = message.from_user.username or f"{USERNAMELESS_ID_PREFIX}{message.from_user.id}"
    history_message: Message
    if message.text:
      history_message = Message(author=message_author, content=message.text)
    elif message.photo:
      history_message = Message(
        author=message_author,
        content=ImageContent(
          images=[
            await get_image_from_telegram_photo(cast(Bot, self.application.bot), message.photo)
          ],
          text=message.caption,
        ),
      )
      # If the user uploads multiple photos in a single message, Telegram API
      # will emit different message events for them
      # TODO(yurij): wait for other photos here
    else:
      raise ValueError("Unsupported message type")

    # Add message to chat history
    if topic_id not in self.chat_sessions:
      self.chat_sessions[topic_id] = ChatSession(
        bot=cast(Bot, self.application.bot),
        ai_username=self.username,
        openai_client=self.openai,
        openai_model_name=self.openai_model,
        max_completion_tokens=OPENAI_RESPONSE_MAX_TOKENS,
        max_history_tokens=HISTORY_MAX_TOKENS,
        prompt=str(self.prompt),
        tools=self.tools,
        chat_id=self.chat_id,
        topic_id=topic_id,
        max_create_response_retry_count=MAX_RETRY_COUNT,
        max_create_response_tool_use_count=MAX_TOOL_USE_COUNT,
        max_telegram_message_length_char=MAX_TELEGRAM_MESSAGE_LENGTH_CHAR,
        max_tool_response_tokens=TOOL_RESPONSE_MAX_TOKENS,
      )
    chat_session = self.chat_sessions[topic_id]
    chat_session.add_message(history_message)

    if not should_respond:
      return

    await chat_session.create_response(
      user_id=f"telegram-{message.from_user.id}",
      bussiness_connection_id=message.business_connection_id,
    )

  def _get_topic_id(self, message: TelegramMessage) -> int:
    # The General topic doesn't have a thread_id; we default to 0 for it
    return message.message_thread_id or 0

  def _is_reply_to_me(self, message: TelegramMessage) -> bool:
    if not message.reply_to_message:
      return False
    if not message.reply_to_message.from_user:
      raise ValueError("Unexpected: reply_to_message has no from_user")
    return message.reply_to_message.from_user.id == self.me.id

  def _is_mentioned(self, message: TelegramMessage) -> bool:
    for entity in message.entities:
      if (
        entity.type == MessageEntityType.MENTION
        and message.parse_entity(entity) == self.username_with_mention
      ):
        return True

    for entity in message.caption_entities:
      if (
        entity.type == MessageEntityType.MENTION
        and message.parse_caption_entity(entity) == self.username_with_mention
      ):
        return True

    return False
