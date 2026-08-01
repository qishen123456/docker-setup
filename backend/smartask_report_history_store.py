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
from typing import Any, Dict, List, Optional

from config_manager import read_json, write_json


HISTORY_FILE = "smartask_report_history.json"
MAX_ITEMS_PER_SCOPE = 30
_LOCK = threading.RLock()


class StaleHistorySnapshotError(ValueError):
    """Raised when a saved history item conflicts with the current fact index."""

    code = "stale_history_snapshot"


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


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_int(*values: Any) -> Optional[int]:
    for value in values:
        parsed = _to_int(value)
        if parsed is not None:
            return parsed
    return None


_CN_NUMBER_MAP = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def _parse_cn_number(text: str) -> Optional[int]:
    text = str(text or "").strip()
    if not text:
        return None
    if text.isdigit():
        return _to_int(text)
    if text in _CN_NUMBER_MAP:
        return _CN_NUMBER_MAP[text]
    if "十" in text:
        left, _, right = text.partition("十")
        tens = _CN_NUMBER_MAP.get(left, 1) if left else 1
        ones = _CN_NUMBER_MAP.get(right, 0) if right else 0
        return tens * 10 + ones
    return None


def _explicit_rank_limit_from_question(question: str) -> Optional[int]:
    text = str(question or "")
    if not text:
        return None
    patterns = [
        r"(?:前|后|倒数|垫底|落后|最低|最差|最高|最好)\s*的?\s*([0-9]{1,2}|[一二两三四五六七八九十]{1,3})\s*(?:个|家|名|位|条)?",
        r"([0-9]{1,2}|[一二两三四五六七八九十]{1,3})\s*(?:个|家|名|位|条)?\s*(?:最差|最好|最低|最高|垫底|落后|倒数)",
        r"(?:top|bottom)\s*([0-9]{1,2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if not match:
            continue
        value = _parse_cn_number(match.group(1))
        if value is not None and 0 < value <= 20:
            return value
    return None


def _dataset_result_from_item(item: Dict[str, Any]) -> Dict[str, Any]:
    result = ((item.get("reportSnapshot") or {}).get("result") or {})
    if not isinstance(result, dict):
        return {}
    dataset_results = result.get("dataset_results")
    if isinstance(dataset_results, list) and dataset_results and isinstance(dataset_results[0], dict):
        return dataset_results[0]
    return result


def _question_from_item(item: Dict[str, Any], dataset_result: Dict[str, Any]) -> str:
    snapshot = item.get("reportSnapshot") if isinstance(item.get("reportSnapshot"), dict) else {}
    result = snapshot.get("result") if isinstance(snapshot.get("result"), dict) else {}
    return str(
        item.get("question")
        or snapshot.get("question")
        or result.get("question")
        or dataset_result.get("question")
        or item.get("title")
        or ""
    ).strip()


def _node_index_has_children(dataset_id: Any, node_name: str) -> bool:
    node_name = str(node_name or "").strip()
    if not node_name:
        return False
    target_dataset_id = _to_int(dataset_id)
    node_index = read_json("dataset_node_index.json") or {}
    for dataset in node_index.get("datasets") or []:
        current_id = _to_int(dataset.get("dataset_id"))
        if target_dataset_id is not None and current_id != target_dataset_id:
            continue
        for node in dataset.get("nodes") or []:
            if str(node.get("parent_name") or "").strip() == node_name:
                return True
    return False


def _is_explicit_aggregate_question(question: str) -> bool:
    return bool(re.search(r"(整体|总体|总览|汇总|全部|总计|合计)", str(question or "")))


def _is_stale_history_snapshot(item: Dict[str, Any]) -> bool:
    """Detect old snapshots that would restore a known-invalid interpretation.

    完全保留快照策略：只清理 ranking 数量明显不匹配的快照，不再因数据层级变化
    （focusNode leaf 冲突、自环异常等）删除历史记录，避免用户刷新后历史丢失。
    """
    dataset_result = _dataset_result_from_item(item)
    if not dataset_result:
        return False

    question = _question_from_item(item, dataset_result)
    query_intent = dataset_result.get("query_intent") if isinstance(dataset_result.get("query_intent"), dict) else {}
    explicit_limit = _explicit_rank_limit_from_question(question)
    stored_limit = _first_int(query_intent.get("top_n"), query_intent.get("top_limit"), query_intent.get("bottom_limit"))
    if (
        str(query_intent.get("intent") or "").lower() == "ranking"
        and explicit_limit is not None
        and stored_limit is not None
        and 0 < stored_limit < explicit_limit
    ):
        return True

    # 完全保留快照：不再因节点索引更新导致 focusNode leaf 冲突而删除历史记录
    # 这类变化属于数据/口径演进，不应让用户的历史对话消失。
    return False


def _safe_item(item: Dict[str, Any]) -> Dict[str, Any]:
    source = deepcopy(item or {})
    report_snapshot = source.get("reportSnapshot") if isinstance(source.get("reportSnapshot"), dict) else {}
    if not report_snapshot.get("result") and isinstance((source.get("sessionState") or {}).get("result"), dict):
        legacy_result = (source.get("sessionState") or {}).get("result") or {}
        report_snapshot = {
            "version": 2,
            "question": legacy_result.get("question") or source.get("question") or source.get("title") or "",
            "updatedAt": source.get("updatedAt") or datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            "datasetId": source.get("datasetId") or legacy_result.get("dataset_id") or None,
            "datasetName": source.get("datasetName") or legacy_result.get("dataset_name") or "",
            "result": legacy_result,
        }

    result = report_snapshot.get("result") if isinstance(report_snapshot.get("result"), dict) else {}
    if not result:
        safe = {
            "id": str(source.get("id") or "").strip(),
            "title": str(source.get("title") or source.get("question") or "未命名问题")[:24],
            "question": str(source.get("question") or source.get("title") or ""),
            "datasetId": source.get("datasetId"),
            "datasetName": source.get("datasetName") or "自动路由数据集",
            "updatedAt": source.get("updatedAt") or datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            "reportSnapshot": {},
        }
    else:
        question = str(
            source.get("question")
            or report_snapshot.get("question")
            or result.get("question")
            or source.get("title")
            or "未命名问题"
        ).strip()
        dataset_results = result.get("dataset_results") if isinstance(result.get("dataset_results"), list) else []
        first_dataset = dataset_results[0] if dataset_results and isinstance(dataset_results[0], dict) else {}
        updated_at = source.get("updatedAt") or report_snapshot.get("updatedAt") or datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        safe = {
            "id": str(source.get("id") or "").strip(),
            "title": str(source.get("title") or question or "未命名问题")[:24],
            "question": question,
            "datasetId": source.get("datasetId") or report_snapshot.get("datasetId") or result.get("dataset_id") or first_dataset.get("dataset_id"),
            "datasetName": source.get("datasetName") or report_snapshot.get("datasetName") or result.get("dataset_name") or first_dataset.get("dataset_name") or "自动路由数据集",
            "updatedAt": updated_at,
            "reportSnapshot": {
                **report_snapshot,
                "version": report_snapshot.get("version") or 2,
                "question": question,
                "updatedAt": updated_at,
                "result": result,
            },
        }
    safe["id"] = str(safe.get("id") or "").strip()
    safe["updatedAt"] = safe.get("updatedAt") or datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    safe["serverUpdatedAt"] = datetime.now().isoformat(timespec="seconds")
    if _is_stale_history_snapshot(safe):
        raise StaleHistorySnapshotError("history snapshot is stale and conflicts with current node index.")
    return safe


def list_history(user: Dict[str, Any] | None, limit: int = 50) -> List[Dict[str, Any]]:
    scope = build_history_scope(user)
    with _LOCK:
        store = _read_store()
        items = (store.get("history_by_scope") or {}).get(scope) or []
        if not isinstance(items, list):
            return []
        fresh_items = []
        changed = False
        for item in items:
            if isinstance(item, dict) and _is_stale_history_snapshot(item):
                changed = True
                continue
            fresh_items.append(item)
        if changed:
            store.setdefault("history_by_scope", {})[scope] = fresh_items
            _write_store(store)
        return deepcopy(fresh_items[: max(1, min(int(limit or 50), MAX_ITEMS_PER_SCOPE))])


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
        by_scope[scope] = [
            entry for entry in [safe, *items]
            if isinstance((entry.get("reportSnapshot") or {}).get("result"), dict)
        ][:MAX_ITEMS_PER_SCOPE]
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


def filter_history_dataset_results(
    history_items: List[Dict[str, Any]],
    allowed_dataset_ids: List[int] | set[int] | None,
) -> List[Dict[str, Any]]:
    """按数据集权限裁剪历史快照的 dataset_results。

    最小权限原则：历史 GET 返回前，把不在 allowed_dataset_ids 中的数据集结果移除。
    - 部分有权限：仅保留有权限的 dataset_results
    - 全部无权限：清空 dataset_results，并记录权限隔离错误（保留快照元信息，方便用户定位已丢失的历史条目）
    - allowed_dataset_ids 为 None：视为未启用权限系统，不做裁剪

    不修改传入的 history_items，返回全新 deepcopy 后的列表。
    """
    if allowed_dataset_ids is None:
        return deepcopy(history_items)

    allowed = {_to_int(x) for x in allowed_dataset_ids}
    allowed.discard(None)

    safe_items: List[Dict[str, Any]] = []
    for raw in history_items:
        item = deepcopy(raw or {})
        snapshot = item.get("reportSnapshot")
        if not isinstance(snapshot, dict):
            safe_items.append(item)
            continue
        result = snapshot.get("result")
        if not isinstance(result, dict):
            safe_items.append(item)
            continue
        dataset_results = result.get("dataset_results")
        if not isinstance(dataset_results, list) or not dataset_results:
            safe_items.append(item)
            continue

        filtered = [
            ds for ds in dataset_results
            if isinstance(ds, dict) and _to_int(ds.get("dataset_id")) in allowed
        ]
        if len(filtered) == len(dataset_results):
            # 全部在权限内，不改动
            safe_items.append(item)
            continue

        result["dataset_results"] = filtered
        if not filtered:
            result["error"] = result.get("error") or "权限不足，历史报告数据已按当前账号权限隔离。"
        snapshot["result"] = result
        item["reportSnapshot"] = snapshot
        safe_items.append(item)

    return safe_items

