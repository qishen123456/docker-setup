"""Report scene registry.

Keeps scene detection declarative so report modes do not keep spreading across
prompt text, SQL generation, and frontend rendering.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


SCENES: Dict[str, Dict[str, Any]] = {
    "detail": {
        "label": "detail",
        "layout": "detail",
        "required_contract": ["nameColumn", "metrics"],
    },
    "comparative": {
        "label": "comparative",
        "layout": "comparison",
        "required_contract": ["nameColumn", "metrics"],
    },
    "ranking": {
        "label": "ranking",
        "layout": "ranking",
        "required_contract": ["nameColumn", "metrics"],
    },
    "filter": {
        "label": "filter",
        "layout": "filter",
        "required_contract": ["nameColumn", "metrics"],
    },
    "drilldown": {
        "label": "drilldown",
        "layout": "detail",
        "required_contract": ["nameColumn", "metrics"],
    },
    "diagnostic": {
        "label": "diagnostic",
        "layout": "detail",
        "required_contract": ["nameColumn", "metrics", "signalRules"],
    },
}


_RANKING_RE = re.compile(r"排名|排行|前\s*(?:\d+|[一二两三四五六七八九十]+)|Top\s*\d+|TOP\s*\d+|最好|最差|最高|最低", re.I)
_COMPARATIVE_RE = re.compile(r"对比|比较|哪个|谁更|差异|分别|各自|和.+比|跟.+比|与.+比|\bvs\b", re.I)
_DIAGNOSTIC_RE = re.compile(r"为什么|原因|归因|下滑|异常|差距|风险|缺口", re.I)


def detect_report_scene(
    question: str,
    focus_node: Optional[Dict[str, Any]],
    selected_count: int,
    query_intent: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return the final report scene and explain why it was selected."""

    text = question or ""
    reasons = []
    if isinstance(query_intent, dict) and query_intent.get("intent") == "filter":
        key = "filter"
        reasons.append("命中数据集意图策略：filter")
    elif isinstance(query_intent, dict) and query_intent.get("intent") == "drilldown":
        key = "drilldown"
        reasons.append("命中数据集意图策略：drilldown")
    elif _RANKING_RE.search(text):
        key = "ranking"
        reasons.append("问题包含排名/最好/最差/Top 等关键词")
    elif selected_count > 1 or _COMPARATIVE_RE.search(text):
        key = "comparative"
        if selected_count > 1:
            reasons.append(f"命中 {selected_count} 个对比主体")
        if _COMPARATIVE_RE.search(text):
            reasons.append("问题包含对比/比较/差异等关键词")
    elif _DIAGNOSTIC_RE.search(text):
        key = "diagnostic"
        reasons.append("问题包含原因/异常/风险/缺口等诊断关键词")
    elif focus_node:
        key = "detail"
        reasons.append("命中单个可下钻主体")
    else:
        key = "detail"
        reasons.append("未触发特殊场景，按常规分析处理")

    scene = SCENES[key]
    return {
        "key": key,
        "label": scene["label"],
        "layout": scene["layout"],
        "required_contract": scene.get("required_contract", []),
        "reasons": reasons,
    }


def layout_for_scene(scene_key: str) -> str:
    return SCENES.get(scene_key, SCENES["detail"]).get("layout", "detail")
