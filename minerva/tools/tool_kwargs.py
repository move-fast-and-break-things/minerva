from telegram import Bot
from typing import TypedDict


class DefaultToolKwargs(TypedDict):
  bot: Bot
  chat_id: int
  topic_id: int
  reply_to_message_id: int
