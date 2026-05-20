from __future__ import annotations

import re
from typing import Any, Dict, List


class SqlQualitySkill:
    key = "sql_quality"

    DANGEROUS_PATTERN = re.compile(
        r"\b(insert|update|delete|drop|truncate|alter|create|grant|revoke|merge|call|execute|exec)\b",
        re.IGNORECASE,
    )

    FIELD_PATTERN = re.compile(r"\bfields\s*(?:->>|->)\s*'([^']+)'", re.IGNORECASE)
    TABLE_PATTERN = re.compile(r"\b(?:from|join)\s+([a-zA-Z_][\w.]*)", re.IGNORECASE)

    @staticmethod
    def _read_only(sql: str) -> bool:
        text = re.sub(r"/\*.*?\*/", " ", str(sql or ""), flags=re.S)
        text = re.sub(r"--.*?$", " ", text, flags=re.M).strip()
        if not text:
            return False
        if SqlQualitySkill.DANGEROUS_PATTERN.search(text):
            return False
        return bool(re.match(r"^\s*(with|select)\b", text, flags=re.I))

    @staticmethod
    def _asset_context_for_dataset(contexts: Dict[str, Dict[str, Any]], dataset_id: Any) -> Dict[str, Any]:
        return contexts.get(str(dataset_id)) or {}

    @staticmethod
    def _known_fields(context: Dict[str, Any]) -> set[str]:
        result = set()
        for item in context.get("data_dictionary") or []:
            if not isinstance(item, dict):
                continue
            for key in ("jsonb_key", "semantic_name", "column_name"):
                value = str(item.get(key) or "").strip()
                if value:
                    result.add(value)
        return result

    @staticmethod
    def _known_tables(context: Dict[str, Any]) -> set[str]:
        result = set()
        for item in context.get("schema_definition") or []:
            if not isinstance(item, dict):
                continue
            value = str(item.get("table_name") or "").strip()
            if value:
                result.add(value)
                result.add(value.split(".")[-1])
        return result

    def run(self, *, result: Dict[str, Any], asset_contexts: Dict[str, Dict[str, Any]] | None = None) -> Dict[str, Any]:
        dataset_results = result.get("dataset_results") if isinstance(result, dict) else []
        asset_contexts = asset_contexts or {}
        reports = []
        total_score = 0

        for dataset in dataset_results or []:
            if not isinstance(dataset, dict):
                continue
            report = self._inspect_dataset(dataset, self._asset_context_for_dataset(asset_contexts, dataset.get("dataset_id")))
            reports.append(report)
            total_score += int(report.get("score") or 0)

        avg_score = round(total_score / len(reports), 2) if reports else 0
        warnings = [warning for item in reports for warning in item.get("warnings") or []]
        return {
            "score": avg_score,
            "ok": avg_score >= 70 and not any(item.get("level") == "high" for item in warnings),
            "dataset_count": len(reports),
            "datasets": reports,
            "warning_count": len(warnings),
            "warnings": warnings,
        }

    def _inspect_dataset(self, dataset: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        sql = str(dataset.get("sql") or "").strip()
        review = dataset.get("agent3_review") if isinstance(dataset.get("agent3_review"), dict) else {}
        rows = dataset.get("rows") if isinstance(dataset.get("rows"), list) else []
        columns = dataset.get("columns") if isinstance(dataset.get("columns"), list) else []
        warnings: List[Dict[str, Any]] = []
        checks: List[Dict[str, Any]] = []
        score = 100

        def add_check(code: str, ok: bool, message: str, penalty: int = 0, level: str = "medium") -> None:
            nonlocal score
            checks.append({"code": code, "ok": ok, "message": message})
            if not ok:
                score -= penalty
                warnings.append({"level": level, "code": code, "message": message})

        add_check("sql_present", bool(sql), "SQL 已生成。" if sql else "未生成可检查 SQL。", 30, "high")
        add_check("read_only", self._read_only(sql), "SQL 通过只读检查。" if self._read_only(sql) else "SQL 未通过只读检查。", 35, "high")

        if review:
            approved = review.get("approved")
            add_check(
                "agent3_approved",
                approved is not False,
                "Agent3 复核通过。" if approved is not False else "Agent3 复核未通过。",
                25,
                "high",
            )
            if review.get("risks"):
                warnings.append(
                    {
                        "level": "medium",
                        "code": "agent3_risks",
                        "message": "Agent3 识别到风险：" + "；".join(str(item) for item in (review.get("risks") or [])[:5]),
                    }
                )
                score -= 8
        else:
            add_check("agent3_review_present", False, "未找到 Agent3 复核结构。", 10, "medium")

        known_fields = self._known_fields(context)
        used_fields = sorted(set(self.FIELD_PATTERN.findall(sql)))
        missing_fields = [item for item in used_fields if known_fields and item not in known_fields]
        add_check(
            "field_mapping",
            not missing_fields,
            "SQL 字段均可在数据字典中找到。" if not missing_fields else f"SQL 引用了数据字典外字段：{', '.join(missing_fields[:8])}",
            20,
            "high",
        )

        known_tables = self._known_tables(context)
        used_tables = sorted(set(item.split(".")[-1] for item in self.TABLE_PATTERN.findall(sql)))
        unknown_tables = [item for item in used_tables if known_tables and item not in known_tables]
        add_check(
            "table_mapping",
            not unknown_tables,
            "SQL 表引用通过资产校验。" if not unknown_tables else f"SQL 引用了资产外表：{', '.join(unknown_tables[:5])}",
            15,
            "medium",
        )

        add_check("columns_returned", bool(columns), "查询返回字段。" if columns else "查询未返回字段。", 15, "medium")
        add_check("rows_returned", bool(rows), f"查询返回 {len(rows)} 行。" if rows else "查询返回 0 行。", 15, "medium")

        return {
            "dataset_id": dataset.get("dataset_id"),
            "dataset_name": dataset.get("dataset_name"),
            "score": max(score, 0),
            "sql_present": bool(sql),
            "row_count": len(rows),
            "column_count": len(columns),
            "used_fields": used_fields[:30],
            "used_tables": used_tables[:20],
            "checks": checks,
            "warnings": warnings,
        }
