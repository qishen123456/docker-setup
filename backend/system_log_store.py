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


def _parse_limit(value: Any, default: int = 100) -> Optional[int]:
    raw = str(value if value is not None else default).strip().lower()
    if raw in {"", "none"}:
        return default
    if raw in {"0", "-1", "all", "全部"}:
        return None
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return default


def _parse_date_bound(value: Any, *, end: bool = False) -> Optional[datetime]:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw[:10])
    except ValueError:
        return None
    return parsed + timedelta(days=1) if end else parsed


def _append_date_filters(where: List[str], params: List[Any], filters: Dict[str, Any]) -> None:
    start = _parse_date_bound(filters.get("date_from"))
    end = _parse_date_bound(filters.get("date_to"), end=True)
    if start:
        where.append("created_at >= %s")
        params.append(start)
    if end:
        where.append("created_at < %s")
        params.append(end)


TOKEN_USAGE_SQL = """
    GREATEST(
        CASE WHEN (details->>'total_tokens') ~ '^[0-9]+(\\.[0-9]+)?$'
            THEN (details->>'total_tokens')::numeric ELSE 0 END,
        CASE WHEN (details #>> '{token_usage,total_tokens}') ~ '^[0-9]+(\\.[0-9]+)?$'
            THEN (details #>> '{token_usage,total_tokens}')::numeric ELSE 0 END,
        CASE WHEN (details #>> '{usage,total_tokens}') ~ '^[0-9]+(\\.[0-9]+)?$'
            THEN (details #>> '{usage,total_tokens}')::numeric ELSE 0 END,
        CASE
            WHEN category IN ('qa', 'low_confidence', 'error')
             AND (question <> '' OR sql_text <> '' OR answer_text <> '')
            THEN CEIL((char_length(question) + char_length(sql_text) + char_length(answer_text))::numeric / 3)
            ELSE 0
        END
    )
"""


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
            "OR answer_text ILIKE %s OR error_message ILIKE %s OR details::text ILIKE %s)"
        )
        params.extend([like] * 10)

    trace_id = str(filters.get("trace_id") or "").strip()
    if trace_id:
        like = f"%{trace_id}%"
        where.append("(details::text ILIKE %s OR request_path ILIKE %s)")
        params.extend([like, like])

    _append_date_filters(where, params, filters)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    limit = _parse_limit(filters.get("limit"), 100)
    offset = max(0, int(filters.get("offset") or 0))
    page_sql = "OFFSET %s" if limit is None else "LIMIT %s OFFSET %s"
    page_params = [offset] if limit is None else [limit, offset]

    with _connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"SELECT COUNT(*) AS count FROM system_event_logs {where_sql};", params)
        total = int((cur.fetchone() or {}).get("count") or 0)
        cur.execute(
            f"""
            SELECT *
            FROM system_event_logs
            {where_sql}
            ORDER BY created_at DESC, id DESC
            {page_sql};
            """,
            [*params, *page_params],
        )
        rows = [_serialize_row(dict(row)) for row in cur.fetchall()]
        return rows, total


def get_log(log_id: int) -> Optional[Dict[str, Any]]:
    _ensure_schema()
    with _connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM system_event_logs WHERE id = %s;", (int(log_id),))
        row = cur.fetchone()
        return _serialize_row(dict(row)) if row else None


