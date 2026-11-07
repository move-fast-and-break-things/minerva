import base64
from io import BytesIO
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pypdf import PdfReader, PdfWriter

from minerva.tools.read_pdf_file import read_pdf_file


def get_tool_kwargs(page_count: int) -> dict[str, Any]:
  writer = PdfWriter()
  for _ in range(page_count):
    writer.add_blank_page(width=612, height=792)
  pdf = BytesIO()
  writer.write(pdf)

  file = AsyncMock()
  file.download_as_bytearray.return_value = bytearray(pdf.getvalue())
  bot = AsyncMock()
  bot.get_file.return_value = file
  return {"bot": bot, "chat_id": 1, "topic_id": 2, "reply_to_message_id": 3}


@pytest.mark.asyncio
async def test_read_pdf_file_returns_requested_pages():
  kwargs = get_tool_kwargs(4)

  result = await read_pdf_file("file-id", 2, 3, **kwargs)

  kwargs["bot"].get_file.assert_awaited_once_with("file-id")
  assert result.text == "PDF file file-id, pages 2-3 of 4"
  assert result.page_count == 2
  pdf = base64.b64decode(result.data_url.removeprefix("data:application/pdf;base64,"))
  assert len(PdfReader(BytesIO(pdf)).pages) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("first_page, last_page", [(0, 1), (2, 1), (1, 9), (1, 6)])
async def test_read_pdf_file_rejects_invalid_page_ranges(first_page: int, last_page: int):
  with pytest.raises(ValueError):
    await read_pdf_file("file-id", first_page, last_page, **get_tool_kwargs(8))
