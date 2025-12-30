"""
Metrics and date logic: due-days, streaks, success rates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import pandas as pd


WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]  # 0..6


def parse_custom_days(custom_days: str) -> Set[int]:
    """
    Convert '0,1,2' -> {0,1,2}. Empty string -> empty set.
    """
    custom_days = (custom_days or "").strip()
    if not custom_days:
        return set()
    out = set()
    for p in custom_days.split(","):
        p = p.strip()
        if p == "":
            continue
        try:
            out.add(int(p))
        except ValueError:
            continue
    return out


def is_due_on(habit: dict, d: date) -> bool:
    st = habit.get("schedule_type", "daily")
    if st == "daily":
        return True
    if st == "weekdays":
        return d.weekday() < 5
    if st == "custom":
        allowed = parse_custom_days(habit.get("custom_days", ""))
        return d.weekday() in allowed
    return True


def daterange(start: date, end: date) -> List[date]:
    """
    Inclusive date range.
    """
    days = []
    cur = start
    while cur <= end:
        days.append(cur)
        cur += timedelta(days=1)
    return days


def due_days_for_habit(habit: dict, start: date, end: date) -> List[date]:
    return [d for d in daterange(start, end) if is_due_on(habit, d)]


def checkin_lookup(checkins: Sequence[dict]) -> Dict[str, int]:
    """
    'YYYY-MM-DD' -> 0/1
    """
    return {c["day"]: int(c.get("done", 0)) for c in checkins}


def current_streak(habit: dict, checkins: Sequence[dict], today: date) -> int:
    """
    Count consecutive *due* days ending at today
    where the habit was marked done.
    """
    lookup = checkin_lookup(checkins)
    # Walk backwards from today until a miss on a due day
    streak = 0
    cur = today
    while True:
        if not is_due_on(habit, cur):
            cur -= timedelta(days=1)
            # stop if it drifts too far (safety)
            if streak == 0 and (today - cur).days > 60:
                return 0
            continue

        key = cur.isoformat()
        if lookup.get(key, 0) == 1:
            streak += 1
            cur -= timedelta(days=1)
            continue
        break
    return streak


def longest_streak(habit: dict, checkins: Sequence[dict], start: date, end: date) -> int:
    lookup = checkin_lookup(checkins)
    longest = 0
    cur_streak = 0
    for d in daterange(start, end):
        if not is_due_on(habit, d):
            continue
        if lookup.get(d.isoformat(), 0) == 1:
            cur_streak += 1
            longest = max(longest, cur_streak)
        else:
            cur_streak = 0
    return longest


def success_rate(habit: dict, checkins: Sequence[dict], start: date, end: date) -> float:
    """
    done / due for the window.
    """
    due = due_days_for_habit(habit, start, end)
    if not due:
        return 0.0
    lookup = checkin_lookup(checkins)
    done = sum(1 for d in due if lookup.get(d.isoformat(), 0) == 1)
    return done / len(due)


def heatmap_frame(habit: dict, checkins: Sequence[dict], month_start: date, month_end: date) -> pd.DataFrame:
    """
    Build a dataframe for a calendar-like heatmap for one month.

    Columns:
      - day (date)
      - done (0/1/None)
      - due (0/1)
      - dow (0..6)
      - week (int, week index within the month)
    """
    lookup = checkin_lookup(checkins)
    rows = []
    # Align weeks to Monday for a stable calendar layout
    first_monday = month_start - timedelta(days=month_start.weekday())
    for d in daterange(first_monday, month_end):
        due = 1 if is_due_on(habit, d) and (month_start <= d <= month_end) else 0
        done = lookup.get(d.isoformat(), None) if due else None
        week = (d - first_monday).days // 7
        rows.append(
            {
                "day": d,
                "day_num": d.day if (month_start <= d <= month_end) else None,
                "done": done,
                "due": due,
                "dow": d.weekday(),
                "week": week,
            }
        )
    return pd.DataFrame(rows)
