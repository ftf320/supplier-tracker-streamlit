"""Suppliers list page with powerful filtering, interactive table, and actions."""

from __future__ import annotations

import streamlit as st
import pandas as pd

from db.database import (
    get_suppliers_df,
    delete_supplier,
    change_status,
    get_supplier,
)
from ui.components import (
    inject_global_css,
    render_status_badge,
    get_status_display,
)
from ui.form import show_add_dialog, show_edit_dialog
from ui.detail import show_detail_dialog
from utils.helpers import (
    is_overdue,
    format_date,
    get_export_filename,
    export_suppliers_to_excel,
    delete_all_attachments_for_supplier,  # now handles Supabase Storage too
)
from utils.i18n import t, get_lang
from utils.constants import STATUSES, COUNTRIES


def _apply_filters(
    df: pd.DataFrame,
    search_text: str,
    platforms: list[str],
    statuses: list[str],
    countries: list[str],
    cnood_entities: list[str],
    registration_categories: list[str],
    supplier_vendor_types: list[str],
    only_overdue: bool,
) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    filtered = df.copy()

    # Search across several columns (now includes country + owner)
    if search_text and search_text.strip():
        q = search_text.strip().lower()
        mask = (
            filtered["company_name_cn"].astype(str).str.lower().str.contains(q, na=False)
            | filtered["company_name_en"].astype(str).str.lower().str.contains(q, na=False)
            | filtered["contact_name"].astype(str).str.lower().str.contains(q, na=False)
            | filtered.get("owner", pd.Series([""] * len(filtered))).astype(str).str.lower().str.contains(q, na=False)
            | filtered["notes"].astype(str).str.lower().str.contains(q, na=False)
            | filtered.get("country", pd.Series([""] * len(filtered))).astype(str).str.lower().str.contains(q, na=False)
            | filtered.get("cnood_entity", pd.Series([""] * len(filtered))).astype(str).str.lower().str.contains(q, na=False)
            | filtered.get("registration_category", pd.Series([""] * len(filtered))).astype(str).str.lower().str.contains(q, na=False)
            | filtered.get("supplier_vendor_type", pd.Series([""] * len(filtered))).astype(str).str.lower().str.contains(q, na=False)
        )
        filtered = filtered[mask]

    # Platform multi-select
    if platforms:
        filtered = filtered[filtered["platform"].isin(platforms)]

    # Status multi-select
    if statuses:
        filtered = filtered[filtered["status"].isin(statuses)]

    # Country multi-select
    if countries:
        filtered = filtered[filtered["country"].isin(countries)]

    # New fields multi-select filters
    if cnood_entities:
        filtered = filtered[filtered.get("cnood_entity", "").fillna("").isin(cnood_entities)]

    if registration_categories:
        filtered = filtered[filtered.get("registration_category", "").fillna("").isin(registration_categories)]

    if supplier_vendor_types:
        filtered = filtered[filtered.get("supplier_vendor_type", "").fillna("").isin(supplier_vendor_types)]

    # Only overdue
    if only_overdue:
        mask = filtered.apply(
            lambda r: is_overdue(r.get("deadline"), r.get("status", "")), axis=1
        )
        filtered = filtered[mask]

    return filtered


