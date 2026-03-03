from unittest.mock import AsyncMock
from typing import Any, cast

import pytest

from minerva.tools.fetch_html import (
  PlaywrightHtmlFetcher,
  clean_html,
  close_fetch_html_browser,
  fetch_html,
)


def test_clean_html():
  html = """<html>
  <head>
    <title>Test</title>
    <script>alert('Hello, World!')</script>
    <style>body { background-color: red; }</style>
  </head>
  <body>
    <h1 class="test-class">Hello, World!</h1>
    <p>This is a test.</p>
  </body>
</html>"""
  expected_clean_html = """<title>Test</title><h1>Hello, World!</h1><p>This is a test.</p>"""
  assert clean_html(html) == expected_clean_html


def test_clean_html_doesnt_destroy_plaintext_files():
  text = """This is a plaintext file."""
  expected_clean_text = """This is a plaintext file."""
  assert clean_html(text) == expected_clean_text


@pytest.mark.asyncio
async def test_fetch_html_uses_rendered_html_from_playwright(monkeypatch: pytest.MonkeyPatch):
  mock_fetch_rendered_html = AsyncMock(
    return_value="""
<html>
  <head><script>console.log('x')</script></head>
  <body><h1 class="headline">Rendered</h1></body>
</html>
"""
  )
  monkeypatch.setattr(
    "minerva.tools.fetch_html.PLAYWRIGHT_HTML_FETCHER.fetch_rendered_html",
    mock_fetch_rendered_html,
  )

  tool_kwargs: dict[str, Any] = {
    "bot": cast(Any, None),
    "chat_id": 1,
    "topic_id": 1,
    "reply_to_message_id": None,
  }
  result = await fetch_html("https://example.com", **tool_kwargs)

  assert result == "<h1>Rendered</h1>"
  assert mock_fetch_rendered_html.await_count == 1


@pytest.mark.asyncio
async def test_close_fetch_html_browser_calls_fetcher_close(monkeypatch: pytest.MonkeyPatch):
  mock_close = AsyncMock()
  monkeypatch.setattr(
    "minerva.tools.fetch_html.PLAYWRIGHT_HTML_FETCHER.close",
    mock_close,
  )

  await close_fetch_html_browser()

  assert mock_close.await_count == 1


@pytest.mark.asyncio
async def test_page_is_closed_on_content_type_error(monkeypatch: pytest.MonkeyPatch):
  mock_response = AsyncMock()
  mock_response.all_headers = AsyncMock(return_value={"content-type": "application/pdf"})

  mock_page = AsyncMock()
  mock_page.goto = AsyncMock(return_value=mock_response)

  mock_browser = AsyncMock()
  mock_browser.new_page = AsyncMock(return_value=mock_page)

  monkeypatch.setattr(
    "minerva.tools.fetch_html._get_playwright_api",
    lambda: (None, Exception, Exception),
  )

  fetcher = PlaywrightHtmlFetcher()
  fetcher._browser = mock_browser

  with pytest.raises(ValueError, match="Unexpected content type"):
    await fetcher.fetch_rendered_html("https://example.com/file.pdf")

  mock_page.close.assert_awaited_once()
