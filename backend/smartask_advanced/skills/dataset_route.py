from __future__ import annotations

from typing import Any, Dict, List

from dataset_dimension_profiles import get_dataset_profile

from .common import as_int_list, tokens


class DatasetRouteSkill:
    key = "dataset_route"

    def __init__(self, repository):
        self.repository = repository

    @staticmethod
    def _profile_level_score(question: str, dataset: Dict[str, Any]) -> int:
        profile = get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
        if not profile:
            return 0
        text = str(question or "").replace(" ", "").lower()
        specific_levels = {
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
        score = 0
        for level in profile.get("levels") or []:
            aliases = [
                str(level.get("dimension_name") or ""),
                *[str(item or "") for item in (level.get("aliases") or [])],
            ]
            for alias in aliases:
                normalized_alias = alias.replace(" ", "").lower()
                if normalized_alias in specific_levels and normalized_alias in text:
                    score = max(score, 55)
        return score

    @staticmethod
    def score(question: str, dataset: Dict[str, Any]) -> int:
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
        return overlap * 12 + direct + name_hit + DatasetRouteSkill._profile_level_score(question, dataset)

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
