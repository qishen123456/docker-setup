# -*- coding: utf-8 -*-
"""统一确认卡候选生成器（对象 → 各数据集精确节点 → 节点级完整问句）。

设计文档：docs/unified-confirm-card-design.md
核心：把"选数据集"升级为"选节点级完整问句"——对象在多数据集/多节点歧义时，
从 flat_alias_index 查出精确节点（含 node_level），拼"数据集·节点·类型"完整问句，
用户一次确认 = 对象+数据集+节点类型一次锁定，不再弹第二张卡。

约束（AGENTS.md）：
- 独立模块，不在 four_agent_ask.py 增类
- 权限红线：候选按 allowed_dataset_ids 过滤（同 typo_fastpath.py:137-141）
- fail-open：任何异常返回空列表，绝不阻断主流程
"""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, List, Optional

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(CURRENT_DIR, "..", "..", "config")
_NODE_INDEX_PATH = os.path.join(CONFIG_DIR, "dataset_node_index.json")

_cache_lock = threading.Lock()
_index_cache: Dict[str, Any] = {"mtime": 0.0, "by_alias": {}}

# 数据集名里的指标后缀（用于提取业务名，如"消费者事业部开单金额"→"消费者事业部"）
_METRIC_SUFFIXES = ("开单金额", "达成率", "任务目标", "回款", "业绩")


def _load_by_alias() -> Dict[str, List[Dict[str, Any]]]:
    """加载 flat_alias_index 并按 alias 建索引（带 mtime 缓存）。"""
    try:
        mtime = os.path.getmtime(_NODE_INDEX_PATH)
        with _cache_lock:
            if _index_cache["mtime"] == mtime and _index_cache["by_alias"]:
                return _index_cache["by_alias"]
            with open(_NODE_INDEX_PATH, "r", encoding="utf-8") as fh:
                index = json.load(fh)
            by_alias: Dict[str, List[Dict[str, Any]]] = {}
            for item in index.get("flat_alias_index") or []:
                alias = str(item.get("alias") or "").strip()
                if not alias:
                    continue
                matches = item.get("matches") or []
                if matches:
                    by_alias[alias] = matches
            _index_cache["mtime"] = mtime
            _index_cache["by_alias"] = by_alias
            return by_alias
    except Exception:
        return _index_cache.get("by_alias") or {}


def _business_name(dataset_name: str) -> str:
    """从数据集名提取业务名（去指标后缀）：'消费者事业部开单金额'→'消费者事业部'。"""
    name = str(dataset_name or "").strip()
    for suf in _METRIC_SUFFIXES:
        if name.endswith(suf):
            return name[: -len(suf)]
    return name


def format_full_question(dataset_name: str, node_name: str, metric_hint: str = "业绩") -> str:
    """拼节点级完整问句：'消费者事业部 · 上海城市公司的业绩'。"""
    biz = _business_name(dataset_name)
    node = str(node_name or "").strip()
    if not node:
        return ""
    return f"{biz} · {node}的{metric_hint}" if biz else f"{node}的{metric_hint}"


# ---- 默认推荐（2026-08-31 用户确认交互定稿）----
_SETTINGS_PATH = os.path.join(CONFIG_DIR, "unified_confirm_settings.json")
_settings_cache: Dict[str, Any] = {"mtime": 0.0, "data": {}}
_DEFAULT_DATASET_PRIORITY = [2, 3, 62]  # 消费者 > 商用 > 电商


