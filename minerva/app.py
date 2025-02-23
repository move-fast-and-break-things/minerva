from minerva.config import (
  AI_NAME,
  OPENAI_API_KEY,
  OPENAI_MODEL,
  TELEGRAM_BOT_TOKEN,
  TELEGRAM_CHAT_ID,
)

from telegram import Update
from telegram.ext import Application

from minerva.minerva import Minerva


def main():
  if OPENAI_API_KEY is None:
    raise ValueError("OPENAI_API_KEY is required")
  if TELEGRAM_BOT_TOKEN is None:
    raise ValueError("TELEGRAM_BOT_TOKEN is required")
  if TELEGRAM_CHAT_ID is None:
    raise ValueError("TELEGRAM_CHAT_ID is required")
  if OPENAI_MODEL is None:
    raise ValueError("OPENAI_MODEL is required")

  print(f"Starting {AI_NAME} powered by {OPENAI_MODEL}")

  async def initialize_minerva(application: Application) -> None:
    minerva = Minerva(
      application,
      chat_id=TELEGRAM_CHAT_ID,
      openai_api_key=OPENAI_API_KEY,
      openai_model=OPENAI_MODEL,
    )
    await minerva.initialize()

  application = (
    Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(initialize_minerva).build()
  )
  application.run_polling(allowed_updates=[Update.MESSAGE, Update.MY_CHAT_MEMBER])


if __name__ == "__main__":
  main()
