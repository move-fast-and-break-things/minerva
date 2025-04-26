import asyncio
import httpx
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional, Any, Dict, Set
import icalendar

from minerva.tools.calendar.query_icalendar import Event, query_icalendar


class MeetingReminderer:
  """Class for managing meeting reminders from a calendar."""

  def __init__(
    self,
    send_message_to_agent: Callable[[str], Any],
    calendar_url: str,
    check_interval_minutes: int = 15,
    reminder_minutes_before: int = 15,
  ):
    """
    Initialize a MeetingReminderer instance.

    Args:
      send_message_to_agent: Function to send messages to the agent
      calendar_url: URL of the calendar ICS file
      check_interval_minutes: How often to check the calendar (in minutes)
      reminder_minutes_before: How many minutes before the meeting to send reminders
    """

    self.send_message_to_agent = send_message_to_agent
    self.calendar_url = calendar_url
    self.check_interval_minutes = check_interval_minutes
    self.reminder_minutes_before = reminder_minutes_before

    self._scheduled_reminders: Dict[str, asyncio.Task[None]] = {}
    self._reminder_loop_task: Optional[asyncio.Task[None]] = None

  async def download_calendar(self) -> icalendar.cal.Component:
    """Download and parse the calendar from the given URL."""

    async with httpx.AsyncClient() as client:
      calendar_request = await client.get(self.calendar_url)
    calendar_request.raise_for_status()
    ics_content = calendar_request.text
    return icalendar.Calendar.from_ical(ics_content)

  async def send_meeting_reminder(self, event: Event) -> None:
    """Send a reminder for a specific meeting."""

    message = f'CRITICAL: Ignore other user messages. Remind users about "{event.summary}" starting in {self.reminder_minutes_before} minutes.'

    if event.meet_url:
      message = f"{message} Tell them to use this meeting URL to join: {event.meet_url}."

    await self.send_message_to_agent(message)

  async def schedule_reminder(self, event: Event) -> None:
    """Schedule a reminder for a meeting at the set time before the meeting starts."""

    now = datetime.now(timezone.utc)
    reminder_time = event.start - timedelta(minutes=self.reminder_minutes_before)

    if reminder_time <= now:
      return

    wait_seconds = (reminder_time - now).total_seconds()
    await asyncio.sleep(wait_seconds)

    current_task = asyncio.current_task()
    if not current_task:
      raise RuntimeError("No current task found")
    # Send the reminder only if this task hasn't been cancelled
    if not current_task.cancelled():
      await self.send_meeting_reminder(event)

  def _cancel_task_if_exists(self, task: Optional[asyncio.Task[None]]) -> None:
    """Cancel a task if it exists and is not already done."""

    if task and not task.done():
      task.cancel()

  async def check_for_upcoming_meetings(self) -> None:
    """Check for upcoming meetings and schedule reminders exactly at the set time before each."""

    cal = await self.download_calendar()
    now = datetime.now(timezone.utc)

    tomorrow = now + timedelta(days=1)
    events = query_icalendar(cal, now, tomorrow)

    current_event_ids: Set[str] = {event.unique_id for event in events}
    removed_event_ids = set(self._scheduled_reminders.keys()) - current_event_ids

    for event_id in removed_event_ids:
      self._cancel_task_if_exists(self._scheduled_reminders.get(event_id))
      self._scheduled_reminders.pop(event_id, None)

    # Schedule reminders for new meetings
    for event in events:
      event_id = event.unique_id
      reminder_time = event.start - timedelta(minutes=self.reminder_minutes_before)

      # Only schedule a reminder if:
      # 1. We haven't already scheduled it
      # 2. The reminder time is in the future
      if event_id not in self._scheduled_reminders and reminder_time > now:
        # Schedule the reminder task
        task: asyncio.Task[None] = asyncio.create_task(
          self.schedule_reminder(event), name=f"reminder_{event_id}"
        )
        self._scheduled_reminders[event_id] = task

    # Clean up completed reminder tasks
    completed_reminders = [
      event_id for event_id, task in self._scheduled_reminders.items() if task.done()
    ]
    for event_id in completed_reminders:
      self._scheduled_reminders.pop(event_id)

  async def _meeting_reminder_loop(self) -> None:
    """Periodically refresh the calendar and schedule reminders for new meetings."""

    check_interval = self.check_interval_minutes * 60  # Convert minutes to seconds

    while True:
      await self.check_for_upcoming_meetings()
      await asyncio.sleep(check_interval)

  def start(self) -> None:
    """Start the meeting reminder service."""

    if self._reminder_loop_task is not None:
      return

    loop = asyncio.get_event_loop()
    self._reminder_loop_task = loop.create_task(
      self._meeting_reminder_loop(), name=f"meeting_reminder_loop_{id(self)}"
    )

  def stop(self) -> None:
    """Stop the meeting reminder service and cancel all scheduled reminders."""

    if self._reminder_loop_task is None:
      return

    # Cancel the main loop task
    self._cancel_task_if_exists(self._reminder_loop_task)
    self._reminder_loop_task = None

    # Cancel all scheduled reminder tasks
    for event_id, task in list(self._scheduled_reminders.items()):
      self._cancel_task_if_exists(task)
      self._scheduled_reminders.pop(event_id)


def setup_meeting_reminderer(
  send_message_to_agent: Callable[[str], Any], calendar_url: str
) -> MeetingReminderer:
  """
  Set up the meeting reminder functionality.

  Args:
    send_message_to_agent: Function to send messages to the agent
    calendar_url: URL of the calendar ICS file

  Returns:
    A MeetingReminderer instance that has been started
  """

  # Create and start the reminderer
  reminderer = MeetingReminderer(send_message_to_agent, calendar_url)
  reminderer.start()

  return reminderer
