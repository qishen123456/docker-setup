"""
Lightweight auth token store for Feishu login.

The store keeps a small JSON file under config/ so auth survives backend
restart. It is intentionally simple: session tokens are random opaque values,
and user profile data is non-secret Feishu identity metadata.
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from flask import request, session

from config_manager import read_json, write_json


TOKEN_FILE = "auth_tokens.json"
TOKEN_TTL_DAYS = int(os.getenv("SMARTASK_AUTH_TOKEN_TTL_DAYS", "7") or 7)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _load() -> Dict[str, Any]:
    data = read_json(TOKEN_FILE)
    if not isinstance(data, dict):
        return {"tokens": {}}
    tokens = data.get("tokens")
    if not isinstance(tokens, dict):
        data["tokens"] = {}
    return data


def _save(data: Dict[str, Any]) -> None:
    write_json(TOKEN_FILE, data)


def cleanup_expired_tokens() -> None:
    data = _load()
    tokens = data.get("tokens", {})
    now = _now()
    changed = False
    for token, item in list(tokens.items()):
        expires_at = _parse_iso(item.get("expires_at", ""))
        if expires_at and expires_at <= now:
            tokens.pop(token, None)
            changed = True
    if changed:
        _save(data)


def create_session_token(user_info: Dict[str, Any]) -> str:
    cleanup_expired_tokens()
    token = secrets.token_urlsafe(32)
    now = _now()
    data = _load()
    data.setdefault("tokens", {})[token] = {
        "user": user_info,
        "created_at": _iso(now),
        "expires_at": _iso(now + timedelta(days=TOKEN_TTL_DAYS)),
    }
    _save(data)
    session["user"] = user_info
    session["auth_token"] = token
    return token


def resolve_token(token: str) -> Dict[str, Any] | None:
    if not token:
        return None
    data = _load()
    item = data.get("tokens", {}).get(token)
    if not isinstance(item, dict):
        return None
    expires_at = _parse_iso(item.get("expires_at", ""))
    if expires_at and expires_at <= _now():
        data.get("tokens", {}).pop(token, None)
        _save(data)
        return None
    user = item.get("user")
    return user if isinstance(user, dict) else None


def revoke_token(token: str) -> bool:
    data = _load()
    existed = data.get("tokens", {}).pop(token, None) is not None
    if existed:
        _save(data)
    if session.get("auth_token") == token:
        session.pop("auth_token", None)
        session.pop("user", None)
    return existed


def get_current_user() -> Dict[str, Any]:
    token = request.headers.get("X-Auth-Token") or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    user = resolve_token(token)
    if user:
        return user
    session_user = session.get("user")
    return session_user if isinstance(session_user, dict) else {}

