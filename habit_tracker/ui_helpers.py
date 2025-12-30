"""
UI helpers shared across pages (Streamlit).

Keeping this separate avoids repeating small formatting bits.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

import streamlit as st


def app_header(title: str, subtitle: str | None = None) -> None:
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def iso_today() -> str:
    return date.today().isoformat()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def toast_success(msg: str) -> None:
    try:
        st.toast(msg, icon="✅")
    except Exception:
        st.success(msg)


def toast_error(msg: str) -> None:
    try:
        st.toast(msg, icon="⚠️")
    except Exception:
        st.error(msg)


def confirm_box(key: str, label: str = "I understand") -> bool:
    return st.checkbox(label, key=key)