def _prepare_display_df(df: pd.DataFrame, lang: str) -> pd.DataFrame:
    """Create a nice dataframe for st.dataframe with display columns.
    Company name is now a single unified field (merged input).
    """
    if df.empty:
        return pd.DataFrame(columns=["ID", "公司名称", "国家", "平台", "状态", "截止日期", "负责人", "CNOOD Entity", "注册品类", "注册的 supplier/vendor 类型", "备注", "逾期"])

    disp = pd.DataFrame()
    disp["ID"] = df["id"]

    # Single company name (prefer cn, fallback to en for legacy data)
    disp["公司名称"] = df.apply(
        lambda r: (r.get("company_name_cn") or r.get("company_name_en") or "").strip(),
        axis=1,
    )

    disp["国家"] = df.get("country", "").fillna("")
    disp["平台"] = df["platform"]
    disp["提交日期"] = df["submission_date"].apply(lambda d: format_date(d))
    disp["截止日期"] = df["deadline"].apply(lambda d: format_date(d))

    disp["负责人"] = df.get("owner", df.get("contact_name", "")).fillna("")

    # New fields
    disp["CNOOD Entity"] = df.get("cnood_entity", "").fillna("")
    disp["注册品类"] = df.get("registration_category", "").fillna("")
    disp["注册的 supplier/vendor 类型"] = df.get("supplier_vendor_type", "").fillna("")

    # 备注 (notes) optimization:
    # - Show only first 25 characters + "..." 
    # - Empty notes display as "—"
    # - Full content will be available via tooltip / cell hover (aided by column_config help)
    notes = df.get("notes", pd.Series([""] * len(df))).fillna("").astype(str).str.strip()
    def _format_remarks(n: str) -> str:
        if not n:
            return "—"
        return n[:25] + "..." if len(n) > 25 else n
    disp["备注"] = notes.apply(_format_remarks)

    # Status with semantic colors (using emojis for visual distinction via column_config display)
    # + Overdue red highlight (prepended red indicator)
    def _format_status_with_colors(row) -> str:
        status = row.get("status", "")
        base_display = get_status_display(status, lang)

        # Overdue takes precedence with strong red highlight
        if is_overdue(row.get("deadline"), status):
            return "🔴 " + base_display  # Red for overdue

        s_lower = status.lower()
        # Specific color semantics as requested
        if any(k in s_lower for k in ["in progress", "进行中", "审核中"]):
            return "🔵 " + status  # Blue for in progress
        elif any(k in s_lower for k in ["approved", "已批准"]):
            return "🟢 " + status  # Green for approved
        elif any(k in s_lower for k in ["documents submitted", "资料已提交", "已提交"]):
            return "🟠 " + status  # Orange for documents submitted
        # Other statuses keep the original emoji coloring from get_status_display
        return base_display

    disp["状态"] = df.apply(_format_status_with_colors, axis=1)

    # Overdue flag (kept for quick visual scan, now complemented by red status prefix)
    disp["逾期"] = df.apply(
        lambda r: "🔴 逾期" if is_overdue(r.get("deadline"), r.get("status", "")) else "",
        axis=1,
    )

    # Reorder for clarity
    # Note: 公司名称 and 国家 are placed early so pinned=True in column_config works well
    cols = ["ID", "公司名称", "国家", "平台", "状态", "截止日期", "负责人", "CNOOD Entity", "注册品类", "注册的 supplier/vendor 类型", "备注", "逾期"]
    return disp[[c for c in cols if c in disp.columns]]


