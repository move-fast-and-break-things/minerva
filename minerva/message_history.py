from typing import List

import tiktoken

from minerva.env import OPENAI_MODEL
from minerva.prompt import AI_USERNAME_PLACEHOLDER, PROMPT

TOKENIZER = tiktoken.encoding_for_model(OPENAI_MODEL)
HISTORY_MAX_TOKENS = 4096


class Message:
  def __init__(self, author, content):
    self.author = author
    self.content = content
    self.len_tokens = len(TOKENIZER.encode(str(self)))

  def __str__(self):
    return f"{self.author}: {self.content}"


class MessageHistory:
  def __init__(self, bot_username, token_limit=HISTORY_MAX_TOKENS):
    self.bot_username = bot_username
    self.token_limit = token_limit
    self.history: List[Message] = []
    self.current_tokens = len(TOKENIZER.encode(self.format_prompt()))

  def add(self, message: Message):
    self.history.append(message)
    self.current_tokens += message.len_tokens
    while self.current_tokens > self.token_limit:
      deleted_message = self.history.pop(0)
      self.current_tokens -= deleted_message.len_tokens

  def format_prompt(self):
    prompt = PROMPT.replace(AI_USERNAME_PLACEHOLDER, str(self.bot_username))
    for message in self.history:
      prompt += f"\n{message}\n"
    prompt += "\nYour response:"
    return prompt
