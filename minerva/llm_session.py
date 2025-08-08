import json
from openai import AsyncOpenAI

from minerva.format_chat_history_for_openai import format_chat_history_for_openai
from minerva.message_history import Message, MessageHistory


class LlmSession:
  def __init__(
    self,
    ai_username: str,
    openai_client: AsyncOpenAI,
    openai_model_name: str,
    max_completion_tokens: int,
    max_history_tokens: int,
    prompt: str,
  ):
    self.ai_username = ai_username
    self.prompt = prompt
    self.max_completion_tokens = max_completion_tokens
    self.openai_client = openai_client
    self.openai_model_name = openai_model_name
    self.history = MessageHistory(
      prompt_str=prompt,
      token_limit=max_history_tokens,
    )

  def add_message(self, message: Message):
    self.history.add(message)

  async def create_response(self, user_id: str) -> str:
    """
    Create a response from the model using the current history and prompt.

    Args:
      user_id (str): The id of the user that triggered the response creation.

    Returns:
      str: The model's response.
    """

    print(f"OpenAPI prompt:\n{self.prompt}\n\n")
    messages = format_chat_history_for_openai(self.prompt, self.history)
    print(f"Chat history:\n{json.dumps(messages, indent=2)}\n\n")

    response = await self.openai_client.chat.completions.create(
      model=self.openai_model_name,
      messages=messages,
      temperature=1,
      max_completion_tokens=self.max_completion_tokens,
      user=user_id,
    )

    answer = response.choices[0].message.content
    if not answer:
      raise Exception("Unexpected: OpenAI response is empty")

    self.add_message(
      Message(
        author=self.ai_username,
        content=answer,
      )
    )

    return answer
