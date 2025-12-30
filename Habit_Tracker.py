"""
Habit Tracker - Dashboard

Run with:
    streamlit run streamlit_app.py
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import altair as alt
import pandas as pd
import streamlit as st

from habit_tracker import init_db
from habit_tracker import db
from habit_tracker.metrics import is_due_on, success_rate, current_streak
from habit_tracker.ui_helpers import app_header, now_iso, toast_success


st.set_page_config(
    page_title="Habit Tracker",
    page_icon="✅",
    layout="wide",
)

init_db()



def parse_hhmm(text: str) -> tuple[int, int]:
    try:
        hh, mm = text.strip().split(":")
        return int(hh), int(mm)
    except Exception:
        return 18, 0


def month_bounds(d: date) -> tuple[date, date]:
    start = d.replace(day=1)
    # next month start
    if start.month == 12:
        nm = start.replace(year=start.year + 1, month=1, day=1)
    else:
        nm = start.replace(month=start.month + 1, day=1)
    end = nm - timedelta(days=1)
    return start, end


@st.cache_data(ttl=10)
def load_habits():
    return db.list_habits()


@st.cache_data(ttl=10)
def load_checkins_for_habit(habit_id: int):
    return db.list_checkins_for_habit(habit_id)


def daily_progress_frame(habits: list[dict], month_start: date, month_end: date) -> pd.DataFrame:
    """
    Build a per-day frame for the month:
      - due_count, done_count
      - cumulative totals
    """
    days = pd.date_range(month_start, month_end, freq="D")
    due_counts = {d.date(): 0 for d in days}
    done_counts = {d.date(): 0 for d in days}

    # Load checkins per habit (small data, local db)
    for h in habits:
        checkins = load_checkins_for_habit(h["id"])
        done_lookup = {c["day"]: int(c.get("done", 0)) for c in checkins}
        for ts in days:
            day = ts.date()
            if is_due_on(h, day):
                due_counts[day] += 1
                if done_lookup.get(day.isoformat(), 0) == 1:
                    done_counts[day] += 1

    df = pd.DataFrame(
        {
            "day": [d.date() for d in days],
            "due": [due_counts[d.date()] for d in days],
            "done": [done_counts[d.date()] for d in days],
        }
    )
    df["cum_due"] = df["due"].cumsum()
    df["cum_done"] = df["done"].cumsum()
    df["completion_rate"] = df.apply(lambda r: (r["done"] / r["due"]) if r["due"] else 0.0, axis=1)
    return df


def render_month_progress(df: pd.DataFrame) -> None:
    chart_df = df.copy()
    chart_df["day"] = pd.to_datetime(chart_df["day"])

    base = alt.Chart(chart_df).encode(
        x=alt.X("day:T", title="Date")
    )

    done_line = base.mark_line().encode(
        y=alt.Y("cum_done:Q", title="Cumulative completions"),
        tooltip=["day:T", "done:Q", "cum_done:Q", "due:Q", "cum_due:Q"],
    )

    due_line = base.mark_line(strokeDash=[4, 4]).encode(
        y=alt.Y("cum_due:Q"),
        tooltip=["day:T", "due:Q", "cum_due:Q"],
    )

    st.altair_chart((due_line + done_line).interactive(), use_container_width=True)


def render_today(habits: list[dict], today: date) -> None:
    st.subheader("Today")


    if not habits:
        st.info("No habits yet. Create one in **Habits**.")
        return

    due_today = []
    for h in habits:
        if is_due_on(h, today):
            c = db.get_checkin(h["id"], today.isoformat())
            done = bool(c and int(c.get("done", 0)) == 1)
            due_today.append((h, done, c.get("note", "") if c else ""))

    # Reminder banner (only when something is still open)
    reminder = db.get_setting("reminder_time", "18:00")
    hh, mm = parse_hhmm(reminder)
    remind_dt = datetime.combine(today, datetime.min.time()).replace(hour=hh, minute=mm)
    open_items = sum(1 for _, done, _ in due_today if not done)
    if open_items > 0 and datetime.now() >= remind_dt:
        st.warning(f"Reminder: {open_items} habit(s) still open today. (Settings → reminder time: {reminder})")

    if not due_today:
        st.success("Nothing scheduled for today.")
        return

    col1, col2 = st.columns([1.2, 1.0], gap="large")

    with col1:
        st.markdown("#### Due habits")
        for h, done, note in due_today:
            left, right = st.columns([0.75, 0.25])
            with left:
                st.write(f"**{h['name']}**")
                if h.get("description"):
                    st.caption(h["description"])
                if note:
                    st.caption(f"Note: {note}")
            with right:
                label = "Done ✅" if done else "Mark done"
                if st.button(label, key=f"done_{h['id']}"):
                    db.upsert_checkin(
                        habit_id=h["id"],
                        day=today.isoformat(),
                        done=True,
                        note=note or "",
                        created_at=now_iso(),
                    )
                    load_checkins_for_habit.clear()
                    toast_success("Saved")
                    st.rerun()

    with col2:
        st.markdown("#### Quick stats")
        for h, done, _ in due_today:
            checkins = load_checkins_for_habit(h["id"])
            streak = current_streak(h, checkins, today)
            rate_28 = success_rate(h, checkins, today - timedelta(days=27), today)
            st.write(f"**{h['name']}**")
            st.caption(f"Streak: {streak} | 28-day: {rate_28:.0%}")
            st.divider()


def main() -> None:
    app_header("Habit Tracker", "Log daily habits, track streaks, and spot patterns over time.")

    habits = load_habits()
    today = date.today()

    # Month selector (for the progress chart)
    month_pick = st.date_input("Month", value=today, help="Pick any day in the month you want to review.")
    month_start, month_end = month_bounds(month_pick)

    st.divider()
    render_today(habits, today)

    st.divider()
    st.subheader("This month")
    if habits:
        df = daily_progress_frame(habits, month_start, month_end)
        total_due = int(df["due"].sum())
        total_done = int(df["done"].sum())
        rate = (total_done / total_due) if total_due else 0.0

        c1, c2, c3 = st.columns(3)
        c1.metric("Completions", f"{total_done}")
        c2.metric("Due", f"{total_due}")
        c3.metric("Completion rate", f"{rate:.0%}")

        render_month_progress(df)
    else:
        st.info("Create a habit first to see progress for the month.")


if __name__ == "__main__":
    main()
