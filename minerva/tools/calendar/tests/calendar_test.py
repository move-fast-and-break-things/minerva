from asyncio import sleep
from typing import Any, Callable, Optional
import icalendar
import pytest
from datetime import datetime, timezone
from os import path
from unittest.mock import Mock

from freezegun import freeze_time
from freezegun.api import FrozenDateTimeFactory

from minerva.tools.calendar.get_query_calendar import get_query_calendar

from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread

from minerva.tools.calendar.query_icalendar import query_icalendar, Event

DEFAULT_ICS_PATH = path.join(path.dirname(__file__), "fixtures", "test-calendar.ics")


def get_mock_tool_kwargs():
  """Create mock tool kwargs for testing."""
  return {
    "bot": Mock(),
    "chat_id": 12345,
    "topic_id": 0,
    "reply_to_message_id": 0,
  }


def getMockCalendarRequestHandler(ics_paths: Optional[list[str]] = None):
  # because http server recreates the request handler every time, we use this
  # request handler fabric to keep track of the variables which we want to share
  # between multiple requests
  ics_paths = ics_paths or [DEFAULT_ICS_PATH]
  requests_served_count = 0

  class MockCalendarRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
      nonlocal requests_served_count

      ics_path = ics_paths[requests_served_count if requests_served_count < len(ics_paths) else -1]

      with open(ics_path, "rb") as f:
        ics_content = f.read()

      self.send_response(200)
      self.send_header("Content-type", "text/calendar")
      self.end_headers()
      self.wfile.write(ics_content)

      requests_served_count += 1

  return MockCalendarRequestHandler


def with_http_file_server(ics_paths: Optional[list[str]] = None):
  def decorator(fn_async: Callable[..., Any]):
    async def wrapper(*args: tuple[Any, ...], **kwargs: dict[str, Any]):
      # using port 0 to get a random free port
      server_address = ("", 0)
      MockCalendarRequestHandler = getMockCalendarRequestHandler(ics_paths)
      httpd = HTTPServer(server_address, MockCalendarRequestHandler)
      server_thread = Thread(target=httpd.serve_forever)
      try:
        server_thread.start()
        await fn_async(*args, **kwargs, httpd=httpd)
      finally:
        httpd.shutdown()
        server_thread.join()

    return wrapper

  return decorator


def test_query_ics():
  ics_path = DEFAULT_ICS_PATH
  with open(ics_path) as f:
    ics = f.read()
    cal = icalendar.Calendar.from_ical(ics)

  events: list[Event] = query_icalendar(
    cal,
    datetime(2024, 9, 1, tzinfo=timezone.utc),
    datetime(2024, 9, 6, tzinfo=timezone.utc),
  )

  assert len(events) == 3

  print(events[0])

  assert events[0].summary == "Test multi-day"
  assert events[0].description == ""
  assert events[0].meet_url == "https://meet.google.com/broken-link-1"
  assert events[0].start == datetime(2024, 9, 4, 8, 45, tzinfo=timezone.utc)
  assert events[0].end == datetime(2024, 9, 5, 2, 0, tzinfo=timezone.utc)
  assert events[0].recurrence_rule is None

  assert events[1].summary == "Test event 1"
  assert events[1].description == "Test description.\n\nMultiline."
  assert events[1].meet_url == "https://meet.google.com/broken-link-2"
  assert events[1].start == datetime(2024, 9, 2, 10, 0, tzinfo=timezone.utc)
  assert events[1].end == datetime(2024, 9, 2, 11, 0, tzinfo=timezone.utc)
  assert events[1].recurrence_rule is None

  assert events[2].summary == "Test repeated"
  assert events[2].description == "And description"
  assert events[2].meet_url == "https://meet.google.com/broken-link-3"
  assert events[2].start.tzname() == "+04"
  assert events[2].end.tzname() == "+04"
  assert events[2].start == datetime(2024, 9, 5, 11, 0, tzinfo=events[2].start.tzinfo)
  assert events[2].end == datetime(2024, 9, 5, 12, 0, tzinfo=events[2].end.tzinfo)
  assert events[2].recurrence_rule is None


@freeze_time("2024-09-15")
@pytest.mark.asyncio
@with_http_file_server()
async def test_calendar_tool(httpd: HTTPServer):
  query_calendar = get_query_calendar(
    f"http://localhost:{httpd.server_port}/tests/fixtures/test-calendar.ics"
  )
  events: str = await query_calendar(14, **get_mock_tool_kwargs())

  assert (
    events
    == """Event: Test repeated (2024-09-19 07:00:00+00:00 - 2024-09-19 08:00:00+00:00)
Description: And description
Video call: https://meet.google.com/broken-link-3"""
  )


@freeze_time("2024-09-15")
@pytest.mark.asyncio
@with_http_file_server()
async def test_calendar_tool_no_events(httpd: HTTPServer):
  query_calendar = get_query_calendar(
    f"http://localhost:{httpd.server_port}/tests/fixtures/test-calendar.ics"
  )
  events: str = await query_calendar(1, **get_mock_tool_kwargs())

  assert events == """No events found"""


@freeze_time("2024-09-15")
@pytest.mark.asyncio
@with_http_file_server()
async def test_calendar_tool_crashes_if_zero_days(httpd: HTTPServer):
  query_calendar = get_query_calendar(
    f"http://localhost:{httpd.server_port}/tests/fixtures/test-calendar.ics"
  )

  try:
    await query_calendar(0, **get_mock_tool_kwargs())
    assert False
  except ValueError as e:
    assert str(e) == "next_days must be at least 1"


@freeze_time("2024-09-15")
@pytest.mark.asyncio
@with_http_file_server()
async def test_calendar_tool_crashes_if_too_many_days(httpd: HTTPServer):
  query_calendar = get_query_calendar(
    f"http://localhost:{httpd.server_port}/tests/fixtures/test-calendar.ics"
  )

  try:
    await query_calendar(367, **get_mock_tool_kwargs())
    assert False
  except ValueError as e:
    assert str(e) == "next_days must be at most 366"


@freeze_time("2024-09-15", as_arg=True, tick=True)
@pytest.mark.asyncio
@with_http_file_server(
  [
    DEFAULT_ICS_PATH,
    path.join(path.dirname(__file__), "fixtures", "test-calendar-updated.ics"),
  ]
)
async def test_calendar_tool_refetches_calendar(
  frozen_time: FrozenDateTimeFactory, httpd: HTTPServer
):
  query_calendar = get_query_calendar(
    f"http://localhost:{httpd.server_port}/tests/fixtures/test-calendar.ics"
  )
  # let the async refresh loop initialize
  await sleep(0.1)

  events: str = await query_calendar(14, **get_mock_tool_kwargs())

  assert (
    events
    == """Event: Test repeated (2024-09-19 07:00:00+00:00 - 2024-09-19 08:00:00+00:00)
Description: And description
Video call: https://meet.google.com/broken-link-3"""
  )

  frozen_time.tick(60 * 20)
  # let the async refresh loop refetch the calendar
  await sleep(0.1)

  events = await query_calendar(14, **get_mock_tool_kwargs())

  assert events == """No events found"""
