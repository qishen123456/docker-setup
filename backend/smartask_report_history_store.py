"""
Persistent SmartAsk report history.

The UI keeps a localStorage cache for speed, but production deployments need a
server-side copy that survives frontend rebuilds, container recreates, and code
updates. This store writes per-user report snapshots into config/, which is
already mounted by docker-compose and protected by update.sh backups.
"""

from __future__ import annotations

import re
import threading
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List

from config_manager import read_json, write_json


HISTORY_FILE = "smartask_report_history.json"
MAX_ITEMS_PER_SCOPE = 200
_LOCK = threading.RLock()


def _normalize_scope_part(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9_\-@.]+", "_", text, flags=re.I)
    text = re.sub(r"^_+|_+$", "", text)
    return text or "anonymous"


def build_history_scope(user: Dict[str, Any] | None) -> str:
    user = user or {}
    role = _normalize_scope_part(user.get("role") or "user")
    identity = _normalize_scope_part(
        user.get("username")
        or user.get("login_account")
        or user.get("account")
        or user.get("union_id")
        or user.get("permission_identifier")
        or user.get("name")
        or "anonymous"
    )
    return f"{role}:{identity}"


def _empty_store() -> Dict[str, Any]:
    return {"version": 1, "history_by_scope": {}}


def _read_store() -> Dict[str, Any]:
    data = read_json(HISTORY_FILE) or {}
    if not isinstance(data, dict):
        return _empty_store()
    if not isinstance(data.get("history_by_scope"), dict):
        data["history_by_scope"] = {}
    data.setdefault("version", 1)
    return data


def _write_store(data: Dict[str, Any]) -> None:
    write_json(HISTORY_FILE, data)


def _safe_item(item: Dict[str, Any]) -> Dict[str, Any]:
    safe = deepcopy(item or {})
    safe["id"] = str(safe.get("id") or "").strip()
    safe["updatedAt"] = safe.get("updatedAt") or datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    safe["serverUpdatedAt"] = datetime.now().isoformat(timespec="seconds")
    return safe


def list_history(user: Dict[str, Any] | None, limit: int = 50) -> List[Dict[str, Any]]:
    scope = build_history_scope(user)
    with _LOCK:
        items = (_read_store().get("history_by_scope") or {}).get(scope) or []
        if not isinstance(items, list):
            return []
        return deepcopy(items[: max(1, min(int(limit or 50), MAX_ITEMS_PER_SCOPE))])


def upsert_history(user: Dict[str, Any] | None, item: Dict[str, Any]) -> Dict[str, Any]:
    scope = build_history_scope(user)
    safe = _safe_item(item)
    if not safe.get("id"):
        raise ValueError("history item id is required")

    with _LOCK:
        store = _read_store()
        by_scope = store.setdefault("history_by_scope", {})
        items = by_scope.get(scope) or []
        items = [entry for entry in items if str(entry.get("id")) != safe["id"]]
        by_scope[scope] = [safe, *items][:MAX_ITEMS_PER_SCOPE]
        _write_store(store)
    return deepcopy(safe)


def remove_history(user: Dict[str, Any] | None, item_id: str) -> None:
    scope = build_history_scope(user)
    item_id = str(item_id or "").strip()
    with _LOCK:
        store = _read_store()
        by_scope = store.setdefault("history_by_scope", {})
        by_scope[scope] = [
            entry for entry in (by_scope.get(scope) or [])
            if str(entry.get("id")) != item_id
        ]
        _write_store(store)


def clear_history(user: Dict[str, Any] | None) -> None:
    scope = build_history_scope(user)
    with _LOCK:
        store = _read_store()
        store.setdefault("history_by_scope", {})[scope] = []
        _write_store(store)
