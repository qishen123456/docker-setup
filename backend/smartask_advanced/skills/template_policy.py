from __future__ import annotations

from typing import Any, Dict, List


class TemplatePolicySkill:
    key = "template_policy"

    def run(
        self,
        *,
        question: str,
        result: Dict[str, Any],
        intent: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        intent = intent or {}
        warnings: List[Dict[str, Any]] = []
        suggestions: List[str] = []
        dataset_results = result.get("dataset_results") if isinstance(result, dict) else []
        primary = dataset_results[0] if dataset_results and isinstance(dataset_results[0], dict) else {}
        report_config = self._first_dict(
            primary.get("report_config"),
            result.get("report_config") if isinstance(result, dict) else None,
        )
        report_spec = self._first_dict(
            result.get("report_spec") if isinstance(result, dict) else None,
            primary.get("report_spec"),
        )
        spec_debug = report_spec.get("debug") if isinstance(report_spec.get("debug"), dict) else {}
        query_intent = self._first_dict(spec_debug.get("query_intent"), report_config.get("queryIntent"))
        ranking_policy = self._first_dict((report_config.get("intentPolicies") or {}).get("ranking"))

        question_top_n = self._safe_int(intent.get("topN"), 0)
        query_top_n = self._safe_int(query_intent.get("top_n") or query_intent.get("topN"), 0)
        configured_top_n = self._safe_int(ranking_policy.get("defaultTopN"), 0)
        max_top_n = self._safe_int(ranking_policy.get("maxTopN"), 20) or 20
        expected_top_n = question_top_n or configured_top_n or query_top_n or 10
        expected_top_n = max(1, min(max_top_n, expected_top_n))

        row_count = self._row_count(dataset_results)
        chart_rows = self._chart_row_count(report_spec)
        accordion_count = len(report_spec.get("accordions") or []) if isinstance(report_spec.get("accordions"), list) else 0
        mode = str(intent.get("intent") or query_intent.get("intent") or "").strip()
        is_ranking = mode == "ranking" or self._looks_like_ranking(question)

        if is_ranking and not report_config:
            warnings.append(
                {
                    "level": "medium",
                    "code": "template_policy_missing",
                    "message": "未发现数据集报告模板配置，TopN 展示只能使用进阶默认值。",
                }
            )
            suggestions.append("建议在数据集资产中维护 report_config.intentPolicies.ranking.defaultTopN。")

        if question_top_n and query_top_n and question_top_n != query_top_n:
            warnings.append(
                {
                    "level": "high",
                    "code": "template_query_intent_mismatch",
                    "message": f"用户问题要求 Top{question_top_n}，但本轮 queryIntent 为 Top{query_top_n}。",
                }
            )
            suggestions.append("排名类问题应以用户显式 TopN 为最高优先级。")
        elif not question_top_n and configured_top_n and query_top_n and configured_top_n != query_top_n:
            warnings.append(
                {
                    "level": "medium",
                    "code": "template_config_query_topn_mismatch",
                    "message": f"报告模板配置 Top{configured_top_n}，但本轮 queryIntent 为 Top{query_top_n}。",
                }
            )
            suggestions.append("未显式指定 TopN 时，应优先遵循报告模板配置。")

        if is_ranking and row_count >= expected_top_n:
            visible_count = max(chart_rows, accordion_count)
            if visible_count <= 0:
                warnings.append(
                    {
                        "level": "medium",
                        "code": "template_visible_topn_missing",
                        "message": f"报告结构未提供可见 TopN 明细，期望 Top{expected_top_n}。",
                    }
                )
                suggestions.append("report_spec 应提供可渲染的图表行、明细卡片或摘要结构。")
            elif visible_count < expected_top_n:
                warnings.append(
                    {
                        "level": "medium",
                        "code": "template_visible_topn_short",
                        "message": f"报告结构可见数量为 {visible_count}，低于期望 Top{expected_top_n}。",
                    }
                )
                suggestions.append("卡片、图表和摘要模块应跟随 report_config/queryIntent 的 TopN，不应固定 Top3。")

        return {
            "ok": not any(item.get("level") == "high" for item in warnings),
            "mode": mode or ("ranking" if is_ranking else "analysis"),
            "expected_top_n": expected_top_n,
            "source": self._source(question_top_n, query_top_n, configured_top_n),
            "configured_top_n": configured_top_n or None,
            "query_top_n": query_top_n or None,
            "question_top_n": question_top_n or None,
            "max_top_n": max_top_n,
            "row_count": row_count,
            "visible": {
                "chart_rows": chart_rows,
                "accordion_count": accordion_count,
            },
            "warning_count": len(warnings),
            "warnings": warnings,
            "suggestions": sorted(set(suggestions)),
        }

    @staticmethod
    def _first_dict(*values: Any) -> Dict[str, Any]:
        for value in values:
            if isinstance(value, dict):
                return value
        return {}

    @staticmethod
    def _safe_int(value: Any, fallback: int = 0) -> int:
        try:
            current = int(value)
        except Exception:
            return fallback
        return current if current > 0 else fallback

    @staticmethod
    def _row_count(dataset_results: Any) -> int:
        total = 0
        for item in dataset_results or []:
            rows = item.get("rows") if isinstance(item, dict) else []
            if isinstance(rows, list):
                total += len(rows)
        return total

    @staticmethod
    def _chart_row_count(report_spec: Dict[str, Any]) -> int:
        counts = []
        for chart in report_spec.get("charts") or []:
            rows = chart.get("rows") if isinstance(chart, dict) else []
            if isinstance(rows, list):
                counts.append(len(rows))
        return max(counts or [0])

    @staticmethod
    def _looks_like_ranking(question: str) -> bool:
        text = str(question or "").lower()
        return any(token in text for token in ["top", "排名", "排行", "最好", "最差", "最高", "最低", "前十", "前三"])

    @staticmethod
    def _source(question_top_n: int, query_top_n: int, configured_top_n: int) -> str:
        if question_top_n:
            return "question"
        if configured_top_n:
            return "report_config"
        if query_top_n:
            return "query_intent"
        return "advanced_default"
