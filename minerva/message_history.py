from typing import List, NamedTuple, Optional, Union

import tiktoken

from minerva.config import OPENAI_MODEL

TOKENIZER = (
  tiktoken.get_encoding("o200k_base")
  if OPENAI_MODEL.startswith("gpt-4.1-")
  else tiktoken.encoding_for_model(OPENAI_MODEL)
)


class Image(NamedTuple):
  url: str
  height_px: int
  width_px: int


class ImageContent(NamedTuple):
  images: list[Image]
  text: Optional[str] = None


ContentType = Union[str, ImageContent]


# it's a pessimistic image token size computation assuming the "auto" gpt-4o
# image detail mode
def get_image_token_count(image: Image) -> int:
  if image.width_px <= 512 and image.height_px <= 512:
    return 85
  max_tiles = (image.width_px // 512) * (image.height_px // 512)
  return 85 + 170 * max_tiles


def get_message_token_count(author: str, content: ContentType) -> int:
  if isinstance(content, str):
    return len(TOKENIZER.encode(f"{author}: {content}"))
  else:
    text_tokens = len(TOKENIZER.encode(f"{author}: {content.text or ''}"))
    image_tokens = sum(get_image_token_count(image) for image in content.images)
    return text_tokens + image_tokens


class Message:
  def __init__(self, author: str, content: ContentType):
    self.author = author
    self.content = content
    self.len_tokens = get_message_token_count(author, content)


class MessageHistory:
  def __init__(self, prompt_str: str, token_limit: int):
    self.token_limit = token_limit
    self.history: List[Message] = []
    self.current_tokens = len(TOKENIZER.encode(prompt_str))

  def add(self, message: Message):
    self.history.append(message)
    self.current_tokens += message.len_tokens
    while self.current_tokens > self.token_limit:
      deleted_message = self.history.pop(0)
      self.current_tokens -= deleted_message.len_tokens


def trim_by_token_size(message: str, token_limit: int, trimmed_suffix: str = "") -> str:
  tokens = TOKENIZER.encode(message)
  if len(tokens) <= token_limit:
    return message
  return TOKENIZER.decode(tokens[:token_limit]) + trimmed_suffix
