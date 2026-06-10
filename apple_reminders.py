"""Fetches today's reminders from Apple Reminders via AppleScript (macOS only)."""

import subprocess
from dataclasses import dataclass


@dataclass
class Reminder:
    title: str
    due_time: str
    list_name: str
    priority: int


SCRIPT = """
set theDate to current date
set startOfDay to theDate - (time of theDate)
set endOfDay to startOfDay + 86399

set output to ""
tell application "Reminders"
    repeat with aList in lists
        try
            set dueToday to (every reminder of aList whose due date >= startOfDay and due date <= endOfDay and completed is false)
            repeat with rem in dueToday
                set remName to name of rem
                set remDue to due date of rem
                set dueHH to hours of remDue as string
                set dueMM to minutes of remDue as string
                if length of dueHH < 2 then set dueHH to "0" & dueHH
                if length of dueMM < 2 then set dueMM to "0" & dueMM
                set remPriority to priority of rem as string
                set listName to name of aList
                set output to output & dueHH & ":" & dueMM & "|" & remPriority & "|" & listName & "|" & remName & "\\n"
            end repeat
        end try
    end repeat
end tell
return output
"""

SCRIPT_NO_DUE = """
set output to ""
tell application "Reminders"
    repeat with aList in lists
        try
            set undated to (every reminder of aList whose due date is missing value and completed is false)
            repeat with rem in undated
                set remName to name of rem
                set remPriority to priority of rem as string
                set listName to name of aList
                set output to output & "NODUEDATE|" & remPriority & "|" & listName & "|" & remName & "\\n"
            end repeat
        end try
    end repeat
end tell
return output
"""


def get_today_reminders() -> list[Reminder]:
    try:
        result = subprocess.run(
            ["osascript", "-e", SCRIPT],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return []

        reminders = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) >= 4:
                reminders.append(Reminder(
                    title=parts[3],
                    due_time=parts[0],
                    list_name=parts[2],
                    priority=int(parts[1]) if parts[1].isdigit() else 0,
                ))

        reminders.sort(key=lambda r: r.due_time)
        return reminders

    except Exception:
        return []
