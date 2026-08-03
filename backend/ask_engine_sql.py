"""Pure helpers for the SmartAsk engine."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


def _parse_cn_int(value: Any, default: int = 0) -> int:
    text = str(value or "").strip()
    if not text:
        return default
    if text.isdigit():
        return int(text)
    digits = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if text == "十":
        return 10
    if "十" in text:
        left, _, right = text.partition("十")
        tens = digits.get(left, 1 if not left else 0)
        ones = digits.get(right, 0)
        return tens * 10 + ones if tens else default
    return digits.get(text, default)


def _rank_limit_match(text: str):
    pattern = r"(\d+|[一二两三四五六七八九十]+)"
    return (
        re.search(rf"(?:Top|TOP|top|前|后|倒数)\s*{pattern}", text or "")
        or re.search(rf"(?:最高|最低|最好|最差|垫底|落后)(?:的)?\s*{pattern}\s*(?:个|名|位|家)?", text or "")
        or re.search(rf"第\s*{pattern}\s*(?:名|位)?", text or "")
    )


def _build_ranked_select_sql(*, source_cte: str, source_name: str, output_cte: str, where_clause: str, metric_column: str, direction: str, rank_limit: int, rank_sides: str='', top_rank_limit: int=0, bottom_rank_limit: int=0, tie_breaker: str='剩余任务金额 DESC, 节点名称') -> str:
    direction = 'ASC' if str(direction).upper() == 'ASC' else 'DESC'
    rank_limit = int(rank_limit or 0)
    top_limit = int(top_rank_limit or rank_limit or 0)
    bottom_limit = int(bottom_rank_limit or rank_limit or 0)
    if rank_sides == 'both':
        if top_limit > 0 or bottom_limit > 0:
            return f"\n{source_cte},\n{output_cte} AS (\n    SELECT\n        *,\n        ROW_NUMBER() OVER (\n            ORDER BY {metric_column} DESC, {tie_breaker}\n        ) AS 前排名,\n        ROW_NUMBER() OVER (\n            ORDER BY {metric_column} ASC, {tie_breaker}\n        ) AS 后排名\n    FROM {source_name}\n    WHERE {where_clause}\n),\n双向排名结果 AS (\n    SELECT *, CASE WHEN 前排名 <= {top_limit} THEN '前{top_limit}' ELSE '后{bottom_limit}' END AS 排名分组\n    FROM {output_cte}\n    WHERE 前排名 <= {top_limit} OR 后排名 <= {bottom_limit}\n)\nSELECT *\nFROM 双向排名结果\nORDER BY CASE 排名分组 WHEN '前{top_limit}' THEN 1 ELSE 2 END,\n         CASE WHEN 排名分组 = '前{top_limit}' THEN 前排名 ELSE 后排名 END,\n         节点名称\nLIMIT {top_limit + bottom_limit}\n".strip()
        return f'\n{source_cte},\n{output_cte} AS (\n    SELECT\n        *,\n        ROW_NUMBER() OVER (\n            ORDER BY {metric_column} DESC, {tie_breaker}\n        ) AS 前排名,\n        ROW_NUMBER() OVER (\n            ORDER BY {metric_column} ASC, {tie_breaker}\n        ) AS 后排名\n    FROM {source_name}\n    WHERE {where_clause}\n)\nSELECT *\nFROM {output_cte}\nORDER BY CASE WHEN 前排名 <= 后排名 THEN 1 ELSE 2 END,\n         CASE WHEN 前排名 <= 后排名 THEN 前排名 ELSE 后排名 END,\n         节点名称\nLIMIT 10000\n'.strip()
    if rank_limit > 0:
        return f'\n{source_cte},\n{output_cte} AS (\n    SELECT\n        *,\n        ROW_NUMBER() OVER (\n            ORDER BY {metric_column} {direction}, {tie_breaker}\n        ) AS 全局排名\n    FROM {source_name}\n    WHERE {where_clause}\n)\nSELECT *\nFROM {output_cte}\nWHERE 全局排名 <= {rank_limit}\nORDER BY 全局排名, {metric_column} {direction}, {tie_breaker}\nLIMIT {rank_limit}\n'.strip()
    return f'\n{source_cte},\n{output_cte} AS (\n    SELECT\n        *,\n        ROW_NUMBER() OVER (\n            ORDER BY {metric_column} {direction}, {tie_breaker}\n        ) AS 全局排名\n    FROM {source_name}\n    WHERE {where_clause}\n)\nSELECT *\nFROM {output_cte}\nORDER BY 全局排名, {metric_column} {direction}, {tie_breaker}\nLIMIT 10000\n'.strip()


def _is_read_only_sql(sql_text: str) -> bool:
    """判断 SQL 是否为只读查询。

    以 controllers/bookshelf.py 的更严格版本为准（额外拦截 execute/vacuum/analyze/copy）。
    """
    normalized = re.sub(r"/\*.*?\*/", " ", str(sql_text or ""), flags=re.S)
    normalized = re.sub(r"--.*?$", " ", normalized, flags=re.M).strip().lower()
    if not normalized:
        return False
    if not (normalized.startswith("select") or normalized.startswith("with")):
        return False
    blocked_keywords = (
        "insert", "update", "delete", "drop", "truncate", "alter",
        "create", "replace", "grant", "revoke", "merge", "call",
        "execute", "vacuum", "analyze", "copy",
    )
    blocked_pattern = rf"\b(?:{'|'.join(blocked_keywords)})\b"
    return re.search(blocked_pattern, normalized) is None


def _normalize_known_sql_alias_typos(sql_text: str) -> str:
    sql = str(sql_text or "")
    sql = re.sub(r"条线[\s_-]*type\b", "条线类型", sql, flags=re.IGNORECASE)
    return sql
