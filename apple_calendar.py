"""Fetches today's events from Apple Calendar via AppleScript (macOS only)."""

import subprocess
from dataclasses import dataclass
from datetime import date


@dataclass
class CalendarEvent:
    title: str
    start_time: str
    end_time: str
    calendar: str
    all_day: bool


SCRIPT = """
set theDate to current date
set startOfDay to theDate - (time of theDate)
set endOfDay to startOfDay + 86399

set output to ""
tell application "Calendar"
    repeat with aCal in calendars
        try
            set dayEvents to (every event of aCal whose start date >= startOfDay and start date <= endOfDay)
            repeat with evt in dayEvents
                set evtTitle to summary of evt
                set evtStart to start date of evt
                set evtEnd to end date of evt
                set isAllDay to allday event of evt
                set calName to name of aCal
                if isAllDay then
                    set output to output & "ALLDAY|" & calName & "|" & evtTitle & "\\n"
                else
                    set startHH to hours of evtStart as string
                    set startMM to minutes of evtStart as string
                    set endHH to hours of evtEnd as string
                    set endMM to minutes of evtEnd as string
                    if length of startHH < 2 then set startHH to "0" & startHH
                    if length of startMM < 2 then set startMM to "0" & startMM
                    if length of endHH < 2 then set endHH to "0" & endHH
                    if length of endMM < 2 then set endMM to "0" & endMM
                    set output to output & startHH & ":" & startMM & "|" & endHH & ":" & endMM & "|" & calName & "|" & evtTitle & "\\n"
                end if
            end repeat
        end try
    end repeat
end tell
return output
"""


def get_today_events() -> list[CalendarEvent]:
    try:
        result = subprocess.run(
            ["osascript", "-e", SCRIPT],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return []

        events = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if parts[0] == "ALLDAY" and len(parts) >= 3:
                events.append(CalendarEvent(
                    title=parts[2],
                    start_time="Весь день",
                    end_time="",
                    calendar=parts[1],
                    all_day=True,
                ))
            elif len(parts) >= 4:
                events.append(CalendarEvent(
                    title=parts[3],
                    start_time=parts[0],
                    end_time=parts[1],
                    calendar=parts[2],
                    all_day=False,
                ))

        events.sort(key=lambda e: ("23:59" if e.all_day else e.start_time))
        return events

    except Exception:
        return []


def get_tomorrow_events() -> list[CalendarEvent]:
    script = SCRIPT.replace(
        "set startOfDay to theDate - (time of theDate)",
        "set startOfDay to (theDate - (time of theDate)) + 86400",
    )
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return []

        events = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if parts[0] == "ALLDAY" and len(parts) >= 3:
                events.append(CalendarEvent(
                    title=parts[2],
                    start_time="Весь день",
                    end_time="",
                    calendar=parts[1],
                    all_day=True,
                ))
            elif len(parts) >= 4:
                events.append(CalendarEvent(
                    title=parts[3],
                    start_time=parts[0],
                    end_time=parts[1],
                    calendar=parts[2],
                    all_day=False,
                ))

        events.sort(key=lambda e: ("23:59" if e.all_day else e.start_time))
        return events

    except Exception:
        return []
