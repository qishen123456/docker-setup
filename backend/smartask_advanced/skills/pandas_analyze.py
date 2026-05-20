from __future__ import annotations

from typing import Any, Dict, List

from .common import compact_row, first_present, number_value, to_jsonable

try:
    import pandas as pd
except Exception:  # pragma: no cover - runtime fallback for slim environments
    pd = None


class PandasAnalyzeSkill:
    key = "pandas_analyze"

    LABEL_COLUMNS = ["组织路径", "orgPath", "路径", "分公司", "代表处", "城市公司", "城市", "业务代表", "业务员", "名称", "name"]
    RATE_COLUMNS = ["达成率", "完成率", "完成进度", "完成比例", "rate", "completion"]
    TASK_COLUMNS = ["总任务", "任务", "目标", "年度目标", "target"]
    ACTUAL_COLUMNS = ["实际", "开单", "完成", "年度开单", "actual"]
    GAP_COLUMNS = ["缺口", "差额", "gap"]

    def run(self, result: Dict[str, Any], intent: Dict[str, Any] | None = None) -> Dict[str, Any]:
        datasets = result.get("dataset_results") if isinstance(result, dict) else []
        intent = intent or {}
        topn = int(intent.get("topN") or 10)
        analyses = []
        for dataset in datasets or []:
            rows = dataset.get("rows") if isinstance(dataset, dict) else []
            if not isinstance(rows, list) or not rows:
                analyses.append(
                    {
                        "dataset_id": dataset.get("dataset_id"),
                        "dataset_name": dataset.get("dataset_name"),
                        "row_count": 0,
                        "summary": "无可加工数据行",
                    }
                )
                continue
            analyses.append(self._analyze_dataset(dataset, rows, topn, intent=intent))
        return {"datasets": analyses, "engine": "pandas" if pd is not None else "python"}

    def _analyze_dataset(
        self,
        dataset: Dict[str, Any],
        rows: List[Dict[str, Any]],
        topn: int,
        intent: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        intent = intent or {}
        first_row = rows[0] if isinstance(rows[0], dict) else {}
        label_column = first_present(first_row, self.LABEL_COLUMNS)
        rate_column = first_present(first_row, self.RATE_COLUMNS)
        task_column = first_present(first_row, self.TASK_COLUMNS)
        actual_column = first_present(first_row, self.ACTUAL_COLUMNS)
        gap_column = first_present(first_row, self.GAP_COLUMNS)

        if pd is not None:
            frame = pd.DataFrame(rows)
            row_count = int(len(frame.index))
        else:
            frame = None
            row_count = len(rows)

        metrics: Dict[str, Any] = {
            "label_column": label_column,
            "rate_column": rate_column,
            "task_column": task_column,
            "actual_column": actual_column,
            "gap_column": gap_column,
        }

        for key, column in [("task_total", task_column), ("actual_total", actual_column), ("gap_total", gap_column)]:
            if not column:
                continue
            values = [number_value(row.get(column)) for row in rows if isinstance(row, dict)]
            values = [value for value in values if value is not None]
            if values:
                metrics[key] = round(sum(values), 4)

        analysis_rows = rows
        target_level = str(intent.get("targetLevel") or "").strip()
        grouped = self._group_by_target_level(
            rows=rows,
            target_level=target_level,
            label_column=label_column,
            rate_column=rate_column,
            task_column=task_column,
            actual_column=actual_column,
            gap_column=gap_column,
        )
        if grouped.get("rows"):
            analysis_rows = grouped.get("rows") or rows
            label_column = grouped.get("label_column") or label_column
            metrics["ranking_level"] = grouped.get("target_level")
            metrics["ranking_source"] = "target_level_aggregation"
            metrics["group_count"] = len(analysis_rows)

        ranking = self._ranking(analysis_rows, label_column, rate_column or actual_column or task_column, topn)
        return {
            "dataset_id": dataset.get("dataset_id"),
            "dataset_name": dataset.get("dataset_name"),
            "row_count": row_count,
            "metrics": to_jsonable(metrics),
            "ranking": ranking,
            "summary": self._summary(dataset, row_count, ranking, metrics),
        }

    def _group_by_target_level(
        self,
        *,
        rows: List[Dict[str, Any]],
        target_level: str,
        label_column: str,
        rate_column: str,
        task_column: str,
        actual_column: str,
        gap_column: str,
    ) -> Dict[str, Any]:
        if not target_level or target_level in {"业务代表", "业务员"}:
            return {}
        first_row = rows[0] if rows and isinstance(rows[0], dict) else {}
        level_column = self._find_level_column(first_row, self._level_candidates(target_level))
        if not level_column:
            return {}

        grouped: Dict[str, Dict[str, Any]] = {}
        rate_values: Dict[str, List[float]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            label = str(row.get(level_column) or "").strip()
            if not label:
                continue
            item = grouped.setdefault(level_column + "::" + label, {level_column: label})
            rate_values.setdefault(label, [])
            for source, target in [
                (task_column, task_column),
                (actual_column, actual_column),
                (gap_column, gap_column),
            ]:
                if not source:
                    continue
                value = number_value(row.get(source))
                if value is not None:
                    item[target] = round(number_value(item.get(target)) or 0, 4) + value
            if rate_column:
                rate = number_value(row.get(rate_column))
                if rate is not None:
                    rate_values[label].append(rate)

        output = []
        for item in grouped.values():
            label = str(item.get(level_column) or "")
            task = number_value(item.get(task_column)) if task_column else None
            actual = number_value(item.get(actual_column)) if actual_column else None
            if rate_column:
                if task and actual is not None:
                    item[rate_column] = round(actual / task * 100, 4)
                elif rate_values.get(label):
                    item[rate_column] = round(sum(rate_values[label]) / len(rate_values[label]), 4)
            output.append(item)
        if len(output) <= 1:
            return {}
        return {"rows": output, "label_column": level_column, "target_level": target_level}

    @staticmethod
    def _level_candidates(target_level: str) -> List[str]:
        mapping = {
            "事业部": ["事业部", "业务事业部"],
            "分公司": ["分公司", "大区", "区域"],
            "城市公司": ["城市公司", "城市分公司", "城市"],
            "城市": ["城市公司", "城市分公司", "城市"],
            "代表处": ["代表处", "办事处"],
            "业务部": ["业务部", "行业部"],
        }
        return mapping.get(target_level, [target_level])

    @staticmethod
    def _find_level_column(row: Dict[str, Any], candidates: List[str]) -> str:
        keys = list((row or {}).keys())
        for expected in candidates:
            for key in keys:
                if expected == key:
                    return key
        for expected in candidates:
            for key in keys:
                if expected in str(key or ""):
                    return key
        return ""

    def _ranking(self, rows: List[Dict[str, Any]], label_column: str, sort_column: str, topn: int) -> Dict[str, Any]:
        if not sort_column:
            return {"sort_column": "", "top": [], "bottom": []}

        ranked = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            value = number_value(row.get(sort_column))
            if value is None:
                continue
            ranked.append({"label": str(row.get(label_column) or row.get("名称") or row.get("name") or ""), "value": value, "row": compact_row(row)})
        ranked.sort(key=lambda item: item["value"], reverse=True)
        return {
            "sort_column": sort_column,
            "top": to_jsonable(ranked[:topn]),
            "bottom": to_jsonable(list(reversed(ranked[-topn:])) if ranked else []),
        }

    @staticmethod
    def _summary(dataset: Dict[str, Any], row_count: int, ranking: Dict[str, Any], metrics: Dict[str, Any]) -> str:
        name = dataset.get("dataset_name") or "当前数据集"
        sort_column = ranking.get("sort_column")
        top = ranking.get("top") or []
        if top and sort_column:
            best = top[0]
            label = best.get("label") or "排名第一对象"
            return f"{name} 共 {row_count} 行，按 {sort_column} 排名最高为 {label}。"
        if metrics.get("actual_total") is not None:
            return f"{name} 共 {row_count} 行，实际完成合计 {metrics.get('actual_total')}。"
        return f"{name} 共 {row_count} 行，已完成结构化加工。"
