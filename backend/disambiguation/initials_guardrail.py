# -*- coding: utf-8 -*-
"""首字母静默护栏（P1-a 影子模式 / 冻结范围 2）。

只观察记录，**绝不改活体行为**：检测问题中的拉丁字母缩写（2~10 个连续字母，
如 NB/XB/DJ/JD/tmall/dongbu/shangyong，大小写不限），用拼音索引把它映射到书架
实体候选（≤4 字母按首字母：NB→南部/宁波；≥5 字母按无调全拼：dongbu→东部），
写入影子日志字段 initials_guardrail，攒数据供 P1-b 决策。

重点标记危险场景：pipeline_verdict=pass（直接答了）且缩写映射到多个/零个实体
（DJ→83 行静默答错类，三方合并报告 §6.1 实锤），日志加 risk=silent_wrong_suspect。

安全约束：
  1. 开关 initials_guardrail_enabled（gatekeeper_settings.json），只影响记不记；
  2. 复用 pinyin_index 的索引（mtime 缓存），不另建表；pypinyin 缺失时仍能检出
     缩写本体（映射候选为空——"零映射"本身就是重要影子数据）；
  3. 任何异常 → 返回空列表（fail-open），主流程零感知。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

_TOKEN_RE = re.compile(r"[A-Za-z]{2,10}")
# ≤4 字母按首字母映射（NB→南部），≥5 字母按无调全拼映射（dongbu→东部）
_INITIALS_MAX_LEN = 4

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(CURRENT_DIR, "..", "..", "config")
_ALIASES_PATH = os.path.join(CONFIG_DIR, "abbreviation_aliases.json")
_aliases_cache: Dict[str, Any] = {"mtime": 0.0, "data": {}}


def _load_aliases() -> Dict[str, str]:
    """读人工精排映射表（abbreviation_aliases.json），mtime 缓存。任何失败返回 {}。"""
    try:
        mtime = os.path.getmtime(_ALIASES_PATH)
        if mtime != _aliases_cache["mtime"]:
            with open(_ALIASES_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh).get("aliases") or {}
            _aliases_cache["data"] = {str(k).lower(): str(v) for k, v in data.items() if v}
            _aliases_cache["mtime"] = mtime
        return _aliases_cache["data"]
    except Exception:
        return {}


def is_enabled() -> bool:
    """开关 initials_guardrail_enabled，缺省 True。fail-open：读不到配置保持记录。"""
    try:
        from disambiguation.shadow_gatekeeper import _load_settings
        return bool(_load_settings().get("initials_guardrail_enabled", True))
    except Exception:
        return True


def pipeline_verdict(result: Dict[str, Any]) -> str:
    """从流水线结果推四态 verdict：pass / confirm / card / zero（error 单列）。"""
    try:
        result = result or {}
        route = result.get("route") or {}
        if result.get("error"):
            return "error"
        if (
            result.get("early_clarify")
            or result.get("clarify_suggestion")
            or route.get("decision") == "early_clarify"
        ):
            return "card"
        if route.get("requires_confirmation") or result.get("requires_confirmation"):
            return "confirm"
        if int(result.get("row_count") or 0) > 0:
            return "pass"
        return "zero"
    except Exception:
        return "unknown"


def map_token(
    token: str,
    allowed_dataset_ids: Optional[List[int]] = None,
    top_n: int = 8,
) -> List[str]:
    """把拉丁 token 映射到书架实体候选（别名原文，按 node 去重）。任何失败返回 []。

    优先级：人工精排表（abbreviation_aliases.json，如 jd→京东直营）> 拼音首字母/全拼索引。
    索引撞车时返回多个候选（双候选来自索引节点，不硬猜）。
    """
    try:
        token = str(token or "").strip().lower()
        if len(token) < 2:
            return []
        curated = _load_aliases().get(token)
        if curated:
            return [curated]
        from disambiguation.pinyin_index import _load_index

        allowed = set(int(d) for d in (allowed_dataset_ids or []) if d)
        by_initials = len(token) <= _INITIALS_MAX_LEN
        seen = set()
        out: List[str] = []
        for entry in _load_index():
            if allowed and int(entry.get("dataset_id") or 0) not in allowed:
                continue
            hit = False
            for reading in entry.get("readings_plain") or set():
                syllables = [s for s in reading if s]
                if not syllables:
                    continue
                if by_initials:
                    if "".join(s[0] for s in syllables) == token:
                        hit = True
                        break
                elif "".join(syllables) == token:
                    hit = True
                    break
            if not hit:
                continue
            key = (entry.get("node_name"), entry.get("dataset_id"))
            if key in seen:
                continue
            seen.add(key)
            text = str(entry.get("text") or entry.get("node_name") or "").strip()
            if text:
                out.append(text)
            if len(out) >= top_n:
                break
        return out
    except Exception:
        return []


def build_guardrail_entries(
    question: str,
    result: Optional[Dict[str, Any]] = None,
    allowed_dataset_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    """检测 + 映射 + verdict + 风险标记。无拉丁缩写或任何异常 → []。"""
    try:
        question = str(question or "").strip()
        if not question:
            return []
        verdict = pipeline_verdict(result or {})
        entries: List[Dict[str, Any]] = []
        seen_tokens = set()
        for m in _TOKEN_RE.finditer(question):
            token = m.group(0)
            key = token.lower()
            if key in seen_tokens:
                continue
            seen_tokens.add(key)
            mapping = map_token(token, allowed_dataset_ids)
            item: Dict[str, Any] = {
                "detected": token,
                "mapping_candidates": mapping,
                "pipeline_verdict": verdict,
            }
            # 危险场景：直接答了，但缩写映射不唯一（多个/零个实体）→ 静默答错嫌疑
            if verdict == "pass" and len(mapping) != 1:
                item["risk"] = "silent_wrong_suspect"
            entries.append(item)
        return entries
    except Exception:
        return []


def build_initials_preview(
    question: str,
    user: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """首字母提示条（超管预览，P1-b soft_hint 的预览形态）。

    命中条件：开关 initials_preview_enabled + 用户在可见角色内 + 问题中恰有 1 个
    拉丁缩写 + 映射候选 ≥1（精排表优先，索引撞车则多候选都列出，由用户点选）。
    返回 clarify_suggestion 结构（纠正条样式，不含 early_clarify——确认卡照常显示）。
    任何异常返回 None（fail-open），活体流程零感知。
    """
    try:
        from disambiguation.shadow_gatekeeper import _load_settings, is_visible_user

        settings = _load_settings()
        if not settings.get("initials_preview_enabled", False):
            return None
        if not is_visible_user(user):
            return None
        question = str(question or "").strip()
        tokens = list(dict.fromkeys(m.group(0) for m in _TOKEN_RE.finditer(question)))
        if len(tokens) != 1:
            return None
        token = tokens[0]
        mapping = map_token(token)
        if not mapping:
            return None
        mapping = list(dict.fromkeys(mapping))  # 同别名撞多节点（上海→城市公司/代表处）展示去重
        candidates = []
        for entity in mapping[:4]:
            # 实体后缀与 token 后原文重叠时去重（TM直营→天猫直营直营 ✗ → 天猫直营 ✓）
            pos = question.find(token)
            following = question[pos + len(token):]
            overlap = 0
            for L in range(min(4, len(entity), len(following)), 0, -1):
                if entity.endswith(following[:L]):
                    overlap = L
                    break
            cand = question[:pos] + entity + following[overlap:] if pos >= 0 else question
            if cand != question and cand not in candidates:
                candidates.append(cand)
        if not candidates:
            return None
        return {
            "action": "suggest",
            "interpretation": question,
            "reason": f"「{token}」可能是缩写，书架里对应：{' / '.join(mapping[:4])}",
            "candidates": candidates,
            "confidence": 0.9 if len(mapping) == 1 else 0.6,
            "source": "initials_guardrail",
        }
    except Exception:
        return None
