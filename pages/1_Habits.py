"""
Habits page

Create, edit, and delete habits. Schedules are kept intentionally simple:
- daily
- weekdays
- custom days (pick the weekdays)
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from habit_tracker import init_db
from habit_tracker import db
from habit_tracker.metrics import WEEKDAY_NAMES
from habit_tracker.ui_helpers import app_header, now_iso, toast_error, toast_success

init_db()

st.set_page_config(page_title="Habits", page_icon="📌", layout="wide")


def days_to_string(selected: list[int]) -> str:
    return ",".join(str(d) for d in sorted(selected))


def string_to_days(s: str) -> list[int]:
    s = (s or "").strip()
    if not s:
        return []
    out = []
    for p in s.split(","):
        p = p.strip()
        if p == "":
            continue
        try:
            out.append(int(p))
        except ValueError:
            pass
    return sorted(set([d for d in out if 0 <= d <= 6]))


def main() -> None:
    app_header("Habits", "Create habits and define when they are due.")

    habits = db.list_habits()

    left, right = st.columns([0.9, 1.1], gap="large")

    with left:
        st.subheader("Your habits")
        if not habits:
            st.info("No habits yet.")
        else:
            for h in habits:
                cols = st.columns([0.75, 0.25])
                with cols[0]:
                    st.write(f"**{h['name']}**")
                    if h.get("description"):
                        st.caption(h["description"])
                with cols[1]:
                    if st.button("Edit", key=f"edit_{h['id']}"):
                        st.session_state["edit_id"] = h["id"]
                        st.rerun()

        st.divider()


    with right:
        st.subheader("New Habit")

        edit_id = st.session_state.get("edit_id", None)
        habit = db.get_habit(edit_id) if edit_id else None

        name_default = habit["name"] if habit else ""
        desc_default = habit.get("description", "") if habit else ""
        schedule_default = habit.get("schedule_type", "daily") if habit else "daily"
        custom_default = string_to_days(habit.get("custom_days", "")) if habit else []

        name = st.text_input("Name", value=name_default, placeholder="e.g. Walk 20 minutes")
        desc = st.text_area("Description", value=desc_default, height=90, placeholder="Optional")
        schedule_type = st.selectbox(
            "Schedule",
            options=["daily", "weekdays", "custom"],
            index=["daily", "weekdays", "custom"].index(schedule_default),
            help="Defines on which days this habit is expected.",
        )

        selected_days: list[int] = custom_default
        if schedule_type == "custom":
            st.caption("Custom days")
            day_cols = st.columns(7)
            new_selected = []
            for i, nm in enumerate(WEEKDAY_NAMES):
                with day_cols[i]:
                    if st.checkbox(nm, value=(i in custom_default), key=f"day_{i}"):
                        new_selected.append(i)
            selected_days = new_selected

        custom_days = days_to_string(selected_days) if schedule_type == "custom" else ""

        save_col, del_col = st.columns([0.6, 0.4])
        with save_col:
            if st.button("Save", type="primary"):
                if not name.strip():
                    toast_error("Please enter a name.")
                else:
                    try:
                        if habit:
                            db.update_habit(
                                habit_id=habit["id"],
                                name=name,
                                description=desc,
                                schedule_type=schedule_type,
                                custom_days=custom_days,
                            )
                            toast_success("Habit updated")
                        else:
                            db.create_habit(
                                name=name,
                                description=desc,
                                schedule_type=schedule_type,
                                custom_days=custom_days,
                                created_at=now_iso(),
                            )
                            toast_success("Habit created")
                        st.session_state["edit_id"] = None
                        st.rerun()
                    except Exception as e:
                        toast_error("Could not save habit. Names must be unique.")
        with del_col:
            if habit:
                if st.button("Delete", help="Deletes the habit and its check-ins."):
                    st.session_state["confirm_delete"] = True

        if habit and st.session_state.get("confirm_delete"):
            st.warning("This will remove the habit and its history.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Cancel"):
                    st.session_state["confirm_delete"] = False
                    st.rerun()
            with c2:
                if st.button("Delete permanently", type="primary"):
                    db.delete_habit(habit["id"])
                    st.session_state["confirm_delete"] = False
                    st.session_state["edit_id"] = None
                    toast_success("Habit deleted")
                    st.rerun()


if __name__ == "__main__":
    main()
