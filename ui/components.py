"""Reusable UI components and styling for a clean professional look."""

from __future__ import annotations

import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional

from utils.constants import get_status_color, DEFAULT_COLOR
from utils.helpers import format_date, is_overdue
from utils.i18n import t, get_lang


def inject_global_css() -> None:
    """Inject professional custom CSS once per run."""
    css = """
    <style>
    /* Global clean business look */
    .stApp {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }

    /* Sidebar polish */
    section[data-testid="stSidebar"] {
        background-color: #F1F5F9;
        border-right: 1px solid #E2E8F0;
    }

    /* Metric / Stat cards */
    .metric-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px 18px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
        transition: transform 0.1s ease, box-shadow 0.1s ease;
    }
    .metric-card:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
    }
    .metric-label {
        font-size: 13px;
        color: #64748B;
        font-weight: 500;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 26px;
        font-weight: 700;
        line-height: 1.1;
        color: #0F172A;
    }
    .metric-sub {
        font-size: 11px;
        color: #94A3B8;
    }

    /* Status badge (pill) */
    .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 3px 11px;
        border-radius: 9999px;
        font-size: 12.5px;
        font-weight: 600;
        color: white;
        letter-spacing: 0.2px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        white-space: nowrap;
    }

    /* Timeline */
    .timeline {
        position: relative;
        margin: 8px 0 4px;
        padding-left: 28px;
    }
    .timeline::before {
        content: "";
        position: absolute;
        left: 11px;
        top: 6px;
        bottom: 6px;
        width: 2px;
        background: #E2E8F0;
    }
    .timeline-item {
        position: relative;
        margin-bottom: 14px;
    }
    .timeline-dot {
        position: absolute;
        left: 2px;
        top: 5px;
        width: 18px;
        height: 18px;
        border-radius: 9999px;
        background: white;
        border: 3px solid #64748B;
        box-shadow: 0 0 0 3px rgba(100, 116, 139, 0.1);
    }
    .timeline-content {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 13px;
    }
    .timeline-time {
        font-family: ui-monospace, monospace;
        font-size: 11.5px;
        color: #64748B;
    }
    .timeline-status {
        font-weight: 600;
    }

    /* Attachment row */
    .attachment-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 6px 10px;
        margin-bottom: 6px;
        font-size: 13px;
    }
    .attachment-name {
        font-weight: 500;
        color: #1E293B;
        word-break: break-all;
    }

    /* Overdue highlight */
    .overdue-text {
        color: #DC2626 !important;
        font-weight: 600;
    }

    /* Form section header */
    .section-header {
        font-size: 15px;
        font-weight: 600;
        color: #1E40AF;
        margin: 12px 0 6px;
        padding-bottom: 4px;
        border-bottom: 2px solid #E0E7FF;
    }

    /* Nice container for selected supplier actions */
    .action-panel {
        background: linear-gradient(145deg, #F8FAFC, #FFFFFF);
        border: 1px solid #CBD5E1;
        border-radius: 12px;
        padding: 14px 16px;
        margin-top: 8px;
    }

    /* Dataframe tweaks */
    .stDataFrame {
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        overflow: hidden;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 8px;
    }

    /* Stepper & comment polish (also defined locally in detail for isolation) */
    .stepper-row { display:flex; gap:6px; align-items:center; margin: 8px 0; }
    .comment-bubble {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 6px 10px;
        margin: 4px 0;
        font-size: 13px;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_status_badge(status: str, size: str = "normal") -> str:
    """Return HTML for a nice colored status pill."""
    color = get_status_color(status)
    font_size = "11.5px" if size == "small" else "12.8px"
    padding = "2px 9px" if size == "small" else "3.5px 12px"
    html = f"""
    <span class="status-badge" style="
        background-color: {color};
        font-size: {font_size};
        padding: {padding};
    ">{status}</span>
    """
    return html


def render_metric_card(label: str, value: str | int, color: str | None = None, sub: str = "") -> None:
    """Render a single nice metric card using columns + markdown."""
    color = color or "#1E40AF"
    sub_html = f'<div class="metric-sub">{sub}</div>' if sub else ""
    html = f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value" style="color:{color};">{value}</div>
        {sub_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_timeline(history: List[Dict], lang: str = "zh") -> None:
    """Beautiful vertical status history timeline."""
    if not history:
        st.caption(t("history_empty", lang))
        return

    items_html = []
    for h in history:
        changed_at = h.get("changed_at", "")
        # Truncate time for readability
        try:
            dt = datetime.fromisoformat(changed_at.replace(" ", "T"))
            time_str = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            time_str = str(changed_at)[:16]

        old = h.get("old_status") or ""
        new = h.get("new_status") or ""
        note = h.get("note") or ""

        if old:
            status_line = f'<span class="timeline-status">{old} → {new}</span>'
        else:
            status_line = f'<span class="timeline-status">{t("history_initial", lang, status=new)}</span>'

        note_html = ""
        if note:
            note_html = f'<div style="font-size:11.5px;color:#64748B;margin-top:2px;">{note}</div>'

        dot_color = get_status_color(new)
        item = f"""
        <div class="timeline-item">
            <div class="timeline-dot" style="border-color:{dot_color};"></div>
            <div class="timeline-content">
                <div class="timeline-time">{time_str}</div>
                <div>{status_line}</div>
                {note_html}
            </div>
        </div>
        """
        items_html.append(item)

    full = f'<div class="timeline">{"".join(items_html)}</div>'
    st.markdown(full, unsafe_allow_html=True)


def render_attachment_row(attachment: Dict, show_delete: bool = True, lang: str = "zh") -> None:
    """Render a single attachment row (used inside st.container or loop).
    Actual buttons are provided by the caller.
    """
    orig = attachment.get("original_filename", "file")
    uploaded = attachment.get("uploaded_at", "")[:16]
    by = attachment.get("uploaded_by") or ""
    by_html = f"<br><span style='font-size:10px;color:#64748B;'>by {by}</span>" if by else ""
    html = f"""
    <div class="attachment-row">
        <div>
            <span class="attachment-name">📎 {orig}</span><br>
            <span style="font-size:10.5px;color:#94A3B8;">{uploaded}</span>
            {by_html}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_overdue_warning(deadline: Optional[str], status: str, lang: str = "zh") -> None:
    if is_overdue(deadline, status):
        st.warning(t("overdue_flag", lang) + " — " + t("deadline_label", lang) + f" {format_date(deadline)}", icon="⚠️")


def get_status_display(status: str, lang: str = "zh") -> str:
    """For dataframe display: emoji + localized label."""
    from utils.constants import get_status_label, get_status_color
    emoji_map = {
        "Not Started": "⚪",
        "In Progress": "🔵",
        "Documents Submitted": "📄",
        "Under Review": "🔍",
        "Approved": "✅",
        "Rejected": "❌",
        "On Hold": "⏸️",
    }
    emoji = emoji_map.get(status, "⚪")
    label = get_status_label(status, lang)
    return f"{emoji} {label}"
