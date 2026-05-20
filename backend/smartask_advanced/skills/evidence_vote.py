from __future__ import annotations

from typing import Any, Dict, List


class EvidenceVoteSkill:
    key = "evidence_vote"

    def run(
        self,
        *,
        route_guard: Dict[str, Any] | None = None,
        sql_quality: Dict[str, Any] | None = None,
        pandas_report: Dict[str, Any] | None = None,
        template_policy: Dict[str, Any] | None = None,
        answer_contract: Dict[str, Any] | None = None,
        self_check: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        route_guard = route_guard or {}
        sql_quality = sql_quality or {}
        pandas_report = pandas_report or {}
        template_policy = template_policy or {}
        answer_contract = answer_contract or {}
        self_check = self_check or {}

        votes: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        self._vote_route(votes, warnings, route_guard)
        self._vote_sql(votes, warnings, sql_quality)
        self._vote_template(votes, warnings, template_policy)
        self._vote_pandas(votes, warnings, pandas_report)
        self._vote_answer(votes, warnings, answer_contract)
        self._vote_self_check(votes, warnings, self_check)

        score = max(0, min(100, 50 + sum(int(item.get("weight") or 0) for item in votes)))
        high_risk = any(item.get("level") == "high" for item in warnings)
        if high_risk or score < 45:
            decision = "review_required"
            action = "建议人工确认数据源、SQL 或核心结论后再采信。"
        elif score < 70:
            decision = "accept_with_caution"
            action = "可以作为辅助参考，但建议关注进阶风险提示。"
        else:
            decision = "accept"
            action = "多信号一致，当前结果可作为本轮经营分析参考。"

        return {
            "decision": decision,
            "confidence_score": score,
            "votes": votes,
            "warning_count": len(warnings),
            "warnings": warnings,
            "recommended_action": action,
        }

    @staticmethod
    def _add(votes: List[Dict[str, Any]], source: str, weight: int, decision: str, reason: str) -> None:
        votes.append({"source": source, "weight": weight, "decision": decision, "reason": reason})

    def _vote_route(self, votes: List[Dict[str, Any]], warnings: List[Dict[str, Any]], route_guard: Dict[str, Any]) -> None:
        action = str(route_guard.get("action") or "")
        if action in {"auto_lock", "manual_respected", "cross_dataset_compare"}:
            self._add(votes, "route_guard", 18, "support", route_guard.get("reason") or "路由守门通过。")
        elif action in {"manual_mismatch", "needs_confirmation"}:
            self._add(votes, "route_guard", -22, "risk", route_guard.get("reason") or "路由存在歧义。")
            warnings.append({"level": "high" if action == "manual_mismatch" else "medium", "code": f"vote_{action}", "message": route_guard.get("reason") or "路由存在歧义。"})
        elif action:
            self._add(votes, "route_guard", -5, "weak", route_guard.get("reason") or "路由置信度不足。")

    def _vote_sql(self, votes: List[Dict[str, Any]], warnings: List[Dict[str, Any]], sql_quality: Dict[str, Any]) -> None:
        score = float(sql_quality.get("score") or 0)
        if score >= 85:
            self._add(votes, "sql_quality", 20, "support", f"SQL 质量评分 {score}。")
        elif score >= 65:
            self._add(votes, "sql_quality", 8, "weak", f"SQL 质量评分 {score}，建议关注轻微风险。")
        else:
            self._add(votes, "sql_quality", -20, "risk", f"SQL 质量评分 {score}，低于进阶可信阈值。")
            warnings.append({"level": "high", "code": "vote_sql_quality_low", "message": f"SQL 质量评分 {score}，低于进阶可信阈值。"})

    def _vote_pandas(self, votes: List[Dict[str, Any]], warnings: List[Dict[str, Any]], pandas_report: Dict[str, Any]) -> None:
        datasets = [item for item in pandas_report.get("datasets") or [] if isinstance(item, dict)]
        row_count = sum(int(item.get("row_count") or 0) for item in datasets)
        has_ranking = any(((item.get("ranking") or {}).get("top") or []) for item in datasets)
        if row_count > 0 and has_ranking:
            self._add(votes, "pandas_analyze", 16, "support", f"Pandas 已加工 {row_count} 行并形成排序证据。")
        elif row_count > 0:
            self._add(votes, "pandas_analyze", 8, "weak", f"Pandas 已加工 {row_count} 行，但排序证据不足。")
        else:
            self._add(votes, "pandas_analyze", -18, "risk", "结果无可加工数据行。")
            warnings.append({"level": "high", "code": "vote_no_rows", "message": "结果无可加工数据行。"})

    def _vote_template(self, votes: List[Dict[str, Any]], warnings: List[Dict[str, Any]], template_policy: Dict[str, Any]) -> None:
        if not template_policy:
            return
        expected = template_policy.get("expected_top_n")
        if template_policy.get("warning_count"):
            high = any(item.get("level") == "high" for item in template_policy.get("warnings") or [])
            self._add(votes, "template_policy", -14 if high else -8, "risk", f"模板 TopN 策略存在风险，期望 Top{expected}。")
            warnings.extend([item for item in template_policy.get("warnings") or [] if isinstance(item, dict)])
        else:
            self._add(votes, "template_policy", 8, "support", f"模板 TopN 策略通过，期望 Top{expected}。")

    def _vote_answer(self, votes: List[Dict[str, Any]], warnings: List[Dict[str, Any]], answer_contract: Dict[str, Any]) -> None:
        if answer_contract.get("warning_count"):
            high = any(item.get("level") == "high" for item in answer_contract.get("warnings") or [])
            self._add(votes, "answer_contract", -18 if high else -10, "risk", "核心结论表达存在风险。")
            warnings.extend([item for item in answer_contract.get("warnings") or [] if isinstance(item, dict)])
        elif answer_contract:
            self._add(votes, "answer_contract", 12, "support", "核心结论契约检查通过。")

    def _vote_self_check(self, votes: List[Dict[str, Any]], warnings: List[Dict[str, Any]], self_check: Dict[str, Any]) -> None:
        if self_check.get("warning_count"):
            high = any(item.get("level") == "high" for item in self_check.get("warnings") or [])
            self._add(votes, "self_check", -20 if high else -10, "risk", "结果自检发现风险。")
            warnings.extend([item for item in self_check.get("warnings") or [] if isinstance(item, dict)])
        elif self_check:
            self._add(votes, "self_check", 10, "support", "结果自检通过。")
