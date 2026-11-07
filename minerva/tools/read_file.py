from io import BytesIO
from typing import Unpack

from pypdf import PdfReader

from minerva.tools.tool_kwargs import DefaultToolKwargs

CHUNK_CHARS = 4000


async def read_file(file_id: str, offset: int, **kwargs: Unpack[DefaultToolKwargs]) -> str:
  """Read a text or PDF file shared in the chat by its file_id, starting from the character offset.

  Returns up to 4000 characters and the file's total length. To read further, call again with a
  larger offset.
  """

  file = await kwargs["bot"].get_file(file_id)
  data = await file.download_as_bytearray()
  text = (
    "\n".join(page.extract_text() for page in PdfReader(BytesIO(data)).pages)
    if data.startswith(b"%PDF")
    else data.decode("utf-8", errors="replace")
  )
  start = min(offset, len(text))
  end = min(start + CHUNK_CHARS, len(text))
  return f"chars {start}-{end} of {len(text)}:\n{text[start:end]}"
