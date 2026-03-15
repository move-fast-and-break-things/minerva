from typing import Any, Callable, NotRequired, TypedDict
from telegram import Bot


class DefaultToolKwargs(TypedDict):
  bot: Bot
  chat_id: int
  topic_id: int
  reply_to_message_id: int | None
  openai_client: NotRequired[Any]
  ai_username: NotRequired[str]
  add_message_to_history: NotRequired[Callable[..., Any]]
