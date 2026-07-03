"""Central constants for the Supplier Registration Tracker.

Canonical (stored) values use the English workflow per spec.
Chinese display labels are provided via get_status_label() + i18n.
"""

from __future__ import annotations

# === Canonical workflow statuses (stored in DB, used for logic) ===
STATUSES: list[str] = [
    "Not Started",
    "In Progress",
    "Documents Submitted",
    "Under Review",
    "Approved",
    "Rejected",
    "On Hold",
]

# Statuses considered "terminal" (no longer active workflow; never count as overdue)
TERMINAL_STATUSES: set[str] = {"Approved", "Rejected", "On Hold"}

# "In Progress" group for dashboard KPI (everything active in the main flow)
IN_PROGRESS_STATUSES: set[str] = {"In Progress", "Documents Submitted", "Under Review"}

# "Completed" for dashboard (Approved is the success terminal)
COMPLETED_STATUSES: set[str] = {"Approved"}

# === Platforms (focused on foreign-supplier procurement portals per reference) ===
PLATFORMS: list[str] = [
    "SAIPREM",
    "SupplHi",
    "Target Portal",
    "Other",
]

# === Countries (for filters + realistic foreign seed) ===
COUNTRIES: list[str] = [
    "Germany",
    "Japan",
    "United States",
    "Vietnam",
    "South Korea",
    "India",
    "China",
    "Other",
]

# === Fixed actor (simplified from previous Current Actor picker) ===
# All comments, uploads, owner defaults, and status notes now use this single fixed value.
FIXED_ACTOR: str = "Stella - 注册"

# Professional color palette for status badges (hex) — updated for new statuses
STATUS_COLORS: dict[str, str] = {
    "Not Started": "#94A3B8",          # slate gray
    "In Progress": "#3B82F6",          # blue
    "Documents Submitted": "#8B5CF6",  # violet
    "Under Review": "#F59E0B",         # amber
    "Approved": "#10B981",             # emerald green
    "Rejected": "#EF4444",             # red
    "On Hold": "#64748B",              # neutral slate
}

# Fallback / neutral
DEFAULT_COLOR = "#64748B"

# For dashboard cards etc.
METRIC_COLORS = {
    "total": "#1E40AF",
    "in_progress": "#3B82F6",
    "completed": "#10B981",
    "delayed": "#DC2626",
    "overdue": "#DC2626",
}


def get_status_label(status: str, lang: str = "zh") -> str:
    """Return localized label for a canonical status. Falls back to status itself."""
    zh_map = {
        "Not Started": "未开始",
        "In Progress": "进行中",
        "Documents Submitted": "资料已提交",
        "Under Review": "审核中",
        "Approved": "已批准",
        "Rejected": "已拒绝",
        "On Hold": "已搁置",
    }
    en_map = {
        "Not Started": "Not Started",
        "In Progress": "In Progress",
        "Documents Submitted": "Documents Submitted",
        "Under Review": "Under Review",
        "Approved": "Approved",
        "Rejected": "Rejected",
        "On Hold": "On Hold",
    }
    if lang == "zh":
        return zh_map.get(status, status)
    return en_map.get(status, status)


def get_status_color(status: str) -> str:
    return STATUS_COLORS.get(status, DEFAULT_COLOR)
