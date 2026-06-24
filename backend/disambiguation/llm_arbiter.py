from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from dataset_dimension_profiles import find_group_matches, get_dataset_profile, resolve_member_mentions
from .option_builder import build_dataset_options, fallback_confirmation
from .scoring import CandidateContext, needs_llm_arbitration, score_snapshot, _question_has_explicit_scope

ChatJsonFn = Callable[[str, str, Dict[str, Any], Any, str, str], Dict[str, Any]]


class DisambiguationArbiter:
    def should_arbitrate(self, question: str, candidate_contexts: List[CandidateContext], history: List[Dict[str, Any]]) -> bool:
        return needs_llm_arbitration(question, candidate_contexts, history)

    def evaluate(
        self,
        question: str,
        candidate_contexts: List[CandidateContext],
        history: List[Dict[str, Any]],
        chat_json: ChatJsonFn,
        trace: Any = None,
    ) -> Dict[str, Any]:
        candidates = self._candidate_payload(question, candidate_contexts)
        if not candidates:
            return {"need_confirm": False, "options": [], "auto_pick_option_id": ""}

        fallback = self._fallback(question, candidates, candidate_contexts)
        profile_auto_pick = self._profile_auto_pick(candidates)
        if profile_auto_pick:
            return profile_auto_pick
        if not self.should_arbitrate(question, candidate_contexts, history):
            return {"need_confirm": False, "options": [], "auto_pick_option_id": "", "reason": "high_confidence"}

        system_prompt = """
你是智能问数的数据集与统计口径仲裁器。
你只能根据候选数据集、候选分数、Golden SQL、数据字典摘要和对话历史判断是否需要确认。
不要硬编码字段名集合；如果上下文已经能消解追问，应自动选择并给出 auto_pick_option_id。
如果候选数据集的 resolved_profile_scope 已经把用户合称、简称或集合口径映射为明确成员，优先相信画像映射，不要把数据集名称误判为唯一业务对象。
如果多个数据集或统计口径都合理，必须让用户确认。

【评分与推荐】
- 为每个候选数据集从 0-100 打分（candidate_scores），评分维度：问题与数据集业务域的匹配度、层级/实体在数据集中的支持程度、常见问法和 Golden SQL 样本的相似度。
- 将得分最高的选项作为"系统推荐"放在 options 的第一位（label 中体现"系统推荐"）。
- 若 top 候选与 runner-up 的差距很小（<15 分）或 runner-up 分数也较高（>=55），必须 need_confirm=true。
- 只有当某个候选明显领先（score>=80 且 margin>=20）且口径无歧义时，才可 auto_pick。

只输出 JSON。
""".strip()
        user_prompt = f"""
用户当前问题：
{question}

最近对话历史（最多8轮）：
{json.dumps(history[-8:], ensure_ascii=False)}

候选数据集：
{json.dumps(candidates, ensure_ascii=False)}

分数摘要：
{json.dumps(score_snapshot(candidate_contexts), ensure_ascii=False)}

输出 JSON：
{{
  "need_confirm": true,
  "confirm_question": "一句面向业务用户的确认问题",
  "options": [
    {{"option_id":"arbiter_dataset_1", "dataset_id":1, "label":"系统推荐：商用事业部", "scope_filter":{{}}, "reason":"为什么适合", "score": 85}}
  ],
  "candidate_scores": [
    {{"dataset_id": 1, "dataset_name": "商用事业部", "score": 85, "reason": "匹配理由"}}
  ],
  "auto_pick_option_id": "",
  "refined_query": "可选：结合上下文重写后的问题",
  "reason": "简短判断依据"
}}
""".strip()
        result = chat_json(system_prompt, user_prompt, fallback, trace, "disambiguation.arbiter", "DisambiguationArbiter")
        return self._normalize(result, candidates, fallback, question, candidate_contexts)

    def _candidate_payload(self, question: str, candidate_contexts: List[CandidateContext]) -> List[Dict[str, Any]]:
        payload = []
        for dataset, context, score in candidate_contexts[:5]:
            dataset_id = int(dataset.get("id") or 0)
            if not dataset_id:
                continue
            samples = context.get("golden_sql_samples") or []
            dictionary = context.get("data_dictionary") or []
            profile_scope = self._profile_scope_payload(question, dataset)
            payload.append(
                {
                    "dataset_id": dataset_id,
                    "dataset_name": dataset.get("dataset_name") or f"数据集 {dataset_id}",
                    "dataset_code": dataset.get("dataset_code") or "",
                    "business_domain": dataset.get("business_domain") or "",
                    "score_hint": int(score or 0),
                    "sample_questions": [item.get("question") for item in samples[:3] if item.get("question")],
                    "dictionary_terms": [item.get("semantic_name") or item.get("column_name") for item in dictionary[:20]],
                    "has_lld": bool(str((context.get("lld_document") or {}).get("content") or "").strip()),
                    "resolved_profile_scope": profile_scope,
                }
            )
        return payload

    @staticmethod
    def _profile_scope_payload(question: str, dataset: Dict[str, Any]) -> Dict[str, Any]:
        profile = get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
        if not profile:
            return {}
        resolved = resolve_member_mentions(question, profile)
        groups = find_group_matches(question, profile)
        return {
            "intent": resolved.get("intent"),
            "scope_mode": resolved.get("scope_mode"),
            "all_members": resolved.get("all_members") or [],
            "entities": resolved.get("entities") or [],
            "matched_groups": [
                {
                    "group_name": item.get("group_name"),
                    "matched_alias": item.get("matched_alias"),
                    "dimension_name": item.get("dimension_name"),
                    "members": item.get("members") or [],
                }
                for item in groups
            ],
        }

    @staticmethod
    def _profile_auto_pick(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        hits = [
            item for item in candidates
            if (item.get("resolved_profile_scope") or {}).get("all_members")
        ]
        if not hits:
            return {}
        first = hits[0]
        first_members = [
            str(item).strip()
            for item in ((first.get("resolved_profile_scope") or {}).get("all_members") or [])
            if str(item).strip()
        ]
        if len(first_members) <= 1:
            return {}
        same_scope_hits = []
        first_member_set = set(first_members)
        for item in hits:
            members = {
                str(member).strip()
                for member in ((item.get("resolved_profile_scope") or {}).get("all_members") or [])
                if str(member).strip()
            }
            if members == first_member_set:
                same_scope_hits.append(item)
        if len(same_scope_hits) != len(hits):
            return {}
        return {
            "need_confirm": False,
            "confirm_question": "",
            "options": build_dataset_options([first]),
            "auto_pick_option_id": f"arbiter_dataset_{first['dataset_id']}",
            "refined_query": "",
            "reason": "profile_scope_resolved",
        }

    def _fallback(self, question: str, candidates: List[Dict[str, Any]], candidate_contexts: List[CandidateContext]) -> Dict[str, Any]:
        if len(candidate_contexts) >= 2 and not _question_has_explicit_scope(question, candidate_contexts):
            forced = fallback_confirmation(candidates[:3], question)
            forced["need_confirm"] = True
            forced["reason"] = "lacks_explicit_scope"
            forced["confirm_question"] = forced.get("confirm_question") or "问题中未明确指定事业部或数据集口径，请确认要分析哪个数据集："
            return forced
        scores = score_snapshot(candidate_contexts)
        if scores["top_score"] >= 70 and scores["margin"] >= 12:
            top = candidates[0]
            return {
                "need_confirm": False,
                "confirm_question": "",
                "options": build_dataset_options(candidates[:1]),
                "auto_pick_option_id": f"arbiter_dataset_{top['dataset_id']}",
                "refined_query": question,
                "reason": "top_candidate_score_clear",
            }
        return fallback_confirmation(candidates[:3], question)

    def _normalize(
        self,
        result: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        fallback: Dict[str, Any],
        question: str = "",
        candidate_contexts: Optional[List[CandidateContext]] = None,
    ) -> Dict[str, Any]:
        if not isinstance(result, dict):
            result = fallback
        force_scope_confirm = (
            candidate_contexts is not None
            and len(candidate_contexts) >= 2
            and not _question_has_explicit_scope(question, candidate_contexts)
        )
        candidate_by_id = {int(item["dataset_id"]): item for item in candidates if item.get("dataset_id")}
        normalized_options = []
        for index, option in enumerate(result.get("options") or []):
            if not isinstance(option, dict):
                continue
            dataset_id = int(option.get("dataset_id") or 0)
            if not dataset_id or dataset_id not in candidate_by_id:
                continue
            option_id = str(option.get("option_id") or option.get("id") or f"arbiter_dataset_{dataset_id}")
            normalized_options.append(
                {
                    "id": option_id,
                    "option_id": option_id,
                    "label": str(option.get("label") or candidate_by_id[dataset_id].get("dataset_name") or f"数据集 {dataset_id}"),
                    "description": str(option.get("reason") or option.get("description") or ""),
                    "dataset_ids": [dataset_id],
                    "option_type": "dataset_disambiguation",
                    "confirmation_type": "dataset_disambiguation",
                    "scope_filter": option.get("scope_filter") or {},
                }
            )

        if bool(result.get("need_confirm")) and not normalized_options:
            return fallback

        auto_pick = str(result.get("auto_pick_option_id") or "")
        valid_ids = {item["id"] for item in normalized_options}
        if auto_pick and auto_pick not in valid_ids:
            auto_pick = ""

        if force_scope_confirm and not auto_pick and not bool(result.get("need_confirm")):
            result["need_confirm"] = True
            if not normalized_options:
                return fallback

        return {
            "need_confirm": bool(result.get("need_confirm")) and not auto_pick,
            "confirm_question": str(result.get("confirm_question") or fallback.get("confirm_question") or "请确认要使用哪个数据集口径："),
            "options": normalized_options or build_dataset_options(candidates[:1]),
            "auto_pick_option_id": auto_pick,
            "refined_query": str(result.get("refined_query") or ""),
            "reason": str(result.get("reason") or fallback.get("reason") or ""),
        }
