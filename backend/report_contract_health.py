"""Validation helpers for dataset report contracts."""

from __future__ import annotations

from typing import Any, Dict, List


def _is_non_empty_text(value: Any) -> bool:
    return bool(str(value or "").strip())


def _column_exists(columns: List[str], column: str) -> bool:
    if not column:
        return False
    return str(column) in {str(item) for item in columns or []}


def validate_report_contract(
    config: Dict[str, Any] | None,
    columns: List[str] | None = None,
    scene: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return a lightweight contract health/debug payload.

    This does not fail the pipeline. It explains whether the report contract was
    actually useful for the current SQL result and which fields are missing.
    """
    config = config if isinstance(config, dict) else {}
    columns = [str(item) for item in (columns or [])]
    scene = scene if isinstance(scene, dict) else {}

    missing: List[str] = []
    warnings: List[str] = []
    standard_columns = []

    for key in ("nameColumn", "parentColumn", "levelColumn"):
        value = str(config.get(key) or "").strip()
        if not value:
            missing.append(key)
            continue
        if columns and _column_exists(columns, value):
            standard_columns.append(value)
        elif columns:
            warnings.append(f"{key}={value} 未出现在本次 SQL 结果列中")

    track_column = str(config.get("trackColumn") or "").strip()
    if track_column and columns and _column_exists(columns, track_column):
        standard_columns.append(track_column)

    metrics = [item for item in (config.get("metrics") or []) if isinstance(item, dict)]
    if not metrics:
        missing.append("metrics")
    metric_keys = {str(item.get("key") or "") for item in metrics if _is_non_empty_text(item.get("key"))}
    metric_columns = []
    for metric in metrics:
        column = str(metric.get("column") or "").strip()
        if column:
            metric_columns.append(column)
            if columns and _column_exists(columns, column):
                standard_columns.append(column)
            elif columns:
                warnings.append(f"指标列 {column} 未出现在本次 SQL 结果列中")

    if not any(str(item.get("format") or "") == "percent" or "率" in str(item.get("label") or item.get("column") or "") for item in metrics):
        warnings.append("未识别到百分比/达成率指标，排名和风险分析可能不稳定")

    analysis_dimensions = [item for item in (config.get("analysisDimensions") or []) if isinstance(item, dict)]
    if not analysis_dimensions:
        warnings.append("analysisDimensions 为空，系统只能根据 SQL 结果临时推断上下级")

    signal_rules = [item for item in (config.get("signalRules") or []) if isinstance(item, dict)]
    for rule in signal_rules:
        rule_key = str(rule.get("key") or "")
        if rule_key and rule_key not in metric_keys:
            warnings.append(f"信号灯规则引用了不存在的指标 key={rule_key}")

    sql_contract = config.get("sqlOutputContract") if isinstance(config.get("sqlOutputContract"), dict) else {}
    if not sql_contract.get("requiredColumns"):
        warnings.append("sqlOutputContract.requiredColumns 为空，Agent2 缺少标准输出列约束")

    required_for_scene = scene.get("required_contract") or []
    for key in required_for_scene:
        if key == "metrics" and not metrics:
            missing.append("metrics")
        elif key == "signalRules" and not signal_rules:
            warnings.append("当前场景建议配置 signalRules")
        elif key not in ("metrics", "signalRules") and not _is_non_empty_text(config.get(key)):
            missing.append(key)

    missing = sorted(set(missing))
    warnings = sorted(set(warnings))
    standard_columns = list(dict.fromkeys(standard_columns))
    score = 100
    score -= len(missing) * 18
    score -= min(len(warnings) * 6, 36)
    score = max(0, min(100, score))
    level = "healthy" if score >= 85 else "warning" if score >= 60 else "danger"
    return {
        "used": bool(config),
        "score": score,
        "level": level,
        "missing": missing,
        "warnings": warnings,
        "standard_columns_detected": standard_columns,
        "metric_columns": metric_columns,
        "analysis_dimension_count": len(analysis_dimensions),
        "metric_count": len(metrics),
        "signal_rule_count": len(signal_rules),
    }
