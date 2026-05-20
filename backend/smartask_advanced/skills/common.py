from __future__ import annotations

import math
import re
from decimal import Decimal
from typing import Any, Dict, Iterable, List


def tokens(text: str) -> set[str]:
    return {
        item
        for item in re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{1,4}", str(text or "").lower())
        if item.strip()
    }


def as_int_list(values: Iterable[Any] | None) -> List[int]:
    result: List[int] = []
    for value in values or []:
        try:
            current = int(value)
        except Exception:
            continue
        if current not in result:
            result.append(current)
    return result


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def number_value(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        current = float(value)
        return current if math.isfinite(current) else None
    text = str(value).strip().replace(",", "").replace("，", "")
    if not text:
        return None
    multiplier = 1.0
    if text.endswith("%"):
        text = text[:-1]
    if text.endswith("亿"):
        multiplier = 100000000.0
        text = text[:-1]
    elif text.endswith("万"):
        multiplier = 10000.0
        text = text[:-1]
    try:
        current = float(text) * multiplier
    except Exception:
        return None
    return current if math.isfinite(current) else None


def first_present(row: Dict[str, Any], candidates: List[str]) -> str:
    keys = list(row.keys())
    for expected in candidates:
        for key in keys:
            if expected == key or expected in key:
                return key
    return ""


def compact_row(row: Dict[str, Any], max_keys: int = 10) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for index, (key, value) in enumerate((row or {}).items()):
        if index >= max_keys:
            break
        result[str(key)] = to_jsonable(value)
    return result
