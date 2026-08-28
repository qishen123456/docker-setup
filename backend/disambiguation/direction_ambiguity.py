# -*- coding: utf-8 -*-
"""方向歧义快检（澄清方案第 0.5 层）。

纯规则、毫秒级、不调 LLM。拦的是"两个方向词叠用"的口误（不是错字，第 0 层管不着）：
  用户输入「看下最好不的业务员」——"最好不"是"最好/最不好"说一半的混合形态，
  语义上正反皆有可能，必须让用户选，而不是替用户猜。

v1.1 弹卡词目（均为真实观察到的用户形态）：
  A.「最好不的」——"最好/最不好"说一半的混合形态（2026-08-28 实测案例）；
  B. 相邻双方向词叠加（如「最好最坏的」）——两个不同的最X直接相连、中间无连接词，
     不是合法中文（合法的会带"和/与/或"：做最好和最坏的打算），正反皆有可能。
其余 5 个臆想词目（最差不的/最高不的/最低不的/最多不的/最少不的）只记影子日志
不弹卡——它们的真实意图映射全靠猜（"最高不"是 最高 还是 最低？），
攒到真实分布数据后再配各自的候选对，避免生成"最不差的"这种不像人话的候选。

安全约束（评审 7 洞 + 2 微调后的定稿）：
  1. 触发词必须带"的"（"最好不的"），合法的"最好不按月度算"（had better not）不含"的"，天然放行；
  2. 合法疑问句"他的业绩最不好吗？"是 最+不+好 结构，不匹配 最+好+不 形态，天然放行；
  3. 候选为原位替换（replace count=1，学 typo_fastpath.py:201），不整句模板重写——
     追问场景（"那最好不的呢"）的上下文结构完整保留；
  4. 独立开关 direction_ambiguity_enabled（gatekeeper_settings.json），与守门员
     角色门控解耦：纯正则零 LLM 成本、不读别名表（无权限泄漏面），默认全员开放；
  5. 任何异常静默放行（fail-open），绝不拦死正常问数。
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(CURRENT_DIR, "..", "..", "config")
_SETTINGS_PATH = os.path.join(CONFIG_DIR, "gatekeeper_settings.json")

# v1 弹卡词目 A：真实观察到的口误形态
_V1_FRAGMENT = "最好不的"
# 候选对：原位替换片段（不含"的"），count=1 只替换第一次出现
_V1_SPAN = "最好不"
_V1_REPLACEMENTS = ("最好", "最不好")

# v1.1 弹卡词目 B：相邻双方向词叠加（最X最Y的，X≠Y，中间无连接词）。
# 词目含"坏"（最坏的业务员是真实问法）；相同词叠加（最好最好的）不算歧义。
_STACKED_RE = re.compile(r"(最[好差坏高低多少])(最[好差坏高低多少])的")

# 观察位：臆想词目只记日志不弹卡（真实意图映射无数据支撑，见模块 docstring 第 3 条）
_OBSERVE_RE = re.compile(r"最[差高低多少]不的")


def is_enabled() -> bool:
    """独立开关：direction_ambiguity_enabled，缺省 True（全员开放，不挂角色门控）。"""
    try:
        with open(_SETTINGS_PATH, "r", encoding="utf-8") as fh:
            settings = json.load(fh)
        return bool(settings.get("direction_ambiguity_enabled", True))
    except Exception:
        return True  # fail-open：配置读不到就保持开放（本层不拦只会回到老流程，无风险）


def detect_direction_ambiguity(question: str) -> Optional[Dict[str, Any]]:
    """检测方向歧义口误。命中返回 {fragment, candidates, reason}，否则 None。

    命中 v1 词目 → 返回两个候选问题（原位替换，正反各一）；
    命中观察位词目 → 返回 {"observe_only": True} 由调用方只记日志；
    其余 → None。
    """
    try:
        question = str(question or "").strip()
        if not question:
            return None
        if _V1_FRAGMENT in question:
            candidates = [
                question.replace(_V1_SPAN, repl, 1) for repl in _V1_REPLACEMENTS
            ]
            # 候选必须互不相同且都不同于原问题，否则是退化场景，不弹
            candidates = [c for c in candidates if c != question]
            if len(set(candidates)) != len(_V1_REPLACEMENTS) or not candidates:
                return None
            return {
                "fragment": _V1_SPAN,
                "candidates": candidates,
                "reason": "「最好不」可能是「最好」或「最不好」的口误，两种方向结果相反",
            }
        if _OBSERVE_RE.search(question):
            return {"observe_only": True, "fragment": _OBSERVE_RE.search(question).group(0)}
        # 词目 B：相邻双方向词叠加（"最好最坏的"）。候选=分别只保留其中一个方向词，原位放回。
        stacked = _STACKED_RE.search(question)
        if stacked and stacked.group(1) != stacked.group(2):
            span = stacked.group(1) + stacked.group(2)
            candidates = [
                question.replace(span, stacked.group(1), 1),
                question.replace(span, stacked.group(2), 1),
            ]
            candidates = [c for c in candidates if c != question]
            if len(set(candidates)) == 2:
                return {
                    "fragment": span,
                    "candidates": candidates,
                    "reason": f"「{span}」两个方向词叠在一起了，可能是「{stacked.group(1)}」或「{stacked.group(2)}」，两种方向结果相反",
                }
        return None
    except Exception:
        return None  # fail-open


def build_direction_clarify_result(
    question: str,
    hit: Dict[str, Any],
    session_id: str = "",
) -> Dict[str, Any]:
    """构造方向歧义短路的极简结果，结构与 typo_fastpath.build_early_clarify_result 一致。

    前端据 early_clarify=True 渲染纠正卡（两个方向候选 chip + 按原问题继续查），
    不渲染 PlanCard/报告等无用卡片。候选措辞优先用 LLM 自然语言生成
    （排名第一/倒数第一/两个都要对比），LLM 失败回退机械替换候选（fail-open）。
    """
    candidates = [str(c) for c in (hit.get("candidates") or []) if str(c).strip()]
    try:
        from disambiguation.shadow_gatekeeper import generate_direction_candidates

        llm_candidates = generate_direction_candidates(question, str(hit.get("fragment") or ""))
        if llm_candidates:
            candidates = llm_candidates
    except Exception:
        pass  # fail-open：机械候选兜底
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
            "reason": str(hit.get("reason") or ""),
            "candidates": candidates,
            "confidence": 1.0,
            "source": "direction_ambiguity",
        },
        "early_clarify": True,
        "session_id": session_id or "",
    }


def log_direction(question: str, hit: Dict[str, Any], user: Optional[Dict[str, Any]] = None,
                  session_id: str = "") -> None:
    """写影子日志（gk_source=direction_ambiguity），弹卡/观察都记。fail-open。"""
    try:
        from disambiguation.shadow_gatekeeper import _append_log, _load_settings

        settings = _load_settings()
        if not settings.get("enabled"):
            return
        log_path = str(
            settings.get("log_path")
            or os.path.join(CONFIG_DIR, "shadow_gatekeeper_log.jsonl")
        )
        observe_only = bool(hit.get("observe_only"))
        record = {
            "question": question,
            "session_id": session_id or "",
            "user_id": str((user or {}).get("username") or (user or {}).get("id") or ""),
            "timestamp": int(time.time()),
            "dataset_id": None,
            "prompt_version": "direction_ambiguity_v1",
            "sql_status": "short_circuit" if not observe_only else "observe",
            "rows_returned": 0,
            "gk_source": "direction_ambiguity",
            "gk_status": "ok",
            "gk_action": "observe" if observe_only else "suggest",
            "gk_latency_ms": 0,
            "would_block": not observe_only,
            "block_reason": str(hit.get("reason") or f"观察位命中「{hit.get('fragment')}」，未弹卡"),
            "self_confidence": None if observe_only else 1.0,
            "candidate_options_topN": [str(c)[:120] for c in (hit.get("candidates") or [])][:3],
        }
        _append_log(record, log_path)
    except Exception:
        pass
