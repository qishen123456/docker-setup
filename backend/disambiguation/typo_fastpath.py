# -*- coding: utf-8 -*-
"""明显错字快检（Typo Fast-path / 澄清方案第 0 层）。

纯代码、毫秒级、不调 LLM。只拦"铁证级"错字：
  - 带组织后缀的片段（…分公司/事业部/代表处/业务部/城市公司）不在别名表，
    但与某个别名编辑距离 ≤1 且候选唯一；
  - 人名（业务代表/承接人级别节点）：同长度子串编辑距离恰好为 1 且候选唯一。

命中 → controller 短路返回纠正卡（不进问数流水线）；
未命中/拿不准 → 一律放行，绝不影响正常问数（fail-open）。

安全约束（对应方案评审结论）：
  1. 别名表按 allowed_dataset_ids 过滤——不泄漏无权限数据集的组织名；
  2. 泛层级词（"分公司""代表处"等单独出现）不参与匹配；
  3. 候选非唯一不拦；
  4. 别名最短 3 字——2 字串错 1 字=50% 差异，实测误拦"京东的业绩"→"京津"，
     2 字人名纠错主动放弃，交由守门员纠正条兜底（2026-08-28 评审后收紧）；
  5. 不做同音匹配（无 pypinyin 依赖，靠编辑距离+首字锚定+边界规则控制精度）。
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(CURRENT_DIR, "..", "..", "config")
_NODE_INDEX_PATH = os.path.join(CONFIG_DIR, "dataset_node_index.json")

# 泛层级词单独出现时不参与错字匹配（"各分公司的排名"里的"分公司"不是实体）
GENERIC_LEVEL_WORDS = {
    "分公司", "事业部", "代表处", "业务部", "城市分公司", "城市公司",
    "业务代表", "业务员", "承接人", "业务承接人",
}

ORG_SUFFIXES = ("城市分公司", "城市公司", "分公司", "事业部", "代表处", "业务部", "业务代表")
# 组织片段：后缀 + 前面 2~6 个汉字
_ORG_FRAGMENT_RE = re.compile(
    r"[一-龥]{2,6}?(?:城市分公司|城市公司|分公司|事业部|代表处|业务部|业务代表)"
)

_PERSON_LEVELS = {"业务代表", "承接人", "业务承接人", "业务员", "员工", "个人"}

# 片段开头的连接词/虚词要剥掉（"东部分公事和南部分公司" 会切出 "和南部分公司"）
_LEADING_STOPWORDS = "和与跟及或还就的了在看查询问下各把被让给从向对"
# 滑窗边界：窗口前必须是 非汉字/句首/引导动词虚词；窗口后必须是 非汉字/常见后续词
# （防"前三的"里的"三的"误中"三明"、"完成率"里的"成率"误中"成都"）
_LEAD_OK = set(_LEADING_STOPWORDS) | set("知道到想说位名")
_FOLLOW_OK = set("的业绩完成达成开单排名情况怎么样多少咋样了呢吧和与跟")

_cache_lock = threading.Lock()
_alias_cache: Dict[str, Any] = {"mtime": 0.0, "entries": []}


def _load_alias_entries() -> List[Dict[str, Any]]:
    """加载全部别名（带数据集/层级），按文件 mtime 缓存。"""
    try:
        mtime = os.path.getmtime(_NODE_INDEX_PATH)
        with _cache_lock:
            if _alias_cache["mtime"] == mtime and _alias_cache["entries"]:
                return _alias_cache["entries"]
            with open(_NODE_INDEX_PATH, "r", encoding="utf-8") as fh:
                index = json.load(fh)
            entries: List[Dict[str, Any]] = []
            for ds in index.get("datasets") or []:
                ds_id = ds.get("dataset_id")
                for node in ds.get("nodes") or []:
                    for alias in node.get("aliases") or []:
                        alias = str(alias).strip()
                        if not alias or alias in GENERIC_LEVEL_WORDS:
                            continue
                        entries.append({
                            "alias": alias,
                            "node_name": str(node.get("node_name") or alias),
                            "level": str(node.get("node_level") or ""),
                            "dataset_id": ds_id,
                        })
            _alias_cache["mtime"] = mtime
            _alias_cache["entries"] = entries
            return entries
    except Exception:
        return _alias_cache.get("entries") or []


def _lev_le1(a: str, b: str) -> bool:
    """编辑距离 ≤1 判定（等长替换 1 字，或增删 1 字）。"""
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if a == b:
        return False  # 精确命中不算错字
    if la == lb:
        diff = sum(1 for x, y in zip(a, b) if x != y)
        return diff == 1
    # 长度差 1：长串删 1 字后能等于短串
    if la > lb:
        a, b = b, a
        la, lb = lb, la
    i = j = 0
    skipped = False
    while i < la and j < lb:
        if a[i] == b[j]:
            i += 1
            j += 1
        elif not skipped:
            skipped = True
            j += 1
        else:
            return False
    return True


def _unique_node(cands: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    nodes = {c["node_name"] for c in cands}
    if len(nodes) != 1:
        return None
    return cands[0]


def detect_obvious_typo(
    question: str,
    allowed_dataset_ids: Optional[List[int]] = None,
) -> Optional[Dict[str, Any]]:
    """检测明显错字。命中返回 {fragment, suggestion, node_name, corrected_question}，否则 None。

    别名驱动滑窗匹配（覆盖后缀本身打错的场景，如"东部分公事""京东直赢"）：
    对每个别名（长的优先），在问题里滑等长窗（替换 1 字）和 ±1 窗（增删 1 字），
    要求首字相同、窗内全汉字、候选节点唯一。
    """
    try:
        question = str(question or "").strip()
        if not question:
            return None
        allowed = set(int(d) for d in (allowed_dataset_ids or []) if d)
        entries = [
            e for e in _load_alias_entries()
            if not allowed or int(e.get("dataset_id") or 0) in allowed
        ]
        if not entries:
            return None
        alias_set = {e["alias"] for e in entries}
        qlen = len(question)

        hits: List[Dict[str, Any]] = []
        # 长别名优先：3 字人名先于 2 字命中，避免"刘志威"被 2 字别名误切
        for e in sorted(entries, key=lambda x: len(x["alias"]), reverse=True):
            alias = e["alias"]
            # 2 字别名不参与快检：错 1 字=50% 差异，实测会误拦"京东的业绩"→"京津"这类正常问法
            # （2 字人名纠错如"丁洁→丁杰"主动放弃，交由后续守门员纠正条兜底，换取零误拦）
            if len(alias) < 3:
                continue
            if alias in question:
                continue
            alen = len(alias)
            for wlen in (alen, alen - 1, alen + 1):
                if wlen < 2 or wlen > qlen:
                    continue
                for start in range(0, qlen - wlen + 1):
                    window = question[start:start + wlen]
                    if not re.fullmatch(r"[一-龥]+", window):
                        continue
                    if window in alias_set:
                        continue
                    # 首字锚定：真实错字极少错在首字，且能挡住"金额超过"→"周超"这类误配
                    if window[0] != alias[0]:
                        continue
                    # 边界约束：前邻必须是句首/非汉字/引导虚词，后邻必须是句尾/非汉字/常见后续词
                    if start > 0:
                        prev = question[start - 1]
                        if re.match(r"[一-龥]", prev) and prev not in _LEAD_OK:
                            continue
                    end = start + wlen
                    if end < qlen:
                        nxt = question[end]
                        if re.match(r"[一-龥]", nxt) and nxt not in _FOLLOW_OK:
                            continue
                    if not _lev_le1(window, alias):
                        continue
                    hits.append({"window": window, "entry": e})

        if not hits:
            return None
        # 只取最长别名的命中；同长候选必须指向唯一节点
        max_len = max(len(h["entry"]["alias"]) for h in hits)
        best = [h for h in hits if len(h["entry"]["alias"]) == max_len]
        windows = {h["window"] for h in best}
        nodes = {h["entry"]["node_name"] for h in best}
        if len(nodes) != 1 or len(windows) != 1:
            return None
        hit = best[0]
        fragment = hit["window"]
        alias = hit["entry"]["alias"]
        return {
            "fragment": fragment,
            "suggestion": alias,
            "node_name": hit["entry"]["node_name"],
            "dataset_id": hit["entry"].get("dataset_id"),
            "corrected_question": question.replace(fragment, alias, 1),
            "match_kind": "alias_window",
        }
    except Exception:
        return None  # fail-open：任何异常都放行原问题


def build_early_clarify_result(
    question: str,
    hit: Dict[str, Any],
    session_id: str = "",
) -> Dict[str, Any]:
    """构造错字短路的极简结果：只带纠正卡数据，rows/analysis/steps 全空。

    前端据 early_clarify=True 渲染醒目纠正卡（候选 chip + 按原问题继续查），
    不渲染 PlanCard/报告等无用卡片。clarify_suggestion 结构与守门员 build_correction 一致。
    """
    fragment = str(hit.get("fragment") or "")
    suggestion = str(hit.get("suggestion") or "")
    corrected = str(hit.get("corrected_question") or "")
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
            "reason": f"「{fragment}」疑似「{suggestion}」的错字",
            "candidates": [corrected] if corrected else [],
            "confidence": 1.0,
            "source": "typo_fastpath",
        },
        "early_clarify": True,
        "session_id": session_id or "",
    }


def log_fastpath(
    question: str,
    hit: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    session_id: str = "",
) -> None:
    """写一条影子日志（gk_source=typo_fastpath），用于离线统计拦/放量。fail-open。"""
    try:
        from disambiguation.shadow_gatekeeper import _append_log, _load_settings

        settings = _load_settings()
        if not settings.get("enabled"):
            return
        log_path = str(
            settings.get("log_path")
            or os.path.join(CONFIG_DIR, "shadow_gatekeeper_log.jsonl")
        )
        record = {
            "question": question,
            "session_id": session_id or "",
            "user_id": str((user or {}).get("username") or (user or {}).get("id") or ""),
            "timestamp": int(time.time()),
            "dataset_id": hit.get("dataset_id"),
            "prompt_version": "typo_fastpath_v1",
            "sql_status": "short_circuit",
            "rows_returned": 0,
            "gk_source": "typo_fastpath",
            "gk_status": "ok",
            "gk_action": "suggest",
            "gk_latency_ms": 0,
            "would_block": True,
            "block_reason": f"「{hit.get('fragment')}」疑似「{hit.get('suggestion')}」的错字",
            "self_confidence": 1.0,
            "candidate_options_topN": [str(hit.get("corrected_question") or "")[:120]],
        }
        _append_log(record, log_path)
    except Exception:
        pass
