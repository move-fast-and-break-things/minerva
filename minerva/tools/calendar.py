from datetime import datetime, timedelta, timezone
from typing import NamedTuple, Optional
import icalendar
import recurring_ical_events
import httpx


class Event(NamedTuple):
  summary: str
  description: str
  meet_url: Optional[str]
  start: datetime
  end: datetime
  recurrence_rule: Optional[icalendar.vRecur]

  def __str__(self):
    return f"""Event: {self.summary} ({self.start.astimezone(tz=timezone.utc)} - {self.end.astimezone(tz=timezone.utc)})
Description: {self.description}
Video call: {self.meet_url}"""  # noqa: E501


def _trim_google_meet_links_from_description(description: str) -> str:
  """Remove Google Meet links and help from the event description

  Google Calendar adds text with the Google Meet link and Google Meet help to the
  end of the event description. This function removes that text to make the
  description less noisy. We extract the Google Meet event link from the
  x-google-conference property.
  """

  # Remove the last three lines from the description if the third to last contains
  # "Google Meet: https://"
  lines = description.splitlines()
  if len(lines) >= 3 and "Google Meet: https://" in lines[-3]:
    return "\n".join(lines[:-3]).strip()


def parse_ics(ics_content: str) -> icalendar.Calendar:
  return icalendar.Calendar.from_ical(ics_content)


def query_downloaded_calendar(
  cal: icalendar.Calendar,
  date_from: datetime,
  date_to: datetime,
) -> list[Event]:
  filtered_cal = recurring_ical_events.of(cal).between(date_from, date_to)
  events = []
  for component in filtered_cal:
    if component.name == "VEVENT":
      summary = str(component.get("summary"))
      description = _trim_google_meet_links_from_description(str(component.get("description", "")))
      x_google_conference = str(component.get("x-google-conference"))
      start = component.get("dtstart").dt
      end = component.get("dtend").dt
      rrule = component.get("rrule")
      events.append(Event(summary, description, x_google_conference, start, end, rrule))
  return events


def get_query_calendar(calendar_url: str):
  async def query_calendar(next_days: int) -> str:
    """Query the event calendar for the next `next_days` days.

    Args:
      next_days: The number of days to query the calendar for. Should be at least 1. The max 366.

    The function lists all dates and times in the UTC timezone"""
    if next_days < 1:
      raise ValueError("next_days must be at least 1")
    if next_days > 366:
      raise ValueError("next_days must be at most 366")

    async with httpx.AsyncClient() as client:
      calendar_request = await client.get(calendar_url)
    calendar_request.raise_for_status()
    ics_content = calendar_request.text
    cal = parse_ics(ics_content)

    events = query_downloaded_calendar(cal, datetime.now(), timedelta(days=next_days))
    if not events:
      return "No events found"
    return "\n\n".join([str(event) for event in events])

  return query_calendar
