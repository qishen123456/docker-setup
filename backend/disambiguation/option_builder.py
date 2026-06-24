from __future__ import annotations

from typing import Any, Dict, List


def build_dataset_options(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    options = []
    for index, item in enumerate(candidates[:4], start=1):
        dataset_id = int(item.get("dataset_id") or 0)
        if not dataset_id:
            continue
        dataset_name = str(item.get("dataset_name") or f"数据集 {dataset_id}")
        score = item.get("score") if item.get("score") is not None else item.get("score_hint")
        reason = str(item.get("match_reason") or item.get("reason") or "").strip()
        if not reason:
            reason = f"按 {dataset_name} 的业务口径继续。"
        options.append(
            {
                "id": f"arbiter_dataset_{dataset_id}",
                "option_id": f"arbiter_dataset_{dataset_id}",
                "label": dataset_name,
                "reason": reason,
                "description": reason,
                "dataset_ids": [dataset_id],
                "option_type": "dataset_disambiguation",
                "confirmation_type": "dataset_disambiguation",
                "scope_filter": item.get("scope_filter") or {},
                "score": int(score) if score is not None else None,
            }
        )
    return options


def fallback_confirmation(candidates: List[Dict[str, Any]], question: str) -> Dict[str, Any]:
    return {
        "need_confirm": True,
        "confirm_question": "当前问题可能命中多个数据集或统计口径，请确认要使用哪个口径：",
        "options": build_dataset_options(candidates),
        "auto_pick_option_id": "",
        "reason": f"候选数据集分数接近，问题为：{question}",
    }
