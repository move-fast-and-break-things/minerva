from telegram import InputFile
from io import BytesIO
from typing import Unpack

from minerva.tools.tool_kwargs import DefaultToolKwargs


async def send_text_file(filename: str, content: str, **kwargs: Unpack[DefaultToolKwargs]) -> str:
  """Send a text file with the given filename and content to the user.

  This tool triggers Minerva to send a document back to the user in the current
  chat/topic. The actual sending is handled by the chat session; this function
  returns a short confirmation for the model's internal tool response history.
  """

  data = content.encode("utf-8")
  input_file = InputFile(BytesIO(data), filename=filename)
  await kwargs["bot"].send_document(
    chat_id=kwargs["chat_id"],
    document=input_file,
    message_thread_id=kwargs["topic_id"],
    reply_to_message_id=kwargs["reply_to_message_id"],
  )

  # The actual sending is performed by the chat session, which has access to the
  # Telegram Bot instance and thread context.
  return f"sent:{filename}:{len(content.encode('utf-8'))}"
