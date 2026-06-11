"""Database layer for Supplier Registration Tracker.

All persistence via Supabase (Postgres + Storage).
Replaces previous SQLite implementation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
from supabase import create_client, Client

from utils.constants import STATUSES, PLATFORMS, TERMINAL_STATUSES, COUNTRIES, ACTORS

# Use centralized cached client to avoid duplication and circular imports
from db.supabase_client import get_supabase_client

supabase: Client = get_supabase_client()


def get_supabase() -> Client:
    """Convenience accessor for the cached Supabase client."""
    return supabase


def init_db(seed_if_empty: bool = False) -> None:
    """No-op for Supabase (tables are managed externally in Supabase dashboard).
    Kept for backward compatibility with app.py calls.
    """
    # Connection is established via the cached client at import time.
    # You can add table existence checks here if desired.
    pass


# No local SQLite schema or connection needed anymore.
# Tables are managed in Supabase Postgres.
# See the comment above get_supabase_client() for recommended table creation SQL.
#
# To add the new fields, run in Supabase SQL Editor:
# ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS cnood_entity TEXT;
# ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS registration_category TEXT;
# ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS supplier_vendor_type TEXT;


# ------------------------------------------------------------------
# Supabase CRUD - Suppliers
# ------------------------------------------------------------------
def _handle_response(response, single: bool = False):
    """Basic error handling for Supabase responses."""
    if hasattr(response, "error") and response.error:
        raise Exception(f"Supabase error: {response.error}")
    data = getattr(response, "data", None)
    if data is None:
        return None if single else []
    if single:
        return data[0] if data else None
    return data


def get_supplier(supplier_id: int) -> Optional[Dict[str, Any]]:
    try:
        response = (
            supabase.table("suppliers")
            .select("*")
            .eq("id", supplier_id)
            .single()
            .execute()
        )
        return _handle_response(response, single=True)
    except Exception:
        # fallback if .single() not found or empty
        response = (
            supabase.table("suppliers")
            .select("*")
            .eq("id", supplier_id)
            .execute()
        )
        data = _handle_response(response)
        return data[0] if data else None


def get_all_suppliers() -> List[Dict[str, Any]]:
    response = (
        supabase.table("suppliers")
        .select("*")
        .order("updated_at", desc=True)
        .order("id", desc=True)
        .execute()
    )
    return _handle_response(response) or []


def get_suppliers_df() -> pd.DataFrame:
    """Convenience: return all suppliers as DataFrame (for filtering/export)."""
    suppliers = get_all_suppliers()
    if not suppliers:
        return pd.DataFrame(
            columns=[
                "id", "company_name_cn", "company_name_en", "country", "platform",
                "status", "submission_date", "deadline", "contact_name", "owner",
                "contact_email", "contact_phone", "notes", "created_at", "updated_at",
                "cnood_entity", "registration_category", "supplier_vendor_type",
            ]
        )
    return pd.DataFrame(suppliers)


def add_supplier(data: Dict[str, Any]) -> int:
    """
    Insert a new supplier via Supabase. Returns new id.
    """
    now = datetime.utcnow().isoformat()
    insert_data = {
        "company_name_cn": data.get("company_name_cn"),
        "company_name_en": data.get("company_name_en"),
        "country": data.get("country") or "Other",
        "platform": data.get("platform"),
        "status": data.get("status"),
        "submission_date": data.get("submission_date"),
        "deadline": data.get("deadline"),
        "contact_name": data.get("contact_name"),
        "owner": data.get("owner"),
        "contact_email": data.get("contact_email"),
        "contact_phone": data.get("contact_phone"),
        "notes": data.get("notes"),
        "cnood_entity": data.get("cnood_entity"),
        "registration_category": data.get("registration_category"),
        "supplier_vendor_type": data.get("supplier_vendor_type"),
        "created_at": now,
        "updated_at": now,
    }

    response = supabase.table("suppliers").insert(insert_data).execute()
    inserted = _handle_response(response)
    if not inserted:
        raise Exception("Failed to insert supplier")

    supplier_id = inserted[0]["id"]

    # Log initial status history
    actor = data.get("owner") or ""
    init_note = f"初始创建{' by ' + actor if actor else ''}"
    _log_status_change(supplier_id, None, data.get("status"), init_note)

    return supplier_id


def update_supplier(supplier_id: int, data: Dict[str, Any], status_note: Optional[str] = None) -> None:
    """
    Update supplier fields via Supabase. If status changed, automatically log to history.
    """
    current = get_supplier(supplier_id)
    if not current:
        raise ValueError(f"Supplier {supplier_id} not found")

    old_status = current.get("status")
    new_status = data.get("status", old_status)

    update_data = {
        "company_name_cn": data.get("company_name_cn"),
        "company_name_en": data.get("company_name_en"),
        "country": data.get("country") or current.get("country") or "Other",
        "platform": data.get("platform"),
        "status": new_status,
        "submission_date": data.get("submission_date"),
        "deadline": data.get("deadline"),
        "contact_name": data.get("contact_name"),
        "owner": data.get("owner"),
        "contact_email": data.get("contact_email"),
        "contact_phone": data.get("contact_phone"),
        "notes": data.get("notes"),
        "cnood_entity": data.get("cnood_entity"),
        "registration_category": data.get("registration_category"),
        "supplier_vendor_type": data.get("supplier_vendor_type"),
        "updated_at": datetime.utcnow().isoformat(),
    }

    supabase.table("suppliers").update(update_data).eq("id", supplier_id).execute()

    if new_status != old_status:
        note = status_note
        if note and data.get("owner"):
            note = f"{note} (by {data.get('owner')})"
        _log_status_change(supplier_id, old_status, new_status, note)

    # bump not strictly needed as we set updated_at above


def delete_supplier(supplier_id: int) -> None:
    """Delete supplier. Related records should cascade if FK constraints are set in Supabase."""
    # First clean up storage files for this supplier
    try:
        from utils.helpers import delete_all_files_for_supplier
        delete_all_files_for_supplier(supplier_id)
    except Exception:
        pass  # non-fatal

    supabase.table("suppliers").delete().eq("id", supplier_id).execute()


# ------------------------------------------------------------------
# Status history
# ------------------------------------------------------------------
def _log_status_change(
    supplier_id: int,
    old_status: Optional[str],
    new_status: str,
    note: Optional[str] = None,
) -> None:
    """Insert status history row (Supabase version)."""
    try:
        supabase.table("status_history").insert({
            "supplier_id": supplier_id,
            "old_status": old_status,
            "new_status": new_status,
            "note": note,
            "changed_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as e:
        # non-fatal for history
        print(f"Warning: failed to log status change: {e}")


def get_status_history(supplier_id: int) -> List[Dict[str, Any]]:
    response = (
        supabase.table("status_history")
        .select("*")
        .eq("supplier_id", supplier_id)
        .order("changed_at", desc=True)
        .execute()
    )
    return _handle_response(response) or []


def change_status(
    supplier_id: int, new_status: str, note: Optional[str] = None
) -> None:
    """Convenience wrapper to change only status (and log)."""
    current = get_supplier(supplier_id)
    if not current:
        raise ValueError("Supplier not found")
    if new_status == current.get("status"):
        return
    data = current.copy()
    data["status"] = new_status
    update_supplier(supplier_id, data, status_note=note)


# ------------------------------------------------------------------
# Attachments (metadata + Supabase Storage path)
# ------------------------------------------------------------------
def add_attachment(
    supplier_id: int, original_filename: str, stored_path: str, uploaded_by: Optional[str] = None
) -> int:
    """Insert attachment metadata. stored_path should be the Supabase Storage key."""
    response = supabase.table("attachments").insert({
        "supplier_id": supplier_id,
        "original_filename": original_filename,
        "stored_path": stored_path,
        "uploaded_by": uploaded_by,
        "uploaded_at": datetime.utcnow().isoformat(),
    }).execute()

    inserted = _handle_response(response)
    if inserted:
        # bump supplier updated_at
        supabase.table("suppliers").update({"updated_at": datetime.utcnow().isoformat()}).eq("id", supplier_id).execute()
        return inserted[0]["id"]
    return -1


def get_attachments(supplier_id: int) -> List[Dict[str, Any]]:
    response = (
        supabase.table("attachments")
        .select("*")
        .eq("supplier_id", supplier_id)
        .order("uploaded_at", desc=True)
        .execute()
    )
    return _handle_response(response) or []


def delete_attachment(attachment_id: int) -> Optional[int]:
    """Delete attachment record. Returns supplier_id for file cleanup by caller (storage delete handled in UI/helpers)."""
    # Get supplier_id first
    row_resp = supabase.table("attachments").select("supplier_id").eq("id", attachment_id).single().execute()
    row = _handle_response(row_resp, single=True)
    if not row:
        return None
    supplier_id = row.get("supplier_id")

    supabase.table("attachments").delete().eq("id", attachment_id).execute()

    if supplier_id:
        supabase.table("suppliers").update({"updated_at": datetime.utcnow().isoformat()}).eq("id", supplier_id).execute()

    return supplier_id


# ------------------------------------------------------------------
# Team Comments (separate from status history)
# ------------------------------------------------------------------
def get_comments(supplier_id: int) -> List[Dict[str, Any]]:
    response = (
        supabase.table("comments")
        .select("*")
        .eq("supplier_id", supplier_id)
        .order("created_at", desc=False)
        .execute()
    )
    return _handle_response(response) or []


def add_comment(supplier_id: int, author: str, content: str) -> int:
    response = supabase.table("comments").insert({
        "supplier_id": supplier_id,
        "author": author,
        "content": content,
        "created_at": datetime.utcnow().isoformat(),
    }).execute()

    inserted = _handle_response(response)
    if inserted:
        supabase.table("suppliers").update({"updated_at": datetime.utcnow().isoformat()}).eq("id", supplier_id).execute()
        return inserted[0]["id"]
    return -1


# ------------------------------------------------------------------
# Data management (clear / reset)
# ------------------------------------------------------------------
def clear_all_data() -> None:
    """Delete ALL supplier records (cascades to history/attachments/comments if FKs set)
    and remove all files from the Supabase Storage 'uploads' bucket.
    """
    # 1. Delete all rows from suppliers (recommended to have ON DELETE CASCADE on child tables)
    try:
        supabase.table("suppliers").delete().neq("id", 0).execute()  # delete all
    except Exception:
        # fallback: delete one by one if needed
        suppliers = get_all_suppliers()
        for s in suppliers:
            supabase.table("suppliers").delete().eq("id", s["id"]).execute()

    # 2. Clear all files in Supabase Storage uploads bucket
    try:
        from utils.helpers import delete_all_files_for_supplier
        # For global clear we list root and remove
        files = supabase.storage.from_("uploads").list("")
        paths_to_remove = [f["name"] for f in files if f.get("name")]
        if paths_to_remove:
            supabase.storage.from_("uploads").remove(paths_to_remove)
    except Exception as e:
        print(f"Warning: could not clear all storage files: {e}")


# Seed data has been removed (no longer applicable with Supabase).
# Users can add data manually via the UI or import via Excel if a migration script is added later.
