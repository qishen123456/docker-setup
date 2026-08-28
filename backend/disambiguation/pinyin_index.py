# -*- coding: utf-8 -*-
"""拼音索引（输入理解层 P0 地基 / 设计文档 §3）。

职责：只做"证据召回"，不做决策——从书架捞出与片段字形/读音最接近的节点，
作为 LLM 主判的锚定证据（§4 anchor_evidence）和 0 行诊断的候选召回（§5）。

边界规则（设计文档 §3.4，2026-08-28 实测后修订）：
  1. 2 字条目走硬门不走打分：片段与条目的**无调全拼完全相等**才召回
     （只做同音维度，不做字形近似——与 typo_fastpath"2 字放弃字形纠错"互补不重叠，
     京东 jingdong ≠ 京津 jingjin，硬门天然不误拦）。
     注：初版要求"含调全拼相等"，实测 pypinyin 返回声调符号（liú 非 liu2），
     且语音转文字常丢声调（订杰 dìngjié→丁杰 dīngjié 是真实失误形态），
     故放宽为无调全拼相等；候选集是封闭书架（346 别名），最终决策权在 LLM 主判层；
  2. ≥3 字条目走打分：无调拼音音节差异 + 字形编辑距离，综合分=min(两者)，
     且要求首音节（无调）相同（锚定，宁可漏不可滥）；
  3. 权限红线：召回按 allowed_dataset_ids 过滤（同 typo_fastpath.py:137-141）；
  4. 热更新：按 dataset_node_index.json mtime 缓存，文件变更即重建；
  5. fail-open：pypinyin 不可用 / 任何异常 → 召回返回空，绝不阻断主流程。
"""
from __future__ import annotations

import os
import threading
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

try:
    from pypinyin import Style, pinyin
    _PYPINYIN_OK = True
except Exception:  # pragma: no cover - 依赖缺失时整模块静默失效
    _PYPINYIN_OK = False

from disambiguation.typo_fastpath import _load_alias_entries

# ≥3 字条目的打分阈值：短词严、长词宽
_DIST_THRESHOLD = {3: 1, 4: 1, 5: 2, 6: 2}

_cache_lock = threading.Lock()
_index_cache: Dict[str, Any] = {"mtime": 0.0, "entries": []}


def _plain_syllable(s: str) -> str:
    """音节去声调：pypinyin TONE 风格返回声调符号（liú/wēi），
    NFD 分解后去掉组合记号（Mn），同时兼容数字调（liu2）。"""
    decomposed = unicodedata.normalize("NFD", s)
    return "".join(
        ch for ch in decomposed
        if unicodedata.category(ch) != "Mn" and not ch.isdigit()
    )


def _readings(text: str) -> List[Tuple[str, ...]]:
    """含调全拼的全部读音组合（多音字取笛卡尔积，截断防爆）。"""
    try:
        lists = pinyin(text, style=Style.TONE, heteronym=True)
        combos: List[Tuple[str, ...]] = [tuple()]
        for syllables in lists:
            combos = [c + (s,) for c in combos for s in syllables][:8]
        return combos
    except Exception:
        return []


def _plain(tone_syllables: Tuple[str, ...]) -> Tuple[str, ...]:
    return tuple(_plain_syllable(s) for s in tone_syllables)


def _build_entries() -> List[Dict[str, Any]]:
    """从别名表建索引条目（复用 typo_fastpath 的加载与过滤口径）。"""
    entries: List[Dict[str, Any]] = []
    for e in _load_alias_entries():
        alias = e["alias"]
        readings = _readings(alias)
        if not readings:
            continue
        entries.append({
            "text": alias,
            "node_name": e["node_name"],
            "level": e.get("level") or "",
            "dataset_id": e.get("dataset_id"),
            "readings_tone": readings,
            "readings_plain": {_plain(r) for r in readings},
        })
    return entries


def _load_index() -> List[Dict[str, Any]]:
    """按 dataset_node_index.json 的 mtime 缓存索引（热更新，§3.4）。"""
    if not _PYPINYIN_OK:
        return []
    try:
        from disambiguation.typo_fastpath import _NODE_INDEX_PATH
        mtime = os.path.getmtime(_NODE_INDEX_PATH)
        with _cache_lock:
            if _index_cache["mtime"] == mtime and _index_cache["entries"]:
                return _index_cache["entries"]
            _index_cache["entries"] = _build_entries()
            _index_cache["mtime"] = mtime
            return _index_cache["entries"]
    except Exception:
        return _index_cache.get("entries") or []


def _char_dist(a: str, b: str, cutoff: int = 3) -> int:
    """字形编辑距离（DP，超 cutoff 提前返回 cutoff）。"""
    la, lb = len(a), len(b)
    if abs(la - lb) >= cutoff:
        return cutoff
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        row_min = i
        for j in range(1, lb + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] != b[j - 1]))
            row_min = min(row_min, cur[j])
        if row_min >= cutoff:
            return cutoff
        prev = cur
    return prev[lb]


