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
        report_config = primary.get("report_config") or result.get("report_config") or {}
        sql_contract = report_config.get("sqlOutputContract") or {}
        amount_unit = str(
            sql_contract.get("amountUnit")
            or report_config.get("amountUnit")
            or report_config.get("amountUnitConvention")
            or ""
        ).strip() or "元"
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
            "amount_unit": amount_unit,
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
        # 条件类追问不拼完整 base，避免阈值叠加；沿用数据集、层级，并明确金额单位。
        if self._looks_like_condition_followup(text):
            amount_unit = str(last.get("amount_unit") or "元").strip()
            if amount_unit == "元":
                unit_hint = "注意：金额字段输出单位为'元'，例如 500万 必须写作 5000000，不能写成 500。"
            elif amount_unit == "万元":
                unit_hint = "注意：金额字段输出单位为'万元'，例如 500万 应写作 500。"
            else:
                unit_hint = f"注意：金额字段输出单位为'{amount_unit}'。"
            last_sql = str(last.get("sql") or "").strip()
            sql_hint = f"\n上一轮 SQL 供参考（不要保留其筛选条件）：\n{last_sql}" if last_sql else ""
            return f"基于上一轮的数据集和统计层级，独立回答新问题（不要保留上一轮的筛选条件）。{unit_hint}{sql_hint}\n新问题：{text}"
        return f"{base}\n本轮追问：{text}\n请沿用上一轮的数据集、统计层级、指标口径和时间范围，只替换或补充本轮追问明确表达的对象。"

    @staticmethod
    def _looks_like_followup(text: str) -> bool:
        compact = text.replace(" ", "")
        if len(compact) <= 12 and any(token in compact for token in ("那", "也", "呢", "对比", "相比", "继续", "这个", "它")):
            return True
        # 纯指标追问（达成率/完成率/多少/咋样）需沿用上轮主体，识别为追问；
        # 排除带组织层级词的新问法，避免"各分公司业绩咋样"被误判为追问。
        metric_tokens = ("达成率", "完成率", "进度", "多少", "咋样", "怎么样", "如何", "怎样")
        org_level_tokens = ("事业部", "分公司", "代表处", "业务部", "城市公司", "业务代表")
        if any(token in compact for token in metric_tokens) and len(compact) <= 12 and not any(t in compact for t in org_level_tokens):
            return True
        # 比较/筛选类条件追问也需要上文语境（如数据集、层级），视为追问
        if any(token in compact for token in ("大于", "小于", "高于", "低于", "超过", "不足", "等于", "不少于", "不多于")):
            return True
        return any(token in compact for token in ("那东部", "那南部", "也看", "继续看", "和它比", "相比呢"))

    @staticmethod
    def _looks_like_condition_followup(text: str) -> bool:
        compact = text.replace(" ", "")
        return any(token in compact for token in ("大于", "小于", "高于", "低于", "超过", "不足", "等于", "不少于", "不多于"))

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
