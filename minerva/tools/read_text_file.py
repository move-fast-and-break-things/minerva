from typing import Unpack

from minerva.tools.tool_kwargs import DefaultToolKwargs

CHUNK_CHARS = 4000


async def read_text_file(file_id: str, offset: int, **kwargs: Unpack[DefaultToolKwargs]) -> str:
  """Read a text file shared in the chat by its file_id, starting from the character offset.

  Returns up to 4000 characters and the file's total length. To read further, call again with a
  larger offset.
  """

  file = await kwargs["bot"].get_file(file_id)
  text = (await file.download_as_bytearray()).decode("utf-8", errors="replace")
  start = min(offset, len(text))
  end = min(start + CHUNK_CHARS, len(text))
  return f"chars {start}-{end} of {len(text)}:\n{text[start:end]}"
