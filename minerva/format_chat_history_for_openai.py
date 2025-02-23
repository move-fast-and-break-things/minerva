from minerva.message_history import ContentType, ImageContent, MessageHistory
from minerva.tool_utils import TOOL_PREFIX


def format_chat_history_for_openai(system_prompt: str, chat_history: MessageHistory):
  messages = [{"role": "system", "content": system_prompt}]
  for message in chat_history.history:
    content: ContentType = None
    if isinstance(message.content, str):
      content = [{"type": "text", "text": message.content}]
    elif isinstance(message.content, ImageContent):
      content = []
      for image in message.content.images:
        content.append({
            "type": "image_url",
            "image_url": {"url": image.url},
        })
      if message.content.text:
        content.append({"type": "text", "text": message.content.text})

    messages.append({
        "role": "system" if message.author.startswith(TOOL_PREFIX) else "user",
        "content": content,
        "name": message.author,
    })
  return messages
