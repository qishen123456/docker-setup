from __future__ import annotations

from typing import Any, Dict, List


def _business_name(dataset_name: str) -> str:
    """从数据集名提取业务名（复用 unified_confirm 的逻辑）：'消费者事业部开单金额'→'消费者事业部'。"""
    try:
        from .unified_confirm import _business_name as _biz
        return _biz(dataset_name)
    except Exception:
        return dataset_name


def build_dataset_options(candidates: List[Dict[str, Any]], question: str = "") -> List[Dict[str, Any]]:
    """数据集级确认卡选项。

    2026-09-02 统一交互（与节点级确认卡风格一致）：
    - label：有 question 时拼完整问句 '{业务名} · {原问题}'（如 '商用事业部 · sh的业绩'），
      无 question 时保持数据集名（auto_pick 场景不展示给用户选）。
    - 加 dataset_name 字段（前端预选联动用，同节点级确认卡）。
    """
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
        q = str(question or "").strip()
        label = f"{_business_name(dataset_name)} · {q}" if q else dataset_name
        options.append(
            {
                "id": f"arbiter_dataset_{dataset_id}",
                "option_id": f"arbiter_dataset_{dataset_id}",
                "label": label,
                "reason": reason,
                "description": reason,
                "dataset_ids": [dataset_id],
                "dataset_name": dataset_name,
                "option_type": "dataset_disambiguation",
                "confirmation_type": "dataset_disambiguation",
                "scope_filter": item.get("scope_filter") or {},
                "score": int(score) if score is not None else None,
            }
        )
    return options


def fallback_confirmation(candidates: List[Dict[str, Any]], question: str) -> Dict[str, Any]:
    """消歧仲裁器兜底确认卡。

    2026-09-02 统一交互：文案改"你是不是想问："（与节点级确认卡一致），
    选项为完整问句 + dataset_name，并按数据集优先级排序 + recommended 标记。
    """
    try:
        from .unified_confirm import apply_recommendation
        options = apply_recommendation(build_dataset_options(candidates, question))
    except Exception:
        options = build_dataset_options(candidates, question)  # fail-open：排序失败用原序
    return {
        "need_confirm": True,
        "confirm_question": "你是不是想问：",
        "options": options,
        "auto_pick_option_id": "",
        "reason": f"候选数据集分数接近，问题为：{question}",
    }
