from __future__ import annotations

from typing import Any, Dict, List, Tuple


def stream_delta_value_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: List[str] = []
        for item in value:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "".join(parts)
    if isinstance(value, dict):
        return str(value.get("text") or value.get("content") or "")
    return str(value)


def extract_stream_delta(delta_obj: Any) -> Tuple[str, str]:
    content_delta = stream_delta_value_to_text(getattr(delta_obj, "content", ""))
    reasoning_delta = ""
    # reasoning_details 是 MiniMax reasoning_split=True 的思考字段（list-of-dict，stream_delta_value_to_text 已兼容）
    reasoning_keys = ("reasoning_content", "reasoning", "reasoning_text", "reasoning_details")

    for key in reasoning_keys:
        reasoning_delta = stream_delta_value_to_text(getattr(delta_obj, key, ""))
        if reasoning_delta:
            break

    if not reasoning_delta:
        dict_sources: List[Dict[str, Any]] = []
        extra = getattr(delta_obj, "model_extra", None)
        if isinstance(extra, dict):
            dict_sources.append(extra)
        additional = getattr(delta_obj, "additional_kwargs", None)
        if isinstance(additional, dict):
            dict_sources.append(additional)
        try:
            dumped = delta_obj.model_dump()
            if isinstance(dumped, dict):
                dict_sources.append(dumped)
        except Exception:
            pass

        for source in dict_sources:
            for key in reasoning_keys:
                reasoning_delta = stream_delta_value_to_text(source.get(key))
                if reasoning_delta:
                    break
            if reasoning_delta:
                break

    return content_delta, reasoning_delta
