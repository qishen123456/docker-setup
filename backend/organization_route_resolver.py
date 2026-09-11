from __future__ import annotations

import json
import os
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
    # 数据集域前缀别名豁免（2026-09-03 用服接入实测）：事业部根节点的"额外别名"
    # （非节点名前缀，如"用服"之于"用户服务与运营事业部"）紧跟层级词时是
    # "域+层级"用法（"用服分公司"=用服事业部的分公司），不是后缀冲突。
    # 若按普通冲突拒绝，"用服分公司滤芯排名"的"用服"会被丢弃，路由被其他数据集的
    # 节点别名（如电商"滤芯"）拐走。只豁免根节点额外别名，后缀剥离别名（"消费者"）
    # 保持原冲突判定不变。
    is_root_scope_alias = bool(alias) and not compact_name.startswith(alias) and node_suffix == "事业部"
    start = 0
    while True:
        index = normalized_question.find(alias, start)
        if index < 0:
            return False
        tail = normalized_question[index + len(alias):]
        conflict_suffix = next((suffix for suffix in ORG_SUFFIXES if tail.startswith(suffix)), "")
        if not conflict_suffix or conflict_suffix == node_suffix or (is_root_scope_alias and conflict_suffix):
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
        self._node_index_cache: Optional[Dict[str, Any]] = None

    def _load_tree(self) -> Dict[str, Any]:
        self._tree_cache = load_organization_trees()
        return self._tree_cache

    def _load_dataset_node_index(self) -> Dict[str, Any]:
        if self._node_index_cache is not None:
            return self._node_index_cache
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "dataset_node_index.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                self._node_index_cache = json.load(fh) or {}
        except Exception:
            self._node_index_cache = {}
        return self._node_index_cache

    # bug 2026-08-26：泛称+层级分解。用户问"商用分公司的业绩"时，
    # "商用分公司"不是真实节点名（实际节点是东部/北部/南部/西部分公司），
    # 旧逻辑把它当节点名塞进 节点名称 IN (...) → 必然 0 行。
    # 分解规则：entity = <节点名或别名> + <层级词>，如 "商用"+"分公司" →
    # 过滤条件应为 层级='分公司' AND 上级名称='商用事业部'（返回该层级全部子节点）。
    _GENERIC_LEVEL_WORDS = ("城市分公司", "分公司", "业务部", "事业部", "代表处", "城市公司")

    def resolve_generic_level_entity(self, entity: str, dataset_id: int) -> Optional[Dict[str, str]]:
        """'商用分公司' → {'level': '分公司', 'parent_name': '商用事业部'}。

        仅当 entity 本身不是该数据集的真实节点名、且去掉层级后缀后的前缀
        能通过 dataset_node_index 别名索引精确命中同数据集节点时生效；
        其余情况返回 None（调用方保持原行为，遵守 N5：不存在节点不得静默改写）。
        """
        text = _compact(str(entity or ""))
        if not text or len(text) < 4:
            return None
        try:
            target_dataset_id = int(dataset_id)
        except (TypeError, ValueError):
            return None
        node_index = self._load_dataset_node_index()
        # 1) entity 本身已是真实节点名 → 不需要分解
        for dataset in node_index.get("datasets") or []:
            if not isinstance(dataset, dict):
                continue
            try:
                if int(dataset.get("dataset_id") or 0) != target_dataset_id:
                    continue
            except (TypeError, ValueError):
                continue
            for node in dataset.get("nodes") or []:
                if _compact(str((node or {}).get("node_name") or "")) == text:
                    return None
            break
        # 2) 逐层级词（长优先）剥后缀，前缀走别名索引精确命中
        alias_index = node_index.get("flat_alias_index") or []
        for level in self._GENERIC_LEVEL_WORDS:
            if not text.endswith(level) or len(text) <= len(level):
                continue
            prefix = text[: -len(level)]
            if len(prefix) < 2:
                continue
            for item in alias_index:
                if not isinstance(item, dict) or _compact(str(item.get("alias") or "")) != prefix:
                    continue
                for match in item.get("matches") or []:
                    if not isinstance(match, dict):
                        continue
                    try:
                        if int(match.get("dataset_id") or 0) != target_dataset_id:
                            continue
                    except (TypeError, ValueError):
                        continue
                    parent_name = _text(match.get("node_name"))
                    if parent_name:
                        return {"level": level, "parent_name": parent_name}
        return None

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
        catalog_dataset_ids = set(catalog_by_id)
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
            dataset_ids = [
                item for item in self._dataset_ids_for_node(node, permissions)
                if item in catalog_dataset_ids
            ]
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

        node_index = self._load_dataset_node_index()
        for dataset in (node_index.get("datasets") or []):
            if not isinstance(dataset, dict):
                continue
            try:
                dataset_id = int(dataset.get("dataset_id") or 0)
            except Exception:
                continue
            if dataset_id <= 0 or dataset_id not in catalog_dataset_ids:
                continue
            if allowed is not None and dataset_id not in allowed:
                continue
            permission_rule = (permissions.get("rules") or {}).get(str(dataset_id)) or {}
            if _text(permission_rule.get("mode")) == "org_tree":
                continue
            for node in dataset.get("nodes") or []:
                if not isinstance(node, dict):
                    continue
                node_name = _text(node.get("node_name"))
                if len(node_name) < 2:
                    continue
                aliases = [
                    _compact(alias)
                    for alias in ([node_name] + list(node.get("aliases") or []))
                    if _text(alias)
                ]
                matched_aliases = [
                    alias
                    for alias in _unique(aliases)
                    if _alias_matches_question(alias, node_name, normalized_question)
                ]
                if not matched_aliases:
                    continue
                parent_name = _text(node.get("parent_name"))
                path_label = " / ".join([item for item in [parent_name, node_name] if item]) or node_name
                mentions.append(
                    {
                        "node_id": f"dataset_node_index:{dataset_id}:{node_name}",
                        "node_name": node_name,
                        "matched_alias": max(matched_aliases, key=len),
                        "level": 0,
                        "tree_type_id": "",
                        "path_names": [item for item in [parent_name, node_name] if item],
                        "path_label": path_label,
                        "dataset_ids": [dataset_id],
                        "dataset_names": [_dataset_name(dataset_id, catalog_by_id)],
                    }
                )

        mentions.sort(key=lambda item: (len(item.get("matched_alias") or ""), item.get("level") or 0), reverse=True)
        deduped: List[Dict[str, Any]] = []
        covered_aliases = set()
        for item in mentions:
            key = item["node_id"]
            if any(existing["node_id"] == key for existing in deduped):
                continue
            same_dataset_and_name = any(
                existing.get("node_name") == item.get("node_name")
                and _unique(existing.get("dataset_ids") or []) == _unique(item.get("dataset_ids") or [])
                for existing in deduped
            )
            if same_dataset_and_name:
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

        # 数据集域前缀收窄（2026-09-03 用服接入实测）：根节点（事业部级）别名与其他
        # 数据集的节点同时命中、且根别名只属于一个数据集时，根别名表达的是"选数据集"
        # 而不是"选节点"（"用服粤桂琼"=用服事业部的粤桂琼分公司）。把 mentions 收窄到
        # 该数据集并优先保留非根节点，避免"用服粤桂琼分公司的业绩"被弹成跨数据集确认卡。
        # 单数据集场景不动（"商用事业部和东部分公司对比"的根节点仍是有效成员）。
        root_mentions = [m for m in mentions if _compact(m.get("node_name")).endswith("事业部")]
        root_dataset_ids = _unique([ds for m in root_mentions for ds in (m.get("dataset_ids") or [])])
        if len(dataset_ids) > 1 and len(root_dataset_ids) == 1:
            scope_id = root_dataset_ids[0]
            narrowed = [m for m in mentions if scope_id in (m.get("dataset_ids") or [])]
            finer = [m for m in narrowed if not _compact(m.get("node_name")).endswith("事业部")]
            mentions = finer or narrowed
            distinct_node_names = _unique([item["node_name"] for item in mentions])
            dataset_ids = _unique([ds for item in mentions for ds in (item.get("dataset_ids") or [])])

        candidate_dataset_ids = dataset_ids[:]
        # 消歧后缀（2026-09-06 文案修订）：面向用户可读的"我理解为您指的是…"，
        # 替代旧"组织树标准名称：X。请优先按这些组织节点所属数据集和组织范围执行。"
        # ——旧文案是系统指令口吻，被 Agent4 复述展示给用户时看不懂（用户实测反馈）。
        refined_suffix = f"（我理解为您指的是：{'、'.join(distinct_node_names)}，请按其所属数据集口径执行。）"
        refined_query = f"{question}{refined_suffix}".strip()

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

        # 修复：多个组织节点且问题是对比意图时，自动识别为跨数据集对比，不再弹确认。
        if len(dataset_ids) > 1 and _is_compare_question(question):
            return {
                "dataset_ids": dataset_ids,
                "intent": "comparison",
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
                "resolved_members": distinct_node_names,
                "scope_mode": "cross",
                "split_queries": [{"dataset_id": ds_id, "sub_query": refined_query} for ds_id in dataset_ids],
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

    def domain_prefix_scope_id(
        self,
        question: str,
        rewritten_question: str,
        catalog: List[Dict[str, Any]],
    ) -> Optional[int]:
        """主体纠正改写丢失数据集域前缀时，返回应锁定的数据集 id；否则返回 None。

        用服接入实测（2026-09-03）：LLM 主体纠正会把"用服粤桂琼"的域前缀"用服"
        当口语剥掉（改写为"粤桂琼分公司的业绩"），路由只剩跨数据集同名节点，
        在消费者/用服之间误弹确认卡。以下条件全部满足时，调用方应放弃改写、
        保留原始问题进入路由（resolve 的域前缀收窄会锁定该数据集）：
        1. 原始问题命中"唯一根节点域别名 + 跨数据集节点"（同 resolve 收窄条件）；
        2. 改写后该条件不再成立（前缀被剥掉）；
        3. 改写保留的主体仍是真实组织节点——防止"商用事业部丁杰"→"丁杰"这类
           人名主体纠正被误拦（人名不在节点索引时条件 3 不成立，改写照常生效）。
        """
        def _scope_id(text: str) -> Optional[int]:
            mentions = self._find_mentions(text, catalog, None)
            if not mentions:
                return None
            dataset_ids = _unique([ds for m in mentions for ds in (m.get("dataset_ids") or [])])
            root_dataset_ids = _unique([
                ds
                for m in mentions
                if _compact(m.get("node_name")).endswith("事业部")
                for ds in (m.get("dataset_ids") or [])
            ])
            if len(dataset_ids) > 1 and len(root_dataset_ids) == 1:
                return int(root_dataset_ids[0])
            return None

        scope_id = _scope_id(question)
        if scope_id is None or _scope_id(rewritten_question) is not None:
            return None
        if not self._find_mentions(rewritten_question, catalog, None):
            return None
        return scope_id
