"""
Aadhya – Supabase Persistent Storage
Stores enquiries and project summaries to Supabase PostgreSQL.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any
from backend.config import get_settings

settings = get_settings()

_client = None


def _get_client():
    global _client
    if _client is None and settings.supabase_url and settings.supabase_service_key:
        try:
            from supabase import create_client
            _client = create_client(settings.supabase_url, settings.supabase_service_key)
        except Exception:
            _client = None
    return _client


def is_configured() -> bool:
    return bool(
        settings.supabase_url
        and settings.supabase_service_key
        and settings.supabase_url != "https://your-project.supabase.co"
    )


# ─── SQL to create tables (run once in Supabase) ─────────────────────────────
SCHEMA_SQL = """
-- Enquiries Table
CREATE TABLE IF NOT EXISTS enquiries (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id TEXT NOT NULL,
    phone_number TEXT,
    channel TEXT,
    extracted_fields JSONB,
    completed_fields JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Project Summaries Table
CREATE TABLE IF NOT EXISTS project_summaries (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id TEXT NOT NULL,
    phone_number TEXT,
    next_step TEXT,
    project_overview TEXT,
    scope_of_work JSONB,
    client_requirements TEXT,
    technical_specs TEXT,
    timeline TEXT,
    special_considerations TEXT,
    estimated_scope TEXT,
    design_direction TEXT,
    execution_readiness TEXT,
    enquiry_snapshot JSONB,
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sessions Log Table
CREATE TABLE IF NOT EXISTS sessions_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id TEXT NOT NULL,
    phone_number TEXT,
    channel TEXT,
    conversation_stage TEXT,
    field_completion_pct INTEGER,
    turn_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_active TIMESTAMPTZ DEFAULT NOW()
);
"""

# ─── CRUD operations ─────────────────────────────────────────────────────────

async def save_enquiry(session) -> bool:
    """Save or upsert enquiry data from a session."""
    if not is_configured():
        return False
    try:
        client = _get_client()
        record = {
            "session_id": session.session_id,
            "phone_number": session.phone_number,
            "channel": session.channel,
            "extracted_fields": session.extracted_fields,
            "completed_fields": session.completed_fields,
            "updated_at": datetime.utcnow().isoformat(),
        }
        client.table("enquiries").upsert(record, on_conflict="session_id").execute()
        return True
    except Exception as e:
        print(f"[Supabase] save_enquiry error: {e}")
        return False


async def save_summary(summary, phone_number: str = "") -> bool:
    """Insert a generated project summary."""
    if not is_configured():
        return False
    try:
        client = _get_client()
        record = {
            "session_id": summary.session_id,
            "phone_number": phone_number,
            "next_step": summary.next_step,
            "project_overview": summary.project_overview,
            "scope_of_work": summary.scope_of_work,
            "client_requirements": summary.client_requirements,
            "technical_specs": summary.technical_specs,
            "timeline": summary.timeline,
            "special_considerations": summary.special_considerations,
            "estimated_scope": summary.estimated_scope,
            "design_direction": summary.design_direction,
            "execution_readiness": summary.execution_readiness,
            "enquiry_snapshot": summary.enquiry_snapshot,
            "generated_at": summary.generated_at.isoformat(),
        }
        client.table("project_summaries").insert(record).execute()
        return True
    except Exception as e:
        print(f"[Supabase] save_summary error: {e}")
        return False


async def upsert_session_log(session) -> bool:
    """Update the sessions_log table with current session state."""
    if not is_configured():
        return False
    try:
        client = _get_client()
        record = {
            "session_id": session.session_id,
            "phone_number": session.phone_number,
            "channel": session.channel,
            "conversation_stage": session.conversation_stage.value,
            "field_completion_pct": session.field_completion_pct,
            "turn_count": session.turn_count,
            "last_active": session.last_active.isoformat(),
        }
        client.table("sessions_log").upsert(record, on_conflict="session_id").execute()
        return True
    except Exception as e:
        print(f"[Supabase] upsert_session_log error: {e}")
        return False


async def get_all_enquiries() -> list[dict]:
    if not is_configured():
        return []
    try:
        client = _get_client()
        result = client.table("enquiries").select("*").order("updated_at", desc=True).execute()
        return result.data or []
    except Exception:
        return []


async def get_all_summaries() -> list[dict]:
    if not is_configured():
        return []
    try:
        client = _get_client()
        result = client.table("project_summaries").select("*").order("generated_at", desc=True).execute()
        return result.data or []
    except Exception:
        return []
