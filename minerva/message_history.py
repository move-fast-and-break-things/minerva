from typing import List

import tiktoken

from minerva.config import OPENAI_MODEL

TOKENIZER = tiktoken.encoding_for_model(OPENAI_MODEL)
HISTORY_MAX_TOKENS = 8192


class Message:
  def __init__(self, author: str, content: str):
    self.author = author
    self.content = content
    self.len_tokens = len(TOKENIZER.encode(str(self)))

  def __str__(self):
    return f"{self.author}: {self.content}"


class MessageHistory:
  def __init__(self, prompt_str: str, token_limit=HISTORY_MAX_TOKENS):
    self.token_limit = token_limit
    self.history: List[Message] = []
    self.current_tokens = len(TOKENIZER.encode(prompt_str))

  def add(self, message: Message):
    self.history.append(message)
    self.current_tokens += message.len_tokens
    while self.current_tokens > self.token_limit:
      deleted_message = self.history.pop(0)
      self.current_tokens -= deleted_message.len_tokens

  def __str__(self):
    return "\n".join(str(message) for message in self.history)


def trim_by_token_size(message: str, token_limit: int, trimmed_suffix: str = "") -> str:
  tokens = TOKENIZER.encode(message)
  if len(tokens) <= token_limit:
    return message
  return TOKENIZER.decode(tokens[:token_limit]) + trimmed_suffix
