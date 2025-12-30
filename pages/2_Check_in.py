"""
Check-in page

Mark habits as done for a selected date. The default is today, but you can
backfill earlier days as well.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from habit_tracker import init_db
from habit_tracker import db
from habit_tracker.metrics import is_due_on
from habit_tracker.ui_helpers import app_header, now_iso, toast_success

init_db()
st.set_page_config(page_title="Check-in", page_icon="🗓️", layout="wide")


def main() -> None:
    app_header("Check-in", "Mark habits as done and add short notes.")

    habits = db.list_habits()
    if not habits:
        st.info("Create a habit first.")
        return

    chosen = st.date_input("Date", value=date.today())

    due = [h for h in habits if is_due_on(h, chosen)]
    if not due:
        st.success("No habits scheduled for this date.")
        return

    st.divider()
    st.write(f"### Due on {chosen.isoformat()}")

    # Preload checkins
    existing = {h["id"]: db.get_checkin(h["id"], chosen.isoformat()) for h in due}

    if st.button("Mark all done"):
        for h in due:
            c = existing.get(h["id"])
            note = c.get("note", "") if c else ""
            db.upsert_checkin(h["id"], chosen.isoformat(), True, note, now_iso())
        toast_success("Saved")
        st.rerun()

    for h in due:
        c = existing.get(h["id"])
        done_default = bool(c and int(c.get("done", 0)) == 1)
        note_default = c.get("note", "") if c else ""

        with st.container(border=True):
            st.write(f"**{h['name']}**")
            if h.get("description"):
                st.caption(h["description"])

            col1, col2 = st.columns([0.25, 0.75])
            with col1:
                done = st.checkbox("Done", value=done_default, key=f"done_{h['id']}")
            with col2:
                note = st.text_input("Note", value=note_default, key=f"note_{h['id']}", placeholder="Optional")

            if st.button("Save", key=f"save_{h['id']}"):
                db.upsert_checkin(
                    habit_id=h["id"],
                    day=chosen.isoformat(),
                    done=done,
                    note=note,
                    created_at=now_iso(),
                )
                toast_success("Saved")
                st.rerun()


if __name__ == "__main__":
    main()
