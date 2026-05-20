from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from data_permission_store import load_data_permissions
from organization_tree_store import load_organization_trees


ORG_ROUTE_REASON = "organization_tree_name_resolved"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _compact(value: Any) -> str:
    return re.sub(r"\s+", "", _text(value)).lower()


def _unique(items: List[Any]) -> List[Any]:
    result = []
    seen = set()
    for item in items:
        key = str(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


ORG_SUFFIXES = ("城市分公司", "城市公司", "分公司", "事业部", "业务部", "代表处")


def _node_suffix(compact_name: str) -> str:
    for suffix in ORG_SUFFIXES:
        if compact_name.endswith(suffix):
            return suffix
    return ""


def _node_aliases(name: str) -> List[str]:
    compact_name = _compact(name)
    if not compact_name:
        return []
    aliases = [compact_name]
    for suffix in ORG_SUFFIXES:
        if compact_name.endswith(suffix):
            prefix = compact_name[: -len(suffix)]
            if len(prefix) >= 2:
                aliases.append(prefix)
            break
    return _unique(aliases)


def _alias_matches_question(alias: str, node_name: str, normalized_question: str) -> bool:
    if not alias or alias not in normalized_question:
        return False
    compact_name = _compact(node_name)
    if alias == compact_name:
        return True

    node_suffix = _node_suffix(compact_name)
    start = 0
    while True:
        index = normalized_question.find(alias, start)
        if index < 0:
            return False
        tail = normalized_question[index + len(alias):]
        conflict_suffix = next((suffix for suffix in ORG_SUFFIXES if tail.startswith(suffix)), "")
        if not conflict_suffix or conflict_suffix == node_suffix:
            return True
        start = index + len(alias)


def _node_label(node: Dict[str, Any]) -> str:
    path = [str(item).strip() for item in (node.get("path_names") or []) if str(item).strip()]
    return " / ".join(path) or _text(node.get("name"))


def _is_compare_question(question: str) -> bool:
    return bool(re.search(r"对比|比较|差异|分别|各自|和.+比|跟.+比|与.+比|\bvs\b", question or "", re.I))


def _dataset_name(dataset_id: int, catalog_by_id: Dict[int, Dict[str, Any]]) -> str:
    item = catalog_by_id.get(int(dataset_id)) or {}
    return _text(item.get("dataset_name")) or f"数据集 {dataset_id}"


class OrganizationRouteResolver:
    """Resolve current-turn organization mentions before LLM dataset routing."""

    def __init__(self):
        self._tree_cache: Optional[Dict[str, Any]] = None

    def _load_tree(self) -> Dict[str, Any]:
        self._tree_cache = load_organization_trees()
        return self._tree_cache

    @staticmethod
    def _dataset_ids_for_node(node: Dict[str, Any], permissions: Dict[str, Any]) -> List[int]:
        node_id = _text(node.get("id"))
        tree_id = _text(node.get("tree_type_id"))
        path_ids = {_text(item) for item in (node.get("path_ids") or []) if _text(item)}
        path_ids.add(node_id)
        result: List[int] = []
        for raw_dataset_id, rule in (permissions.get("rules") or {}).items():
            if not isinstance(rule, dict) or _text(rule.get("mode")) != "org_tree":
                continue
            tree_ids = [_text(item) for item in (rule.get("tree_type_ids") or []) if _text(item)]
            legacy_tree_id = _text(rule.get("tree_type_id"))
            if legacy_tree_id and legacy_tree_id not in tree_ids:
                tree_ids.insert(0, legacy_tree_id)
            if tree_id not in tree_ids:
                continue
            selected = {_text(item) for item in (rule.get("organization_node_ids") or []) if _text(item)}
            if node_id in selected or path_ids.intersection(selected):
                try:
                    result.append(int(raw_dataset_id))
                except Exception:
                    continue
        return _unique(result)

    def _find_mentions(
        self,
        question: str,
        catalog: List[Dict[str, Any]],
        allowed_dataset_ids: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        normalized_question = _compact(question)
        if not normalized_question:
            return []
        allowed = {int(item) for item in allowed_dataset_ids} if allowed_dataset_ids is not None else None
        catalog_by_id = {int(item.get("id")): item for item in catalog if item.get("id") is not None}
        permissions = load_data_permissions()
        nodes = [
            node for node in (self._load_tree().get("nodes") or [])
            if isinstance(node, dict) and node.get("enabled", True)
        ]
        mentions: List[Dict[str, Any]] = []
        for node in nodes:
            name = _text(node.get("name"))
            if len(name) < 2:
                continue
            aliases = [
                alias
                for alias in _node_aliases(name)
                if _alias_matches_question(alias, name, normalized_question)
            ]
            if not aliases:
                continue
            dataset_ids = self._dataset_ids_for_node(node, permissions)
            if allowed is not None:
                dataset_ids = [item for item in dataset_ids if item in allowed]
            if not dataset_ids:
                continue
            matched_alias = max(aliases, key=len)
            mentions.append(
                {
                    "node_id": _text(node.get("id")),
                    "node_name": name,
                    "matched_alias": matched_alias,
                    "level": int(node.get("level") or 0),
                    "tree_type_id": _text(node.get("tree_type_id")),
                    "path_names": [str(item) for item in (node.get("path_names") or [])],
                    "path_label": _node_label(node),
                    "dataset_ids": dataset_ids,
                    "dataset_names": [_dataset_name(item, catalog_by_id) for item in dataset_ids],
                }
            )

        mentions.sort(key=lambda item: (len(item.get("matched_alias") or ""), item.get("level") or 0), reverse=True)
        deduped: List[Dict[str, Any]] = []
        covered_aliases = set()
        for item in mentions:
            key = item["node_id"]
            if any(existing["node_id"] == key for existing in deduped):
                continue
            alias = item.get("matched_alias") or ""
            if alias in covered_aliases and len(alias) < len(_compact(item.get("node_name"))):
                continue
            covered_aliases.add(alias)
            deduped.append(item)
        return deduped

    def _confirmation_option(
        self,
        option_id: str,
        label: str,
        description: str,
        dataset_ids: List[int],
        mentions: List[Dict[str, Any]],
        scope_mode: str,
    ) -> Dict[str, Any]:
        members = _unique([item["node_name"] for item in mentions])
        return {
            "id": option_id,
            "label": label,
            "description": description,
            "dataset_ids": [int(item) for item in dataset_ids],
            "option_type": "organization_tree_scope",
            "confirmation_type": "organization_tree_scope",
            "matched_alias": "、".join(_unique([item.get("matched_alias") or item["node_name"] for item in mentions])),
            "resolved_dimension": "组织树节点",
            "resolved_members": members,
            "resolved_dataset_name": " / ".join(_unique([name for item in mentions for name in item.get("dataset_names") or []])),
            "scope_mode": scope_mode,
            "organization_mentions": mentions,
        }

    def resolve(
        self,
        question: str,
        catalog: List[Dict[str, Any]],
        allowed_dataset_ids: Optional[List[int]] = None,
    ) -> Optional[Dict[str, Any]]:
        mentions = self._find_mentions(question, catalog, allowed_dataset_ids)
        if not mentions:
            return None

        distinct_node_names = _unique([item["node_name"] for item in mentions])
        dataset_ids = _unique([dataset_id for item in mentions for dataset_id in item.get("dataset_ids") or []])
        candidate_dataset_ids = dataset_ids[:]
        refined_suffix = f"组织树标准名称：{'、'.join(distinct_node_names)}。请优先按这些组织节点所属数据集和组织范围执行。"
        refined_query = f"{question}\n{refined_suffix}".strip()

        single_clear_node = len(mentions) == 1 and len(dataset_ids) == 1
        if single_clear_node:
            mention = mentions[0]
            return {
                "dataset_ids": [dataset_ids[0]],
                "intent": "detail",
                "refined_query": refined_query,
                "requires_confirmation": False,
                "decision": "generate_sql",
                "match_score": 98,
                "route_margin": 100,
                "matched_sample_id": None,
                "matched_sample_sql": "",
                "arbiter_reason": ORG_ROUTE_REASON,
                "candidate_dataset_ids": candidate_dataset_ids,
                "organization_mentions": mentions,
                "resolved_members": [mention["node_name"]],
                "scope_mode": "single",
                "split_queries": [{"dataset_id": dataset_ids[0], "sub_query": refined_query}],
            }

        if len(dataset_ids) == 1:
            scope_mode = "compare" if _is_compare_question(question) or len(distinct_node_names) > 1 else "aggregate"
            return {
                "dataset_ids": [dataset_ids[0]],
                "intent": "detail",
                "refined_query": refined_query,
                "requires_confirmation": False,
                "decision": "generate_sql",
                "match_score": 96,
                "route_margin": 100,
                "matched_sample_id": None,
                "matched_sample_sql": "",
                "arbiter_reason": ORG_ROUTE_REASON,
                "candidate_dataset_ids": candidate_dataset_ids,
                "organization_mentions": mentions,
                "resolved_members": distinct_node_names,
                "scope_mode": scope_mode,
                "split_queries": [{"dataset_id": dataset_ids[0], "sub_query": refined_query}],
            }

        options: List[Dict[str, Any]] = []
        by_dataset: Dict[int, List[Dict[str, Any]]] = {}
        for mention in mentions:
            for dataset_id in mention.get("dataset_ids") or []:
                by_dataset.setdefault(int(dataset_id), []).append(mention)
        for dataset_id, dataset_mentions in by_dataset.items():
            scope_mode = "compare" if len(_unique([item["node_name"] for item in dataset_mentions])) > 1 else "single"
            dataset_name = dataset_mentions[0].get("dataset_names", [f"数据集 {dataset_id}"])[0]
            node_text = "、".join(_unique([item["node_name"] for item in dataset_mentions]))
            options.append(
                self._confirmation_option(
                    option_id=f"org_dataset_{dataset_id}",
                    label=f"{dataset_name} · {node_text}",
                    description=f"按组织树命中的 {node_text} 所属数据集继续。路径：{'; '.join(item['path_label'] for item in dataset_mentions[:3])}",
                    dataset_ids=[dataset_id],
                    mentions=dataset_mentions,
                    scope_mode=scope_mode,
                )
            )

        return {
            "dataset_ids": candidate_dataset_ids[:1],
            "intent": "confirm",
            "refined_query": refined_query,
            "requires_confirmation": True,
            "decision": "wait_boss_confirm",
            "match_score": 92,
            "route_margin": 0,
            "confirmation_role": "boss",
            "confirmation_type": "organization_tree_scope",
            "confirmation_question": "检测到本轮问题命中多个组织树节点或存在组织数据集歧义，请确认本次查询口径：",
            "confirmation_options": options,
            "candidate_dataset_ids": candidate_dataset_ids,
            "organization_mentions": mentions,
            "resolved_entities_preview": distinct_node_names,
            "arbiter_reason": "organization_tree_scope_requires_confirmation",
        }
