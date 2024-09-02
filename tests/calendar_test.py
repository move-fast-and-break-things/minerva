from datetime import datetime, timezone
from os import path

import icalendar

from minerva.calendar import parse_ics


def test_parse_ics():
  ics_path = path.join(path.dirname(__file__), "fixtures", "test-calendar.ics")
  with open(ics_path) as f:
    ics = f.read()
    events = parse_ics(ics)

  assert len(events) == 3

  print(events[0])

  assert events[0].summary == "Test multi-day"
  assert events[0].description == ""
  assert events[0].x_google_conference == "https://meet.google.com/broken-link-1"
  assert events[0].start == datetime(2024, 9, 4, 8, 45, tzinfo=timezone.utc)
  assert events[0].end == datetime(2024, 9, 5, 2, 0, tzinfo=timezone.utc)
  assert events[0].recurrence_rule is None

  assert events[1].summary == "Test event 1"
  assert events[1].description == "Test description.\n\nMultiline."
  assert events[1].x_google_conference == "https://meet.google.com/broken-link-2"
  assert events[1].start == datetime(2024, 9, 2, 10, 0, tzinfo=timezone.utc)
  assert events[1].end == datetime(2024, 9, 2, 11, 0, tzinfo=timezone.utc)
  assert events[1].recurrence_rule is None

  assert events[2].summary == "Test repeated"
  assert events[2].description == "And description"
  assert events[2].x_google_conference == "https://meet.google.com/broken-link-3"
  assert events[2].start.tzname() == "+04"
  assert events[2].end.tzname() == "+04"
  assert events[2].start == datetime(2024, 9, 5, 11, 0, tzinfo=events[2].start.tzinfo)
  assert events[2].end == datetime(2024, 9, 5, 12, 0, tzinfo=events[2].end.tzinfo)
  assert events[2].recurrence_rule == icalendar.vRecur(
      FREQ=["WEEKLY"],
      INTERVAL=[2],
      WKST=["SU"],
      BYDAY=["TH"],
  )
