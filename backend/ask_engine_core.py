"""Pure helpers for the SmartAsk engine."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


def _mask_secret(value: str) -> str:
    text = str(value or "")
    if len(text) <= 8:
        return "***" if text else ""
    return f"{text[:4]}***{text[-4:]}"


def _truncate_text(value: Any, limit: int = 4000) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated {len(text) - limit} chars]"


def _stream_preview(value: Any, limit: int = 1400) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return "..." + text[-limit:]


def _should_retry_with_another_model(exc: Exception) -> bool:
    return exc.__class__.__name__ in {
        "AuthenticationError",
        "PermissionDeniedError",
        "APITimeoutError",
        "APIConnectionError",
        "InternalServerError",
        "RateLimitError",
    }


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _normalize_chinese_numbers(text: str) -> str:
    """把常见中文数字（如一亿、两千万）归一化为阿拉伯数字+单位，便于阈值正则匹配。"""
    chinese_digit = {
        "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
        "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    }
    unit_multipliers = {"十": 10, "百": 100, "千": 1000, "万": 10000, "亿": 100000000}

    def _parse_integer(s: str) -> float:
        s = s.replace("个", "")
        total = 0.0
        section = 0.0
        current = 0.0
        for ch in s:
            if ch in chinese_digit:
                current = chinese_digit[ch]
            elif ch == "十":
                if current == 0:
                    current = 1
                section += current * 10
                current = 0
            elif ch == "百":
                section += current * 100
                current = 0
            elif ch == "千":
                section += current * 1000
                current = 0
            elif ch == "万":
                section += current
                total += section * 10000
                section = 0
                current = 0
            elif ch == "亿":
                section += current
                total += section * 100000000
                section = 0
                current = 0
        section += current
        total += section
        return total

    def _parse(s: str) -> float:
        s = s.replace("个", "")
        if "点" in s:
            integer_part, decimal_part = s.split("点", 1)
            integer_value = _parse_integer(integer_part) if integer_part else 0
            decimal_str = "".join(
                str(chinese_digit.get(c, c)) for c in decimal_part
                if c in chinese_digit or c.isdigit()
            )
            decimal_value = float("0." + decimal_str) if decimal_str else 0.0
            return integer_value + decimal_value
        return _parse_integer(s)

    def _repl(m: re.Match) -> str:
        num_str = m.group(1)
        unit = m.group(2)
        try:
            value = _parse(num_str)
        except Exception:
            return m.group(0)
        if value == int(value):
            return f"{int(value)}{unit}"
        return f"{value}{unit}"

    return re.sub(
        r"([一二两三四五六七八九十百千万亿点零]+)(?:个)?(万|亿)",
        _repl,
        text,
    )


def _normalize_prompt_items(items: Any) -> List[Dict[str, Any]]:
    return [item for item in (items or []) if isinstance(item, dict)]


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if value != value:
            return None
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", text)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _tokenize(text: str) -> set:
    parts = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{1,4}", (text or "").lower())
    return {item for item in parts if item.strip()}


def _normalize_compact_text(text: Any) -> str:
    return re.sub(r"\s+", "", str(text or "")).lower()
