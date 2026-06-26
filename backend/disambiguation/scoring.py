from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from organization_tree_store import load_organization_trees

CandidateContext = Tuple[Dict[str, Any], Dict[str, Any], int]


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "")).lower()


def _extract_scope_keywords(candidate_contexts: List[CandidateContext]) -> set:
    """Extract explicit scope identifiers from dataset metadata and organization tree."""
    keywords: set = set()
    for dataset, _context, _score in candidate_contexts:
        for key in ("dataset_name", "dataset_code", "business_domain"):
            value = str(dataset.get(key) or "").strip()
            if value:
                keywords.add(_compact(value))
        for alias in dataset.get("synonyms") or []:
            value = str(alias or "").strip()
            if value:
                keywords.add(_compact(value))
    try:
        tree = load_organization_trees()
        for node in (tree.get("nodes") or []):
            name = str(node.get("name") or "").strip()
            if name:
                keywords.add(_compact(name))
    except Exception:
        pass
    return keywords


def _question_has_explicit_scope(question: str, candidate_contexts: List[CandidateContext]) -> bool:
    """Check whether the question explicitly mentions a dataset or organization scope."""
    compact_question = _compact(question)
    if not compact_question:
        return False
    keywords = _extract_scope_keywords(candidate_contexts)
    for keyword in keywords:
        if keyword and keyword in compact_question:
            return True
    return False


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
    has_explicit_scope = _question_has_explicit_scope(question, candidate_contexts)
    # 只有当头部候选没拉开差距，或亚军分数也很高（>=75）且差距<20 时才需要仲裁
    has_multi_dataset_risk = len(candidate_contexts) >= 2 and (
        scores["top_score"] < 70
        or scores["margin"] < 12
        or (scores["runner_up_score"] >= 75 and scores["margin"] < 20)
    )
    has_context_reference = bool(history) and any(token in text for token in ("那", "它", "这个", "上面", "继续", "也", "相比"))
    # 含层级词时，如果已经明确指定了数据集/业务域，不再因为 margin 偏低强制仲裁
    has_scope_risk = (
        not has_explicit_scope
        and any(token in text for token in ("哪个口径", "口径", "分公司", "代表处", "条线", "事业部", "部门", "团队"))
        and scores["margin"] < 25
    )
    # 关键规则：多个候选数据集且问题未明确指定数据集/组织范围时，必须交由 LLM 仲裁并推荐
    lacks_explicit_scope = len(candidate_contexts) >= 2 and not has_explicit_scope
    return has_multi_dataset_risk or has_context_reference or has_scope_risk or lacks_explicit_scope