def get_stats(filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    _ensure_schema()
    filters = filters or {}
    range_where: List[str] = []
    range_params: List[Any] = []
    _append_date_filters(range_where, range_params, filters)
    if not range_where:
        range_where.append("created_at >= CURRENT_DATE")
    range_sql = f"WHERE {' AND '.join(range_where)}"

    def _count(cur: Any, extra: str = "") -> int:
        sql = f"SELECT COUNT(*) AS count FROM system_event_logs {range_sql}"
        if extra:
            sql += f" AND {extra}"
        cur.execute(sql, range_params)
        return int((cur.fetchone() or {}).get("count") or 0)

    def _top_users(cur: Any, metric_sql: str, alias: str, extra: str = "") -> List[Dict[str, Any]]:
        sql = f"""
            SELECT
                COALESCE(NULLIF(user_name, ''), NULLIF(username, ''), '未知用户') AS display_name,
                COALESCE(NULLIF(username, ''), NULLIF(user_name, ''), 'unknown') AS username,
                MAX(user_name) AS user_name,
                MAX(user_role) AS user_role,
                {metric_sql} AS {alias},
                COUNT(*) AS event_count,
                MAX(created_at) AS last_seen
            FROM system_event_logs
            {range_sql}
        """
        if extra:
            sql += f" AND {extra}"
        sql += f"""
            GROUP BY COALESCE(NULLIF(user_name, ''), NULLIF(username, ''), '未知用户'),
                     COALESCE(NULLIF(username, ''), NULLIF(user_name, ''), 'unknown')
            HAVING {metric_sql} > 0
            ORDER BY {alias} DESC, event_count DESC, last_seen DESC
            LIMIT 8;
        """
        cur.execute(sql, range_params)
        rows = []
        for row in cur.fetchall():
            item = dict(row)
            item["access_count"] = int(float(item.get("access_count") or item.get("event_count") or 0))
            item["event_count"] = int(float(item.get("event_count") or 0))
            for key in (alias,):
                item[key] = int(float(item.get(key) or 0))
            if isinstance(item.get("last_seen"), datetime):
                item["last_seen"] = item["last_seen"].astimezone(timezone.utc).isoformat()
            rows.append(item)
        return rows

    with _connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT category, COUNT(*) AS count
            FROM system_event_logs
            {range_sql}
            GROUP BY category
            ORDER BY count DESC;
            """,
            range_params,
        )
        by_category = [dict(row) for row in cur.fetchall()]
        cur.execute(
            f"""
            SELECT level, COUNT(*) AS count
            FROM system_event_logs
            {range_sql}
            GROUP BY level
            ORDER BY count DESC;
            """,
            range_params,
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

        range_access = _count(cur)
        range_qa = _count(cur, "category IN ('qa', 'low_confidence')")
        range_errors = _count(cur, "(category = 'error' OR level = 'error')")
        range_low_confidence = _count(cur, "category = 'low_confidence'")
        cur.execute(
            f"""
            SELECT COALESCE(SUM({TOKEN_USAGE_SQL}), 0) AS total_tokens
            FROM system_event_logs
            {range_sql};
            """,
            range_params,
        )
        range_tokens = int(float((cur.fetchone() or {}).get("total_tokens") or 0))
        cur.execute(
            f"""
            SELECT *
            FROM system_event_logs
            {range_sql}
              AND category = 'low_confidence'
            ORDER BY created_at DESC, id DESC
            LIMIT 8;
            """,
            range_params,
        )
        recent_low_confidence = [_serialize_row(dict(row)) for row in cur.fetchall()]
        cur.execute(
            f"""
            SELECT *
            FROM system_event_logs
            {range_sql}
              AND (category = 'error' OR level = 'error')
            ORDER BY created_at DESC, id DESC
            LIMIT 8;
            """,
            range_params,
        )
        recent_errors = [_serialize_row(dict(row)) for row in cur.fetchall()]
        cur.execute(
            """
            SELECT date_trunc('hour', created_at) AS bucket, COUNT(*) AS count
            FROM system_event_logs
            WHERE created_at >= NOW() - INTERVAL '24 hours'
            GROUP BY bucket
            ORDER BY bucket;
            """
        )
        hourly_access = [
            {
                "hour": row["bucket"].astimezone(timezone.utc).isoformat() if isinstance(row.get("bucket"), datetime) else str(row.get("bucket") or ""),
                "count": int(row.get("count") or 0),
            }
            for row in cur.fetchall()
        ]
        top_users_by_access = _top_users(cur, "COUNT(*)", "access_count")
        top_users_by_qa = _top_users(cur, "COUNT(*)", "qa_count", "category IN ('qa', 'low_confidence')")
        top_users_by_tokens = _top_users(cur, f"COALESCE(SUM({TOKEN_USAGE_SQL}), 0)", "total_tokens")
        top_users_by_errors = _top_users(cur, "COUNT(*)", "error_count", "(category = 'error' OR level = 'error')")
        top_users_by_low_confidence = _top_users(cur, "COUNT(*)", "low_confidence_count", "category = 'low_confidence'")
    return {
        "by_category": by_category,
        "by_level": by_level,
        "last_24h": last_24h,
        "low_confidence_7d": low_confidence_7d,
        "errors_7d": errors_7d,
        "today_access": range_access,
        "today_qa": range_qa,
        "today_errors": range_errors,
        "today_low_confidence": range_low_confidence,
        "today_tokens": range_tokens,
        "range_access": range_access,
        "range_qa": range_qa,
        "range_errors": range_errors,
        "range_low_confidence": range_low_confidence,
        "range_tokens": range_tokens,
        "recent_low_confidence": recent_low_confidence,
        "recent_errors": recent_errors,
        "hourly_access": hourly_access,
        "top_users_by_access": top_users_by_access,
        "top_users_by_qa": top_users_by_qa,
        "top_users_by_tokens": top_users_by_tokens,
        "top_users_by_errors": top_users_by_errors,
        "top_users_by_low_confidence": top_users_by_low_confidence,
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
