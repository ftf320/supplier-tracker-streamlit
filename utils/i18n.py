"""Simple bilingual (Chinese-first) translation system.

Usage:
    from utils.i18n import t, get_lang, set_lang
    label = t("total_suppliers")
"""

from __future__ import annotations

import streamlit as st

# ------------------------------------------------------------------
# Translation dictionary - Chinese (zh) is complete and primary.
# English (en) is full professional translation.
# ------------------------------------------------------------------
TRANSLATIONS: dict[str, dict[str, str]] = {
    "zh": {
        # App / Nav
        "app_title": "供应商注册追踪系统",
        "app_subtitle": "Supplier Registration Tracker",
        "dashboard": "仪表盘",
        "supplier_list": "供应商列表",
        "add_supplier": "添加供应商",
        "settings": "设置",
        "language": "语言",
        "chinese": "中文",
        "english": "English",
        "switch_lang": "切换语言",

        # Dashboard
        "dashboard_title": "仪表盘概览",
        "total_suppliers": "总供应商数",
        "pending_count": "待处理",
        "approved_count": "已批准",
        "rejected_count": "已拒绝",
        "overdue_count": "逾期未完成",
        "status_distribution": "状态分布",
        "platform_breakdown": "平台分布",
        "recent_activity": "最近活动",
        "no_activity": "暂无活动记录",
        "activity_status_change": "{company}  状态：{old} → {new}",
        "activity_initial": "{company}  新增（初始状态：{status}）",
        "activity_note": "（备注：{note}）",

        # List / Table
        "list_title": "供应商列表",
        "search_placeholder": "搜索公司名称、联系人、备注...",
        "filter_platform": "平台筛选",
        "filter_status": "状态筛选",
        "show_only_overdue": "仅显示逾期",
        "clear_filters": "清除筛选",
        "export_current": "导出当前结果 (Excel)",
        "export_all": "导出全部 (Excel)",
        "no_suppliers": "暂无供应商数据",
        "select_row_hint": "在表格中选择一行以进行编辑、查看详情或删除操作",
        "selected_supplier": "已选中供应商",
        "edit_details": "编辑详情",
        "quick_status_update": "快速更新状态",
        "delete_supplier": "删除供应商",
        "delete_confirm": "确认删除此供应商及其所有附件和历史记录？此操作不可恢复。",
        "delete_success": "供应商已删除",
        "id": "ID",
        "company_cn": "公司名称（中文）",
        "company_en": "公司名称（英文）",
        "platform": "平台",
        "status": "状态",
        "submission_date": "提交日期",
        "deadline": "截止日期",
        "contact": "联系人",
        "overdue_flag": "⚠️ 逾期",
        "not_overdue": "",

        # Form / Add / Edit
        "form_title_add": "添加新供应商",
        "form_title_edit": "编辑供应商",
        "company_name_cn": "公司名称（中文）",
        "company_name_cn_req": "公司名称（中文）*",
        "company_name_en": "公司名称（英文）",
        "company_name_req": "公司名称 *",
        "platform_label": "所属平台*",
        "platform_other": "其他平台名称",
        "status_label": "当前状态*",
        "submission_date_label": "提交日期*",
        "deadline_label": "截止日期",
        "contact_name": "联系人姓名",
        "contact_email": "联系邮箱",
        "contact_phone": "联系电话",
        "notes": "备注",
        "status_change_note": "状态变更说明（可选）",
        "status_change_note_placeholder": "例如：资料已补齐 / 平台反馈问题",
        "attachments_section": "附件管理",
        "current_attachments": "当前附件",
        "no_attachments": "暂无附件",
        "upload_new": "上传新附件（可多选）",
        "upload_help": "支持 PDF、图片、Excel、Word 等。文件将保存在本地 data/uploads/",
        "delete_attachment": "删除",
        "download": "下载",
        "save": "保存",
        "cancel": "取消",
        "save_success": "保存成功！",
        "save_failed": "保存失败",
        "required_field": "必填字段不能为空",
        "back_to_list": "返回列表",

        # History / Timeline
        "status_history": "状态变更历史",
        "history_empty": "暂无变更记录",
        "history_entry": "{time}  {old} → {new}",
        "history_initial": "{time}  初始创建（{status}）",

        # Attachments messages
        "attachment_added": "附件已添加",
        "attachment_deleted": "附件已删除",
        "file_not_found": "文件不存在或已被移动",

        # Export
        "export_success": "Excel 已生成",
        "export_filename": "供应商注册追踪",

        # General / Errors
        "error_generic": "发生错误，请稍后重试",
        "no_selection": "请先在表格中选择一行",
        "confirm": "确认",
        "success": "成功",
        "warning": "警告",

        # Seed / Data (kept for backward compatibility in i18n, but no longer used in UI)
        "seed_completed": "演示数据已重新生成",
        "seed_button": "重新生成演示数据（已停用）",
        "seed_confirm": "这将清空当前所有数据并重新插入演示供应商。确定继续？",

        # === New v2 keys (actor, stepper, comments, detail, KPIs, countries) ===
        "current_actor": "当前操作人",
        "current_actor_help": "选择后，评论、附件上传、默认负责人将使用此人（模拟团队协作）",
        "actor_custom": "其他 / 自定义输入",
        "actor_label": "当前操作人 / Current Actor",

        # Dashboard KPIs (exact spec labels)
        "in_progress_count": "进行中",
        "completed_count": "已完成",
        "delayed_count": "逾期/延误",

        # Detail view
        "detail_view_title": "注册详情 / Registration Detail",
        "visual_stepper": "进度步骤",
        "click_to_advance": "点击步骤可推进状态（非终态）",
        "files_section": "附件管理",
        "upload_hint": "支持多文件上传（可拖拽到上传区）",
        "uploaded_by": "上传人",
        "no_files": "暂无附件",
        "upload_button": "上传选中文件",
        "team_comments": "团队评论",
        "post_comment": "发布评论",
        "comment_placeholder": "记录讨论、补充说明或内部决定...",
        "comment_by": "评论人",
        "no_comments_yet": "暂无评论，团队成员可在此记录进度说明。",
        "activity_feed": "活动记录（状态变更 + 评论）",
        "activity_empty": "暂无活动",
        "edit_basic_info": "编辑基本信息",
        "close": "关闭",
        "advance_note_prompt": "可选备注（将记录到历史）",

        # List / filters / table
        "filter_country": "国家筛选",
        "owner": "负责人",
        "country": "国家",
        "last_updated": "最后更新",
        "view_detail": "查看详情",
        "company_name": "公司名称",
        "platform": "平台",
        "status": "状态",
        "deadline": "截止日期",
        "notes": "备注",
        "overdue": "逾期",

        # List table column help / tooltips
        "status_help": "颜色区分：🔵 进行中/In Progress | 🟢 已批准/Approved | 🟠 资料已提交/Documents Submitted | 其他按语义；逾期以 🔴 红色高亮前缀",
        "notes_help": "仅显示前25字符 + \"...\"（空则显示“—”）。鼠标悬停单元格可查看完整备注内容。",
        "overdue_help": "逾期项使用红色高亮（🔴）",

        # Form additions
        "country_label": "国家 *",
        "owner_label": "内部负责人",
        "owner_placeholder": "默认使用当前操作人，可修改",
        "cnood_entity": "CNOOD Entity",
        "registration_category": "注册品类",
        "supplier_vendor_type": "注册的 supplier/vendor 类型",

        # Step labels (for stepper UI)
        "step_not_started": "未开始",
        "step_in_progress": "进行中",
        "step_documents_submitted": "资料已提交",
        "step_under_review": "审核中",
        "step_approved": "已批准",
        "step_rejected": "已拒绝",
        "step_on_hold": "已搁置",

        # Misc
        "drag_drop_support": "支持拖拽文件到此处",
        "by_actor": "操作人",
    },
    "en": {
        # App / Nav
        "app_title": "Supplier Registration Tracker",
        "app_subtitle": "供应商注册追踪系统",
        "dashboard": "Dashboard",
        "supplier_list": "Suppliers List",
        "add_supplier": "Add Supplier",
        "settings": "Settings",
        "language": "Language",
        "chinese": "中文",
        "english": "English",
        "switch_lang": "Switch Language",

        # Dashboard
        "dashboard_title": "Dashboard Overview",
        "total_suppliers": "Total Suppliers",
        "pending_count": "Pending",
        "approved_count": "Approved",
        "rejected_count": "Rejected",
        "overdue_count": "Overdue",
        "status_distribution": "Status Distribution",
        "platform_breakdown": "Platform Breakdown",
        "recent_activity": "Recent Activity",
        "no_activity": "No recent activity",
        "activity_status_change": "{company}  status: {old} → {new}",
        "activity_initial": "{company}  created (initial: {status})",
        "activity_note": " (note: {note})",

        # List / Table
        "list_title": "Supplier List",
        "search_placeholder": "Search company name, contact, notes...",
        "filter_platform": "Filter by Platform",
        "filter_status": "Filter by Status",
        "show_only_overdue": "Show only overdue",
        "clear_filters": "Clear Filters",
        "export_current": "Export Current Results (Excel)",
        "export_all": "Export All (Excel)",
        "no_suppliers": "No suppliers found",
        "select_row_hint": "Select a row in the table to edit, view details or delete",
        "selected_supplier": "Selected Supplier",
        "edit_details": "Edit Details",
        "quick_status_update": "Quick Status Update",
        "delete_supplier": "Delete Supplier",
        "delete_confirm": "Delete this supplier and ALL its attachments + history? This cannot be undone.",
        "delete_success": "Supplier deleted",
        "id": "ID",
        "company_cn": "Company Name (CN)",
        "company_en": "Company Name (EN)",
        "platform": "Platform",
        "status": "Status",
        "submission_date": "Submission Date",
        "deadline": "Deadline",
        "contact": "Contact",
        "overdue_flag": "⚠️ OVERDUE",
        "not_overdue": "",

        # Form / Add / Edit
        "form_title_add": "Add New Supplier",
        "form_title_edit": "Edit Supplier",
        "company_name_cn": "Company Name (Chinese)",
        "company_name_cn_req": "Company Name (Chinese) *",
        "company_name_en": "Company Name (English)",
        "company_name_req": "Company Name *",
        "platform_label": "Platform *",
        "platform_other": "Other Platform Name",
        "status_label": "Current Status *",
        "submission_date_label": "Submission Date *",
        "deadline_label": "Deadline",
        "contact_name": "Contact Name",
        "contact_email": "Contact Email",
        "contact_phone": "Contact Phone",
        "notes": "Notes",
        "status_change_note": "Status Change Note (optional)",
        "status_change_note_placeholder": "e.g. All documents complete / Platform feedback",
        "attachments_section": "Attachments",
        "current_attachments": "Current Attachments",
        "no_attachments": "No attachments yet",
        "upload_new": "Upload New Attachments (multiple allowed)",
        "upload_help": "PDF, images, Excel, Word, etc. are stored locally in data/uploads/",
        "delete_attachment": "Delete",
        "download": "Download",
        "save": "Save",
        "cancel": "Cancel",
        "save_success": "Saved successfully!",
        "save_failed": "Save failed",
        "required_field": "Required fields cannot be empty",
        "back_to_list": "Back to List",

        # History / Timeline
        "status_history": "Status Change History",
        "history_empty": "No history records",
        "history_entry": "{time}  {old} → {new}",
        "history_initial": "{time}  Created (status: {status})",

        # Attachments messages
        "attachment_added": "Attachment added",
        "attachment_deleted": "Attachment deleted",
        "file_not_found": "File not found or has been moved",

        # Export
        "export_success": "Excel file generated",
        "export_filename": "Supplier_Registration_Tracker",

        # General / Errors
        "error_generic": "An error occurred. Please try again later.",
        "no_selection": "Please select a row in the table first",
        "confirm": "Confirm",
        "success": "Success",
        "warning": "Warning",

        # Seed / Data (kept for backward compatibility in i18n, but no longer used in UI)
        "seed_completed": "Demo data regenerated",
        "seed_button": "Regenerate Demo Data (disabled)",
        "seed_confirm": "This will DELETE all current data and insert fresh demo suppliers. Continue?",

        # === New v2 keys (actor, stepper, comments, detail, KPIs, countries) ===
        "current_actor": "Current Actor",
        "current_actor_help": "Comments, file uploads and default owner will use this person (team simulation)",
        "actor_custom": "Other / Custom",
        "actor_label": "Current Actor / 当前操作人",

        # Dashboard KPIs (exact spec labels)
        "in_progress_count": "In Progress",
        "completed_count": "Completed",
        "delayed_count": "Delayed",

        # Detail view
        "detail_view_title": "Registration Detail",
        "visual_stepper": "Workflow Stepper",
        "click_to_advance": "Click a step to advance (non-terminal states)",
        "files_section": "Attachments",
        "upload_hint": "Multiple files supported — drag & drop into the uploader",
        "uploaded_by": "Uploaded by",
        "no_files": "No attachments yet",
        "upload_button": "Upload Selected Files",
        "team_comments": "Team Comments",
        "post_comment": "Post Comment",
        "comment_placeholder": "Record discussion, clarifications or internal decisions...",
        "comment_by": "By",
        "no_comments_yet": "No comments yet. Team members can post notes here.",
        "activity_feed": "Activity Feed (status changes + comments)",
        "activity_empty": "No activity recorded",
        "edit_basic_info": "Edit Basic Info",
        "close": "Close",
        "advance_note_prompt": "Optional note (will be logged)",

        # List / filters / table
        "filter_country": "Filter by Country",
        "owner": "Owner",
        "country": "Country",
        "last_updated": "Last Updated",
        "view_detail": "View Detail",
        "company_name": "Company Name",
        "platform": "Platform",
        "status": "Status",
        "deadline": "Deadline",
        "notes": "Notes",
        "overdue": "Overdue",

        # List table column help / tooltips
        "status_help": "Color legend: 🔵 In Progress | 🟢 Approved | 🟠 Documents Submitted | others semantic; Overdue highlighted with 🔴 red prefix",
        "notes_help": "Shows first 25 chars + \"...\" (empty shows \"—\"). Hover cell to see full notes content.",
        "overdue_help": "Overdue rows highlighted in red (🔴)",

        # Form additions
        "country_label": "Country *",
        "owner_label": "Internal Owner",
        "owner_placeholder": "Defaults to current actor (editable)",
        "cnood_entity": "CNOOD Entity",
        "registration_category": "Registration Category",
        "supplier_vendor_type": "Supplier/Vendor Type",

        # Step labels
        "step_not_started": "Not Started",
        "step_in_progress": "In Progress",
        "step_documents_submitted": "Documents Submitted",
        "step_under_review": "Under Review",
        "step_approved": "Approved",
        "step_rejected": "Rejected",
        "step_on_hold": "On Hold",

        # Misc
        "drag_drop_support": "Drag & drop files here or click to select",
        "by_actor": "Actor",
    },
}


def get_lang() -> str:
    """Return current language code from session state (defaults to zh)."""
    if "lang" not in st.session_state:
        st.session_state["lang"] = "zh"
    return st.session_state["lang"]


def set_lang(lang: str) -> None:
    if lang in ("zh", "en"):
        st.session_state["lang"] = lang


def t(key: str, lang: str | None = None, **kwargs) -> str:
    """
    Translate key. Falls back to key itself if missing.
    Supports simple .format(**kwargs) interpolation.
    """
    if lang is None:
        lang = get_lang()
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS["zh"])
    text = lang_dict.get(key, TRANSLATIONS["zh"].get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
