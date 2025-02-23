from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Limits Minerva to a specific Telegram chat
TELEGRAM_CHAT_ID_STR = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_CHAT_ID = int(TELEGRAM_CHAT_ID_STR) if TELEGRAM_CHAT_ID_STR is not None else None

CALENDAR_ICS_URL = os.getenv("CALENDAR_ICS_URL")

AI_NAME = "Minerva"
