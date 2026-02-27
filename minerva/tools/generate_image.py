import base64
from io import BytesIO
from typing import Unpack
import httpx
from telegram import InputFile

from minerva.message_history import Image, ImageContent, Message
from minerva.tools.tool_kwargs import DefaultToolKwargs

DEFAULT_IMAGE_MODEL = "gpt-image-1"
DEFAULT_IMAGE_SIZE = "1024x1024"
DEFAULT_IMAGE_FORMAT = "png"


def _get_image_dimensions(size: str) -> tuple[int, int]:
  try:
    width_str, height_str = size.split("x", 1)
    return int(width_str), int(height_str)
  except Exception:
    return (1024, 1024)


async def generate_image(description: str, **kwargs: Unpack[DefaultToolKwargs]) -> str:
  """Generate an image using OpenAI and send it to the chat as photo + original file.

  Args:
    description: A detailed image description.
  """

  openai_client = kwargs.get("openai_client")
  if openai_client is None:
    raise ValueError("openai_client is required")

  ai_username = kwargs.get("ai_username")
  if not ai_username:
    raise ValueError("ai_username is required")

  add_message_to_history = kwargs.get("add_message_to_history")
  if add_message_to_history is None:
    raise ValueError("add_message_to_history is required")

  image_model = kwargs.get("openai_image_model", DEFAULT_IMAGE_MODEL)

  response = await openai_client.images.generate(
    model=image_model,
    prompt=description,
    size=DEFAULT_IMAGE_SIZE,
    output_format=DEFAULT_IMAGE_FORMAT,
  )

  if not response.data:
    raise ValueError("OpenAI returned no image data")

  first_image = response.data[0]
  image_b64 = getattr(first_image, "b64_json", None)
  if image_b64:
    image_bytes = base64.b64decode(image_b64)
  else:
    image_url = getattr(first_image, "url", None)
    if not image_url:
      raise ValueError("OpenAI returned image data in unexpected format")
    async with httpx.AsyncClient() as client:
      image_response = await client.get(image_url)
    image_response.raise_for_status()
    image_bytes = image_response.content
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
  filename = f"generated-image.{DEFAULT_IMAGE_FORMAT}"

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

  width_px, height_px = _get_image_dimensions(DEFAULT_IMAGE_SIZE)
  image_data_uri = f"data:image/{DEFAULT_IMAGE_FORMAT};base64,{image_b64}"
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

  return f"sent:{filename}:{len(image_bytes)}"
