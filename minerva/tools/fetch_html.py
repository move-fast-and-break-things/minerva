from typing import Any, cast
import httpx
import lxml
import lxml.html
import lxml.html.clean  # type: ignore
from playwright.async_api import async_playwright

# TIMEOUT_SEC = 2
TIMEOUT_SEC = 10  # give more time for JS sites

LXML_CLEANER = cast(
  Any,
  lxml.html.clean.Cleaner(
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
  ),
)


async def fetch_html(url: str) -> str:
  """Take an url and return clean HTML content of the page, without JS, styles, or attributes.

  Use this tool when you need to visit a website and fetch its content.
  """

  # async with httpx.AsyncClient() as client:
  #   response = await client.get(
  #     url,
  #     timeout=TIMEOUT_SEC,
  #     headers={
  #       "User-Agent": "Minerva AI Bot - (https://github.com/move-fast-and-break-things/minerva)"
  #     },
  #     follow_redirects=True,
  #   )
  #   response.raise_for_status()

  #   # raise if the response is not text
  #   if not response.headers.get("content-type", "").startswith("text/"):
  #     raise ValueError(f"Unexpected content type: {response.headers.get('content-type')}")

  #   return clean_html(response.text)

  async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.set_default_timeout(TIMEOUT_SEC * 1000)

        # Set a user agent like before
        await page.set_extra_http_headers({
            "User-Agent": "Minerva AI Bot - (https://github.com/move-fast-and-break-things/minerva)"
        })

        await page.goto(url, wait_until="networkidle")  # wait until JS is mostly done
        content = await page.content()
        await browser.close()

    return clean_html(content)


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
