"""
Rich Supplier Detail View (供应商注册详情).

Opened from the list as a large st.dialog.
Contains:
- Visual clickable workflow stepper (Not Started → ... → Approved + terminals)
- File upload area (multi + drag & drop hint) + list with uploaded_by + download/delete
- Team Comments (post with fixed "Stella - 注册" as author)
- Unified Activity feed (status_history + comments combined, time-sorted)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import streamlit as st

from db.database import (
    get_supplier,
    get_status_history,
    get_attachments,
    add_attachment,
    delete_attachment,
    get_comments,
    add_comment,
    change_status,
)
from ui.components import (
    inject_global_css,
    render_status_badge,
    render_overdue_warning,
)
from utils.constants import STATUSES, get_status_label, FIXED_ACTOR
from utils.helpers import (
    upload_file_to_storage as save_uploaded_file,  # Supabase Storage
    get_file_bytes,
    delete_uploaded_file,
    is_overdue,
    format_date,
)
from utils.i18n import t, get_lang


# The main linear workflow steps (for visual stepper)
WORKFLOW_STEPS: List[str] = [
    "Not Started",
    "In Progress",
    "Documents Submitted",
    "Under Review",
    "Approved",
]
TERMINAL_STEPS: List[str] = ["Rejected", "On Hold"]


def _format_ts(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace(" ", "T"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts)[:16]


def _render_stepper(current_status: str, supplier_id: int, lang: str) -> None:
    """Horizontal visual stepper with clickable non-terminal steps."""
    inject_global_css()

    # Custom stepper CSS (injected once per dialog via parent)
    st.markdown(
        """
        <style>
        .stepper {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin: 12px 0 18px;
            gap: 4px;
        }
        .step {
            flex: 1;
            text-align: center;
            position: relative;
        }
        .step-circle {
            width: 28px;
            height: 28px;
            border-radius: 9999px;
            border: 3px solid #CBD5E1;
            background: white;
            margin: 0 auto 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            font-weight: 700;
            color: #64748B;
            box-shadow: 0 1px 2px rgba(15,23,42,0.08);
        }
        .step-circle.active {
            border-color: #1E40AF;
            background: #1E40AF;
            color: white;
        }
        .step-circle.completed {
            border-color: #10B981;
            background: #10B981;
            color: white;
        }
        .step-label {
            font-size: 11px;
            color: #64748B;
            line-height: 1.1;
        }
        .step.active .step-label { color: #1E40AF; font-weight: 600; }
        .step.completed .step-label { color: #059669; }
        .step-line {
            position: absolute;
            top: 13px;
            left: 50%;
            width: 100%;
            height: 3px;
            background: #E2E8F0;
            z-index: -1;
        }
        .step:first-child .step-line { display: none; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    is_terminal = current_status in TERMINAL_STEPS

    cols = st.columns(len(WORKFLOW_STEPS))
    for i, step in enumerate(WORKFLOW_STEPS):
        with cols[i]:
            idx = WORKFLOW_STEPS.index(step)
            is_active = (step == current_status)
            is_completed = (not is_terminal) and (idx < WORKFLOW_STEPS.index(current_status)) if current_status in WORKFLOW_STEPS else False

            circle_class = "step-circle"
            if is_active:
                circle_class += " active"
            elif is_completed:
                circle_class += " completed"

            label = get_status_label(step, lang)

            # Clickable only for non-current, non-terminal target steps
            can_click = (step != current_status) and (not is_terminal) and (step in WORKFLOW_STEPS)

            if can_click:
                if st.button(label, key=f"step_{supplier_id}_{i}", use_container_width=True):
                    # Advance
                    note = st.session_state.get(f"step_note_{supplier_id}", "")
                    try:
                        change_status(supplier_id, step, note=note or f"通过步骤器推进 by {FIXED_ACTOR}")
                        st.success(t("save_success", lang))
                        st.rerun()
                    except Exception as ex:
                        st.error(str(ex))
            else:
                # Non-clickable visual
                st.markdown(
                    f'<div class="step {"active" if is_active else "completed" if is_completed else ""}">'
                    f'<div class="{circle_class}">{i+1}</div>'
                    f'<div class="step-label">{label}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # Terminal states as separate pills below the main flow
    st.markdown("**终态 / Terminal**")
    tcols = st.columns(len(TERMINAL_STEPS))
    for i, term in enumerate(TERMINAL_STEPS):
        with tcols[i]:
            is_cur = (term == current_status)
            label = get_status_label(term, lang)
            if st.button(
                ("✅ " if is_cur else "") + label,
                key=f"term_{supplier_id}_{i}",
                type="primary" if is_cur else "secondary",
                use_container_width=True,
                disabled=is_cur,
            ):
                note = st.session_state.get(f"step_note_{supplier_id}", "")
                try:
                    change_status(supplier_id, term, note=note or f"设置为 {term} by {FIXED_ACTOR}")
                    st.rerun()
                except Exception as ex:
                    st.error(str(ex))

    # Optional note for next advance (simple text input outside buttons)
    st.text_input(
        t("status_change_note", lang) or "状态变更说明（可选）",
        key=f"step_note_{supplier_id}",
        placeholder=t("advance_note_prompt", lang) or "可选备注（将记录到历史）",
    )


def _render_files_section(supplier_id: int, lang: str) -> None:
    st.markdown(f"#### {t('files_section', lang)}")
    st.caption(t("upload_hint", lang) + " · " + t("drag_drop_support", lang))

    attachments = get_attachments(supplier_id)

    if attachments:
        for att in attachments:
            a1, a2, a3, a4 = st.columns([3.2, 1.3, 1.0, 1.0])
            with a1:
                st.markdown(f"📎 **{att['original_filename']}**")
                uploaded = att.get("uploaded_at", "")[:16]
                by = att.get("uploaded_by") or "—"
                st.caption(f"{uploaded}  ·  {t('uploaded_by', lang)}: {by}")
            with a2:
                # Download from Supabase Storage
                try:
                    file_bytes = get_file_bytes(att["stored_path"])
                    st.download_button(
                        t("download", lang),
                        data=file_bytes,
                        file_name=att["original_filename"],
                        key=f"dl_att_{att['id']}",
                        use_container_width=True,
                    )
                except Exception:
                    st.caption(t("file_not_found", lang))
            with a3:
                if st.button(t("delete_attachment", lang), key=f"del_att_{att['id']}", use_container_width=True):
                    delete_uploaded_file(att["stored_path"])
                    delete_attachment(att["id"])
                    st.success(t("attachment_deleted", lang))
                    st.rerun()
            with a4:
                st.write("")  # spacer
    else:
        st.caption(t("no_files", lang))

    # Upload control
    uploaded_files = st.file_uploader(
        t("upload_new", lang),
        accept_multiple_files=True,
        key=f"detail_uploader_{supplier_id}",
        help=t("drag_drop_support", lang),
    )

    if uploaded_files:
        if st.button(t("upload_button", lang), key=f"do_detail_upload_{supplier_id}", type="primary"):
            added = 0
            for uf in uploaded_files:
                try:
                    orig, rel = save_uploaded_file(uf, supplier_id)
                    add_attachment(supplier_id, orig, rel, uploaded_by=FIXED_ACTOR)
                    added += 1
                except Exception as ex:
                    st.error(f"Failed: {ex}")
            if added:
                st.success(f"{t('attachment_added', lang)} ({added})")
                st.rerun()


def _render_comments_section(supplier_id: int, lang: str) -> None:
    st.markdown(f"#### {t('team_comments', lang)}")

    comments = get_comments(supplier_id)

    # Post form
    with st.form(f"comment_form_{supplier_id}", clear_on_submit=True):
        content = st.text_area(
            t("comment_placeholder", lang),
            height=70,
            key=f"comment_text_{supplier_id}",
        )
        posted = st.form_submit_button(t("post_comment", lang), type="primary", use_container_width=True)

    if posted and content and content.strip():
        try:
            add_comment(supplier_id, FIXED_ACTOR, content.strip())
            st.success("评论已发布")
            st.rerun()
        except Exception as ex:
            st.error(str(ex))

    if comments:
        for c in comments:
            ts = _format_ts(c.get("created_at", ""))
            st.markdown(
                f"""
                <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;padding:8px 12px;margin-bottom:6px;">
                    <div style="font-size:12px;color:#64748B;">{ts} · <strong>{c.get('author','')}</strong></div>
                    <div style="margin-top:2px;">{c.get('content','')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.caption(t("no_comments_yet", lang))


def _render_unified_activity(supplier_id: int, lang: str) -> None:
    st.markdown(f"#### {t('activity_feed', lang)}")

    history = get_status_history(supplier_id)
    comments = get_comments(supplier_id)

    events: List[Dict] = []

    for h in history:
        events.append({
            "ts": h.get("changed_at"),
            "type": "status",
            "old": h.get("old_status"),
            "new": h.get("new_status"),
            "note": h.get("note") or "",
        })

    for c in comments:
        events.append({
            "ts": c.get("created_at"),
            "type": "comment",
            "author": c.get("author"),
            "content": c.get("content"),
        })

    # Sort newest first
    events.sort(key=lambda e: e.get("ts") or "", reverse=True)

    if not events:
        st.caption(t("activity_empty", lang))
        return

    for ev in events:
        ts = _format_ts(ev.get("ts", ""))
        if ev["type"] == "status":
            old = ev.get("old") or ""
            new = ev.get("new") or ""
            note = ev.get("note") or ""
            line = f"{old} → {new}" if old else f"初始：{new}"
            extra = f"<div style='font-size:11px;color:#64748B;margin-top:1px;'>{note}</div>" if note else ""
            st.markdown(
                f"""
                <div style="font-size:13px;margin-bottom:6px;display:flex;gap:8px;align-items:flex-start;">
                    <span style="font-family:monospace;color:#64748B;min-width:92px;">{ts}</span>
                    <span>📌 <strong>{line}</strong></span>
                    {extra}
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            author = ev.get("author", "")
            content = ev.get("content", "")
            st.markdown(
                f"""
                <div style="font-size:13px;margin-bottom:6px;display:flex;gap:8px;align-items:flex-start;">
                    <span style="font-family:monospace;color:#64748B;min-width:92px;">{ts}</span>
                    <span>💬 <strong>{author}</strong>: {content}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )


@st.dialog("📋 注册详情 / Supplier Registration Detail")
def _detail_dialog_impl(supplier_id: int, lang: str) -> None:
    inject_global_css()

    supplier = get_supplier(supplier_id)
    if not supplier:
        st.error("Supplier not found")
        return

    # Header - single company name (merged field)
    company_display = supplier.get('company_name_cn') or supplier.get('company_name_en') or ''
    st.markdown(f"### {company_display}")
    c1, c2, c3 = st.columns([1.6, 1.2, 1.2])
    with c1:
        st.markdown(render_status_badge(supplier.get("status", ""), size="normal"), unsafe_allow_html=True)
    with c2:
        st.caption(f"🌍 {supplier.get('country','')} · {supplier.get('platform','')}")
    with c3:
        dl = format_date(supplier.get("deadline"))
        if is_overdue(supplier.get("deadline"), supplier.get("status", "")):
            st.markdown(f'<span style="color:#DC2626;font-weight:600;">⚠️ {dl}</span>', unsafe_allow_html=True)
        else:
            st.caption(f"截止：{dl}")

    render_overdue_warning(supplier.get("deadline"), supplier.get("status", ""), lang)

    # New fields display
    st.markdown("**CNOOD Entity:** " + (supplier.get("cnood_entity") or "—"))
    st.markdown("**注册品类:** " + (supplier.get("registration_category") or "—"))
    st.markdown("**注册的 supplier/vendor 类型:** " + (supplier.get("supplier_vendor_type") or "—"))

    st.markdown("---")

    # Stepper
    st.markdown(f"**{t('visual_stepper', lang)}** · {t('click_to_advance', lang)}")
    _render_stepper(supplier.get("status", ""), supplier_id, lang)

    st.markdown("---")

    # Two-column main content: Files + Comments
    left, right = st.columns([1.05, 1])

    with left:
        _render_files_section(supplier_id, lang)

    with right:
        _render_comments_section(supplier_id, lang)

    st.markdown("---")

    # Unified activity (full width)
    _render_unified_activity(supplier_id, lang)

    st.markdown("---")
    if st.button(t("close", lang) or "关闭", use_container_width=True):
        st.rerun()


# Public API ---------------------------------------------------------

def show_detail_dialog(supplier_id: int, lang: str | None = None) -> None:
    """Open the rich registration detail dialog."""
    lang = lang or get_lang()
    _detail_dialog_impl(supplier_id, lang)
