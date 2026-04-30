from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import RLock
from typing import Any, Deque, Dict, List, Optional


class ShortTermMemoryStore:
    def __init__(self, max_rounds: int = 8, ttl_seconds: int = 2 * 60 * 60):
        self.max_rounds = max_rounds
        self.ttl_seconds = ttl_seconds
        self._items: Dict[str, Deque[Dict[str, Any]]] = defaultdict(lambda: deque(maxlen=self.max_rounds))
        self._lock = RLock()

    def get(self, session_id: str) -> List[Dict[str, Any]]:
        key = str(session_id or "").strip()
        if not key:
            return []
        now = time.time()
        with self._lock:
            items = self._items.get(key)
            if not items:
                return []
            kept = deque((item for item in items if now - float(item.get("created_at", now)) <= self.ttl_seconds), maxlen=self.max_rounds)
            if kept:
                self._items[key] = kept
            else:
                self._items.pop(key, None)
            return [self._public(item) for item in kept]

    def remember_result(
        self,
        session_id: str,
        question: str,
        route: Dict[str, Any],
        result: Dict[str, Any],
    ) -> None:
        dataset_results = result.get("dataset_results") or []
        primary = dataset_results[0] if dataset_results else {}
        rows = result.get("rows") or primary.get("rows") or []
        columns = result.get("columns") or primary.get("columns") or []
        item = {
            "created_at": time.time(),
            "question": question,
            "refined_query": route.get("refined_query") or question,
            "dataset_ids": route.get("dataset_ids") or [],
            "dataset_id": primary.get("dataset_id") or result.get("dataset_id"),
            "dataset_name": primary.get("dataset_name") or result.get("data_source"),
            "intent": route.get("intent"),
            "decision": route.get("decision"),
            "resolved_members": route.get("resolved_members") or [],
            "resolved_dimension": route.get("resolved_dimension") or "",
            "scope_mode": route.get("scope_mode") or "",
            "sql": result.get("sql") or primary.get("sql") or "",
            "columns": columns[:20] if isinstance(columns, list) else [],
            "row_count": result.get("row_count") or primary.get("row_count") or 0,
            "brief_result": self._brief_rows(rows),
            "analysis_summary": self._brief_text(result.get("analysis") or primary.get("analysis") or ""),
        }
        self._append(session_id, item)

    def remember_confirmation(
        self,
        session_id: str,
        question: str,
        route: Dict[str, Any],
        selected_option: Dict[str, Any],
    ) -> None:
        item = {
            "created_at": time.time(),
            "question": question,
            "refined_query": route.get("refined_query") or question,
            "dataset_ids": route.get("dataset_ids") or [],
            "intent": "confirmation",
            "decision": "confirmed",
            "selected_option": selected_option.get("label") or "",
            "resolved_members": selected_option.get("resolved_members") or [],
            "resolved_dimension": selected_option.get("resolved_dimension") or "",
            "scope_mode": selected_option.get("scope_mode") or "",
        }
        self._append(session_id, item)

    def resolve_followup(self, question: str, history: List[Dict[str, Any]]) -> Optional[str]:
        text = str(question or "").strip()
        if not text or not history:
            return None
        if not self._looks_like_followup(text):
            return None
        last = history[-1]
        base = str(last.get("refined_query") or last.get("question") or "").strip()
        if not base:
            return None
        return f"{base}\n本轮追问：{text}\n请沿用上一轮的数据集、统计层级、指标口径和时间范围，只替换或补充本轮追问明确表达的对象。"

    @staticmethod
    def _looks_like_followup(text: str) -> bool:
        compact = text.replace(" ", "")
        if len(compact) <= 12 and any(token in compact for token in ("那", "也", "呢", "对比", "相比", "继续", "这个", "它")):
            return True
        return any(token in compact for token in ("那东部", "那南部", "也看", "继续看", "和它比", "相比呢"))

    def _append(self, session_id: str, item: Dict[str, Any]) -> None:
        key = str(session_id or "").strip()
        if not key:
            return
        with self._lock:
            self._items[key].append(item)

    @staticmethod
    def _brief_rows(rows: Any) -> List[Dict[str, Any]]:
        if not isinstance(rows, list):
            return []
        return [row for row in rows[:3] if isinstance(row, dict)]

    @staticmethod
    def _brief_text(text: Any, limit: int = 500) -> str:
        value = str(text or "").strip()
        return value[:limit]

    @staticmethod
    def _public(item: Dict[str, Any]) -> Dict[str, Any]:
        return {key: value for key, value in item.items() if key != "created_at"}
