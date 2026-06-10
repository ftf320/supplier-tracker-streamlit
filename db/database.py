"""Database layer for Supplier Registration Tracker.

All persistence via SQLite. Everything lives under data/.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from utils.constants import STATUSES, PLATFORMS, TERMINAL_STATUSES, COUNTRIES, ACTORS

# ------------------------------------------------------------------
# Paths & constants - robust for local dev and Streamlit Community Cloud deploys
# (data/ will be created next to the project source regardless of CWD)
# ------------------------------------------------------------------
def _get_project_root() -> Path:
    """Return the project root (supplier-tracker-streamlit/) reliably."""
    # __file__ is .../db/database.py → parent is db/ → parent.parent is project root
    return Path(__file__).resolve().parent.parent

PROJECT_ROOT = _get_project_root()
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "suppliers.db"
UPLOADS_DIR = DATA_DIR / "uploads"


def ensure_data_dirs() -> None:
    """Create data/ and uploads/ if they don't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Return a connection with row factory for dict-like access."""
    ensure_data_dirs()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    if row is None:
        return {}
    return {k: row[k] for k in row.keys()}


# ------------------------------------------------------------------
# Schema
# ------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name_cn TEXT NOT NULL,
    company_name_en TEXT,
    country TEXT NOT NULL DEFAULT 'China',
    platform TEXT NOT NULL,
    status TEXT NOT NULL,
    submission_date TEXT,
    deadline TEXT,
    contact_name TEXT,
    owner TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_suppliers_status ON suppliers(status);
CREATE INDEX IF NOT EXISTS idx_suppliers_platform ON suppliers(platform);
CREATE INDEX IF NOT EXISTS idx_suppliers_country ON suppliers(country);
CREATE INDEX IF NOT EXISTS idx_suppliers_owner ON suppliers(owner);
CREATE INDEX IF NOT EXISTS idx_suppliers_deadline ON suppliers(deadline);

CREATE TABLE IF NOT EXISTS status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    note TEXT,
    changed_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_history_supplier ON status_history(supplier_id);

CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    original_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    uploaded_by TEXT,
    uploaded_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_attachments_supplier ON attachments(supplier_id);

CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    author TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_comments_supplier ON comments(supplier_id);
"""


def init_db(seed_if_empty: bool = False) -> None:
    """Initialize schema and data directories.
    NOTE: Auto-seeding of demo data has been disabled.
    The database will start completely empty. Use the UI "清空所有数据" for manual reset.
    The old _seed_demo_data function remains for manual/testing use only.
    """
    ensure_data_dirs()
    with closing(get_connection()) as conn:
        conn.executescript(SCHEMA)
        conn.commit()

        # Safe forward migrations for existing DBs (idempotent)
        _apply_migrations(conn)

        # Auto-seeding is intentionally disabled (seed_if_empty default is now False).
        # if seed_if_empty:
        #     cur = conn.execute("SELECT COUNT(*) as cnt FROM suppliers")
        #     count = cur.fetchone()["cnt"]
        #     if count == 0:
        #         _seed_demo_data(conn)
        #         conn.commit()


def _bump_updated_at(conn: sqlite3.Connection, supplier_id: int) -> None:
    conn.execute(
        "UPDATE suppliers SET updated_at = datetime('now', 'localtime') WHERE id = ?",
        (supplier_id,),
    )


def _log_status_change(
    conn: sqlite3.Connection,
    supplier_id: int,
    old_status: Optional[str],
    new_status: str,
    note: Optional[str] = None,
) -> None:
    """Insert a history record. Call inside a transaction."""
    conn.execute(
        """
        INSERT INTO status_history (supplier_id, old_status, new_status, note)
        VALUES (?, ?, ?, ?)
        """,
        (supplier_id, old_status, new_status, note),
    )


def _apply_migrations(conn: sqlite3.Connection) -> None:
    """Add new columns/tables for v2 schema (country, owner, uploaded_by, comments). Idempotent."""
    # suppliers columns
    for col, default in [
        ("country TEXT NOT NULL DEFAULT 'China'", "'China'"),
        ("owner TEXT", "NULL"),
    ]:
        try:
            if "owner" in col:
                conn.execute("ALTER TABLE suppliers ADD COLUMN owner TEXT")
            else:
                conn.execute("ALTER TABLE suppliers ADD COLUMN country TEXT NOT NULL DEFAULT 'China'")
        except Exception:
            pass  # already exists

    # attachments uploaded_by
    try:
        conn.execute("ALTER TABLE attachments ADD COLUMN uploaded_by TEXT")
    except Exception:
        pass

    # comments table (if not created by SCHEMA on very old DBs)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER NOT NULL,
                author TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_comments_supplier ON comments(supplier_id)")
    except Exception:
        pass


# ------------------------------------------------------------------
# Suppliers CRUD
# ------------------------------------------------------------------
def get_supplier(supplier_id: int) -> Optional[Dict[str, Any]]:
    with closing(get_connection()) as conn:
        row = conn.execute(
            "SELECT * FROM suppliers WHERE id = ?", (supplier_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None


def get_all_suppliers() -> List[Dict[str, Any]]:
    with closing(get_connection()) as conn:
        rows = conn.execute(
            "SELECT * FROM suppliers ORDER BY updated_at DESC, id DESC"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def get_suppliers_df() -> pd.DataFrame:
    """Convenience: return all suppliers as DataFrame (for filtering/export)."""
    suppliers = get_all_suppliers()
    if not suppliers:
        # Return empty DF with expected columns (v2)
        return pd.DataFrame(
            columns=[
                "id",
                "company_name_cn",
                "company_name_en",
                "country",
                "platform",
                "status",
                "submission_date",
                "deadline",
                "contact_name",
                "owner",
                "contact_email",
                "contact_phone",
                "notes",
                "created_at",
                "updated_at",
            ]
        )
    return pd.DataFrame(suppliers)


def add_supplier(data: Dict[str, Any]) -> int:
    """
    Insert a new supplier. Returns new id.
    data keys: company_name_cn (req), company_name_en, country, platform (req),
               status (req), submission_date, deadline, contact_name, owner, contact_*, notes
    """
    ensure_data_dirs()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with closing(get_connection()) as conn:
        with conn:
            cur = conn.execute(
                """
                INSERT INTO suppliers (
                    company_name_cn, company_name_en, country, platform, status,
                    submission_date, deadline, contact_name, owner, contact_email,
                    contact_phone, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.get("company_name_cn"),
                    data.get("company_name_en"),
                    data.get("country") or "Other",
                    data.get("platform"),
                    data.get("status"),
                    data.get("submission_date"),
                    data.get("deadline"),
                    data.get("contact_name"),
                    data.get("owner"),
                    data.get("contact_email"),
                    data.get("contact_phone"),
                    data.get("notes"),
                    now,
                    now,
                ),
            )
            supplier_id = cur.lastrowid

            # Log initial status as history (no old_status)
            actor = data.get("owner") or ""
            init_note = f"初始创建{' by ' + actor if actor else ''}"
            _log_status_change(conn, supplier_id, None, data.get("status"), init_note)
            return supplier_id


