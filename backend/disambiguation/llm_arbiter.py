from __future__ import annotations

import json
from typing import Any, Callable, Dict, List

from .option_builder import build_dataset_options, fallback_confirmation
from .scoring import CandidateContext, needs_llm_arbitration, score_snapshot

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
        candidates = self._candidate_payload(candidate_contexts)
        if not candidates:
            return {"need_confirm": False, "options": [], "auto_pick_option_id": ""}

        fallback = self._fallback(question, candidates, candidate_contexts)
        if not self.should_arbitrate(question, candidate_contexts, history):
            return {"need_confirm": False, "options": [], "auto_pick_option_id": "", "reason": "high_confidence"}

        system_prompt = """
你是智能问数的数据集与统计口径仲裁器。
你只能根据候选数据集、候选分数、Golden SQL、数据字典摘要和对话历史判断是否需要确认。
不要硬编码字段名集合；如果上下文已经能消解追问，应自动选择并给出 auto_pick_option_id。
如果多个数据集或统计口径都合理，必须让用户确认。
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
    {{"option_id":"arbiter_dataset_1", "dataset_id":1, "label":"商用事业部", "scope_filter":{{}}, "reason":"为什么适合"}}
  ],
  "auto_pick_option_id": "",
  "refined_query": "可选：结合上下文重写后的问题",
  "reason": "简短判断依据"
}}
""".strip()
        result = chat_json(system_prompt, user_prompt, fallback, trace, "disambiguation.arbiter", "DisambiguationArbiter")
        return self._normalize(result, candidates, fallback)

    def _candidate_payload(self, candidate_contexts: List[CandidateContext]) -> List[Dict[str, Any]]:
        payload = []
        for dataset, context, score in candidate_contexts[:5]:
            dataset_id = int(dataset.get("id") or 0)
            if not dataset_id:
                continue
            samples = context.get("golden_sql_samples") or []
            dictionary = context.get("data_dictionary") or []
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
                }
            )
        return payload

    def _fallback(self, question: str, candidates: List[Dict[str, Any]], candidate_contexts: List[CandidateContext]) -> Dict[str, Any]:
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

    def _normalize(self, result: Dict[str, Any], candidates: List[Dict[str, Any]], fallback: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(result, dict):
            result = fallback
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

        return {
            "need_confirm": bool(result.get("need_confirm")) and not auto_pick,
            "confirm_question": str(result.get("confirm_question") or fallback.get("confirm_question") or "请确认要使用哪个数据集口径："),
            "options": normalized_options or build_dataset_options(candidates[:1]),
            "auto_pick_option_id": auto_pick,
            "refined_query": str(result.get("refined_query") or ""),
            "reason": str(result.get("reason") or fallback.get("reason") or ""),
        }