def render_supplier_list(lang: str | None = None, current_actor: str | None = None) -> None:
    lang = lang or get_lang()
    actor = current_actor or "李娜 - 采购经理"
    inject_global_css()

    st.title(t("list_title", lang))

    # Load data
    full_df = get_suppliers_df()

    # --- Top filter bar ---
    with st.container():
        f1, f2, f3, f4, f5, f6 = st.columns([2.0, 1.35, 1.35, 1.35, 1.0, 0.9])

        with f1:
            search = st.text_input(
                "🔍",
                placeholder=t("search_placeholder", lang),
                label_visibility="collapsed",
                key="list_search",
            )

        with f2:
            all_platforms = sorted(full_df["platform"].dropna().unique().tolist()) if not full_df.empty else []
            platforms = st.multiselect(
                t("filter_platform", lang),
                options=all_platforms,
                default=[],
                key="list_platforms",
            )

        with f3:
            statuses = st.multiselect(
                t("filter_status", lang),
                options=STATUSES,
                default=[],
                key="list_statuses",
            )

        with f4:
            all_countries = sorted(full_df["country"].dropna().unique().tolist()) if not full_df.empty else COUNTRIES
            countries = st.multiselect(
                t("filter_country", lang),
                options=all_countries,
                default=[],
                key="list_countries",
            )

        with f5:
            only_overdue = st.checkbox(
                t("show_only_overdue", lang),
                value=False,
                key="list_only_overdue",
            )

        with f6:
            if st.button(t("clear_filters", lang), use_container_width=True, key="clear_btn"):
                for k in ["list_search", "list_platforms", "list_statuses", "list_countries", "list_only_overdue",
                          "list_cnood", "list_reg_cat", "list_vtype"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()

    # --- Additional filters for new fields (CNOOD Entity, 注册品类, supplier/vendor type) ---
    with st.container():
        nf1, nf2, nf3 = st.columns(3)
        with nf1:
            all_cnood = sorted(full_df.get("cnood_entity", pd.Series(dtype=str)).dropna().unique().tolist()) if not full_df.empty else []
            cnood_entities = st.multiselect(
                "CNOOD Entity",
                options=all_cnood,
                default=[],
                key="list_cnood",
            )
        with nf2:
            all_reg = sorted(full_df.get("registration_category", pd.Series(dtype=str)).dropna().unique().tolist()) if not full_df.empty else []
            registration_categories = st.multiselect(
                "注册品类",
                options=all_reg,
                default=[],
                key="list_reg_cat",
            )
        with nf3:
            all_vtype = sorted(full_df.get("supplier_vendor_type", pd.Series(dtype=str)).dropna().unique().tolist()) if not full_df.empty else []
            supplier_vendor_types = st.multiselect(
                "注册的 supplier/vendor 类型",
                options=all_vtype,
                default=[],
                key="list_vtype",
            )

    # Apply filters (keep a "source" copy with original full_df rows for export)
    filtered_source = _apply_filters(
        full_df, search or "", platforms or [], statuses or [], countries or [],
        cnood_entities or [], registration_categories or [], supplier_vendor_types or [], only_overdue
    )
    filtered_df = _prepare_display_df(filtered_source, lang)

    # Action buttons row (removed old demo reseed button per requirement to disable auto/manual demo seeding)
    btn_col1, btn_spacer, btn_col2 = st.columns([1.4, 3.2, 1.6])
    with btn_col1:
        if st.button("➕ " + t("add_supplier", lang), type="primary", use_container_width=True):
            show_add_dialog(lang, current_actor=actor)

    with btn_col2:
        # Export current (respects active filters)
        if st.button("📤 " + t("export_current", lang), use_container_width=True):
            if filtered_source.empty:
                st.warning(t("no_suppliers", lang))
            else:
                export_bytes = export_suppliers_to_excel(filtered_source, lang=lang)
                st.download_button(
                    label="⬇️ 下载 Excel",
                    data=export_bytes,
                    file_name=get_export_filename(lang),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_current",
                )

    # Also global export all (always available)
    with st.expander("更多导出选项", expanded=False):
        if st.button("📤 " + t("export_all", lang), use_container_width=False):
            all_bytes = export_suppliers_to_excel(full_df, lang=lang)
            st.download_button(
                "⬇️ 下载全部数据 Excel",
                data=all_bytes,
                file_name=get_export_filename(lang),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    st.markdown("---")

    # === Main interactive table ===
    # display_df already prepared above as filtered_df (the display version)
    if filtered_df.empty:
        st.info(t("no_suppliers", lang))
        return

    st.caption(t("select_row_hint", lang))

    event = st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="supplier_table",
        column_config={
            # Pinned columns: 公司名称 and 国家 always stay visible on the left when scrolling
            "ID": st.column_config.NumberColumn(width="small"),
            "公司名称": st.column_config.TextColumn(
                "公司名称",
                width="medium",
                pinned=True,  # Freeze / pin to left
            ),
            "国家": st.column_config.TextColumn(
                "国家",
                width="small",
                pinned=True,  # Freeze / pin to left
            ),
            "平台": st.column_config.TextColumn(width="small"),
            "状态": st.column_config.TextColumn(
                "状态",
                width="large",
                help="颜色区分：🔵 In Progress/进行中 | 🟢 Approved/已批准 | 🟠 Documents Submitted/资料已提交 | 其他状态按语义着色；逾期以 🔴 红色高亮前缀显示",
            ),
            "截止日期": st.column_config.TextColumn(width="medium"),
            # 备注 column: truncated display + tooltip guidance for full content on hover
            "备注": st.column_config.TextColumn(
                "备注",
                width="medium",
                help="仅显示前25字符 + \"...\"（空则显示“—”）。鼠标悬停单元格可查看完整备注内容。",
            ),
            "负责人": st.column_config.TextColumn(width="small"),
            "逾期": st.column_config.TextColumn(
                "逾期",
                width="small",
                help="逾期项使用红色高亮（🔴 逾期）",
            ),
            # Other dynamic columns keep default styling
            "CNOOD Entity": st.column_config.TextColumn(width="small"),
            "注册品类": st.column_config.TextColumn(width="small"),
            "注册的 supplier/vendor 类型": st.column_config.TextColumn(width="small"),
        },
    )

    selected_rows = event.selection.rows if hasattr(event, "selection") else []
    selected_id = None
    if selected_rows:
        # Map back to original ID
        try:
            selected_id = int(filtered_df.iloc[selected_rows[0]]["ID"])
        except Exception:
            selected_id = None

    # === Action panel for selected supplier ===
    if selected_id is not None:
        supplier = get_supplier(selected_id)
        if supplier:
            st.markdown('<div class="action-panel">', unsafe_allow_html=True)
            st.markdown(f"### {t('selected_supplier', lang)} #{selected_id}")

            # Quick info
            cols = st.columns([2.5, 1.5, 1.5, 1.5])
            with cols[0]:
                # Single unified company name
                company_display = supplier.get('company_name_cn') or supplier.get('company_name_en') or ''
                st.markdown(f"**{company_display}**", unsafe_allow_html=True)
            with cols[1]:
                st.markdown(render_status_badge(supplier.get("status", ""), size="normal"), unsafe_allow_html=True)
            with cols[2]:
                dl = format_date(supplier.get("deadline"))
                if is_overdue(supplier.get("deadline"), supplier.get("status", "")):
                    st.markdown(f'<span class="overdue-text">⚠️ {dl}</span>', unsafe_allow_html=True)
                else:
                    st.write(dl)
            with cols[3]:
                st.caption(supplier.get("platform", ""))

            # Action buttons - View Detail is primary (rich stepper + files + comments)
            a1, a2, a3, a4 = st.columns(4)
            with a1:
                if st.button("📋 " + t("view_detail", lang), type="primary", use_container_width=True, key=f"detail_{selected_id}"):
                    show_detail_dialog(selected_id, current_actor=actor, lang=lang)

            with a2:
                if st.button("✏️ " + t("edit_details", lang), use_container_width=True, key=f"edit_{selected_id}"):
                    show_edit_dialog(selected_id, lang=lang, current_actor=actor)

            with a3:
                # Quick status (still useful)
                new_status = st.selectbox(
                    t("quick_status_update", lang),
                    options=STATUSES,
                    index=STATUSES.index(supplier["status"]) if supplier["status"] in STATUSES else 0,
                    key=f"quick_status_{selected_id}",
                    label_visibility="collapsed",
                )
                if st.button("更新状态", key=f"update_status_{selected_id}", use_container_width=True):
                    if new_status != supplier["status"]:
                        change_status(selected_id, new_status, note=f"列表快速更新 by {actor}")
                        st.success(t("save_success", lang))
                        st.rerun()
                    else:
                        st.info("状态未改变")

            with a4:
                if st.button("🗑️ " + t("delete_supplier", lang), use_container_width=True):
                    st.session_state["delete_target"] = selected_id

            # Delete confirm
            if st.session_state.get("delete_target") == selected_id:
                st.warning(t("delete_confirm", lang))
                dc1, dc2 = st.columns(2)
                with dc1:
                    if st.button("✅ 确认删除", type="primary", key="confirm_delete"):
                        # Clean files
                        from utils.helpers import delete_all_attachments_for_supplier  # Supabase Storage aware
                        delete_all_attachments_for_supplier(selected_id)
                        delete_supplier(selected_id)
                        st.session_state.pop("delete_target", None)
                        st.success(t("delete_success", lang))
                        st.rerun()
                with dc2:
                    if st.button("取消", key="cancel_delete"):
                        st.session_state.pop("delete_target", None)
                        st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.caption("↑ " + t("select_row_hint", lang))
