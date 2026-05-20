from __future__ import annotations

import re
from typing import Any, Dict, List


class AnswerContractSkill:
    key = "answer_contract"

    RANKING_WORDS = re.compile(r"最高|最低|最好|最差|排名|排行|top|前\d+|前三|前十", re.IGNORECASE)
    COMPARISON_WORDS = re.compile(r"对比|比较|差异|和.+比|与.+比|vs", re.IGNORECASE)

    def run(
        self,
        *,
        question: str,
        result: Dict[str, Any],
        pandas_report: Dict[str, Any] | None = None,
        intent: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        intent = intent or {}
        pandas_report = pandas_report or {}
        analysis = str((result or {}).get("analysis") or "").strip()
        question_text = str(question or "")
        mode = str(intent.get("intent") or self._infer_mode(question_text))
        warnings: List[Dict[str, Any]] = []
        suggestions: List[str] = []
        evidence = self._primary_evidence(pandas_report)

        if mode == "ranking":
            best_label = str((evidence.get("best") or {}).get("label") or "").strip()
            first_part = analysis[:180]
            target_level = str(intent.get("targetLevel") or self._target_level(question_text) or "").strip()
            if target_level and best_label and not self._label_matches_level(best_label, target_level):
                warnings.append(
                    {
                        "level": "high",
                        "code": "ranking_answer_level_mismatch",
                        "message": f"用户询问 {target_level} 层级，但当前最优证据对象是 {best_label}。",
                    }
                )
                suggestions.append(f"请先返回 {target_level} 层级的最优对象，再把下级组织作为支撑证据。")
            if best_label and best_label not in first_part:
                warnings.append(
                    {
                        "level": "medium",
                        "code": "ranking_answer_not_first",
                        "message": f"排名类问题未在开篇直接点名最优对象：{best_label}。",
                    }
                )
                suggestions.append(f"核心结论第一句建议改为：本轮完成最好的对象是 {best_label}。")
            if best_label and best_label not in analysis:
                warnings.append(
                    {
                        "level": "high",
                        "code": "ranking_answer_missing",
                        "message": f"报告正文未出现最优对象：{best_label}。",
                    }
                )
        elif mode == "comparison":
            mentioned = self._mentioned_orgs(question_text)
            missing = [item for item in mentioned if item and item not in analysis]
            if missing:
                warnings.append(
                    {
                        "level": "medium",
                        "code": "comparison_subject_missing",
                        "message": "对比问题报告未完整覆盖对比对象：" + "、".join(missing[:5]),
                    }
                )
                suggestions.append("对比类问题应先给出双方结论，再展开指标差异。")

        if evidence.get("best_rate") is not None and evidence.get("best_rate") < 60:
            suggestions.append("即使最优对象排名第一，也应提示其达成率低于 60% 经营红线。")

        return {
            "ok": not any(item.get("level") == "high" for item in warnings),
            "mode": mode,
            "warning_count": len(warnings),
            "warnings": warnings,
            "suggestions": sorted(set(suggestions)),
            "evidence": evidence,
        }

    def _infer_mode(self, question: str) -> str:
        if self.RANKING_WORDS.search(question or ""):
            return "ranking"
        if self.COMPARISON_WORDS.search(question or ""):
            return "comparison"
        return "analysis"

    @staticmethod
    def _primary_evidence(pandas_report: Dict[str, Any]) -> Dict[str, Any]:
        for dataset in pandas_report.get("datasets") or []:
            ranking = dataset.get("ranking") or {}
            top = ranking.get("top") or []
            if not top:
                continue
            best = top[0]
            value = best.get("value")
            return {
                "dataset_id": dataset.get("dataset_id"),
                "dataset_name": dataset.get("dataset_name"),
                "sort_column": ranking.get("sort_column"),
                "best": {"label": best.get("label"), "value": value},
                "best_row": best.get("row") or {},
                "metrics": dataset.get("metrics") or {},
                "best_rate": value if "率" in str(ranking.get("sort_column") or "") and isinstance(value, (int, float)) else None,
            }
        return {}

    @staticmethod
    def _mentioned_orgs(question: str) -> List[str]:
        candidates = re.findall(r"[\u4e00-\u9fff]{2,12}(?:分公司|事业部|城市公司|代表处|业务部)", question or "")
        result = []
        for item in candidates:
            if item not in result:
                result.append(item)
        return result

    @staticmethod
    def _target_level(question: str) -> str:
        for level in ("事业部", "分公司", "城市公司", "城市", "代表处", "业务部", "业务代表", "业务员"):
            if level in str(question or ""):
                return level
        return ""

    @staticmethod
    def _label_matches_level(label: str, target_level: str) -> bool:
        text = str(label or "")
        level = str(target_level or "")
        if not level:
            return True
        if level == "城市":
            return "城市" in text
        if level in {"业务代表", "业务员"}:
            return True
        return level in text
