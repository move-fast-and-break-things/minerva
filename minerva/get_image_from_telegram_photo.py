import base64
from telegram import Bot, PhotoSize

from minerva.message_history import Image


async def get_image_from_telegram_photo(bot: Bot, photo: tuple[PhotoSize, ...]) -> Image:
  sorted_photo_sizes = sorted(photo, key=lambda p: p.width)
  largest_photo_size = sorted_photo_sizes[-1]
  photo_object = await bot.get_file(largest_photo_size.file_id)
  photo_bytes = await photo_object.download_as_bytearray()
  photo_base64 = f"data:image/jpeg;base64,{base64.b64encode(photo_bytes).decode('utf-8')}"
  return Image(
    url=photo_base64,
    height_px=largest_photo_size.height,
    width_px=largest_photo_size.width,
  )
