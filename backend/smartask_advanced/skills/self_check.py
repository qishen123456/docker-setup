from __future__ import annotations

from typing import Any, Dict, List


class SelfCheckSkill:
    key = "self_check"

    def run(
        self,
        *,
        result: Dict[str, Any],
        assets: List[Dict[str, Any]] | None = None,
        pandas_report: Dict[str, Any] | None = None,
        route_guard: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        warnings: List[Dict[str, Any]] = []
        suggestions: List[str] = []
        dataset_results = result.get("dataset_results") if isinstance(result, dict) else []
        route_guard = route_guard or {}

        if not dataset_results:
            warnings.append({"level": "high", "code": "no_dataset_results", "message": "最终结果没有 dataset_results。"})
            suggestions.append("检查进阶流程是否正确承接基础引擎返回。")

        for dataset in dataset_results or []:
            name = dataset.get("dataset_name") or f"数据集 {dataset.get('dataset_id')}"
            rows = dataset.get("rows") or []
            columns = dataset.get("columns") or []
            if not rows:
                warnings.append({"level": "medium", "code": "empty_rows", "message": f"{name} 返回 0 行数据。"})
                suggestions.append("如问题包含明确组织或业务场景，建议核对数据集路由和组织别名。")
            if not columns:
                warnings.append({"level": "medium", "code": "empty_columns", "message": f"{name} 未返回字段。"})

        asset_ids = {str(item.get("dataset_id")) for item in assets or [] if item.get("dataset_id") is not None}
        result_ids = {str(item.get("dataset_id")) for item in dataset_results or [] if item.get("dataset_id") is not None}
        if asset_ids and result_ids and asset_ids.isdisjoint(result_ids):
            warnings.append(
                {
                    "level": "high",
                    "code": "asset_result_mismatch",
                    "message": "进阶资产预判数据集与最终查询数据集不一致。",
                }
            )
            suggestions.append("提示用户数据集与业务场景可能不匹配，并提供手动切换数据源。")

        guard_action = str(route_guard.get("action") or "")
        guard_expected_ids = {str(item) for item in (route_guard.get("recommended_dataset_ids") or route_guard.get("apply_dataset_ids") or [])}
        if guard_action == "manual_mismatch":
            warnings.append(
                {
                    "level": "high",
                    "code": "route_guard_manual_mismatch",
                    "message": "手动选择数据集与组织树解析的数据集不一致。",
                }
            )
            suggestions.append("提示用户数据集与业务场景不匹配，是否切换数据源？")
        elif guard_action == "needs_confirmation":
            warnings.append(
                {
                    "level": "medium",
                    "code": "route_guard_needs_confirmation",
                    "message": "进阶路由守门判断数据源存在歧义。",
                }
            )
            suggestions.append("建议用户确认组织范围或手动选择数据集后再执行。")
        if guard_expected_ids and result_ids and guard_expected_ids.isdisjoint(result_ids):
            warnings.append(
                {
                    "level": "high",
                    "code": "route_guard_result_mismatch",
                    "message": "进阶路由建议数据集与最终查询数据集不一致。",
                }
            )
            suggestions.append("提示用户数据集与业务场景可能不匹配，并提供手动切换数据源。")

        for item in (pandas_report or {}).get("datasets") or []:
            ranking = item.get("ranking") or {}
            top = ranking.get("top") or []
            sort_column = str(ranking.get("sort_column") or "")
            if "达成率" in sort_column and top:
                best_value = top[0].get("value")
                if isinstance(best_value, (int, float)) and best_value < 60:
                    warnings.append(
                        {
                            "level": "medium",
                            "code": "below_redline",
                            "message": f"{item.get('dataset_name')} 最优达成率仍低于 60% 红线。",
                        }
                    )

        return {
            "ok": not any(item.get("level") == "high" for item in warnings),
            "warning_count": len(warnings),
            "warnings": warnings,
            "suggestions": sorted(set(suggestions)),
        }
