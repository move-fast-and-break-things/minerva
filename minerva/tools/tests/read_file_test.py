from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from minerva.tools.read_file import CHUNK_CHARS, read_file


def get_tool_kwargs(content: bytes) -> dict[str, Any]:
  file = AsyncMock()
  file.download_as_bytearray.return_value = bytearray(content)
  bot = AsyncMock()
  bot.get_file.return_value = file
  return {"bot": bot, "chat_id": 1, "topic_id": 2, "reply_to_message_id": 3}


@pytest.mark.asyncio
async def test_read_file_reads_whole_small_file():
  kwargs = get_tool_kwargs("héllo".encode())

  result = await read_file("file-id", 0, **kwargs)

  assert result == "chars 0-5 of 5:\nhéllo"
  kwargs["bot"].get_file.assert_awaited_once_with("file-id")


@pytest.mark.asyncio
async def test_read_file_reads_chunks_from_offset():
  text = "a" * CHUNK_CHARS + "b" * 10
  kwargs = get_tool_kwargs(text.encode())

  first = await read_file("file-id", 0, **kwargs)
  second = await read_file("file-id", CHUNK_CHARS, **kwargs)

  assert first == f"chars 0-{CHUNK_CHARS} of {len(text)}:\n{'a' * CHUNK_CHARS}"
  assert second == f"chars {CHUNK_CHARS}-{len(text)} of {len(text)}:\n{'b' * 10}"


@pytest.mark.asyncio
async def test_read_file_handles_offset_past_end():
  kwargs = get_tool_kwargs(b"abc")

  result = await read_file("file-id", 10, **kwargs)

  assert result == "chars 3-3 of 3:\n"


@pytest.mark.asyncio
async def test_read_file_extracts_pdf_text():
  kwargs = get_tool_kwargs((Path(__file__).parent / "fixtures" / "hello.pdf").read_bytes())

  result = await read_file("file-id", 0, **kwargs)

  assert result == "chars 0-9 of 9:\nHello PDF"
