from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from bookshelf_repository import BookshelfRepository


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(CURRENT_DIR, "logs")
FALLBACK_LOG = os.path.join(LOG_DIR, "system_event_logs.jsonl")

MAX_TEXT = 12000
_SCHEMA_READY = False


SYSTEM_LOG_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS system_event_logs (
    id BIGSERIAL PRIMARY KEY,
    category VARCHAR(48) NOT NULL DEFAULT 'access',
    event_type VARCHAR(96) NOT NULL DEFAULT 'event',
    level VARCHAR(24) NOT NULL DEFAULT 'info',
    title VARCHAR(255) NOT NULL DEFAULT '',
    username VARCHAR(128) NOT NULL DEFAULT '',
    user_name VARCHAR(255) NOT NULL DEFAULT '',
    user_role VARCHAR(64) NOT NULL DEFAULT '',
    user_source VARCHAR(64) NOT NULL DEFAULT '',
    ip_address VARCHAR(96) NOT NULL DEFAULT '',
    user_agent TEXT NOT NULL DEFAULT '',
    request_method VARCHAR(16) NOT NULL DEFAULT '',
    request_path TEXT NOT NULL DEFAULT '',
    status_code INT,
    duration_ms INT,
    question TEXT NOT NULL DEFAULT '',
    thinking_process JSONB NOT NULL DEFAULT '[]'::jsonb,
    sql_text TEXT NOT NULL DEFAULT '',
    answer_text TEXT NOT NULL DEFAULT '',
    confidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT NOT NULL DEFAULT '',
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_system_event_logs_category_time
    ON system_event_logs (category, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_event_logs_level_time
    ON system_event_logs (level, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_event_logs_user_time
    ON system_event_logs (username, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_event_logs_event_type_time
    ON system_event_logs (event_type, created_at DESC);
"""


def _connect():
    return BookshelfRepository()._connect()


def _ensure_schema() -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with _connect() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(SYSTEM_LOG_SCHEMA_SQL)
    _SCHEMA_READY = True


def _truncate(value: Any, limit: int = MAX_TEXT) -> str:
    text = "" if value is None else str(value)
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated {len(text) - limit} chars]"


def _json_safe(value: Any, depth: int = 0) -> Any:
    if depth > 6:
        return _truncate(value, 1000)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _truncate(value)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item, depth + 1) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item, depth + 1) for item in list(value)[:200]]
    return _truncate(value)


def _user_snapshot(user: Optional[Dict[str, Any]]) -> Dict[str, str]:
    user = user or {}
    return {
        "username": str(user.get("username") or user.get("email") or user.get("mobile") or user.get("user_id") or user.get("open_id") or "").strip(),
        "user_name": str(user.get("name") or user.get("permission_name") or user.get("username") or "").strip(),
        "user_role": str(user.get("role") or "").strip(),
        "user_source": str(user.get("source") or "").strip(),
    }


def request_snapshot(req: Any = None) -> Dict[str, Any]:
    if req is None:
        return {}
    forwarded_for = str(req.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return {
        "ip_address": forwarded_for or str(req.headers.get("X-Real-IP") or req.remote_addr or ""),
        "user_agent": str(req.headers.get("User-Agent") or ""),
        "request_method": str(req.method or ""),
        "request_path": str(req.full_path or req.path or "").rstrip("?"),
    }


def _fallback_write(payload: Dict[str, Any]) -> None:
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        payload = dict(payload)
        payload["fallback_time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        with open(FALLBACK_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(_json_safe(payload), ensure_ascii=False) + "\n")
    except Exception:
        pass


def log_event(
    *,
    category: str,
    event_type: str,
    level: str = "info",
    title: str = "",
    user: Optional[Dict[str, Any]] = None,
    request_info: Optional[Dict[str, Any]] = None,
    status_code: Optional[int] = None,
    duration_ms: Optional[int] = None,
    question: str = "",
    thinking_process: Any = None,
    sql_text: str = "",
    answer_text: str = "",
    confidence: Any = None,
    error_message: str = "",
    details: Any = None,
) -> Optional[int]:
    request_info = request_info or {}
    row = {
        "category": _truncate(category or "access", 48),
        "event_type": _truncate(event_type or "event", 96),
        "level": _truncate(level or "info", 24),
        "title": _truncate(title or "", 255),
        **_user_snapshot(user),
        "ip_address": _truncate(request_info.get("ip_address"), 96),
        "user_agent": _truncate(request_info.get("user_agent"), 4000),
        "request_method": _truncate(request_info.get("request_method"), 16),
        "request_path": _truncate(request_info.get("request_path"), 4000),
        "status_code": int(status_code) if status_code is not None else None,
        "duration_ms": int(duration_ms) if duration_ms is not None else None,
        "question": _truncate(question),
        "thinking_process": _json_safe(thinking_process or []),
        "sql_text": _truncate(sql_text),
        "answer_text": _truncate(answer_text),
        "confidence": _json_safe(confidence or {}),
        "error_message": _truncate(error_message),
        "details": _json_safe(details or {}),
    }
    try:
        _ensure_schema()
        with _connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO system_event_logs(
                    category, event_type, level, title,
                    username, user_name, user_role, user_source,
                    ip_address, user_agent, request_method, request_path,
                    status_code, duration_ms, question, thinking_process,
                    sql_text, answer_text, confidence, error_message, details
                )
                VALUES (
                    %(category)s, %(event_type)s, %(level)s, %(title)s,
                    %(username)s, %(user_name)s, %(user_role)s, %(user_source)s,
                    %(ip_address)s, %(user_agent)s, %(request_method)s, %(request_path)s,
                    %(status_code)s, %(duration_ms)s, %(question)s, %(thinking_process)s::jsonb,
                    %(sql_text)s, %(answer_text)s, %(confidence)s::jsonb, %(error_message)s, %(details)s::jsonb
                )
                RETURNING id;
                """,
                {
                    **row,
                    "thinking_process": Json(row["thinking_process"]),
                    "confidence": Json(row["confidence"]),
                    "details": Json(row["details"]),
                },
            )
            saved = cur.fetchone()
            return int(saved["id"]) if saved else None
    except Exception as exc:
        _fallback_write({"insert_failed": str(exc), **row})
        return None


def _serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(row)
    created_at = item.get("created_at")
    if isinstance(created_at, datetime):
        item["created_at"] = created_at.astimezone(timezone.utc).isoformat()
    return item


def list_logs(filters: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
    _ensure_schema()
    where = []
    params: List[Any] = []

    category = str(filters.get("category") or "").strip()
    if category:
        if category == "qa_all":
            where.append("category IN ('qa', 'low_confidence')")
        else:
            where.append("category = %s")
            params.append(category)

    level = str(filters.get("level") or "").strip()
    if level:
        where.append("level = %s")
        params.append(level)

    keyword = str(filters.get("keyword") or "").strip()
    if keyword:
        like = f"%{keyword}%"
        where.append(
            "(title ILIKE %s OR event_type ILIKE %s OR username ILIKE %s OR user_name ILIKE %s "
            "OR request_path ILIKE %s OR question ILIKE %s OR sql_text ILIKE %s "
            "OR answer_text ILIKE %s OR error_message ILIKE %s)"
        )
        params.extend([like] * 9)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    limit = max(1, min(int(filters.get("limit") or 100), 500))
    offset = max(0, int(filters.get("offset") or 0))

    with _connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"SELECT COUNT(*) AS count FROM system_event_logs {where_sql};", params)
        total = int((cur.fetchone() or {}).get("count") or 0)
        cur.execute(
            f"""
            SELECT *
            FROM system_event_logs
            {where_sql}
            ORDER BY created_at DESC, id DESC
            LIMIT %s OFFSET %s;
            """,
            [*params, limit, offset],
        )
        rows = [_serialize_row(dict(row)) for row in cur.fetchall()]
        return rows, total


def get_log(log_id: int) -> Optional[Dict[str, Any]]:
    _ensure_schema()
    with _connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM system_event_logs WHERE id = %s;", (int(log_id),))
        row = cur.fetchone()
        return _serialize_row(dict(row)) if row else None


def get_stats() -> Dict[str, Any]:
    _ensure_schema()
    with _connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT category, COUNT(*) AS count
            FROM system_event_logs
            GROUP BY category
            ORDER BY count DESC;
            """
        )
        by_category = [dict(row) for row in cur.fetchall()]
        cur.execute(
            """
            SELECT level, COUNT(*) AS count
            FROM system_event_logs
            GROUP BY level
            ORDER BY count DESC;
            """
        )
        by_level = [dict(row) for row in cur.fetchall()]
        cur.execute(
            """
            SELECT COUNT(*) AS count
            FROM system_event_logs
            WHERE created_at >= NOW() - INTERVAL '24 hours';
            """
        )
        last_24h = int((cur.fetchone() or {}).get("count") or 0)
        cur.execute(
            """
            SELECT COUNT(*) AS count
            FROM system_event_logs
            WHERE category = 'low_confidence'
              AND created_at >= NOW() - INTERVAL '7 days';
            """
        )
        low_confidence_7d = int((cur.fetchone() or {}).get("count") or 0)
        cur.execute(
            """
            SELECT COUNT(*) AS count
            FROM system_event_logs
            WHERE category = 'error'
              AND created_at >= NOW() - INTERVAL '7 days';
            """
        )
        errors_7d = int((cur.fetchone() or {}).get("count") or 0)
    return {
        "by_category": by_category,
        "by_level": by_level,
        "last_24h": last_24h,
        "low_confidence_7d": low_confidence_7d,
        "errors_7d": errors_7d,
    }


def clear_logs(category: str = "", days: int = 0, before_date: str = "") -> int:
    _ensure_schema()
    where = []
    params: List[Any] = []
    if category:
        if category == "qa_all":
            where.append("category IN ('qa', 'low_confidence')")
        else:
            where.append("category = %s")
            params.append(category)
    if before_date:
        try:
            cutoff = datetime.fromisoformat(str(before_date)[:10]) + timedelta(days=1)
            where.append("created_at < %s")
            params.append(cutoff)
        except ValueError:
            raise ValueError("before_date must be YYYY-MM-DD")
    elif days > 0:
        where.append("created_at < NOW() - (%s || ' days')::interval")
        params.append(int(days))
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    with _connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"DELETE FROM system_event_logs {where_sql};", params)
        return int(cur.rowcount or 0)
