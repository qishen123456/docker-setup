from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

from dataset_dimension_profiles import get_dataset_profile

from .common import as_int_list, tokens


class DatasetRouteSkill:
    key = "dataset_route"
    SPECIFIC_LEVELS = {
        "代表处",
        "办事处",
        "网点",
        "业务代表",
        "业务员",
        "业务部",
        "行业业务部",
        "城市公司",
        "城市分公司",
    }

    # 通用指标/统计口径词，不适合作为数据集判别依据
    METRIC_ONLY_ALIASES = {
        "达成率", "完成率", "开单", "开单金额", "年度开单", "销售金额", "销售",
        "任务", "任务金额", "总任务", "年度任务", "任务达成", "剩余任务", "缺口", "差额",
        "实际", "实际金额", "完成情况", "完成金额", "业绩", "指标", "数据", "分析", "结果",
    }
    # 通用组织/层级词，单独命中不能区分数据集
    GENERIC_ALIASES = {
        "事业部", "分公司", "代表处", "业务部", "城市公司", "城市分公司",
        "业务员", "业务代表", "公司", "部门", "团队",
    }

    def __init__(self, repository):
        self.repository = repository

    @staticmethod
    def _compact(text: str) -> str:
        return re.sub(r"\s+", "", str(text or "")).lower()

    @staticmethod
    def _profile_supported_levels(profile: Dict[str, Any]) -> set[str]:
        supported = set()
        for level in profile.get("levels") or []:
            aliases = [
                str(level.get("dimension_name") or ""),
                *[str(item or "") for item in (level.get("aliases") or [])],
            ]
            for alias in aliases:
                normalized_alias = alias.replace(" ", "").lower()
                if normalized_alias in DatasetRouteSkill.SPECIFIC_LEVELS:
                    supported.add(normalized_alias)
        return supported

    @staticmethod
    def _node_index_supported_levels(dataset: Dict[str, Any]) -> set[str]:
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "config",
            "dataset_node_index.json",
        )
        try:
            with open(path, "r", encoding="utf-8") as fh:
                node_index = json.load(fh)
        except Exception:
            return set()
        try:
            dataset_id = int(dataset.get("id") or 0)
        except Exception:
            dataset_id = 0
        dataset_code = DatasetRouteSkill._compact(dataset.get("dataset_code") or "")
        dataset_name = DatasetRouteSkill._compact(dataset.get("dataset_name") or "")
        supported = set()
        for item in node_index.get("datasets") or []:
            if not isinstance(item, dict):
                continue
            try:
                item_id = int(item.get("dataset_id") or 0)
            except Exception:
                item_id = 0
            item_code = DatasetRouteSkill._compact(item.get("dataset_code") or "")
            item_name = DatasetRouteSkill._compact(item.get("dataset_name") or "")
            code_matches = bool(
                dataset_code
                and (
                    item_code == dataset_code
                    or item_code.startswith(f"{dataset_code}_")
                    or dataset_code.startswith(f"{item_code}_")
                )
            )
            name_matches = bool(
                dataset_name
                and (
                    item_name == dataset_name
                    or dataset_name in item_name
                    or item_name in dataset_name
                )
            )
            if not ((dataset_id and item_id == dataset_id) or code_matches or name_matches):
                continue
            for node in item.get("nodes") or []:
                if not isinstance(node, dict):
                    continue
                level = DatasetRouteSkill._compact(node.get("node_level") or "")
                if level in DatasetRouteSkill.SPECIFIC_LEVELS:
                    supported.add(level)
        return supported

    @staticmethod
    def _profile_level_score(question: str, dataset: Dict[str, Any]) -> int:
        profile = get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
        text = str(question or "").replace(" ", "").lower()
        asked = {item for item in DatasetRouteSkill.SPECIFIC_LEVELS if item in text}
        if not asked:
            return 0
        supported = DatasetRouteSkill._profile_supported_levels(profile) if profile else set()
        if not supported:
            supported = DatasetRouteSkill._node_index_supported_levels(dataset)
        score = 0
        if asked.intersection(supported):
            score = 55
        unsupported = [item for item in asked if item not in supported]
        if unsupported:
            score -= min(60, 35 * len(unsupported))
        return score

    @staticmethod
    def _alias_score(question: str, dataset: Dict[str, Any]) -> int:
        """基于数据集名称、业务域、同义词的子串匹配打分。"""
        q = DatasetRouteSkill._compact(question)
        if not q:
            return 0

        alias_items = [
            (str(dataset.get("dataset_name") or ""), 100),
            (str(dataset.get("business_domain") or ""), 98),
        ]
        for synonym in dataset.get("synonyms") or []:
            alias_items.append((str(synonym or ""), 95))

        score = 0
        subject_suffixes = ("事业部", "分公司", "代表处", "业务部")
        for alias, base_score in alias_items:
            compact_alias = DatasetRouteSkill._compact(alias)
            if len(compact_alias) < 2:
                continue
            if compact_alias in DatasetRouteSkill.METRIC_ONLY_ALIASES or compact_alias in DatasetRouteSkill.GENERIC_ALIASES:
                continue
            if compact_alias in q:
                score = max(score, base_score)
                continue
            # 如果别名带事业部/分公司等业务主体后缀，前缀命中也加分
            for suffix in subject_suffixes:
                if compact_alias.endswith(suffix):
                    prefix = compact_alias[: -len(suffix)]
                    if len(prefix) >= 2 and prefix in q:
                        score = max(score, 90)
                    break
        return score

    @classmethod
    def score(cls, question: str, dataset: Dict[str, Any]) -> int:
        alias_score = cls._alias_score(question, dataset)
        if alias_score >= 90:
            return alias_score + cls._profile_level_score(question, dataset)

        query_tokens = tokens(question)
        text = " ".join(
            [
                str(dataset.get("dataset_name") or ""),
                str(dataset.get("business_domain") or ""),
                str(dataset.get("dataset_code") or ""),
                " ".join(dataset.get("synonyms") or []),
            ]
        )
        dataset_tokens = tokens(text)
        overlap = len(query_tokens.intersection(dataset_tokens))
        direct = sum(18 for token in query_tokens if token and token in text.lower())
        name_hit = 35 if str(dataset.get("dataset_name") or "") and str(dataset.get("dataset_name")) in question else 0
        return alias_score + overlap * 12 + direct + name_hit + cls._profile_level_score(question, dataset)

    def run(self, question: str, preferred_dataset_ids=None, limit: int = 3) -> List[Dict[str, Any]]:
        preferred = set(as_int_list(preferred_dataset_ids))
        catalog = self.repository.get_agent1_catalog()
        scored = []
        for item in catalog:
            dataset_id = int(item.get("id") or 0)
            score = 1000 if dataset_id in preferred else self.score(question, item)
            if score <= 0:
                continue
            scored.append({**item, "advanced_score": score})
        scored.sort(key=lambda item: (int(item.get("advanced_score") or 0), int(item.get("id") or 0)), reverse=True)
        if preferred:
            return [item for item in scored if int(item.get("id") or 0) in preferred][:limit]
        return scored[:limit]
