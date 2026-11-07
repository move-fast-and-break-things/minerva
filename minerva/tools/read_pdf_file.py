import base64
from io import BytesIO
from typing import Unpack

from pypdf import PdfReader, PdfWriter

from minerva.message_history import Message, PdfContent
from minerva.tools.tool_kwargs import DefaultToolKwargs

MAX_PAGES = 5


async def read_pdf_file(
  file_id: str, first_page: int, last_page: int, **kwargs: Unpack[DefaultToolKwargs]
) -> str:
  """Read pages from first_page to last_page (1-based, inclusive, at most 5 pages) of a PDF file
  shared in the chat by its file_id.

  The pages, including their text and images, are added to the conversation. To read further,
  call again with the next pages.
  """

  add_message_to_history = kwargs.get("add_message_to_history")
  ai_username = kwargs.get("ai_username")
  if add_message_to_history is None or ai_username is None:
    raise ValueError("add_message_to_history and ai_username are required")

  file = await kwargs["bot"].get_file(file_id)
  reader = PdfReader(BytesIO(await file.download_as_bytearray()))
  page_count = len(reader.pages)
  if not 1 <= first_page <= last_page <= page_count:
    raise ValueError(f"Pages must be within 1-{page_count}")
  if last_page - first_page + 1 > MAX_PAGES:
    raise ValueError(f"Read at most {MAX_PAGES} pages at once")

  writer = PdfWriter()
  writer.append(reader, (first_page - 1, last_page))
  pdf = BytesIO()
  writer.write(pdf)

  pages = f"pages {first_page}-{last_page} of {page_count}"
  add_message_to_history(
    Message(
      author=ai_username,
      content=PdfContent(
        data_url=f"data:application/pdf;base64,{base64.b64encode(pdf.getvalue()).decode()}",
        filename=f"{file_id}.pdf",
        page_count=last_page - first_page + 1,
        text=f"PDF file {file_id}, {pages}",
      ),
    )
  )
  return f"Added {pages} to the conversation."
