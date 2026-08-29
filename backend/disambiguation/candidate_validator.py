# -*- coding: utf-8 -*-
"""候选出口书架校验（P1-a 影子模式 / 冻结范围 1：书架否决权）。

对所有候选出口（守门员纠正条 / 错字快检 / 方向歧义 / 0 行诊断）产出的候选问题做
书架校验。**影子模式：只记录不拦截**——本模块不改动任何候选，只输出判定并写影子日志，
供 P1-b 决策"哪些候选出口该被书架否决"。

检出两类实锤问题（三方合并报告 §4 P0-3）：
  1. 编造不存在的节点：候选里出现 X分公司/X代表处/X事业部 形态、书架（含别名）里却没有的
     节点（实锤："东北三省"→候选"东北部分公司"）；与某别名编辑距离 ≤1 的单独标记为
     near_alias_node（疑似错字残留/同音跑偏，如候选残留"商泳事业部"）；
  2. 文本拼接污染：候选里的书架别名是和功能词残段拼出来的
     （实锤："达成率100%以上海代表处"=「100%以」+「上海代表处」；"未达播分之百"=「未达」+「播」）。

安全约束：
  1. 纯代码、毫秒级、不调 LLM；任何异常 → pass=True 全放行（fail-open），绝不拦候选；
  2. 开关 candidate_validation_enabled（gatekeeper_settings.json），只影响记不记校验日志；
  3. 别名表复用 typo_fastpath 的加载与权限过滤口径，不另抄表。
"""
from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List, Optional

from disambiguation.typo_fastpath import (
    GENERIC_LEVEL_WORDS,
    _LEADING_STOPWORDS,
    _lev_le1,
    _load_alias_entries,
)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(CURRENT_DIR, "..", "..", "config")

# 拼接污染判定：前邻字+别名首字构成功能词（"以上海"=「以上」+「海」），
# 且该别名未出现在原问题、功能词出现在原问题 → 候选里的这个实体是从原文残段拼出来的。
_FUNCTION_BIGRAMS = frozenset({
    "以上", "以下", "以前", "以后", "之上", "之下", "以内", "以外",
    "未达", "已达", "达到", "达成", "超过", "超出", "低于", "高于", "不足", "接近",
})

# 疑似节点词：组织后缀 + 前面 2~6 个汉字；后缀前一字是虚词则不算节点
# （挡"排名第一的业务员"里"的业务员"这种假节点）。
_ORG_FRAGMENT_RE = re.compile(
    r"[一-龥]{2,6}?(?<![的和与跟及或还就又都在看查询问])"
    r"(?:城市分公司|城市公司|分公司|事业部|代表处|业务部|业务代表)"
)

_MASK = "※"


def _has_near_variant(alias: str, question: str) -> bool:
    """原问题里是否存在该别名的编辑距离 ≤1 变体（合法错字纠正的信号，如"商泳事业部"）。"""
    try:
        qlen = len(question)
        alen = len(alias)
        for wlen in (alen - 1, alen, alen + 1):
            if wlen < 2 or wlen > qlen:
                continue
            for start in range(0, qlen - wlen + 1):
                if _lev_le1(question[start:start + wlen], alias):
                    return True
    except Exception:
        pass
    return False


def is_enabled() -> bool:
    """开关 candidate_validation_enabled，缺省 True。fail-open：读不到配置保持记录。"""
    try:
        from disambiguation.shadow_gatekeeper import _load_settings
        return bool(_load_settings().get("candidate_validation_enabled", True))
    except Exception:
        return True


def _mask_known_aliases(text: str, aliases: List[str], question: str):
    """把候选串里的书架别名占位遮蔽，返回 (遮蔽后文本, 拼接污染列表)。

    长别名优先、不重叠。拼接判定：别名未出现在原问题，且 前邻字+别名首字 是功能词、
    且该功能词出现在原问题里（污染来自原文残段，如「达成率100%以上」的「以上」）。
    """
    spans = []  # (start, end, alias)
    for alias in sorted(aliases, key=len, reverse=True):
        start = 0
        while True:
            idx = text.find(alias, start)
            if idx < 0:
                break
            end = idx + len(alias)
            if not any(idx < e and end > s for s, e, _ in spans):
                spans.append((idx, end, alias))
            start = idx + 1
    spliced: List[Dict[str, str]] = []
    if question:
        for s, _e, alias in spans:
            if s == 0 or alias in question:
                continue
            bigram = text[s - 1] + alias[0]
            if bigram not in question:
                continue
            # 规则 1：前邻字+别名首字是功能词（"以上海"=「以上」+「海」、"未达播"=「未达」+「播」）
            if bigram in _FUNCTION_BIGRAMS:
                spliced.append({"alias": alias, "bigram": bigram})
                continue
            # 规则 2：原文残段+书架节点拼成新串（"东北三省"→候选"东北部分公司"=「东」+「北部分公司」）。
            # 合法错字纠正除外：原文里有该别名的编辑距离≤1 变体（"看商泳事业部"→"看商用事业部"）。
            if len(alias) >= 3 and not _has_near_variant(alias, question):
                spliced.append({"alias": alias, "bigram": bigram})
    chars = list(text)
    for s, e, _alias in spans:
        for i in range(s, e):
            chars[i] = _MASK
    return "".join(chars), spliced


