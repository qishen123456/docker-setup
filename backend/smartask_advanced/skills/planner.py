from __future__ import annotations

import re
from typing import Any, Dict


class PlannerSkill:
    key = "planner"

    @staticmethod
    def infer(question: str) -> Dict[str, Any]:
        text = str(question or "")
        topn = None
        match = re.search(r"(?:top|前|最)[^\d一二三四五六七八九十]{0,4}(\d+|一|二|三|四|五|六|七|八|九|十)", text, re.I)
        if match:
            mapping = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
            topn = mapping.get(match.group(1))
            if topn is None:
                try:
                    topn = int(match.group(1))
                except Exception:
                    topn = None

        intent = "analysis"
        if re.search(r"最高|最低|最好|最差|排名|排行|top|前\d+|前三|前十", text, re.I):
            intent = "ranking"
        elif re.search(r"对比|比较|差异|和.+比|与.+比|vs", text, re.I):
            intent = "comparison"
        elif re.search(r"为什么|原因|归因|影响|驱动", text, re.I):
            intent = "diagnosis"
        elif re.search(r"趋势|环比|同比|按月|按日|变化", text, re.I):
            intent = "trend"

        target_level = ""
        for level in ("业务员", "业务代表", "代表处", "城市公司", "城市", "分公司", "事业部"):
            if level in text:
                target_level = level
                break

        return {
            "intent": intent,
            "topN": topn,
            "targetLevel": target_level,
            "needsOrgPath": bool(re.search(r"分公司|代表处|城市|业务员|人员|组织|路径", text)),
            "requiresComparison": bool(re.search(r"对比|比较|差异|和.+比|与.+比|vs", text, re.I)),
        }
