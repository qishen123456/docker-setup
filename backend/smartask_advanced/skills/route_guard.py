from __future__ import annotations

import re
from typing import Any, Dict, List

from organization_route_resolver import OrganizationRouteResolver

from .common import as_int_list


class RouteGuardSkill:
    key = "route_guard"

    def __init__(self, repository):
        self.repository = repository
        self.organization_resolver = OrganizationRouteResolver()

    @staticmethod
    def _looks_like_branch_dataset_ambiguity(question: str, candidates: List[Dict[str, Any]]) -> bool:
        text = str(question or "").strip()
        compact = re.sub(r"\s+", "", text)
        if not compact or "分公司" not in compact:
            return False
        if any(token in compact for token in ["商用", "商用事业部", "消费者", "消费者事业部", "城市分公司", "城市公司", "代表处", "业务部", "业务员", "业务代表"]):
            return False
        names = [str(item.get("dataset_name") or "") for item in (candidates or [])[:3]]
        has_commercial = any("商用事业部" in name for name in names)
        has_consumer = any("消费者" in name for name in names)
        return has_commercial and has_consumer

    @staticmethod
    def _unique_int(values) -> List[int]:
        if values is None:
            values = []
        elif isinstance(values, (str, int, float)):
            values = [values]
        result: List[int] = []
        for value in values or []:
            try:
                current = int(value)
            except Exception:
                continue
            if current not in result:
                result.append(current)
        return result

    @staticmethod
    def _compact_org_route(route: Dict[str, Any] | None) -> Dict[str, Any]:
        if not isinstance(route, dict):
            return {}
        return {
            "dataset_ids": RouteGuardSkill._unique_int(route.get("dataset_ids") or []),
            "candidate_dataset_ids": RouteGuardSkill._unique_int(route.get("candidate_dataset_ids") or route.get("dataset_ids") or []),
            "requires_confirmation": bool(route.get("requires_confirmation")),
            "decision": route.get("decision"),
            "reason": route.get("arbiter_reason"),
            "resolved_members": route.get("resolved_members") or route.get("resolved_entities_preview") or [],
            "organization_mentions": [
                {
                    "node_name": item.get("node_name"),
                    "matched_alias": item.get("matched_alias"),
                    "path_label": item.get("path_label"),
                    "dataset_ids": RouteGuardSkill._unique_int(item.get("dataset_ids") or []),
                    "dataset_names": item.get("dataset_names") or [],
                }
                for item in (route.get("organization_mentions") or [])[:8]
                if isinstance(item, dict)
            ],
            "confirmation_options": [
                {
                    "id": item.get("id"),
                    "label": item.get("label"),
                    "dataset_ids": RouteGuardSkill._unique_int(item.get("dataset_ids") or []),
                    "resolved_members": item.get("resolved_members") or [],
                }
                for item in (route.get("confirmation_options") or [])[:6]
                if isinstance(item, dict)
            ],
        }

    @staticmethod
    def _looks_like_cross_dataset_compare(question: str, org_route: Dict[str, Any]) -> bool:
        text = str(question or "").lower()
        compare_intent = any(token in text for token in ["对比", "比较", "差异", "vs", "相比", "进度"])
        if not compare_intent:
            compare_intent = bool(re.search(r"[\u4e00-\u9fff]{2,20}(和|与|跟)[\u4e00-\u9fff]{2,20}", text))
        mentions = org_route.get("organization_mentions") or []
        mentioned_names = {
            str(item.get("node_name") or "").strip()
            for item in mentions
            if isinstance(item, dict) and str(item.get("node_name") or "").strip()
        }
        mentioned_dataset_ids = {
            int(dataset_id)
            for item in mentions
            if isinstance(item, dict)
            for dataset_id in RouteGuardSkill._unique_int(item.get("dataset_ids") or [])
        }
        return compare_intent and len(mentioned_names) >= 2 and len(mentioned_dataset_ids) >= 2

    @staticmethod
    def _candidate_signal(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        top = candidates[0] if candidates else {}
        second = candidates[1] if len(candidates) > 1 else {}
        top_score = int(top.get("advanced_score") or 0) if top else 0
        second_score = int(second.get("advanced_score") or 0) if second else 0
        margin = top_score - second_score
        return {
            "top_dataset_id": int(top.get("id") or 0) if top else 0,
            "top_dataset_name": top.get("dataset_name") if top else "",
            "top_score": top_score,
            "second_score": second_score,
            "margin": margin,
            "candidate_count": len(candidates or []),
        }

    def run(
        self,
        *,
        question: str,
        candidates: List[Dict[str, Any]],
        preferred_dataset_ids=None,
        allowed_dataset_ids=None,
    ) -> Dict[str, Any]:
        preferred = self._unique_int(preferred_dataset_ids)
        signal = self._candidate_signal(candidates)
        catalog = self.repository.get_agent1_catalog()
        try:
            org_route = self.organization_resolver.resolve(question, catalog, allowed_dataset_ids=allowed_dataset_ids)
        except Exception as exc:
            org_route = None
            org_error = str(exc)
        else:
            org_error = ""

        org_compact = self._compact_org_route(org_route)
        org_dataset_ids = self._unique_int(org_compact.get("candidate_dataset_ids") or org_compact.get("dataset_ids") or [])
        result: Dict[str, Any] = {
            "action": "observe",
            "confidence": "low",
            "apply_dataset_ids": [],
            "recommended_dataset_ids": org_dataset_ids or ([signal["top_dataset_id"]] if signal.get("top_dataset_id") else []),
            "manual_selected": bool(preferred),
            "preferred_dataset_ids": preferred,
            "candidate_signal": signal,
            "organization_route": org_compact,
            "organization_route_error": org_error,
            "reason": "",
            "warnings": [],
        }

        if preferred:
            if (
                len(org_dataset_ids) > 1
                and self._looks_like_cross_dataset_compare(question, org_compact)
                and set(preferred).intersection(set(org_dataset_ids))
            ):
                result.update(
                    {
                        "action": "cross_dataset_compare",
                        "confidence": "high",
                        "apply_dataset_ids": org_dataset_ids,
                        "recommended_dataset_ids": org_dataset_ids,
                        "reason": "问题明确要求多个事业部/组织口径对比，已覆盖当前手动选择并纳入全部命中数据集。",
                    }
                )
            elif org_dataset_ids and set(preferred).isdisjoint(set(org_dataset_ids)):
                result.update(
                    {
                        "action": "manual_mismatch",
                        "confidence": "medium",
                        "reason": "用户手动选择的数据集与组织树解析的数据集不一致。",
                    }
                )
                result["warnings"].append("手动选择数据集可能与本轮业务组织不匹配。")
            else:
                result.update(
                    {
                        "action": "manual_respected",
                        "confidence": "high",
                        "recommended_dataset_ids": preferred,
                        "reason": "检测到用户已手动选择数据集，进阶流程尊重手动选择。",
                    }
                )
            return result

        if org_compact:
            if len(org_dataset_ids) > 1 and self._looks_like_cross_dataset_compare(question, org_compact):
                result.update(
                    {
                        "action": "cross_dataset_compare",
                        "confidence": "high",
                        "apply_dataset_ids": org_dataset_ids,
                        "recommended_dataset_ids": org_dataset_ids,
                        "reason": "问题明确要求多个事业部/组织口径对比，且组织树命中多个数据集，进阶流程按跨数据集对比执行。",
                    }
                )
                return result
            if org_dataset_ids and len(org_dataset_ids) == 1:
                result.update(
                    {
                        "action": "auto_lock",
                        "confidence": "high",
                        "apply_dataset_ids": org_dataset_ids,
                        "recommended_dataset_ids": org_dataset_ids,
                        "reason": "组织树命中多个组织但均指向同一数据集，进阶流程可按同源对比受控锁定。",
                    }
                )
                return result
            if org_compact.get("requires_confirmation"):
                result.update(
                    {
                        "action": "needs_confirmation",
                        "confidence": "medium",
                        "reason": "组织树命中多个组织或多个数据集，需要用户确认口径。",
                    }
                )
                result["warnings"].append("组织范围存在歧义，建议确认数据源后再执行。")
                return result
            if org_dataset_ids:
                result.update(
                    {
                        "action": "needs_confirmation",
                        "confidence": "medium",
                        "recommended_dataset_ids": org_dataset_ids,
                        "reason": "组织树命中多个候选数据集，需要用户确认业务场景。",
                    }
                )
                result["warnings"].append("组织范围跨多个数据集，建议确认数据源后再执行。")
                return result

        if not candidates:
            result.update({"action": "no_candidate", "reason": "未识别到可用候选数据集。"})
            result["warnings"].append("未识别到候选数据资产，建议手动选择数据集。")
            return result

        if self._looks_like_branch_dataset_ambiguity(question, candidates):
            result.update(
                {
                    "action": "needs_confirmation",
                    "confidence": "medium",
                    "reason": "问题只提到“分公司”，但当前候选同时包含商用事业部和消费者事业部，存在数据集歧义，需要先确认口径。",
                }
            )
            result["warnings"].append("请先确认是商用事业部分公司，还是消费者事业部分公司。")
            return result

        top_dataset_id = signal.get("top_dataset_id")
        high_score = int(signal.get("top_score") or 0) >= 90
        acceptable_score = int(signal.get("top_score") or 0) >= 45 and int(signal.get("margin") or 0) >= 18
        if top_dataset_id and (high_score or acceptable_score):
            result.update(
                {
                    "action": "auto_lock",
                    "confidence": "medium" if not high_score else "high",
                    "apply_dataset_ids": [top_dataset_id],
                    "recommended_dataset_ids": [top_dataset_id],
                    "reason": "候选数据集语义得分领先，进阶流程可受控锁定该数据源。",
                }
            )
            return result

        result.update(
            {
                "action": "needs_confirmation",
                "confidence": "low",
                "reason": "候选数据集得分不够明确，需要用户确认数据源。",
            }
        )
        result["warnings"].append("数据集路由置信度不足，建议手动确认数据源。")
        return result
