import asyncio
from typing import Unpack
import lxml
import lxml.html
from lxml.html import clean
from playwright.async_api import (
  Error as PlaywrightError,
  TimeoutError as PlaywrightTimeoutError,
  async_playwright,
)

from minerva.tools.tool_kwargs import DefaultToolKwargs  # type: ignore

DEFAULT_MAX_ACTIVE_TABS = 3
NAVIGATION_TIMEOUT_MS = 10_000
NETWORK_IDLE_TIMEOUT_MS = 2_000
MINERVA_USER_AGENT = "Minerva AI Bot"

LXML_CLEANER = clean.Cleaner(
  scripts=True,
  javascript=True,
  comments=True,
  style=True,
  inline_style=True,
  meta=True,
  page_structure=False,
  processing_instructions=True,
  annoying_tags=True,
  remove_tags=["html", "head", "body"],
  kill_tags=["header", "footer"],
  remove_unknown_tags=True,
  # remove all attrs
  safe_attrs_only=True,
  safe_attrs=[],
)


def _is_text_content_type(content_type: str) -> bool:
  normalized = content_type.lower()
  return normalized.startswith("text/") or "application/xhtml+xml" in normalized


class PlaywrightHtmlFetcher:
  def __init__(self, max_active_tabs: int = DEFAULT_MAX_ACTIVE_TABS):
    self._tabs_semaphore = asyncio.Semaphore(max_active_tabs)
    self._startup_lock = asyncio.Lock()
    self._browser = None
    self._playwright = None

  async def _ensure_browser(self):
    if self._browser is not None:
      return self._browser

    async with self._startup_lock:
      if self._browser is not None:
        return self._browser

      pw = await async_playwright().start()
      try:
        browser = await pw.chromium.launch(headless=True)
      except Exception:
        await pw.stop()
        raise
      self._playwright = pw
      self._browser = browser
      return self._browser

  async def close(self):
    if self._browser is not None:
      await self._browser.close()
      self._browser = None
    if self._playwright is not None:
      await self._playwright.stop()
      self._playwright = None

  async def fetch_rendered_html(self, url: str) -> str:
    browser = await self._ensure_browser()

    async with self._tabs_semaphore:
      page = await browser.new_page(user_agent=MINERVA_USER_AGENT)
      try:
        try:
          response = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=NAVIGATION_TIMEOUT_MS,
          )
        except PlaywrightError as err:
          raise ValueError(f"Failed to load page {url}: {err}") from err

        if response is None:
          raise ValueError("Failed to load page: empty browser response")

        if not response.ok:
          raise ValueError(f"HTTP {response.status} for {url}")

        headers = await response.all_headers()
        content_type = headers.get("content-type", "")
        if content_type and not _is_text_content_type(content_type):
          raise ValueError(f"Unexpected content type: {content_type}")

        try:
          # Dynamic websites may still be hydrating after DOM content is loaded.
          await page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_TIMEOUT_MS)
        except PlaywrightTimeoutError:
          pass

        return await page.content()
      finally:
        await page.close()


PLAYWRIGHT_HTML_FETCHER = PlaywrightHtmlFetcher()


async def fetch_html(url: str, **kwargs: Unpack[DefaultToolKwargs]) -> str:
  """Take an url and return clean HTML content of the page, without JS, styles, or attributes.

  Use this tool when you need to visit a website and fetch its content.
  """
  html = await PLAYWRIGHT_HTML_FETCHER.fetch_rendered_html(url)
  return clean_html(html)


async def close_fetch_html_browser() -> None:
  await PLAYWRIGHT_HTML_FETCHER.close()


def clean_html(html: str) -> str:
  parsed_html = lxml.html.fromstring(html)
  clean_html = LXML_CLEANER.clean_html(parsed_html)

  # remove all newlines
  for element in clean_html.iter():
    element.tail = None
    if element.text:
      element.text = element.text.strip()

  return (clean_html.text or "") + "".join(
    [lxml.html.tostring(node, encoding="unicode") for node in clean_html.iterchildren()]
  )