def _pinyin_dist(frag_readings: List[Tuple[str, ...]], entry: Dict[str, Any]) -> Optional[int]:
    """无调拼音音节差异（等长逐位比较；不等长不召回）。取全部读音的最小值。"""
    best: Optional[int] = None
    for fr in frag_readings:
        fp = _plain(fr)
        for ep in entry["readings_plain"]:
            if len(fp) != len(ep):
                continue
            d = sum(1 for x, y in zip(fp, ep) if x != y)
            if best is None or d < best:
                best = d
    return best


def _plain_equal(frag_readings: List[Tuple[str, ...]], entry: Dict[str, Any]) -> bool:
    """2 字硬门：无调全拼完全相等（任一读音组合命中即可）。"""
    frag_plains = {_plain(fr) for fr in frag_readings}
    return bool(frag_plains & entry["readings_plain"])


def recall(
    fragment: str,
    allowed_dataset_ids: Optional[List[int]] = None,
    top_n: int = 5,
) -> List[Dict[str, Any]]:
    """对单个片段召回最近邻节点（按综合分升序，按 node_name 去重）。

    返回 [{text, node_name, dataset_id, level, match_type, pinyin_dist, char_dist, score}]。
    任何失败返回 []（fail-open）。
    """
    try:
        fragment = str(fragment or "").strip()
        flen = len(fragment)
        if flen < 2 or flen > 6 or not _PYPINYIN_OK:
            return []
        allowed = set(int(d) for d in (allowed_dataset_ids or []) if d)
        frag_readings = _readings(fragment)
        if not frag_readings:
            return []

        hits: List[Dict[str, Any]] = []
        for entry in _load_index():
            if entry["text"] == fragment:
                continue  # 精确命中不是"纠正证据"
            if allowed and int(entry.get("dataset_id") or 0) not in allowed:
                continue
            if flen == 2:
                # 硬门：只做无调全拼完全相等的同音召回
                if len(entry["text"]) == 2 and _plain_equal(frag_readings, entry):
                    hits.append({**{k: entry[k] for k in ("text", "node_name", "dataset_id", "level")},
                                 "match_type": "homophone", "pinyin_dist": 0,
                                 "char_dist": _char_dist(fragment, entry["text"]), "score": 0})
                continue
            # ≥3 字打分：首音节（无调）锚定（任一读音组合首音节相同即可）
            frag_firsts = {_plain(r)[0] for r in frag_readings if r}
            entry_firsts = {ep[0] for ep in entry["readings_plain"] if ep}
            if not (frag_firsts & entry_firsts):
                continue
            pd = _pinyin_dist(frag_readings, entry)
            cd = _char_dist(fragment, entry["text"])
            threshold = _DIST_THRESHOLD.get(flen, 2)
            score = min(pd if pd is not None else 99, cd)
            if score <= threshold:
                hits.append({**{k: entry[k] for k in ("text", "node_name", "dataset_id", "level")},
                             "match_type": "fuzzy", "pinyin_dist": pd, "char_dist": cd, "score": score})

        hits.sort(key=lambda h: (h["score"], h["char_dist"]))
        seen, out = set(), []
        for h in hits:
            if h["node_name"] in seen:
                continue
            seen.add(h["node_name"])
            out.append(h)
            if len(out) >= top_n:
                break
        return out
    except Exception:
        return []


def recall_in_question(
    question: str,
    allowed_dataset_ids: Optional[List[int]] = None,
    top_n: int = 5,
) -> List[Dict[str, Any]]:
    """对整问滑窗 2~6 字召回锚定证据（§4 anchor_evidence 的生产者）。

    返回 [{fragment, candidates: [...]}]，只保留有候选的片段。
    噪音过滤：候选实体原文已逐字出现在问题中（即用户没写错它）→ 不召回。
    """
    try:
        question = str(question or "").strip()
        if not question:
            return []
        merged: Dict[str, List[Dict[str, Any]]] = {}
        qlen = len(question)
        for wlen in range(2, 7):
            for start in range(0, qlen - wlen + 1):
                window = question[start:start + wlen]
                if not all("一" <= ch <= "龥" for ch in window):
                    continue
                for c in recall(window, allowed_dataset_ids, top_n=3):
                    if c["text"] in question:
                        continue  # 该实体在问题中已写对，不是纠正证据
                    cands = merged.setdefault(window, [])
                    if c["node_name"] not in {x["node_name"] for x in cands}:
                        cands.append(c)
        out = [{"fragment": f, "candidates": cs[:top_n]} for f, cs in merged.items()]
        out.sort(key=lambda r: min(c["score"] for c in r["candidates"]))
        return out[:top_n]
    except Exception:
        return []
