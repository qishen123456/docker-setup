from __future__ import annotations

from typing import Any, Dict, List, Tuple

CandidateContext = Tuple[Dict[str, Any], Dict[str, Any], int]


def score_snapshot(candidate_contexts: List[CandidateContext]) -> Dict[str, Any]:
    top = candidate_contexts[:3]
    top_score = int(top[0][2]) if top else 0
    runner_up_score = int(top[1][2]) if len(top) > 1 else 0
    return {
        "top_score": top_score,
        "runner_up_score": runner_up_score,
        "margin": top_score - runner_up_score,
        "candidate_count": len(candidate_contexts),
    }


def needs_llm_arbitration(question: str, candidate_contexts: List[CandidateContext], history: List[Dict[str, Any]]) -> bool:
    if not candidate_contexts:
        return False
    scores = score_snapshot(candidate_contexts)
    text = str(question or "")
    has_multi_dataset_risk = len(candidate_contexts) >= 2 and (
        scores["top_score"] < 70 or scores["margin"] < 12 or scores["runner_up_score"] >= 60
    )
    has_context_reference = bool(history) and any(token in text for token in ("那", "它", "这个", "上面", "继续", "也", "相比"))
    has_scope_risk = any(token in text for token in ("哪个口径", "口径", "分公司", "代表处", "条线", "事业部", "部门", "团队")) and scores["margin"] < 18
    return has_multi_dataset_risk or has_context_reference or has_scope_risk
