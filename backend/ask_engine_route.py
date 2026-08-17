"""Pure helpers for the SmartAsk engine."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


def _build_route_thought(route: Dict[str, Any], question: str, catalog: List[Dict[str, Any]]) -> str:
    if not isinstance(route, dict):
        return ""
    catalog_by_id = {int(item.get("id") or 0): item for item in catalog if item.get("id") is not None}
    dataset_ids = [int(item) for item in (route.get("dataset_ids") or route.get("candidate_dataset_ids") or []) if item is not None]
    dataset_name = ""
    if dataset_ids:
        dataset_name = catalog_by_id.get(dataset_ids[0], {}).get("dataset_name") or f"数据集 {dataset_ids[0]}"

    if route.get("requires_confirmation"):
        return "问题提到的口径在当前多个候选数据集中都可能成立，系统无法自动锁定唯一数据源，需要先确认本次分析范围。"

    reason = str(route.get("arbiter_reason") or "")
    if reason == "organization_tree_name_resolved":
        members = route.get("resolved_members") or []
        member_text = "、".join(str(item) for item in members[:2]) if members else "目标组织"
        return f"已从组织树识别到「{member_text}」，对应数据集「{dataset_name}」，系统已直接锁定数据范围。"

    if reason.startswith("explicit_dataset_"):
        return f"问题明确提到数据集/业务域关键词，匹配到「{dataset_name}」，系统自动锁定数据源。"

    if reason == "entity_mention_unique":
        return f"问题中提到的对象在多个候选数据集中只有「{dataset_name}」能解析，系统已锁定该数据源。"

    if reason.startswith("target_level_unique:"):
        level = reason.split(":", 1)[1] or "目标层级"
        return f"问题提到的「{level}」口径只有「{dataset_name}」支持，系统已直接锁定。"

    if reason == "single_allowed_dataset":
        return f"当前只有一个可用数据集「{dataset_name}」，系统已默认采用。"

    if reason == "profile_scope_resolved":
        return f"问题中的简称/合称已映射为「{dataset_name}」的明确成员范围，系统已锁定数据源。"

    if dataset_name:
        return f"根据问题关键词与数据集语义匹配，系统优先选择「{dataset_name}」作为数据源。"
    return "已完成问题理解，正在准备进入后续分析。"


def _looks_like_ranking_question(question: str) -> bool:
    text = str(question or "").lower()
    return bool(re.search(
        r"前\s*(?:\d+|[一二两三四五六七八九十]+)|后\s*(?:\d+|[一二两三四五六七八九十]+)|"
        r"倒数|排名|排行|\btop\s*\d*|最高|最低|最好|最差|最大|最小|垫底|落后",
        text,
    ))


def _route_entity_resolution(route: Dict[str, Any]) -> Dict[str, Any]:
    members = []
    for name in route.get("resolved_members") or route.get("resolved_entities_preview") or []:
        value = str(name or "").strip()
        if value and value not in members:
            members.append(value)
    for mention in route.get("organization_mentions") or []:
        if not isinstance(mention, dict):
            continue
        value = str(mention.get("node_name") or "").strip()
        if value and value not in members:
            members.append(value)
    if not members:
        return {}
    scope_mode = str(route.get("scope_mode") or "").strip().lower()
    if scope_mode not in {"single", "compare", "aggregate", "ranking"}:
        scope_mode = "compare" if len(members) > 1 else "single"
    return {
        "intent": "compare" if scope_mode == "compare" else ("single" if scope_mode == "single" else scope_mode),
        "scope_mode": scope_mode,
        "entities": [
            {
                "dimension_name": "组织树节点",
                "members": members,
                "matched_phrase": "、".join(members),
                "source": "organization_tree_route",
            }
        ],
        "all_members": members,
        "confidence": 1.0,
        "source": "organization_tree_route",
    }


def _matched_org_level_terms(question: str) -> List[str]:
    text = str(question or "")
    ordered_terms = ["业务承接人", "任务承接人", "承接人", "负责人", "城市分公司", "城市公司", "业务代表", "业务员", "代表处", "业务部", "分公司", "条线"]
    matched: List[str] = []
    for term in ordered_terms:
        if term not in text:
            continue
        if term == "分公司" and "城市分公司" in matched:
            continue
        matched.append(term)
    return matched


def _summarize_candidate_strengths(context: Dict[str, Any]) -> Dict[str, Any]:
    samples = context.get("golden_sql_samples", []) or []
    common_questions = context.get("common_questions", []) or []
    return {
        "golden_sql_count": len(samples),
        "top_sample_questions": [item.get("question", "") for item in samples[:3] if item.get("question")],
        "common_question_examples": [item.get("question_text", "") for item in common_questions[:3] if item.get("question_text")],
        "has_lld": bool(str((context.get("lld_document") or {}).get("content") or "").strip()),
        "schema_table_count": len(context.get("schema_definition", []) or []),
        "dictionary_count": len(context.get("data_dictionary", []) or []),
    }


def _filter_route_by_allowed_datasets(route: Dict[str, Any], allowed_set: set[int]) -> Dict[str, Any]:
    route = dict(route or {})

    def allowed_ids(values: Any) -> List[int]:
        result: List[int] = []
        for item in values or []:
            try:
                dataset_id = int(item)
            except (TypeError, ValueError):
                continue
            if dataset_id in allowed_set and dataset_id not in result:
                result.append(dataset_id)
        return result

    route["dataset_ids"] = allowed_ids(route.get("dataset_ids"))
    route["candidate_dataset_ids"] = allowed_ids(route.get("candidate_dataset_ids"))
    route["split_queries"] = [
        item for item in (route.get("split_queries") or [])
        if isinstance(item, dict) and allowed_ids([item.get("dataset_id")])
    ]
    filtered_options = []
    for option in route.get("confirmation_options") or []:
        if not isinstance(option, dict):
            continue
        next_option = dict(option)
        next_option["dataset_ids"] = allowed_ids(next_option.get("dataset_ids"))
        if next_option["dataset_ids"]:
            filtered_options.append(next_option)
    route["confirmation_options"] = filtered_options
    if route.get("requires_confirmation") and not filtered_options:
        route["requires_confirmation"] = False
        route["decision"] = "generate_sql"
    return route
