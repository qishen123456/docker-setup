from __future__ import annotations

import re
from typing import Any, Callable, Dict


def rank_request_spec(
    text: str,
    default_limit: int,
    max_limit: int,
    *,
    rank_limit_match: Callable[[str], Any],
    parse_cn_int: Callable[[Any, int], int],
) -> Dict[str, Any]:
    text = str(text or "")
    top_match = re.search(r"(?:Top|TOP|top|前)\s*(\d+|[一二两三四五六七八九十]+)", text)
    bottom_match = re.search(
        r"(?:后|倒数|垫底|落后)(?:的)?\s*(\d+|[一二两三四五六七八九十]+)\s*(?:个|名|位|家)?",
        text,
    )
    generic_match = rank_limit_match(text)
    top_limit = parse_cn_int(top_match.group(1), 0) if top_match else 0
    bottom_limit = parse_cn_int(bottom_match.group(1), 0) if bottom_match else 0
    if not top_limit and not bottom_limit and generic_match:
        generic_limit = parse_cn_int(generic_match.group(1), default_limit)
        if re.search(r"(?:后|倒数|最低|最差|垫底)", text):
            bottom_limit = generic_limit
        else:
            top_limit = generic_limit
    top_requested = bool(
        top_match
        or re.search(r"(?:Top|TOP|top|最高|最好|第\s*(?:\d+|[一二两三四五六七八九十]+)\s*(?:名|位)?)", text)
    )
    bottom_requested = bool(bottom_match or re.search(r"(?:倒数|最低|最差|垫底)", text))
    effective_limit = max(top_limit, bottom_limit) or default_limit
    if effective_limit:
        effective_limit = max(1, min(max_limit, effective_limit))
    if top_limit:
        top_limit = max(1, min(max_limit, top_limit))
    if bottom_limit:
        bottom_limit = max(1, min(max_limit, bottom_limit))
    return {
        "limit": effective_limit,
        "top_limit": top_limit,
        "bottom_limit": bottom_limit,
        "sides": "both" if top_requested and bottom_requested else ("bottom" if bottom_requested else "top"),
        "direction": "asc" if bottom_requested and not top_requested else "desc",
    }