def _extract_suspect_nodes(masked: str) -> List[str]:
    """从遮蔽后文本提取"形态像组织节点"的片段（剥开头虚词、去泛层级词）。"""
    suspects: List[str] = []
    for m in _ORG_FRAGMENT_RE.finditer(masked):
        frag = m.group(0).lstrip(_LEADING_STOPWORDS)
        if len(frag) < 3 or frag in GENERIC_LEVEL_WORDS:
            continue
        if frag not in suspects:
            suspects.append(frag)
    return suspects


def validate_candidates(
    candidates: List[str],
    question: str = "",
    allowed_dataset_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """校验候选列表。

    返回 {"candidates": 通过校验者, "rejected": [{candidate, code, reason}], "pass": bool}。
    code ∈ spliced_alias（拼接污染）/ fabricated_node（编造节点）/ near_alias_node（错字残留）。
    任何异常 → 原样全放行 pass=True（fail-open），绝不拦候选。
    """
    try:
        cands = [str(c).strip() for c in (candidates or []) if str(c).strip()]
        if not cands:
            return {"candidates": [], "rejected": [], "pass": True}
        question = str(question or "").strip()
        allowed = set(int(d) for d in (allowed_dataset_ids or []) if d)
        entries = [
            e for e in _load_alias_entries()
            if not allowed or int(e.get("dataset_id") or 0) in allowed
        ]
        aliases = sorted({e["alias"] for e in entries})
        alias_set = set(aliases)
        survivors: List[str] = []
        rejected: List[Dict[str, Any]] = []
        for cand in cands:
            problems: List[Dict[str, str]] = []
            masked, spliced = _mask_known_aliases(cand, aliases, question)
            for sp in spliced:
                problems.append({
                    "code": "spliced_alias",
                    "reason": f"疑似文本拼接污染：「{sp['alias']}」由原文「{sp['bigram']}」残段拼接而成",
                })
            for frag in _extract_suspect_nodes(masked):
                if frag in alias_set:
                    continue
                near = next((a for a in aliases if len(a) >= 3 and _lev_le1(frag, a)), None)
                if near:
                    problems.append({
                        "code": "near_alias_node",
                        "reason": f"书架无节点「{frag}」（近似「{near}」，疑似错字残留/同音跑偏）",
                    })
                else:
                    problems.append({
                        "code": "fabricated_node",
                        "reason": f"书架不存在该节点「{frag}」，疑似编造",
                    })
            if problems:
                rejected.append({
                    "candidate": cand,
                    "code": problems[0]["code"],
                    "reason": "；".join(p["reason"] for p in problems),
                })
            else:
                survivors.append(cand)
        return {"candidates": survivors, "rejected": rejected, "pass": not rejected}
    except Exception:
        return {"candidates": [str(c) for c in (candidates or [])], "rejected": [], "pass": True}


def validate_and_log(
    source: str,
    question: str,
    candidates: List[str],
    user: Optional[Dict[str, Any]] = None,
    session_id: str = "",
    allowed_dataset_ids: Optional[List[int]] = None,
) -> Optional[Dict[str, Any]]:
    """校验 + 写一条影子日志（gk_source=candidate_validation_<source>）。fail-open。

    供没有自身影子日志的候选出口（0 行诊断卡）在弹卡点调用；只记日志，不改弹卡内容。
    返回校验结果（调用方一般忽略），异常返回 None。
    """
    try:
        if not is_enabled():
            return None
        started = time.time()
        result = validate_candidates(
            candidates, question=question, allowed_dataset_ids=allowed_dataset_ids
        )
        from disambiguation.shadow_gatekeeper import _append_log, _load_settings

        settings = _load_settings()
        if not settings.get("enabled"):
            return result
        log_path = str(
            settings.get("log_path") or os.path.join(CONFIG_DIR, "shadow_gatekeeper_log.jsonl")
        )
        total = len(result["rejected"]) + len(result["candidates"])
        record = {
            "question": str(question or ""),
            "session_id": session_id or "",
            "user_id": str((user or {}).get("username") or (user or {}).get("id") or ""),
            "timestamp": int(started),
            "dataset_id": None,
            "prompt_version": "candidate_validator_v1",
            "sql_status": "observe",
            "rows_returned": 0,
            "gk_source": f"candidate_validation_{source}",
            "gk_status": "ok",
            "gk_action": "observe",
            "gk_latency_ms": int((time.time() - started) * 1000),
            "would_block": False,
            "block_reason": "" if result["pass"] else f"书架校验否决 {len(result['rejected'])}/{total} 个候选",
            "self_confidence": None,
            "candidate_options_topN": [str(c)[:120] for c in (candidates or [])][:3],
            "candidate_validation": result,
        }
        _append_log(record, log_path)
        return result
    except Exception:
        return None
