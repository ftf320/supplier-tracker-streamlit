"""
Supplier Registration Tracker (供应商注册追踪系统)
Main entry point. Run with: streamlit run app.py

Clean professional internal tool with full local persistence.
"""

from __future__ import annotations

import streamlit as st

from db.database import init_db
from ui.components import inject_global_css
from ui.dashboard import render_dashboard
from ui.list_view import render_supplier_list
from ui.form import show_add_dialog
from ui.detail import show_detail_dialog  # new rich detail
from utils.i18n import t, get_lang, set_lang
from utils.constants import ACTORS
import os

# ------------------------------------------------------------------
# Page config (must be first Streamlit command)
# ------------------------------------------------------------------
st.set_page_config(
    page_title="供应商注册追踪系统 | Supplier Registration Tracker",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize DB (schema + directories only).
# Demo data seeding is DISABLED. The app now starts completely clean.
init_db(seed_if_empty=False)

# Inject professional CSS
inject_global_css()

# ------------------------------------------------------------------
# Session state defaults
# ------------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state["page"] = "dashboard"
if "lang" not in st.session_state:
    st.session_state["lang"] = "zh"


def _nav_button(label: str, page_key: str, emoji: str = "") -> None:
    """Sidebar nav button that sets current page."""
    is_active = st.session_state.get("page") == page_key
    if st.button(
        f"{emoji} {label}",
        key=f"nav_{page_key}",
        use_container_width=True,
        type="primary" if is_active else "secondary",
    ):
        st.session_state["page"] = page_key
        st.rerun()


def sidebar() -> None:
    """Global sidebar with branding, language, navigation and quick actions."""
    lang = get_lang()

    with st.sidebar:
        # Brand
        st.markdown(
            f"""
            <div style="padding: 6px 4px 12px;">
                <h2 style="margin:0; color:#1E40AF;">📋 {t("app_title", lang)}</h2>
                <div style="color:#64748B; font-size:12px;">{t("app_subtitle", lang)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Language
        st.markdown(f"**{t('language', lang)}**")
        lang_choice = st.radio(
            "lang",
            options=["zh", "en"],
            format_func=lambda x: t("chinese", lang) if x == "zh" else t("english", lang),
            horizontal=True,
            label_visibility="collapsed",
            key="lang_radio",
            index=0 if lang == "zh" else 1,
        )
        if lang_choice != lang:
            set_lang(lang_choice)
            st.rerun()

        st.markdown("---")

        # === Current Actor (team collaboration simulation) ===
        st.markdown(f"**{t('current_actor', lang)}**")
        st.caption(t("current_actor_help", lang))

        current_actor = st.session_state.get("current_actor", ACTORS[0])
        actor_options = ACTORS + [t("actor_custom", lang)]
        # Find index
        try:
            default_idx = actor_options.index(current_actor) if current_actor in actor_options else 0
        except Exception:
            default_idx = 0

        actor_choice = st.selectbox(
            t("actor_label", lang),
            options=actor_options,
            index=default_idx,
            key="actor_select",
            label_visibility="collapsed",
        )

        if actor_choice == t("actor_custom", lang):
            custom = st.text_input(
                "自定义姓名 - 角色",
                value=current_actor if current_actor not in ACTORS else "",
                key="actor_custom_input",
                placeholder="例如：小王 - 财务",
            )
            if custom and custom.strip():
                st.session_state["current_actor"] = custom.strip()
            else:
                st.session_state["current_actor"] = ACTORS[0]
        else:
            st.session_state["current_actor"] = actor_choice

        current_actor = st.session_state.get("current_actor", ACTORS[0])
        st.caption(f"✅ {current_actor}")

        st.markdown("---")

        # Navigation
        st.markdown("**导航 / Navigation**")
        _nav_button(t("dashboard", lang), "dashboard", "📊")
        _nav_button(t("supplier_list", lang), "list", "📋")
        _nav_button(t("add_supplier", lang), "add", "➕")

        st.markdown("---")

        # Quick actions
        st.markdown("**快捷操作**")

        if st.button("📤 " + t("export_all", lang), use_container_width=True, key="sidebar_export_all"):
            from db.database import get_suppliers_df
            from utils.helpers import export_suppliers_to_excel, get_export_filename
            df = get_suppliers_df()
            xlsx = export_suppliers_to_excel(df, lang=lang)
            st.download_button(
                "⬇️ 下载 Excel",
                data=xlsx,
                file_name=get_export_filename(lang),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="sidebar_dl_all",
            )

        st.markdown("---")

        # === Data Management ===
        st.markdown("**数据管理**")

        # Clear all data button (new requirement)
        if st.button("🗑️ 清空所有数据", use_container_width=True, key="sidebar_clear_all"):
            st.session_state["sidebar_clear_confirm"] = True

        if st.session_state.get("sidebar_clear_confirm"):
            st.warning("⚠️ 此操作将永久删除所有供应商记录、状态历史、评论以及所有已上传的文件！\n数据库结构会保留，但数据会全部清空。")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("确认清空", key="sidebar_clear_yes", type="primary"):
                    from db.database import clear_all_data
                    clear_all_data()
                    st.session_state["sidebar_clear_confirm"] = False
                    st.success("所有数据已清空！现在是干净状态。")
                    st.rerun()
            with c2:
                if st.button("取消", key="sidebar_clear_no"):
                    st.session_state["sidebar_clear_confirm"] = False
                    st.rerun()

        st.markdown("---")

        # Footer info
        st.caption("本地数据存储在 ./data 文件夹\nFully local • SQLite + files")
        st.caption("内部工具 • Internal Use Only")

        # Cloud deployment notice (visible on Streamlit Community Cloud)
        if os.getenv("STREAMLIT_SHARING_MODE") or "STREAMLIT_CLOUD" in os.environ or os.getenv("HOSTNAME", "").startswith("streamlit"):
            st.warning(
                "⚠️ 正在 Streamlit Community Cloud 上运行。\n"
                "data/ 目录为临时存储，重启/重新部署后数据和上传的文件会丢失。\n"
                "请定期使用「导出全部」备份重要数据。",
                icon="☁️"
            )


def main() -> None:
    sidebar()
    lang = get_lang()
    current_actor = st.session_state.get("current_actor", "李娜 - 采购经理")

    page = st.session_state.get("page", "dashboard")

    if page == "dashboard":
        render_dashboard(lang, current_actor=current_actor)
    elif page == "list":
        render_supplier_list(lang, current_actor=current_actor)
    elif page == "add":
        # Show prominent add form + also offer direct dialog button
        st.title(t("add_supplier", lang))
        st.info("点击下方按钮打开添加表单（新供应商默认负责人为当前操作人）。附件与评论请在「供应商列表 → 查看详情」中管理。")
        if st.button("➕ 打开添加表单 / Open Add Form", type="primary"):
            show_add_dialog(lang, current_actor=current_actor)
        st.markdown("---")
        st.caption("提示：添加后请到「供应商列表」中选择该行，点击「查看详情」进行文件上传、团队评论和可视化步骤推进。")
    else:
        render_dashboard(lang, current_actor=current_actor)

    # Global help / footer note
    with st.expander("使用提示 / Tips", expanded=False):
        st.markdown(
            """
            - 程序启动时为**完全干净状态**（不再自动生成示例数据）。
            - 左侧「当前操作人」选择器用于模拟团队协作（评论、附件上传、默认负责人均使用该人）。
            - 左侧「数据管理」区域有「🗑️ 清空所有数据」按钮，可一键删除所有记录和上传文件（保留数据库结构）。
            - 所有数据与附件均保存在本地 `data/` 目录，可随时备份整个文件夹。
            - 在「供应商列表」选中一行后点击「查看详情」，使用可视化步骤器推进状态、上传文件（支持拖拽）、发布团队评论。
            - 状态变更 + 评论合并展示在统一活动记录中。
            - 建议定期使用「导出当前结果」备份关键数据。
            """
        )


if __name__ == "__main__":
    main()
