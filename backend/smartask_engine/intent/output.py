from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass(frozen=True)
class IntentPorts:
    safe_dict: Callable[[Any], Dict[str, Any]]
    safe_int: Callable[[Any, int], int]
    normalize_chinese_numbers: Callable[[str], str]
    rank_limit_match: Callable[[str], Any]
    parse_cn_int: Callable[[Any, int], int]
    resolved_entity_names: Callable[[Dict[str, Any]], list]
    question_subject_names: Callable[..., list]
    is_dataset_root_name: Callable[[str, Dict[str, Any]], bool]
    rank_request_spec: Callable[[str, int, int], Dict[str, Any]]
    default_report_config: Callable[[], Dict[str, Any]]
    dataset_profile: Callable[[str, str], Dict[str, Any]]


def empty_intent() -> Dict[str, Any]:
    return {
        "intent": "unknown",
        "source": "report_config.intentPolicies",
        "target_level": "",
        "top_n": None,
        "sort_metric_key": "",
        "sort_metric_column": "",
        "direction": "",
        "rank_sides": "",
        "output_mode": "",
        "matched_triggers": [],
    }