def update_supplier(supplier_id: int, data: Dict[str, Any], status_note: Optional[str] = None) -> None:
    """
    Update supplier fields. If status changed, automatically log to history.
    """
    current = get_supplier(supplier_id)
    if not current:
        raise ValueError(f"Supplier {supplier_id} not found")

    old_status = current.get("status")
    new_status = data.get("status", old_status)

    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                """
                UPDATE suppliers SET
                    company_name_cn = ?,
                    company_name_en = ?,
                    country = ?,
                    platform = ?,
                    status = ?,
                    submission_date = ?,
                    deadline = ?,
                    contact_name = ?,
                    owner = ?,
                    contact_email = ?,
                    contact_phone = ?,
                    notes = ?,
                    updated_at = datetime('now', 'localtime')
                WHERE id = ?
                """,
                (
                    data.get("company_name_cn"),
                    data.get("company_name_en"),
                    data.get("country") or current.get("country") or "Other",
                    data.get("platform"),
                    new_status,
                    data.get("submission_date"),
                    data.get("deadline"),
                    data.get("contact_name"),
                    data.get("owner"),
                    data.get("contact_email"),
                    data.get("contact_phone"),
                    data.get("notes"),
                    supplier_id,
                ),
            )

            if new_status != old_status:
                note = status_note
                if note and data.get("owner"):
                    note = f"{note} (by {data.get('owner')})"
                _log_status_change(conn, supplier_id, old_status, new_status, note)

            _bump_updated_at(conn, supplier_id)  # safety


def delete_supplier(supplier_id: int) -> None:
    """Delete supplier (attachments and history cascade via FK)."""
    with closing(get_connection()) as conn:
        with conn:
            conn.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))


