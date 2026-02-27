from typing import TYPE_CHECKING, Any, Callable, NotRequired, TypedDict
from telegram import Bot

if TYPE_CHECKING:
  from openai import AsyncOpenAI


class DefaultToolKwargs(TypedDict):
  bot: Bot
  chat_id: int
  topic_id: int
  reply_to_message_id: int | None
  openai_client: NotRequired["AsyncOpenAI"]
  openai_image_model: NotRequired[str]
  ai_username: NotRequired[str]
  add_message_to_history: NotRequired[Callable[[Any], None]]
