from datetime import datetime, timedelta
from typing import Unpack
import icalendar
import httpx

from minerva.tools.calendar.query_icalendar import query_icalendar
from minerva.tools.tool_kwargs import DefaultToolKwargs


def get_query_calendar(calendar_url: str):
  async def query_calendar(next_days: int, **kwargs: Unpack[DefaultToolKwargs]) -> str:
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
    cal = icalendar.Calendar.from_ical(ics_content)

    events = query_icalendar(cal, datetime.now(), timedelta(days=next_days))
    if not events:
      return "No events found"
    return "\n\n".join([str(event) for event in events])

  return query_calendar
