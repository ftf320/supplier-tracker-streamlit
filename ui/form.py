"""Add / Edit supplier form (rendered inside st.dialog for clean UX)."""

from __future__ import annotations

import streamlit as st
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from db.database import (
    get_supplier,
    add_supplier,
    update_supplier,
    get_status_history,
    get_attachments,
    add_attachment,
    delete_attachment,
)
from ui.components import (
    inject_global_css,
    render_timeline,
    render_status_badge,
    render_overdue_warning,
)
from utils.constants import STATUSES, PLATFORMS, ACTORS
from utils.helpers import (
    format_date,
    upload_file_to_storage as save_uploaded_file,  # Supabase Storage version
    get_file_bytes,
    delete_uploaded_file,
    is_overdue,
)
from utils.i18n import t, get_lang


def _platform_select_widget(default: str = "", key: str = "platform") -> str:
    """Selectbox + optional custom input for platform."""
    options = PLATFORMS + ["其他（手动输入）"]
    current = default if default in PLATFORMS else ("其他（手动输入）" if default else options[0])
    idx = options.index(current) if current in options else 0

    plat = st.selectbox(
        t("platform_label", get_lang()),
        options=options,
        index=idx,
        key=f"{key}_select",
    )
    if plat == "其他（手动输入）":
        custom = st.text_input(
            t("platform_other", get_lang()),
            value=default if default and default not in PLATFORMS else "",
            key=f"{key}_custom",
        )
        return custom.strip() if custom else "其他"
    return plat


@st.dialog("➕ 添加新供应商 / Add New Supplier")
def _add_dialog_impl(lang: str, current_actor: str | None = None) -> None:
    """Internal dialog implementation."""
    inject_global_css()
    actor = current_actor or "李娜 - 采购经理"

    with st.form("add_supplier_form", clear_on_submit=False):
        # Merged company name field (single input supporting Chinese or English)
        company_name = st.text_input(
            t("company_name_req", lang),
            key="add_company_name",
        )

        # Country changed to free text input (manual entry, no longer restricted list)
        country = st.text_input(
            t("country_label", lang),
            key="add_country",
        )

        # "所属平台"（平台）字段已按需求从“添加新供应商”表单中完全移除。
        # 新增的供应商将默认使用 platform="Other"。

        c1, c2 = st.columns(2)
        with c1:
            # Default to first non-terminal
            status = st.selectbox(t("status_label", lang), options=STATUSES, index=0, key="add_status")
        with c2:
            sub_date = st.date_input(
                t("submission_date_label", lang),
                value=date.today(),
                key="add_sub_date",
            )

        deadline = st.date_input(
            t("deadline_label", lang),
            value=None,
            key="add_deadline",
        )

        c3, c4 = st.columns(2)
        with c3:
            contact = st.text_input(t("contact_name", lang), key="add_contact")
        with c4:
            phone = st.text_input(t("contact_phone", lang), key="add_phone")

        email = st.text_input(t("contact_email", lang), key="add_email")

        owner = st.text_input(
            t("owner_label", lang),
            value=actor,
            key="add_owner",
            help=t("owner_placeholder", lang),
        )

        # New fields
        cnood_entity = st.text_input(
            t("cnood_entity", lang),
            key="add_cnood_entity",
        )

        registration_category = st.text_area(
            t("registration_category", lang),
            height=120,
            key="add_registration_category",
        )

        supplier_vendor_type = st.text_input(
            t("supplier_vendor_type", lang),
            key="add_supplier_vendor_type",
        )

        notes = st.text_area(t("notes", lang), height=90, key="add_notes")

        # For new, attachments after create (show hint)
        st.caption("💡 " + t("attachments_section", lang) + " — 保存后请到列表 → 查看详情 进行附件上传与团队评论")

        submitted = st.form_submit_button(t("save", lang), type="primary", use_container_width=True)

    if submitted:
        if not company_name or not country:
            st.error(t("required_field", lang))
            return

        data = {
            "company_name_cn": company_name.strip(),
            "company_name_en": None,  # Merged field: primary name stored in cn for new records
            "country": country.strip() if country else None,
            "platform": "Other",   # Platform field removed from add form; default to "Other"
            "status": status,
            "submission_date": sub_date.isoformat() if sub_date else None,
            "deadline": deadline.isoformat() if deadline else None,
            "contact_name": contact.strip() if contact else None,
            "owner": owner.strip() if owner else actor,
            "contact_email": email.strip() if email else None,
            "contact_phone": phone.strip() if phone else None,
            "cnood_entity": cnood_entity.strip() if cnood_entity else None,
            "registration_category": registration_category.strip() if registration_category else None,
            "supplier_vendor_type": supplier_vendor_type.strip() if supplier_vendor_type else None,
            "notes": notes.strip() if notes else None,
        }

        try:
            new_id = add_supplier(data)
            st.success(t("save_success", lang) + f" (ID: {new_id})")
            st.rerun()
        except Exception as e:
            st.error(f"{t('save_failed', lang)}: {e}")


