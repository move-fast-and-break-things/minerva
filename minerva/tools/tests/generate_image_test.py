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
  def __init__(self, response: Any):
    self.response = response
    self.calls: list[dict[str, Any]] = []

  async def generate(self, **kwargs: Any):
    self.calls.append(kwargs)
    return self.response


class FakeOpenAIClient:
  def __init__(self, response: Any):
    self.images = FakeImagesClient(response)


class FakeBot:
  def __init__(self):
    self.send_photo = AsyncMock()
    self.send_document = AsyncMock()


class FakeHttpxResponse:
  def __init__(self, content: bytes, content_type: str = "image/png"):
    self.content = content
    self.headers = {"content-type": content_type}

  def raise_for_status(self):
    return None


class FakeHttpxClient:
  def __init__(self, content: bytes, content_type: str = "image/png"):
    self.content = content
    self.content_type = content_type
    self.requested_url: str | None = None
    self.request_timeout: int | None = None

  async def __aenter__(self):
    return self

  async def __aexit__(self, exc_type: Any, exc: Any, tb: Any):
    return None

  async def get(self, url: str, **kwargs: Any):
    self.requested_url = url
    self.request_timeout = kwargs.get("timeout")
    return FakeHttpxResponse(content=self.content, content_type=self.content_type)


def get_default_tool_kwargs():
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


@pytest.mark.asyncio
async def test_generate_image_downloads_image_when_only_url_is_returned(monkeypatch: pytest.MonkeyPatch):
  response = SimpleNamespace(
    data=[SimpleNamespace(b64_json=None, url="https://example.com/image.png")],
  )
  openai_client = FakeOpenAIClient(response=response)
  kwargs, _, history = get_default_tool_kwargs()
  kwargs["openai_client"] = openai_client

  image_bytes = b"fake-png-bytes"
  fake_httpx_client = FakeHttpxClient(content=image_bytes)
  async_client_kwargs: dict[str, Any] = {}

  def fake_async_client(**kwargs: Any):
    async_client_kwargs.update(kwargs)
    return fake_httpx_client

  monkeypatch.setattr("minerva.tools.generate_image.httpx.AsyncClient", fake_async_client)

  await generate_image("test", **kwargs)

  assert fake_httpx_client.requested_url == "https://example.com/image.png"
  assert fake_httpx_client.request_timeout == 10
  assert async_client_kwargs["follow_redirects"] is True
  assert len(history) == 1


@pytest.mark.asyncio
async def test_generate_image_fails_when_image_url_has_unexpected_content_type(
  monkeypatch: pytest.MonkeyPatch,
):
  response = SimpleNamespace(
    data=[SimpleNamespace(b64_json=None, url="https://example.com/image.png")],
  )
  openai_client = FakeOpenAIClient(response=response)
  kwargs, _, _ = get_default_tool_kwargs()
  kwargs["openai_client"] = openai_client

  fake_httpx_client = FakeHttpxClient(content=b"{}", content_type="application/json")
  monkeypatch.setattr(
    "minerva.tools.generate_image.httpx.AsyncClient",
    lambda **_kwargs: fake_httpx_client,
  )

  with pytest.raises(ValueError, match="Unexpected content type for generated image"):
    await generate_image("test", **kwargs)