def _load_recommend_settings() -> Dict[str, Any]:
    """读推荐规则配置（带 mtime 缓存 + 默认值，fail-open）。"""
    try:
        mtime = os.path.getmtime(_SETTINGS_PATH)
        with _cache_lock:
            if _settings_cache["mtime"] == mtime and _settings_cache["data"]:
                return _settings_cache["data"]
            with open(_SETTINGS_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                data = {}
            _settings_cache["mtime"] = mtime
            _settings_cache["data"] = data
            return data
    except Exception:
        return _settings_cache.get("data") or {}


def apply_recommendation(options: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """候选按推荐规则排序，并在"有明确倾向"时给第 1 个标 recommended:true。

    规则：
    - 排序：按 dataset_priority（可配置，默认 消费者>商用>电商），不在列表的排最后。
    - recommended 角标：仅当第 1 个与第 2 个【数据集不同】（系统有明确倾向）时标；
      同数据集撞车（如 nb→南部/北部、sh→上海城市/深圳城市同在消费者）不硬标——
      避免系统对真歧义"假装有倾向"。此时 recommend_on_tie=true 才强制标。
    - 无论是否 recommended，排序后第 1 个都是"默认选中"项（解析条默认显示它）。
    fail-open：任何异常按原顺序返回。
    """
    if not options:
        return options
    try:
        settings = _load_recommend_settings()
        priority = settings.get("dataset_priority") or _DEFAULT_DATASET_PRIORITY
        recommend_on_tie = bool(settings.get("recommend_on_tie", False))

        def _rank(opt: Dict[str, Any]) -> int:
            ids = opt.get("dataset_ids") or []
            did = int(ids[0]) if ids else 0
            try:
                return priority.index(did)
            except ValueError:
                return len(priority)

        opts = sorted(options, key=_rank)
        for o in opts:
            o.pop("recommended", None)

        def _did(opt: Dict[str, Any]) -> int:
            ids = opt.get("dataset_ids") or []
            return int(ids[0]) if ids else 0

        if len(opts) == 1:
            opts[0]["recommended"] = True
        elif _did(opts[0]) != _did(opts[1]):
            opts[0]["recommended"] = True  # 数据集优先级有明确倾向
        elif recommend_on_tie:
            opts[0]["recommended"] = True  # 撞车但配置允许硬标
        return opts
    except Exception:
        return options


def lookup_object_nodes(obj_alias: str) -> List[Dict[str, Any]]:
    """查对象别名在书架里的所有精确节点（各数据集）。"""
    obj_alias = str(obj_alias or "").strip()
    if not obj_alias:
        return []
    by_alias = _load_by_alias()
    return by_alias.get(obj_alias) or []


def build_unified_candidates(
    obj_aliases: List[str],
    metric_hint: str = "业绩",
    allowed_dataset_ids: Optional[List[int]] = None,
    top_n: int = 6,
) -> List[Dict[str, Any]]:
    """对象别名列表 → 各数据集精确节点 → 节点级完整问句候选。

    obj_aliases: 对象别名列表（如 ["上海"]，或拼音首字母展开后的 ["南部", "北部"]）。
    返回候选：{dataset_id, dataset_name, business_name, node_name, node_level,
              track, parent_name, full_question, option_label}。
    权限红线：按 allowed_dataset_ids 过滤。fail-open：异常返回 []。
    """
    try:
        if not obj_aliases:
            return []
        allowed = set(int(d) for d in (allowed_dataset_ids or []) if d)
        seen = set()
        candidates: List[Dict[str, Any]] = []
        for alias in obj_aliases:
            for m in lookup_object_nodes(alias):
                ds_id = m.get("dataset_id")
                if allowed and int(ds_id or 0) not in allowed:
                    continue
                node_name = str(m.get("node_name") or "").strip()
                if not node_name:
                    continue
                dedup_key = (int(ds_id or 0), node_name)
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                ds_name = str(m.get("dataset_name") or "").strip()
                biz = _business_name(ds_name)
                node_level = str(m.get("node_level") or "").strip()
                # 完整问句：数据集业务名 · 节点全名 的 指标
                full_q = f"{biz} · {node_name}的{metric_hint}" if biz else f"{node_name}的{metric_hint}"
                candidates.append({
                    "dataset_id": ds_id,
                    "dataset_name": ds_name,
                    "business_name": biz,
                    "node_name": node_name,
                    "node_level": node_level,
                    "track": str(m.get("track") or "").strip(),
                    "parent_name": str(m.get("parent_name") or "").strip(),
                    "full_question": full_q,
                    "option_label": full_q,
                })
        return candidates[:top_n]
    except Exception:
        return []


def is_multi_node_ambiguous(candidates: List[Dict[str, Any]]) -> bool:
    """候选是否构成"多节点/多数据集歧义"（>1 个不同节点或跨数据集）。"""
    if len(candidates) <= 1:
        return False
    nodes = {c.get("node_name") for c in candidates}
    datasets = {c.get("dataset_id") for c in candidates}
    return len(nodes) > 1 or len(datasets) > 1


def extract_object_aliases(question: str, max_aliases: int = 3) -> List[str]:
    """从问题提取对象别名（flat_alias_index 的 alias 在问题里出现，最长匹配优先）。

    最长匹配优先避免短 alias 先吞（"上海城市公司"优先于"上海"）。
    单字 alias 不匹配（避免误匹配）。fail-open：异常返回 []。
    """
    try:
        question = str(question or "").strip()
        if not question:
            return []
        by_alias = _load_by_alias()
        found: List[str] = []
        for alias in sorted(by_alias.keys(), key=len, reverse=True):
            if len(alias) < 2:
                continue
            if alias in question and alias not in found:
                found.append(alias)
                if len(found) >= max_aliases:
                    break
        return found
    except Exception:
        return []


def build_unified_confirm_route(
    question: str,
    allowed_dataset_ids: Optional[List[int]],
    build_option_fn,
    metric_hint: str = "业绩",
) -> Optional[Dict[str, Any]]:
    """对象多节点歧义 → 统一确认卡路由（节点级完整问句候选），否则 None。

    在数据集确认逻辑之前调用：对象在多个数据集/多节点类型歧义时，
    返回"你是不是想问：节点级完整问句候选"的确认卡，替换"选数据集"卡。
    build_option_fn: four_agent_ask._build_confirmation_option（构造选项）。
    fail-open：任何异常/不构成歧义返回 None（走原数据集确认逻辑）。
    """
    try:
        obj_aliases = extract_object_aliases(question)
        if not obj_aliases:
            return None
        cands = build_unified_candidates(obj_aliases, metric_hint, allowed_dataset_ids)
        if not is_multi_node_ambiguous(cands):
            return None
        options = []
        for c in cands:
            options.append(
                build_option_fn(
                    option_id=f"unified_node_{c['dataset_id']}_{c['node_name']}",
                    label=c["full_question"],
                    description=f"按 {c['business_name']} · {c['node_name']}（{c['node_level']}）口径继续。",
                    dataset_ids=[c["dataset_id"]],
                    option_type="unified_node_confirm",
                    extra={
                        "confirmation_type": "unified_node_confirm",
                        "resolved_subject_name": c["node_name"],
                        "resolved_subject_level": c["node_level"],
                        "resolved_dataset_name": c["dataset_name"],
                        "full_question": c["full_question"],
                        "track": c["track"],
                    },
                )
            )
        ds_ids = list(dict.fromkeys(c["dataset_id"] for c in cands))
        return {
            "dataset_ids": ds_ids,
            "intent": "confirm",
            "refined_query": question,
            "requires_confirmation": True,
            "decision": "wait_boss_confirm",
            "match_score": 100,
            "confirmation_role": "boss",
            "confirmation_type": "unified_node_confirm",
            "confirmation_question": "你是不是想问：",
            "confirmation_options": options,
            "candidate_dataset_ids": ds_ids,
            "arbiter_reason": "unified_node_confirm",
        }
    except Exception:
        return None
