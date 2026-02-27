from types import SimpleNamespace
from unittest.mock import AsyncMock
from typing import Any

import pytest

from minerva.message_history import ImageContent
from minerva.tools.generate_image import generate_image

ONE_PIXEL_PNG_B64 = (
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jG90AAAAASUVORK5CYII="
)


class FakeImagesClient:
  def __init__(self, response: object):
    self.response = response
    self.calls: list[dict[str, object]] = []

  async def generate(self, **kwargs: object):
    self.calls.append(kwargs)
    return self.response


class FakeOpenAIClient:
  def __init__(self, response: object):
    self.images = FakeImagesClient(response)


class FakeBot:
  def __init__(self):
    self.send_photo = AsyncMock()
    self.send_document = AsyncMock()


def get_default_tool_kwargs() -> tuple[dict[str, Any], FakeBot, list[Any]]:
  bot = FakeBot()
  history: list[Any] = []
  kwargs: dict[str, Any] = {
    "bot": bot,
    "chat_id": 1,
    "topic_id": 2,
    "reply_to_message_id": 3,
    "ai_username": "minerva",
    "add_message_to_history": history.append,
  }
  return kwargs, bot, history


@pytest.mark.asyncio
async def test_generate_image():
  response = SimpleNamespace(
    data=[
      SimpleNamespace(
        b64_json=ONE_PIXEL_PNG_B64,
      )
    ]
  )
  openai_client = FakeOpenAIClient(response=response)
  kwargs, bot, history = get_default_tool_kwargs()
  kwargs["openai_client"] = openai_client

  result = await generate_image("red square", **kwargs)

  assert result.startswith("sent:generated-image.png:")
  assert bot.send_photo.await_count == 1
  assert bot.send_document.await_count == 1

  photo_await_args = bot.send_photo.await_args
  assert photo_await_args is not None
  photo_kwargs = photo_await_args.kwargs
  assert photo_kwargs["chat_id"] == 1
  assert photo_kwargs["message_thread_id"] == 2
  assert photo_kwargs["reply_to_message_id"] == 3

  assert len(history) == 1
  message = history[0]
  assert message.author == "minerva"
  assert isinstance(message.content, ImageContent)
  assert message.content.text == "Generated image."
  assert len(message.content.images) == 1
  image = message.content.images[0]
  assert image.url == f"data:image/png;base64,{ONE_PIXEL_PNG_B64}"
  assert image.width_px == 1024
  assert image.height_px == 1024

  call = openai_client.images.calls[0]
  assert call["prompt"] == "red square"
  assert call["model"] == "gpt-image-1"
  assert call["size"] == "1024x1024"
  assert call["response_format"] == "b64_json"
  assert call["output_format"] == "png"


@pytest.mark.asyncio
async def test_generate_image_fails_when_openai_client_is_missing():
  kwargs, _, _ = get_default_tool_kwargs()

  with pytest.raises(ValueError, match="openai_client is required"):
    await generate_image("test", **kwargs)


@pytest.mark.asyncio
async def test_generate_image_fails_when_b64_json_is_missing():
  response = SimpleNamespace(
    data=[SimpleNamespace(b64_json=None)],
  )
  openai_client = FakeOpenAIClient(response=response)
  kwargs, _, _ = get_default_tool_kwargs()
  kwargs["openai_client"] = openai_client

  with pytest.raises(ValueError, match="unexpected format"):
    await generate_image("test", **kwargs)
