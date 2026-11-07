from minerva.message_history import MessageHistory, PdfContent
from minerva.tool_utils import TOOL_PREFIX
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.chat_completion_content_part_param import ChatCompletionContentPartParam


def format_chat_history_for_openai(
  system_prompt: str, chat_history: MessageHistory
) -> list[ChatCompletionMessageParam]:
  messages: list[ChatCompletionMessageParam] = [{"role": "system", "content": system_prompt}]
  for message in chat_history.history:
    # File parts are only allowed in user messages, so only text tool responses go as system ones
    if message.author.startswith(TOOL_PREFIX) and isinstance(message.content, str):
      messages.append(
        {
          "role": "system",
          "content": message.content,
          "name": message.author,
        }
      )
      continue

    content: list[ChatCompletionContentPartParam] = []
    if isinstance(message.content, str):
      content = [{"type": "text", "text": message.content}]
    elif isinstance(message.content, PdfContent):
      content = [
        {
          "type": "file",
          "file": {"filename": message.content.filename, "file_data": message.content.data_url},
        },
        {"type": "text", "text": message.content.text},
      ]
    else:
      for image in message.content.images:
        content.append(
          {
            "type": "image_url",
            "image_url": {"url": image.url},
          }
        )
      if message.content.text:
        content.append({"type": "text", "text": message.content.text})

    messages.append(
      {
        "role": "user",
        "content": content,
        "name": message.author,
      }
    )
  return messages
