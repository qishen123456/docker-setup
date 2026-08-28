# -*- coding: utf-8 -*-
"""0 行诊断器（输入理解层 P0.5 / 设计文档 §5）。

触发：流水线全部数据集返回 0 行。三分支（判定顺序即优先级，纯代码不调 LLM）：
  B 路由错数据集：主体在书架、但不属于本次使用的数据集 → 卡片给"切换数据集重查"候选；
  C 真没数据：主体在书架且数据集正确（或泛问无主体）→ 不弹卡，把垃圾分析报告
    换成诚实文案（不编痛点、不编建议）；
  A 对象不存在：书架查无此对象 → 拼音索引召回 1~3 个近邻，卡片给"你可能想问"候选。

安全约束：
  1. 独立开关 zero_row_diagnosis_enabled（gatekeeper_settings.json），fail-open；
  2. 拼音召回按 allowed_dataset_ids 过滤（权限红线）；
  3. A/B 卡片结果带 early_clarify=True，调用方负责跳过短期记忆写入（防污染追问上下文）；
  4. 任何异常 → None（不干预），0 行行为回退为旧版兜底报告。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from disambiguation.typo_fastpath import _load_alias_entries, _NODE_INDEX_PATH

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(CURRENT_DIR, "..", "..", "config")
_SETTINGS_PATH = os.path.join(CONFIG_DIR, "gatekeeper_settings.json")


def is_enabled() -> bool:
    try:
        with open(_SETTINGS_PATH, "r", encoding="utf-8") as fh:
            return bool(json.load(fh).get("zero_row_diagnosis_enabled", True))
    except Exception:
        return True  # fail-open：读不到配置保持开放（本层失败只会回退旧行为）


def _dataset_names() -> Dict[int, str]:
    """dataset_id → dataset_name（书架节点索引）。"""
    try:
        with open(_NODE_INDEX_PATH, "r", encoding="utf-8") as fh:
            index = json.load(fh)
        return {
            int(ds["dataset_id"]): str(ds.get("dataset_name") or "")
            for ds in index.get("datasets") or []
            if ds.get("dataset_id") is not None
        }
    except Exception:
        return {}


def _allowed_ids_for_user(current_user: Optional[Dict[str, Any]]) -> Optional[List[int]]:
    """按用户算权限数据集集合；算不出/超管 → None（不过滤）。"""
    if not current_user:
        return None
    try:
        from data_permission_store import allowed_dataset_ids_for_user
        ids = allowed_dataset_ids_for_user(current_user)
        return [int(i) for i in ids] if ids else None
    except Exception:
        return None


def _collect_subjects(route: Dict[str, Any], dataset_results: List[Dict[str, Any]]) -> List[str]:
    """收集流水线已解析的主体名（route 优先，其次各数据集的 query_intent）。"""
    subjects: List[str] = []
    for s in [str(route.get("resolved_subject_name") or "").strip()]:
        if s and s not in subjects:
            subjects.append(s)
    for dr in dataset_results:
        qi = dr.get("query_intent") or {}
        s = str(qi.get("subject_name") or "").strip()
        if s and s not in subjects:
            subjects.append(s)
    return subjects


def _find_alias_owners(subject: str, allowed: Optional[set]) -> List[Dict[str, Any]]:
    """书架别名精确匹配（按权限过滤），返回归属条目列表。"""
    owners = []
    for e in _load_alias_entries():
        if e["alias"] == subject or e["node_name"] == subject:
            ds_id = int(e.get("dataset_id") or 0)
            if allowed and ds_id not in allowed:
                continue
            owners.append(e)
    return owners


def diagnose(
    question: str,
    route: Dict[str, Any],
    dataset_results: List[Dict[str, Any]],
    current_user: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """三分支判定。返回 None=不干预；否则 {branch, subject, candidates, reason, honest_analysis}。"""
    try:
        question = str(question or "").strip()
        if not question:
            return None
        allowed_list = _allowed_ids_for_user(current_user)
        allowed = set(allowed_list) if allowed_list else None
        used_ids = {
            int(d.get("dataset_id") or 0)
            for d in (dataset_results or [])
            if d.get("dataset_id") is not None
        }
        ds_names = _dataset_names()

        # 1. 主体已解析 → 判 B（路由错数据集）或 C（真没数据）
        for subject in _collect_subjects(route or {}, dataset_results or []):
            owners = _find_alias_owners(subject, allowed)
            if not owners:
                continue  # 主体不在书架（可能本身写错）→ 落到拼音召回
            owner_ids = {int(o.get("dataset_id") or 0) for o in owners}
            hit_used = owner_ids & used_ids
            if not hit_used:
                # 分支 B：对象在书架但不在本次用的数据集里
                target_id = sorted(owner_ids)[0]
                target_name = ds_names.get(target_id, f"数据集{target_id}")
                return {
                    "branch": "B",
                    "subject": subject,
                    "target_dataset_id": target_id,
                    "reason": f"「{subject}」在《{target_name}》数据集中，本次查询用的数据集里没有它",
                    "candidates": [f"用{target_name}数据集查{question}"],
                    "honest_analysis": "",
                }
            # 分支 C：主体对、数据集对 → 真没数据，诚实文案
            used_name = ds_names.get(sorted(hit_used)[0], "当前数据集")
            return {
                "branch": "C",
                "subject": subject,
                "candidates": [],
                "reason": "",
                "honest_analysis": (
                    f"「{subject}」在《{used_name}》当前口径下没有查到数据。\n\n"
                    "可能原因：时间范围、筛选条件或你的数据权限范围内确实没有记录。"
                    "可以放宽条件（如去掉时间限制）后再试。"
                ),
            }

        # 2. 主体未解析或不在书架 → 拼音索引召回近邻（分支 A）
        from disambiguation.pinyin_index import recall_in_question
        evidence = recall_in_question(question, allowed_list, top_n=3)
        candidates: List[str] = []
        for ev in evidence:
            frag = ev.get("fragment") or ""
            for cand in (ev.get("candidates") or []):
                text = str(cand.get("text") or "").strip()
                if not text or text == frag:
                    continue
                rewritten = question.replace(frag, text, 1)
                if rewritten and rewritten != question and rewritten not in candidates:
                    candidates.append(rewritten)
            if len(candidates) >= 3:
                break
        if candidates:
            frags = "、".join(f"「{ev.get('fragment')}」" for ev in evidence[:2])
            return {
                "branch": "A",
                "subject": "",
                "candidates": candidates[:3],
                "reason": f"书架中没有找到{frags}对应的对象，你可能想问的是：",
                "honest_analysis": "",
            }

        # 3. 通用 C：无主体、无近邻 → 诚实通用文案
        return {
            "branch": "C",
            "subject": "",
            "candidates": [],
            "reason": "",
            "honest_analysis": (
                f"围绕「{question[:50]}」没有查到匹配数据。\n\n"
                "可以检查：对象名称是否与业务口径一致、时间范围是否过窄、"
                "或换一个数据集重试。"
            ),
        }
    except Exception:
        return None  # fail-open


def build_clarify_result(
    question: str,
    diagnosis: Dict[str, Any],
    route: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """分支 A/B 的 early_clarify 卡片结果（结构与 typo_fastpath.build_early_clarify_result 一致，
    前端零改动）。"""
    return {
        "question": question,
        "rows": [],
        "row_count": 0,
        "columns": [],
        "steps": [],
        "analysis": "",
        "route": {
            "dataset_ids": [],
            "requires_confirmation": False,
            "decision": "early_clarify",
        },
        "clarify_suggestion": {
            "action": "suggest",
            "interpretation": question,
            "reason": str(diagnosis.get("reason") or ""),
            "candidates": list(diagnosis.get("candidates") or []),
            "confidence": 0.9,
            "source": f"zero_row_diagnosis_{str(diagnosis.get('branch') or '?').lower()}",
        },
        "early_clarify": True,
        "conversation_session_id": str((route or {}).get("conversation_session_id") or ""),
        "zero_row_branch": str(diagnosis.get("branch") or ""),
    }
