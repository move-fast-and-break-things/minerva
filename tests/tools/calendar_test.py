import pytest
from datetime import datetime, timezone
from os import path

from freezegun import freeze_time

from minerva.tools.calendar import query_calendar, parse_ics, CalendarTool

from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread


def with_http_file_server(fn_async):
  async def wrapper(*args, **kwargs):
    # using port 0 to get a random free port
    server_address = ("", 0)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    server_thread = Thread(target=httpd.serve_forever)
    try:
      server_thread.start()
      await fn_async(*args, **kwargs, httpd=httpd)
    finally:
      httpd.shutdown()
      server_thread.join()
  return wrapper


def test_query_ics():
  ics_path = path.join(path.dirname(__file__), "..", "fixtures", "test-calendar.ics")
  with open(ics_path) as f:
    ics = f.read()
    cal = parse_ics(ics)

  events = query_calendar(
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
@with_http_file_server
async def test_calendar_tool(httpd: HTTPServer):
  calendar_tool = CalendarTool(
      f"http://localhost:{httpd.server_port}/tests/fixtures/test-calendar.ics")
  events = await calendar_tool.query(14)

  assert events == """Event: Test repeated (2024-09-19 07:00:00+00:00 - 2024-09-19 08:00:00+00:00)
Description: And description
Video call: https://meet.google.com/broken-link-3"""


@freeze_time("2024-09-15")
@pytest.mark.asyncio
@with_http_file_server
async def test_calendar_tool_no_events(httpd: HTTPServer):
  calendar_tool = CalendarTool(
      f"http://localhost:{httpd.server_port}/tests/fixtures/test-calendar.ics")
  events = await calendar_tool.query(1)

  assert events == """No events found"""


@freeze_time("2024-09-15")
@pytest.mark.asyncio
@with_http_file_server
async def test_calendar_tool_crashes_if_zero_days(httpd: HTTPServer):
  calendar_tool = CalendarTool(
      f"http://localhost:{httpd.server_port}/tests/fixtures/test-calendar.ics")

  try:
    await calendar_tool.query(0)
    assert False
  except ValueError as e:
    assert str(e) == "next_days must be at least 1"


@freeze_time("2024-09-15")
@pytest.mark.asyncio
@with_http_file_server
async def test_calendar_tool_crashes_if_too_many_days(httpd: HTTPServer):
  calendar_tool = CalendarTool(
      f"http://localhost:{httpd.server_port}/tests/fixtures/test-calendar.ics")

  try:
    await calendar_tool.query(367)
    assert False
  except ValueError as e:
    assert str(e) == "next_days must be at most 366"
