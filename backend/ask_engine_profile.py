"""Pure helpers for the SmartAsk engine."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


def _profile_catalog(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    catalog = []
    for level in profile.get("levels") or []:
        if not isinstance(level, dict):
            continue
        members = [str(item).strip() for item in (level.get("members") or []) if str(item).strip()]
        groups = []
        for group in level.get("groups") or []:
            if isinstance(group, dict):
                groups.append(
                    {
                        "group_name": group.get("group_name"),
                        "aliases": group.get("aliases") or [],
                        "members": group.get("members") or [],
                    }
                )
        catalog.append(
            {
                "dimension_name": level.get("dimension_name"),
                "aliases": level.get("aliases") or [],
                "members": members[:80],
                "groups": groups[:20],
            }
        )
    return catalog


def _profile_member_map(profile: Dict[str, Any]) -> Dict[str, str]:
    member_map: Dict[str, str] = {}
    for level in profile.get("levels") or []:
        if not isinstance(level, dict):
            continue
        for member in level.get("members") or []:
            value = str(member or "").strip()
            if value:
                member_map[value] = str(level.get("dimension_name") or "").strip()
    return member_map


def _normalize_llm_ranking_params(raw_ranking: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(raw_ranking, dict):
        return None
    try:
        llm_top_n = int(raw_ranking.get("top_n")) if raw_ranking.get("top_n") is not None else None
    except Exception:
        llm_top_n = None
    llm_sides = str(raw_ranking.get("rank_sides") or "").strip().lower()
    if llm_sides not in {"top", "bottom", "both"}:
        llm_sides = ""
    llm_direction = str(raw_ranking.get("direction") or "").strip().lower()
    if llm_direction not in {"asc", "desc"}:
        llm_direction = ""
    llm_metric = str(raw_ranking.get("metric_hint") or "").strip() or None
    if llm_top_n is None and not llm_sides and not llm_direction and not llm_metric:
        return None
    return {
        "top_n": llm_top_n,
        "rank_sides": llm_sides,
        "direction": llm_direction,
        "metric_hint": llm_metric,
    }


def _normalize_entity_resolution(
    raw: Dict[str, Any],
    fallback: Dict[str, Any],
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    member_map = _profile_member_map(profile)
    ordered_members: List[str] = []
    entities_by_dimension: Dict[str, Dict[str, Any]] = {}

    for entity in raw.get("entities") or []:
        if not isinstance(entity, dict):
            continue
        dimension_name = str(entity.get("dimension_name") or "").strip()
        for member in entity.get("members") or []:
            member_name = str(member or "").strip()
            if not member_name:
                continue
            # 允许不在画像中的人名（如业务代表）
            is_person_name = re.fullmatch(r"[\u4e00-\u9fa5]{2,4}", member_name) is not None
            if not is_person_name and member_name not in member_map:
                continue
            resolved_dimension = dimension_name or member_map.get(member_name) or ""
            if member_name not in ordered_members:
                ordered_members.append(member_name)
            bucket = entities_by_dimension.setdefault(
                resolved_dimension,
                {
                    "dimension_name": resolved_dimension,
                    "members": [],
                    "matched_phrase": str(entity.get("matched_phrase") or entity.get("matched_alias") or "").strip(),
                    "source": str(raw.get("source") or entity.get("source") or "llm_semantic"),
                },
            )
            if member_name not in bucket["members"]:
                bucket["members"].append(member_name)

    if not ordered_members:
        for member in fallback.get("all_members") or []:
            member_name = str(member or "").strip()
            if not member_name or member_name not in member_map or member_name in ordered_members:
                continue
            ordered_members.append(member_name)
            dimension_name = member_map.get(member_name) or ""
            bucket = entities_by_dimension.setdefault(
                dimension_name,
                {
                    "dimension_name": dimension_name,
                    "members": [],
                    "matched_phrase": "",
                    "source": "profile_semantic",
                },
            )
            bucket["members"].append(member_name)
    else:
        for member in fallback.get("all_members") or []:
            member_name = str(member or "").strip()
            if not member_name or member_name not in member_map or member_name in ordered_members:
                continue
            ordered_members.append(member_name)
            dimension_name = member_map.get(member_name) or ""
            bucket = entities_by_dimension.setdefault(
                dimension_name,
                {
                    "dimension_name": dimension_name,
                    "members": [],
                    "matched_phrase": "",
                    "source": "profile_semantic",
                },
            )
            bucket["members"].append(member_name)

    scope_mode = str(raw.get("scope_mode") or raw.get("intent") or fallback.get("scope_mode") or "").lower()
    if len(ordered_members) > 1:
        scope_mode = "compare"
    elif len(ordered_members) == 1 and scope_mode not in {"aggregate", "ranking"}:
        scope_mode = "single"
    elif not ordered_members:
        scope_mode = "unknown"

    confidence = raw.get("confidence", fallback.get("confidence", 0))
    try:
        confidence_value = float(confidence)
    except Exception:
        confidence_value = 0

    # 解析并校验 LLM 输出的 ranking_params
    ranking_params = _normalize_llm_ranking_params(raw.get("ranking_params"))

    has_specific_node = raw.get("has_specific_node")
    if not isinstance(has_specific_node, bool):
        # LLM 未显式输出该标志时，按是否解析出真实成员推断：
        # 没有真实成员则视为未指定具体节点，避免 fallback 正则误触发。
        has_specific_node = bool(ordered_members)

    return {
        "intent": "compare" if scope_mode == "compare" else ("single" if scope_mode == "single" else str(raw.get("intent") or fallback.get("intent") or "unknown")),
        "scope_mode": scope_mode,
        "entities": list(entities_by_dimension.values()),
        "all_members": ordered_members,
        "confidence": confidence_value,
        "source": str(raw.get("source") or ("llm_semantic" if ordered_members else fallback.get("source") or "unknown")),
        "ranking_params": ranking_params,
        "has_specific_node": has_specific_node,
    }


def _profile_scope_hint(question: str, profile: Dict[str, Any], fallback: Dict[str, Any]) -> bool:
    if fallback.get("all_members"):
        return True
    normalized_question = re.sub(r"\s+", "", str(question or ""))
    for level in profile.get("levels") or []:
        if not isinstance(level, dict):
            continue
        terms = [level.get("dimension_name"), *(level.get("aliases") or [])]
        for term in terms:
            if term and str(term) in normalized_question:
                return True
    # 问题中包含显式人名（如"赵标和靳锋的业绩"、"赵标的业绩"）也应触发 Agent1.5 解析
    if re.search(r"[\u4e00-\u9fa5]{2,4}(?:(?:和|与|及|跟|、)[\u4e00-\u9fa5]{2,4})?(?:的)?(?:业绩|绩效|达成率|开单|完成情况|表现)", normalized_question):
        return True
    return False


def _resolved_entity_names(context: Dict[str, Any]) -> List[str]:
    resolved = context.get("resolved_entities") if isinstance(context, dict) else {}
    if not isinstance(resolved, dict):
        return []
    names: List[str] = []
    for name in resolved.get("all_members") or []:
        value = str(name or "").strip()
        if value and value not in names:
            names.append(value)
    for entity in resolved.get("entities") or []:
        if not isinstance(entity, dict):
            continue
        for name in entity.get("members") or []:
            value = str(name or "").strip()
            if value and value not in names:
                names.append(value)
    return names


def _dataset_root_name(dataset: Dict[str, Any]) -> str:
    """从数据集名称中提取可能的根节点名（如'商用事业部'），用于过滤默认带入的根节点别名。"""
    name = str(dataset.get("dataset_name") or "").strip()
    if not name:
        return ""
    name = re.sub(r"（[^）]+）", "", name)
    name = re.sub(r"\s+", "", name)
    name = re.sub(r"^(飞书|安吉|cloud|公共)", "", name, flags=re.I)
    name = re.sub(
        r"(测试数据集|数据集|数据|业绩|报告|分析|经营预算|预算|升级版|阶段一|阶段二|阶段[一二三四五六七八九十]+)$",
        "",
        name,
        flags=re.I,
    )
    # 只要能匹配到“...事业部”，就取到事业部为止，避免残留“经营”等词
    match = re.search(r".*?事业部", name)
    if match:
        return match.group(0)
    return name


def _is_dataset_root_name(name: str, dataset: Dict[str, Any]) -> bool:
    root = _dataset_root_name(dataset)
    if not root or not name:
        return False
    # 保守策略：只过滤名称明确为“XX事业部”的根节点别名，避免误伤普通业务词
    if not root.endswith("事业部"):
        return False
    return name == root


def _should_auto_expand_profile_group(question: str, matched_alias: str, members: List[str]) -> bool:
    if len(members) <= 1:
        return False
    text = re.sub(r"\s+", "", str(question or ""))
    alias = re.sub(r"\s+", "", str(matched_alias or ""))
    if not alias:
        return False
    explicit_group_markers = ("三大", "3大", "三个", "各", "所有", "全部", "每个", "分别", "对比", "比较", "排名", "排行")
    intent_markers = ("业绩", "表现", "情况", "如何", "怎么样", "达成", "开单", "任务", "缺口", "对比", "比较", "排名", "排行")
    return any(marker in alias or marker in text for marker in explicit_group_markers) and any(
        marker in text for marker in intent_markers
    )