@st.dialog("✏️ 编辑供应商 / Edit Supplier")
def _edit_dialog_impl(supplier_id: int, lang: str, current_actor: str | None = None) -> None:
    """Edit dialog with attachments + full history (basic fields only; rich collab is in Detail View)."""
    inject_global_css()
    actor = current_actor or supplier.get("owner") or "李娜 - 采购经理" if 'supplier' in locals() else "李娜 - 采购经理"

    supplier = get_supplier(supplier_id)
    if not supplier:
        st.error("Supplier not found")
        return

    current_status = supplier.get("status")
    st.markdown(f"**ID {supplier_id}** — {supplier.get('company_name_cn','')}")
    st.markdown(render_status_badge(current_status), unsafe_allow_html=True)

    # Overdue banner
    render_overdue_warning(supplier.get("deadline"), current_status, lang)

    # --- Main edit form ---
    with st.form(f"edit_form_{supplier_id}", clear_on_submit=False):
        # Merged company name (single field for add/edit consistency)
        company_name = st.text_input(
            t("company_name_req", lang),
            value=supplier.get("company_name_cn") or supplier.get("company_name_en") or "",
            key=f"edit_company_name_{supplier_id}",
        )

        plat = _platform_select_widget(supplier.get("platform", ""), key=f"edit_plat_{supplier_id}")

        # Country as manual text input (free form, not limited to dropdown)
        country = st.text_input(
            t("country_label", lang),
            value=supplier.get("country", "") or "",
            key=f"edit_country_{supplier_id}",
        )

        c1, c2 = st.columns(2)
        with c1:
            status_idx = STATUSES.index(current_status) if current_status in STATUSES else 0
            new_status = st.selectbox(
                t("status_label", lang),
                options=STATUSES,
                index=status_idx,
                key=f"edit_status_{supplier_id}",
            )
        with c2:
            sub_date = st.date_input(
                t("submission_date_label", lang),
                value=_parse_date_or_today(supplier.get("submission_date")),
                key=f"edit_sub_{supplier_id}",
            )

        deadline = st.date_input(
            t("deadline_label", lang),
            value=_parse_date_or_none(supplier.get("deadline")),
            key=f"edit_dl_{supplier_id}",
        )

        c3, c4 = st.columns(2)
        with c3:
            contact = st.text_input(
                t("contact_name", lang),
                value=supplier.get("contact_name") or "",
                key=f"edit_contact_{supplier_id}",
            )
        with c4:
            phone = st.text_input(
                t("contact_phone", lang),
                value=supplier.get("contact_phone") or "",
                key=f"edit_phone_{supplier_id}",
            )

        email = st.text_input(
            t("contact_email", lang),
            value=supplier.get("contact_email") or "",
            key=f"edit_email_{supplier_id}",
        )

        owner_val = st.text_input(
            t("owner_label", lang),
            value=supplier.get("owner") or actor,
            key=f"edit_owner_{supplier_id}",
        )

        # New fields
        cnood_entity = st.text_input(
            t("cnood_entity", lang),
            value=supplier.get("cnood_entity") or "",
            key=f"edit_cnood_entity_{supplier_id}",
        )

        registration_category = st.text_area(
            t("registration_category", lang),
            value=supplier.get("registration_category") or "",
            height=120,
            key=f"edit_registration_category_{supplier_id}",
        )

        supplier_vendor_type = st.text_input(
            t("supplier_vendor_type", lang),
            value=supplier.get("supplier_vendor_type") or "",
            key=f"edit_supplier_vendor_type_{supplier_id}",
        )

        notes = st.text_area(
            t("notes", lang),
            value=supplier.get("notes") or "",
            height=80,
            key=f"edit_notes_{supplier_id}",
        )

        # Status change note (only if status will change)
        status_note = ""
        if new_status != current_status:
            status_note = st.text_input(
                t("status_change_note", lang),
                placeholder=t("status_change_note_placeholder", lang),
                key=f"status_note_{supplier_id}",
            )

        # Save button inside form
        save_clicked = st.form_submit_button(t("save", lang), type="primary", use_container_width=True)

    if save_clicked:
        if not company_name or not plat or not new_status:
            st.error(t("required_field", lang))
            return

        data = {
            "company_name_cn": company_name.strip(),
            "company_name_en": None,  # Unified name: stored primarily in cn
            "country": country.strip() if country else None,
            "platform": plat,
            "status": new_status,
            "submission_date": sub_date.isoformat() if sub_date else None,
            "deadline": deadline.isoformat() if deadline else None,
            "contact_name": contact.strip() if contact else None,
            "owner": owner_val.strip() if owner_val else None,
            "contact_email": email.strip() if email else None,
            "contact_phone": phone.strip() if phone else None,
            "cnood_entity": cnood_entity.strip() if cnood_entity else None,
            "registration_category": registration_category.strip() if registration_category else None,
            "supplier_vendor_type": supplier_vendor_type.strip() if supplier_vendor_type else None,
            "notes": notes.strip() if notes else None,
        }

        try:
            note_to_log = status_note.strip() if status_note else None
            update_supplier(supplier_id, data, status_note=note_to_log)
            st.success(t("save_success", lang))
            st.rerun()
        except Exception as e:
            st.error(f"{t('save_failed', lang)}: {e}")

    st.markdown("---")

    # --- Attachments section (outside form, live) ---
    st.markdown(f"#### {t('attachments_section', lang)}")

    attachments = get_attachments(supplier_id)

    if attachments:
        st.caption(t("current_attachments", lang))
        for att in attachments:
            a_col1, a_col2, a_col3 = st.columns([4.5, 1.2, 1.0])
            with a_col1:
                st.markdown(f"📎 **{att['original_filename']}**")
                st.caption(f"上传于 {att.get('uploaded_at','')[:16]}")
            with a_col2:
                # Download button - now from Supabase Storage
                try:
                    file_bytes = get_file_bytes(att["stored_path"])
                    st.download_button(
                        t("download", lang),
                        data=file_bytes,
                        file_name=att["original_filename"],
                        key=f"dl_{att['id']}",
                        use_container_width=True,
                    )
                except Exception:
                    st.caption(t("file_not_found", lang))
            with a_col3:
                if st.button(t("delete_attachment", lang), key=f"del_att_{att['id']}", use_container_width=True):
                    # Delete file + record
                    delete_uploaded_file(att["stored_path"])
                    delete_attachment(att["id"])
                    st.success(t("attachment_deleted", lang))
                    st.rerun()
    else:
        st.caption(t("no_attachments", lang))

    # Uploader
    uploaded_files = st.file_uploader(
        t("upload_new", lang),
        accept_multiple_files=True,
        help=t("upload_help", lang),
        key=f"uploader_{supplier_id}",
    )

    if uploaded_files:
        if st.button("📤 上传选中文件", key=f"do_upload_{supplier_id}"):
            added = 0
            for uf in uploaded_files:
                try:
                    orig, rel = save_uploaded_file(uf, supplier_id)
                    add_attachment(supplier_id, orig, rel, uploaded_by=actor)
                    added += 1
                except Exception as ex:
                    st.error(f"Failed to save {uf.name}: {ex}")
            if added:
                st.success(f"{t('attachment_added', lang)} ({added})")
                st.rerun()

    st.markdown("---")

    # --- Status History ---
    st.markdown(f"#### {t('status_history', lang)}")
    history = get_status_history(supplier_id)
    render_timeline(history, lang)


def _parse_date_or_today(dstr: Optional[str]) -> date:
    if not dstr:
        return date.today()
    try:
        return datetime.strptime(dstr[:10], "%Y-%m-%d").date()
    except Exception:
        return date.today()


def _parse_date_or_none(dstr: Optional[str]) -> Optional[date]:
    if not dstr:
        return None
    try:
        return datetime.strptime(dstr[:10], "%Y-%m-%d").date()
    except Exception:
        return None


# Public entry points ---------------------------------------------------------

def show_add_dialog(lang: str | None = None, current_actor: str | None = None) -> None:
    """Open the add supplier dialog."""
    lang = lang or get_lang()
    _add_dialog_impl(lang, current_actor)


def show_edit_dialog(supplier_id: int, lang: str | None = None, current_actor: str | None = None) -> None:
    """Open the edit dialog for a supplier."""
    lang = lang or get_lang()
    _edit_dialog_impl(supplier_id, lang, current_actor)
