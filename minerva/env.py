
from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY is None:
  raise ValueError("OPENAI_API_KEY environment variable is not set")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if TELEGRAM_BOT_TOKEN is None:
  raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")

# Limits Minerva to a specific Telegram chat
TELEGRAM_CHAT_ID_STR = os.getenv("TELEGRAM_CHAT_ID")
if TELEGRAM_CHAT_ID_STR is None:
  raise ValueError("TELEGRAM_CHAT_ID environment variable is not set")
TELEGRAM_CHAT_ID = int(TELEGRAM_CHAT_ID_STR)
