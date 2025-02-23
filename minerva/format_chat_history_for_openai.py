from minerva.message_history import MessageHistory
from minerva.tool_utils import TOOL_PREFIX
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.chat_completion_content_part_param import ChatCompletionContentPartParam


def format_chat_history_for_openai(system_prompt: str, chat_history: MessageHistory):
  messages: list[ChatCompletionMessageParam] = [{"role": "system", "content": system_prompt}]
  for message in chat_history.history:
    if message.author.startswith(TOOL_PREFIX):
      if not isinstance(message.content, str):
        raise Exception("Unexpected: tool response is not a string")
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