# ------------------------------------------------------------------
# Status history
# ------------------------------------------------------------------
def get_status_history(supplier_id: int) -> List[Dict[str, Any]]:
    with closing(get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT * FROM status_history
            WHERE supplier_id = ?
            ORDER BY changed_at DESC, id DESC
            """,
            (supplier_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def change_status(
    supplier_id: int, new_status: str, note: Optional[str] = None
) -> None:
    """Convenience wrapper to change only status (and log)."""
    current = get_supplier(supplier_id)
    if not current:
        raise ValueError("Supplier not found")
    if new_status == current["status"]:
        return
    data = current.copy()
    data["status"] = new_status
    update_supplier(supplier_id, data, status_note=note)


# ------------------------------------------------------------------
# Attachments (metadata only; file IO handled by caller/helpers)
# ------------------------------------------------------------------
def add_attachment(
    supplier_id: int, original_filename: str, stored_path: str, uploaded_by: Optional[str] = None
) -> int:
    with closing(get_connection()) as conn:
        with conn:
            cur = conn.execute(
                """
                INSERT INTO attachments (supplier_id, original_filename, stored_path, uploaded_by)
                VALUES (?, ?, ?, ?)
                """,
                (supplier_id, original_filename, stored_path, uploaded_by),
            )
            _bump_updated_at(conn, supplier_id)
            return cur.lastrowid


def get_attachments(supplier_id: int) -> List[Dict[str, Any]]:
    with closing(get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT * FROM attachments
            WHERE supplier_id = ?
            ORDER BY uploaded_at DESC
            """,
            (supplier_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def delete_attachment(attachment_id: int) -> Optional[int]:
    """Delete attachment record. Returns supplier_id for file cleanup by caller."""
    with closing(get_connection()) as conn:
        with conn:
            row = conn.execute(
                "SELECT supplier_id FROM attachments WHERE id = ?",
                (attachment_id,),
            ).fetchone()
            if not row:
                return None
            supplier_id = row["supplier_id"]
            conn.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
            _bump_updated_at(conn, supplier_id)
            return supplier_id


# ------------------------------------------------------------------
# Team Comments (separate from status history)
# ------------------------------------------------------------------
def get_comments(supplier_id: int) -> List[Dict[str, Any]]:
    with closing(get_connection()) as conn:
        rows = conn.execute(
            """
            SELECT * FROM comments
            WHERE supplier_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (supplier_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def add_comment(supplier_id: int, author: str, content: str) -> int:
    with closing(get_connection()) as conn:
        with conn:
            cur = conn.execute(
                """
                INSERT INTO comments (supplier_id, author, content)
                VALUES (?, ?, ?)
                """,
                (supplier_id, author, content),
            )
            _bump_updated_at(conn, supplier_id)
            return cur.lastrowid


# ------------------------------------------------------------------
# Data management (clear / reset without dropping schema)
# ------------------------------------------------------------------
def clear_all_data() -> None:
    """Delete ALL supplier records (and cascaded history/attachments/comments rows)
    and physically remove all uploaded files under data/uploads/.

    The database file (data/suppliers.db) and table structures are preserved.
    The uploads directory is recreated as empty.

    This is the recommended way to return to a completely clean state.
    """
    from pathlib import Path as _Path
    import shutil as _shutil

    # 1. Remove all data rows (foreign key cascades will clean related tables)
    with closing(get_connection()) as conn:
        with conn:
            conn.execute("DELETE FROM suppliers")

    # 2. Remove physical uploaded files (use the same robust path)
    uploads_root = DATA_DIR / "uploads"
    if uploads_root.exists():
        _shutil.rmtree(uploads_root, ignore_errors=True)

    # 3. Recreate empty uploads directory
    uploads_root.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------------
# Seed data (realistic demo suppliers - 8 foreign-focused)
# NOTE: This function is no longer called automatically on startup.
# ------------------------------------------------------------------
def _seed_demo_data(conn: sqlite3.Connection) -> None:
    """Insert exactly 8 realistic foreign-focused supplier records + history + comments + real sample files."""
    from pathlib import Path as _Path
    import time as _time

    today = date.today()
    # 8 diverse records focused on foreign companies (Germany, Japan, US, Vietnam, Korea, India, China-ref, US)
    demo_suppliers = [
        {
            "company_name_cn": "缪勒精密部件有限公司",
            "company_name_en": "Müller GmbH Precision Components",
            "country": "Germany",
            "platform": "SAIPREM",
            "status": "Approved",
            "submission_date": (today - timedelta(days=55)).isoformat(),
            "deadline": (today - timedelta(days=25)).isoformat(),
            "contact_name": "Hans Mueller",
            "owner": "李娜 - 采购经理",
            "contact_email": "h.mueller@mueller-precision.de",
            "contact_phone": "+49-151-12345678",
            "notes": "所有文件审核通过，合同已签署并激活供应商编码。",
        },
        {
            "company_name_cn": "东京精密工业株式会社",
            "company_name_en": "Tokyo Precision Parts K.K.",
            "country": "Japan",
            "platform": "SupplHi",
            "status": "Under Review",
            "submission_date": (today - timedelta(days=18)).isoformat(),
            "deadline": (today + timedelta(days=10)).isoformat(),
            "contact_name": "佐藤 健",
            "owner": "张伟 - 法务",
            "contact_email": "sato@tokyo-precision.co.jp",
            "contact_phone": "+81-90-1234-5678",
            "notes": "SupplHi 要求补充ISO 14001和RoHS声明，正在加急补交。",
        },
        {
            "company_name_cn": "顶点制造股份有限公司",
            "company_name_en": "Apex Manufacturing Inc.",
            "country": "United States",
            "platform": "Target Portal",
            "status": "In Progress",
            "submission_date": None,
            "deadline": (today + timedelta(days=14)).isoformat(),
            "contact_name": "Sarah Kline",
            "owner": "王强 - 供应链专员",
            "contact_email": "sarah.kline@apex-mfg.com",
            "contact_phone": "+1-650-555-0199",
            "notes": "内部资料准备中，预计本周内完成Target Portal在线提交。",
        },
        {
            "company_name_cn": "永隆电子有限公司",
            "company_name_en": "Vinh Long Electronics Co., Ltd.",
            "country": "Vietnam",
            "platform": "Other",
            "status": "Documents Submitted",
            "submission_date": (today - timedelta(days=22)).isoformat(),
            "deadline": (today + timedelta(days=3)).isoformat(),
            "contact_name": "Nguyen Van Minh",
            "owner": "李娜 - 采购经理",
            "contact_email": "minh@vinhlong-electronics.vn",
            "contact_phone": "+84-90-555-1234",
            "notes": "已通过平台完整提交注册包（含营业执照、ISO、产品目录），等待买家初审。",
        },
        {
            "company_name_cn": "现代穆尔桑株式会社",
            "company_name_en": "Hyundai Moolsan Co., Ltd.",
            "country": "South Korea",
            "platform": "SAIPREM",
            "status": "On Hold",
            "submission_date": (today - timedelta(days=60)).isoformat(),
            "deadline": (today - timedelta(days=12)).isoformat(),
            "contact_name": "Kim Ji-hoon",
            "owner": "陈静 - 质量审核",
            "contact_email": "jihoon@hyundai-moolsan.kr",
            "contact_phone": "+82-10-9876-5432",
            "notes": "因客户项目优先级调整暂时搁置，预计Q3恢复。",
        },
        {
            "company_name_cn": "上海华联精密机械有限公司",
            "company_name_en": "Shanghai Hualian Precision Machinery Co., Ltd.",
            "country": "China",
            "platform": "Target Portal",
            "status": "Not Started",
            "submission_date": None,
            "deadline": (today + timedelta(days=35)).isoformat(),
            "contact_name": "李明",
            "owner": "张伟 - 法务",
            "contact_email": "liming@hualian-mach.cn",
            "contact_phone": "021-5555-7788",
            "notes": "国内参考供应商，新项目需要完成Target Portal注册。",
        },
        {
            "company_name_cn": "巴拉特锻造有限公司",
            "company_name_en": "Bharat Forge Ltd.",
            "country": "India",
            "platform": "SupplHi",
            "status": "Rejected",
            "submission_date": (today - timedelta(days=40)).isoformat(),
            "deadline": (today - timedelta(days=18)).isoformat(),
            "contact_name": "Amit Sharma",
            "owner": "王强 - 供应链专员",
            "contact_email": "amit.sharma@bharatforge.com",
            "contact_phone": "+91-22-5555-0192",
            "notes": "因质量体系文件不完整被拒。计划6月重新整理材料后再次提交。",
        },
        {
            "company_name_cn": "太平洋铸造与物流部件公司",
            "company_name_en": "Pacific Cast & Logistics Parts LLC",
            "country": "United States",
            "platform": "SAIPREM",
            "status": "Documents Submitted",
            "submission_date": (today - timedelta(days=12)).isoformat(),
            "deadline": (today + timedelta(days=8)).isoformat(),
            "contact_name": "Michael Torres",
            "owner": "李娜 - 采购经理",
            "contact_email": "m.torres@pacificcast.com",
            "contact_phone": "+1-310-555-8822",
            "notes": "SAIPREM注册材料已提交，包含商业登记、银行资信及产品规格书。",
        },
    ]

    inserted_ids: List[int] = []
    for s in demo_suppliers:
        cur = conn.execute(
            """
            INSERT INTO suppliers (
                company_name_cn, company_name_en, country, platform, status,
                submission_date, deadline, contact_name, owner, contact_email,
                contact_phone, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                s["company_name_cn"],
                s["company_name_en"],
                s["country"],
                s["platform"],
                s["status"],
                s["submission_date"],
                s["deadline"],
                s["contact_name"],
                s["owner"],
                s["contact_email"],
                s["contact_phone"],
                s["notes"],
            ),
        )
        sid = cur.lastrowid
        inserted_ids.append(sid)

        # Initial history entry for every seeded supplier
        _log_status_change(conn, sid, None, s["status"], "系统演示数据")

    # Richer history + sample comments (mimic real workflow)
    # 0: Germany - Approved (multiple steps)
    sid0 = inserted_ids[0]
    _log_status_change(conn, sid0, "Not Started", "In Progress", "资料准备 by 李娜 - 采购经理")
    _log_status_change(conn, sid0, "In Progress", "Documents Submitted", "全套文件提交")
    _log_status_change(conn, sid0, "Documents Submitted", "Under Review", "进入买家审核")
    _log_status_change(conn, sid0, "Under Review", "Approved", "平台终审通过，合同激活")

    conn.execute(
        "INSERT INTO comments (supplier_id, author, content) VALUES (?, ?, ?)",
        (sid0, "李娜 - 采购经理", "已收到买家平台邀请函，开始整理基础资质文件。"),
    )
    conn.execute(
        "INSERT INTO comments (supplier_id, author, content) VALUES (?, ?, ?)",
        (sid0, "张伟 - 法务", "合同条款已法务复核无误，可直接签署。"),
    )

    # 1: Japan - Under Review
    sid1 = inserted_ids[1]
    _log_status_change(conn, sid1, "Not Started", "In Progress", "开始整理")
    _log_status_change(conn, sid1, "In Progress", "Documents Submitted", "ISO+RoHS补充提交")
    conn.execute(
        "INSERT INTO comments (supplier_id, author, content) VALUES (?, ?, ?)",
        (sid1, "张伟 - 法务", "补充了ISO 14001证书扫描件和RoHS符合声明，请同事复核后提交。"),
    )

    # 3: Vietnam - Documents Submitted (recent, near deadline)
    sid3 = inserted_ids[3]
    conn.execute(
        "INSERT INTO comments (supplier_id, author, content) VALUES (?, ?, ?)",
        (sid3, "李娜 - 采购经理", "已收到买家平台邀请函，开始整理基础资质文件。"),
    )

    # 4: Korea - On Hold
    sid4 = inserted_ids[4]
    _log_status_change(conn, sid4, "Under Review", "On Hold", "客户项目优先级调整")

    # 7: US Pacific - Documents Submitted (fresh)
    sid7 = inserted_ids[7]
    conn.execute(
        "INSERT INTO comments (supplier_id, author, content) VALUES (?, ?, ?)",
        (sid7, "李娜 - 采购经理", "材料已提交，包含商业登记与银行资信。"),
    )

    # Create real placeholder files under data/uploads/<sid>/ for first few suppliers
    uploads_root = DATA_DIR / "uploads"
    uploads_root.mkdir(parents=True, exist_ok=True)

    sample_files = [
        ("营业执照-缪勒精密.pdf", "【演示占位文件】\n公司：缪勒精密部件有限公司 (Germany)\n统一社会信用代码示例：DE123456789\n\n此为系统自动生成的演示文件，实际使用时请替换为真实扫描件。"),
        ("ISO9001-证书-东京精密.txt", "【演示占位文件】\nISO 9001:2015 质量管理体系认证\n公司：Tokyo Precision Parts K.K.\n\n请在此处上传真实的营业执照、ISO证书、产品规格书等附件。"),
        ("供应商资质-顶点制造.txt", "【演示占位文件】\n公司：Apex Manufacturing Inc. (United States)\n\n请在此处上传真实的营业执照、ISO证书、产品规格书等附件。\n\n此文件由系统在首次运行时自动生成，仅用于界面演示。"),
    ]

    for idx, (fname, content) in enumerate(sample_files):
        if idx >= len(inserted_ids):
            break
        sid = inserted_ids[idx]
        sup_dir = uploads_root / str(sid)
        sup_dir.mkdir(parents=True, exist_ok=True)

        ts = int(_time.time() * 1000) + idx
        safe = fname.replace(" ", "_")
        stored_name = f"{ts}_{safe}"
        fpath = sup_dir / stored_name
        fpath.write_text(content, encoding="utf-8")

        actor = demo_suppliers[idx].get("owner") or "系统"
        rel = f"uploads/{sid}/{stored_name}"
        conn.execute(
            """
            INSERT INTO attachments (supplier_id, original_filename, stored_path, uploaded_by)
            VALUES (?, ?, ?, ?)
            """,
            (sid, fname, rel, actor),
        )

    # Make a couple of records feel older for activity
    if len(inserted_ids) > 2:
        conn.execute(
            "UPDATE suppliers SET updated_at = datetime('now', 'localtime', '-25 days') WHERE id = ?",
            (inserted_ids[5],),
        )
    if len(inserted_ids) > 0:
        conn.execute(
            "UPDATE suppliers SET updated_at = datetime('now', 'localtime', '-4 days') WHERE id = ?",
            (inserted_ids[0],),
        )
