from __future__ import annotations

from typing import Any, Dict, List


class ConclusionAdviceSkill:
    key = "conclusion_advice"

    def run(
        self,
        *,
        question: str,
        intent: Dict[str, Any] | None = None,
        pandas_report: Dict[str, Any] | None = None,
        answer_contract: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        intent = intent or {}
        pandas_report = pandas_report or {}
        answer_contract = answer_contract or {}
        mode = str(intent.get("intent") or answer_contract.get("mode") or "analysis")
        evidence = answer_contract.get("evidence") or self._evidence(pandas_report)
        suggestions: List[str] = []
        bullets: List[str] = []

        if mode == "ranking" and evidence.get("best"):
            best = evidence.get("best") or {}
            target_level = str(intent.get("targetLevel") or "对象")
            label = str(best.get("label") or "排名第一对象")
            sort_column = str(evidence.get("sort_column") or "排序指标")
            value = self._format_metric(best.get("value"), sort_column)
            if target_level and target_level not in label and target_level not in {"对象", "业务代表", "业务员"}:
                suggestions.append(f"建议先回到 {target_level} 层级重新聚合，再输出核心结论。当前证据对象是 {label}。")
            else:
                suggestions.append(f"建议核心结论：本轮完成最好的{target_level}是 {label}，{sort_column}为 {value}。")
            metrics = self._metric_payload(evidence)
            for key, label_text in [("task", "总任务"), ("actual", "实际完成"), ("gap", "任务缺口")]:
                if metrics.get(key) is not None:
                    bullets.append(f"{label_text}：{self._format_amount(metrics.get(key))}")
            if evidence.get("best_rate") is not None and evidence.get("best_rate") < 60:
                bullets.append("风险提示：最优对象达成率仍低于 60% 红线，需要提示整体经营压力。")

        elif mode == "comparison":
            suggestions.append("建议核心结论：先分别说明双方关键指标和差距，再展开下级组织证据。")
            bullets.append("对比类问题应包含双方对象、达成率差异、任务差异、实际完成差异和风险节点。")

        if answer_contract.get("suggestions"):
            bullets.extend(str(item) for item in answer_contract.get("suggestions") or [])

        return {
            "mode": mode,
            "needs_rewrite": bool(answer_contract.get("warning_count") or suggestions),
            "suggested_conclusion": suggestions[0] if suggestions else "",
            "bullets": self._unique(bullets)[:8],
            "evidence": evidence,
        }

    @staticmethod
    def _unique(values: List[str]) -> List[str]:
        result = []
        for value in values or []:
            text = str(value or "").strip()
            if text and text not in result:
                result.append(text)
        return result

    @staticmethod
    def _evidence(pandas_report: Dict[str, Any]) -> Dict[str, Any]:
        for dataset in pandas_report.get("datasets") or []:
            ranking = dataset.get("ranking") or {}
            top = ranking.get("top") or []
            if not top:
                continue
            best = top[0]
            sort_column = ranking.get("sort_column")
            value = best.get("value")
            return {
                "dataset_id": dataset.get("dataset_id"),
                "dataset_name": dataset.get("dataset_name"),
                "sort_column": sort_column,
                "best": {"label": best.get("label"), "value": value},
                "best_row": best.get("row") or {},
                "best_rate": value if "率" in str(sort_column or "") and isinstance(value, (int, float)) else None,
                "metrics": dataset.get("metrics") or {},
            }
        return {}

    @staticmethod
    def _metric_payload(evidence: Dict[str, Any]) -> Dict[str, Any]:
        row = evidence.get("best_row") if isinstance(evidence.get("best_row"), dict) else {}
        metrics = evidence.get("metrics") if isinstance(evidence.get("metrics"), dict) else {}
        return {
            "task": ConclusionAdviceSkill._first_number(row, ["总任务", "任务", "目标"]) or metrics.get("task_total"),
            "actual": ConclusionAdviceSkill._first_number(row, ["实际", "开单", "完成", "年度开单"]) or metrics.get("actual_total"),
            "gap": ConclusionAdviceSkill._first_number(row, ["缺口", "差额", "剩余"]) or metrics.get("gap_total"),
        }

    @staticmethod
    def _first_number(row: Dict[str, Any], tokens: List[str]) -> Any:
        for key, value in (row or {}).items():
            text = str(key or "")
            if any(token in text for token in tokens):
                try:
                    return float(value)
                except Exception:
                    return value
        return None

    @staticmethod
    def _format_metric(value: Any, column: str = "") -> str:
        if value is None:
            return "暂无"
        try:
            number = float(value)
        except Exception:
            return str(value)
        if "率" in str(column):
            return f"{number:.2f}%"
        return ConclusionAdviceSkill._format_amount(number)

    @staticmethod
    def _format_amount(value: Any) -> str:
        try:
            number = float(value)
        except Exception:
            return str(value)
        abs_value = abs(number)
        if abs_value >= 100000000:
            return f"{number / 100000000:.2f}亿"
        if abs_value >= 10000:
            return f"{number / 10000:.2f}万"
        return f"{number:.2f}"
