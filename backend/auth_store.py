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
ROLE_LABELS = {
    "super_admin": "超级管理员",
    "admin": "管理员",
    "business_admin": "业务管理员",
    "user": "普通用户",
}


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
    if not isinstance(user, dict):
        return None
    refreshed_user = _refresh_user_from_employee(user)
    if _is_user_disabled(refreshed_user):
        data.get("tokens", {}).pop(token, None)
        _save(data)
        return None
    return refreshed_user


def _refresh_user_from_employee(user: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(user, dict) or user.get("role") == "super_admin":
        return user
    try:
        permissions = read_json("employee_permissions.json")
    except Exception:
        return user
    employees = permissions.get("employees") if isinstance(permissions, dict) else []
    identities = {
        str(user.get(key) or "").strip().lower()
        for key in ("employee_id", "username", "account", "union_id", "open_id", "user_id", "identifier")
        if str(user.get(key) or "").strip()
    }
    for item in employees if isinstance(employees, list) else []:
        if not isinstance(item, dict):
            continue
        candidates = {
            str(item.get(key) or "").strip().lower()
            for key in ("id", "account", "username", "union_id", "unionId", "open_id", "openId", "user_id", "userId", "identifier")
            if str(item.get(key) or "").strip()
        }
        if not identities.intersection(candidates):
            continue
        refreshed = dict(user)
        refreshed["employee_id"] = str(item.get("id") or refreshed.get("employee_id") or "")
        refreshed["username"] = str(item.get("account") or refreshed.get("username") or "")
        refreshed["name"] = str(item.get("name") or refreshed.get("name") or "")
        refreshed["permission_name"] = str(item.get("name") or refreshed.get("permission_name") or "")
        refreshed["role"] = str(item.get("role") or refreshed.get("role") or "user")
        refreshed["role_label"] = ROLE_LABELS.get(refreshed["role"], "普通用户")
        refreshed["role_ids"] = item.get("role_ids") if isinstance(item.get("role_ids"), list) else []
        refreshed["enabled"] = bool(item.get("enabled", True))
        identity_keys = {
            "account": ("account",),
            "identifier": ("identifier",),
            "union_id": ("union_id", "unionId"),
            "open_id": ("open_id", "openId"),
            "user_id": ("user_id", "userId"),
        }
        for key, aliases in identity_keys.items():
            value = next((str(item.get(alias) or "").strip() for alias in aliases if str(item.get(alias) or "").strip()), "")
            if value:
                refreshed[key] = value
        refreshed["permission_identifier"] = (
            refreshed.get("identifier")
            or refreshed.get("union_id")
            or refreshed.get("open_id")
            or refreshed.get("user_id")
            or refreshed.get("account")
            or ""
        )
        for key in ("department", "department_ids", "position", "email", "enterprise_email", "mobile", "job_number", "employee_no", "oa_account", "manager", "organization", "organization_node_ids", "organization_codes", "company"):
            if item.get(key):
                refreshed[key] = item[key]
        return refreshed
    return user


def _is_user_disabled(user: Dict[str, Any]) -> bool:
    if not isinstance(user, dict) or user.get("role") == "super_admin":
        return False
    try:
        permissions = read_json("employee_permissions.json")
    except Exception:
        return False
    employees = permissions.get("employees") if isinstance(permissions, dict) else []
    identities = {
        str(user.get(key) or "").strip().lower()
        for key in ("employee_id", "username", "account", "union_id", "open_id", "user_id", "identifier")
        if str(user.get(key) or "").strip()
    }
    for item in employees if isinstance(employees, list) else []:
        if not isinstance(item, dict):
            continue
        candidates = {
            str(item.get(key) or "").strip().lower()
            for key in ("id", "account", "username", "union_id", "unionId", "open_id", "openId", "user_id", "userId", "identifier")
            if str(item.get(key) or "").strip()
        }
        if identities.intersection(candidates):
            return not bool(item.get("enabled", True))
    return False


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
