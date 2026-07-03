"""Dashboard page renderer."""

from __future__ import annotations

import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime

from db.database import get_suppliers_df, get_status_history, get_all_suppliers
from ui.components import (
    inject_global_css,
    render_metric_card,
    render_status_badge,
    render_timeline,
)
from utils.constants import TERMINAL_STATUSES, IN_PROGRESS_STATUSES, COMPLETED_STATUSES
from utils.helpers import is_overdue, format_date
from utils.i18n import t, get_lang


def _compute_stats(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {
            "total": 0,
            "in_progress": 0,
            "completed": 0,
            "delayed": 0,
            "overdue": 0,
        }

    total = len(df)

    # In Progress group (active workflow)
    in_progress = len(df[df["status"].isin(list(IN_PROGRESS_STATUSES))])

    # Completed (Approved)
    completed = len(df[df["status"].isin(list(COMPLETED_STATUSES))])

    # Delayed = overdue and not terminal
    delayed = 0
    overdue = 0
    for _, row in df.iterrows():
        if is_overdue(row.get("deadline"), row.get("status", "")):
            overdue += 1
            if row.get("status") not in TERMINAL_STATUSES:
                delayed += 1

    return {
        "total": total,
        "in_progress": in_progress,
        "completed": completed,
        "delayed": delayed,
        "overdue": overdue,
    }


def _get_recent_activity(limit: int = 8) -> list[dict]:
    """Collect recent status changes + creations across all suppliers."""
    suppliers = get_all_suppliers()
    if not suppliers:
        return []

    # Map id -> name for display
    id_to_name = {s["id"]: s["company_name_cn"] for s in suppliers}

    all_events = []
    for s in suppliers:
        hist = get_status_history(s["id"])
        for h in hist:
            all_events.append({
                "changed_at": h.get("changed_at"),
                "company": id_to_name.get(s["id"], ""),
                "old_status": h.get("old_status"),
                "new_status": h.get("new_status"),
                "note": h.get("note"),
                "supplier_id": s["id"],
            })

    # Sort by time desc
    all_events.sort(key=lambda x: x.get("changed_at") or "", reverse=True)
    return all_events[:limit]


def render_dashboard(lang: str | None = None) -> None:
    lang = lang or get_lang()
    inject_global_css()

    st.title(t("dashboard_title", lang))

    df = get_suppliers_df()
    stats = _compute_stats(df)

    # === Top stats row (exact spec: Total, In Progress, Completed, Delayed + bonus overdue) ===
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        render_metric_card(
            t("total_suppliers", lang),
            stats["total"],
            color="#1E40AF",
        )
    with c2:
        render_metric_card(
            t("in_progress_count", lang),
            stats["in_progress"],
            color="#3B82F6",
        )
    with c3:
        render_metric_card(
            t("completed_count", lang),
            stats["completed"],
            color="#10B981",
        )
    with c4:
        render_metric_card(
            t("delayed_count", lang),
            stats["delayed"],
            color="#DC2626",
            sub="⚠️" if stats["delayed"] > 0 else "",
        )
    with c5:
        render_metric_card(
            t("overdue_count", lang),
            stats["overdue"],
            color="#DC2626",
            sub="（含终态）" if stats["overdue"] > 0 else "",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # === Charts row ===
    col_left, col_right = st.columns([1.05, 1])

    with col_left:
        st.subheader(t("status_distribution", lang))
        if not df.empty:
            status_counts = df["status"].value_counts().reset_index()
            status_counts.columns = ["status", "count"]
            # Use display labels for nicer pie
            from utils.constants import get_status_label
            status_counts["label"] = status_counts["status"].apply(lambda s: get_status_label(s, lang))
            fig = px.pie(
                status_counts,
                values="count",
                names="label",
                color="status",
                color_discrete_map={
                    "Not Started": "#94A3B8",
                    "In Progress": "#3B82F6",
                    "Documents Submitted": "#8B5CF6",
                    "Under Review": "#F59E0B",
                    "Approved": "#10B981",
                    "Rejected": "#EF4444",
                    "On Hold": "#64748B",
                },
                hole=0.45,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(
                showlegend=True,
                margin=dict(t=10, b=10, l=10, r=10),
                height=320,
            )
            st.plotly_chart(fig, use_container_width=True, key="pie_status")
        else:
            st.caption(t("no_suppliers", lang))

    with col_right:
        st.subheader(t("platform_breakdown", lang))
        if not df.empty:
            plat_counts = df["platform"].value_counts().reset_index()
            plat_counts.columns = ["platform", "count"]
            fig2 = px.bar(
                plat_counts,
                x="count",
                y="platform",
                orientation="h",
                color="count",
                color_continuous_scale="Blues",
            )
            fig2.update_layout(
                showlegend=False,
                margin=dict(t=10, b=10, l=10, r=10),
                height=320,
                yaxis={"categoryorder": "total ascending"},
            )
            st.plotly_chart(fig2, use_container_width=True, key="bar_platform")
        else:
            st.caption(t("no_suppliers", lang))

    st.markdown("---")

    # === Recent Activity ===
    st.subheader(t("recent_activity", lang))
    activity = _get_recent_activity(8)

    if not activity:
        st.caption(t("no_activity", lang))
        return

    for ev in activity:
        company = ev.get("company", "")
        old = ev.get("old_status")
        new = ev.get("new_status")
        note = ev.get("note") or ""
        ts = str(ev.get("changed_at", ""))[:16]

        if old:
            line = t(
                "activity_status_change",
                lang,
                company=company,
                old=old,
                new=new,
            )
        else:
            line = t("activity_initial", lang, company=company, status=new)

        extra = ""
        if note:
            extra = t("activity_note", lang, note=note)

        # Small colored badge for new status
        badge = render_status_badge(new, size="small")

        st.markdown(
            f"""
            <div style="font-size:13px; margin-bottom:6px; display:flex; align-items:center; gap:8px;">
                <span style="font-family:monospace; color:#64748B; min-width:92px;">{ts}</span>
                <span><strong>{company}</strong> — {line} {extra}</span>
                {badge}
            </div>
            """,
            unsafe_allow_html=True,
        )
