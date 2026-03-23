import base64
from io import BytesIO
from typing import Any, Callable, Literal, Unpack
import httpx
from telegram import InputFile

from minerva.message_history import Image, ImageContent, Message
from minerva.tools.tool_kwargs import DefaultToolKwargs
from minerva.config import OPENAI_IMAGE_MODEL

DEFAULT_IMAGE_ASPECT = "square"
DEFAULT_IMAGE_FORMAT = "png"
IMAGE_DOWNLOAD_TIMEOUT_SEC = 10

Aspect = Literal["square", "portrait", "landscape"]

aspects = {
    "square": (1024, 1024),
    "portrait": (1024, 1536),
    "landscape": (1536, 1024),
}

def _get_required_runtime_data(
  kwargs: DefaultToolKwargs,
) -> tuple[Any, str, Callable[[Message], None]]:
  openai_client = kwargs.get("openai_client")
  if openai_client is None:
    raise ValueError("openai_client is required")

  ai_username = kwargs.get("ai_username")
  if not ai_username:
    raise ValueError("ai_username is required")

  add_message_to_history = kwargs.get("add_message_to_history")
  if add_message_to_history is None:
    raise ValueError("add_message_to_history is required")

  return openai_client, ai_username, add_message_to_history



async def _request_image(openai_client: Any, description: str, aspect: Aspect, image_model: str) -> Any:
  response = await openai_client.images.generate(
    model=image_model,
    prompt=description,
    size=f"{'x'.join(map(str, aspects.get(aspect, aspects[DEFAULT_IMAGE_ASPECT])))}",
    output_format=DEFAULT_IMAGE_FORMAT,
  )
  if not response.data:
    raise ValueError("OpenAI returned no image data")
  return response.data[0]


async def _download_image_bytes(image_url: str) -> tuple[bytes, str]:
  async with httpx.AsyncClient(follow_redirects=True) as client:
    image_response = await client.get(image_url, timeout=IMAGE_DOWNLOAD_TIMEOUT_SEC)
  image_response.raise_for_status()

  raw_content_type = image_response.headers.get("content-type", "")
  content_type = raw_content_type.split(";", 1)[0].strip().lower()
  if not content_type.startswith("image/"):
    raise ValueError(f"Unexpected content type for generated image: {raw_content_type!r}")
  image_format = content_type.removeprefix("image/")
  return image_response.content, image_format


async def _resolve_image_data(first_image: Any) -> tuple[bytes, str, str]:
  image_b64 = getattr(first_image, "b64_json", None)
  if image_b64:
    return base64.b64decode(image_b64, validate=True), image_b64, DEFAULT_IMAGE_FORMAT

  image_url = getattr(first_image, "url", None)
  if not image_url:
    raise ValueError("OpenAI returned image data in unexpected format")

  image_bytes, image_format = await _download_image_bytes(image_url)
  return image_bytes, base64.b64encode(image_bytes).decode("utf-8"), image_format


async def _send_generated_image_to_telegram(
  kwargs: DefaultToolKwargs,
  filename: str,
  image_bytes: bytes,
) -> None:
  image_file = InputFile(BytesIO(image_bytes), filename=filename)
  await kwargs["bot"].send_photo(
    chat_id=kwargs["chat_id"],
    photo=image_file,
    message_thread_id=kwargs["topic_id"],
    reply_to_message_id=kwargs["reply_to_message_id"],
  )

  document_file = InputFile(BytesIO(image_bytes), filename=filename)
  await kwargs["bot"].send_document(
    chat_id=kwargs["chat_id"],
    document=document_file,
    message_thread_id=kwargs["topic_id"],
    reply_to_message_id=kwargs["reply_to_message_id"],
  )


def _add_generated_image_to_history(
  add_message_to_history: Callable[[Message], None],
  ai_username: str,
  image_b64: str,
  image_format: str,
  aspect: Aspect,
) -> None:
  width_px, height_px = aspects.get(aspect, aspects[DEFAULT_IMAGE_ASPECT])
  image_data_uri = f"data:image/{image_format};base64,{image_b64}"
  add_message_to_history(
    Message(
      author=ai_username,
      content=ImageContent(
        images=[
          Image(
            url=image_data_uri,
            width_px=width_px,
            height_px=height_px,
          )
        ],
        text="Generated image.",
      ),
    )
  )

async def generate_image(description: str, aspect: Aspect = "square", **kwargs: Unpack[DefaultToolKwargs]) -> str:
  """Generate an image using OpenAI and send it to the chat as photo + original file.

  Args:
    description: A detailed image description.
    aspect: The aspect ratio of the generated image. Should be "square", "portrait", or "landscape".

  If the user asks for a specific resolution, choose the closest aspect and inform the user about what you did in the response.
  """

  openai_client, ai_username, add_message_to_history = _get_required_runtime_data(kwargs)
  first_image = await _request_image(openai_client, description, aspect, OPENAI_IMAGE_MODEL)
  image_bytes, image_b64, image_format = await _resolve_image_data(first_image)

  filename = f"generated-image.{image_format}"
  await _send_generated_image_to_telegram(kwargs, filename, image_bytes)
  _add_generated_image_to_history(add_message_to_history, ai_username, image_b64, image_format, aspect)

  return f"sent:{filename}:{len(image_bytes)}"
