from __future__ import annotations

import re
import time
from typing import Any, Dict, List
from uuid import uuid4

from smartask_basic.service import basic_ask_service

from .config_store import load_config
from .registry import build_skill_plan, capability_summary
from .skills import (
    AnswerContractSkill,
    AssetPackSkill,
    ConclusionAdviceSkill,
    DatasetRouteSkill,
    EvidenceVoteSkill,
    GoldenSqlSkill,
    PandasAnalyzeSkill,
    PlannerSkill,
    RouteGuardSkill,
    SelfCheckSkill,
    SqlQualitySkill,
    TemplatePolicySkill,
)


class AdvancedAskService:
    """
    Advanced ask engine shell.

    The upgraded path owns skill/tool orchestration and observability while the
    stable basic engine still produces the final report contract. Keep new ask
    upgrades here instead of changing four_agent_ask.py.
    """

    name = "advanced"

    def __init__(self, fallback_service=None):
        self.fallback_service = fallback_service or basic_ask_service

    @property
    def repository(self):
        return self.fallback_service.repository

    @staticmethod
    def _now() -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    @staticmethod
    def _has_skill(skills: List[Dict[str, Any]], key: str) -> bool:
        return any(item.get("key") == key for item in skills or [])

    @staticmethod
    def _skill_enabled_map(skills: List[Dict[str, Any]]) -> Dict[str, bool]:
        return {str(item.get("key") or ""): True for item in skills or []}

    def _emit(
        self,
        live_callback,
        *,
        trace_id: str,
        question: str,
        stage: str,
        status: str = "info",
        title: str = "",
        summary: str = "",
        detail_lines: List[str] | None = None,
        thought: str = "",
        tool_type: str = "default",
        started: float | None = None,
        **payload: Any,
    ) -> None:
        if not live_callback:
            return
        event = {
            "time": self._now(),
            "stage": stage,
            "status": status,
            "title": title,
            "summary": summary,
            "detailLines": detail_lines or [],
            "thought": thought,
            "toolType": tool_type,
        }
        if started:
            event["duration_seconds"] = round(time.time() - started, 3)
        event.update(payload)
        try:
            live_callback(
                {
                    "type": "trace",
                    "trace_id": trace_id,
                    "entry": "advanced.ask",
                    "question": question,
                    "event": event,
                }
            )
        except Exception:
            pass

    @staticmethod
    def _short_lines(values: List[str], limit: int = 5) -> List[str]:
        result = []
        for value in values or []:
            text = str(value or "").strip()
            if text and text not in result:
                result.append(text)
            if len(result) >= limit:
                break
        return result

    @staticmethod
    def _prioritize_candidates_by_guard(candidates: List[Dict[str, Any]], route_guard: Dict[str, Any]) -> List[Dict[str, Any]]:
        recommended = []
        for value in (route_guard or {}).get("recommended_dataset_ids") or []:
            try:
                current = int(value)
            except Exception:
                continue
            if current not in recommended:
                recommended.append(current)
        if not recommended:
            return candidates
        by_id = {int(item.get("id") or 0): item for item in candidates or [] if item.get("id") is not None}
        ordered = [by_id[item] for item in recommended if item in by_id]
        ordered.extend([item for item in candidates or [] if int(item.get("id") or 0) not in set(recommended)])
        return ordered

    def _ensure_guard_candidates(self, candidates: List[Dict[str, Any]], route_guard: Dict[str, Any]) -> List[Dict[str, Any]]:
        recommended = []
        for value in (route_guard or {}).get("recommended_dataset_ids") or (route_guard or {}).get("apply_dataset_ids") or []:
            try:
                current = int(value)
            except Exception:
                continue
            if current not in recommended:
                recommended.append(current)
        existing = {int(item.get("id") or 0) for item in candidates or []}
        missing = [item for item in recommended if item not in existing]
        if not missing:
            return candidates
        try:
            catalog = self.repository.get_agent1_catalog()
        except Exception:
            return candidates
        catalog_by_id = {int(item.get("id") or 0): item for item in catalog if item.get("id") is not None}
        appended = []
        for dataset_id in missing:
            item = catalog_by_id.get(dataset_id)
            if item:
                appended.append({**item, "advanced_score": 1000, "advanced_reason": "organization_route_guard"})
        return appended + list(candidates or [])

    @staticmethod
    def _cross_dataset_execution_question(question: str, route_guard: Dict[str, Any]) -> str:
        if (route_guard or {}).get("action") != "cross_dataset_compare":
            return question
        org_route = (route_guard or {}).get("organization_route") or {}
        mentions = []
        for item in org_route.get("organization_mentions") or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("node_name") or "").strip()
            dataset_names = " / ".join(str(value) for value in (item.get("dataset_names") or []) if str(value).strip())
            if name:
                mentions.append(f"{name}{f'（{dataset_names}）' if dataset_names else ''}")
        mention_text = "、".join(dict.fromkeys(mentions))
        instruction = (
            "进阶跨数据集对比执行约束：本轮问题明确要求跨多个事业部/组织口径对比。"
            "请在每个命中的数据集内分别查询该数据集对应事业部的整体进度、达成率、总任务、实际完成和缺口；"
            "不要要求单个数据集同时包含另一个事业部名称；最终按各数据集结果并列对比。"
        )
        if mention_text:
            instruction += f" 命中组织与数据集：{mention_text}。"
        return f"{question}\n{instruction}".strip()

    @staticmethod
    def _cross_dataset_metric_suffix(question: str) -> str:
        text = re.sub(r"\s+", "", str(question or ""))
        if not text:
            return "业绩"
        for pattern in [
            r"(目标达成(?:情况|进度|表现)?)",
            r"(达成率|完成率)",
            r"(开单金额|开单)",
            r"(任务金额|总任务|任务)",
            r"(业绩(?:情况|表现|进度)?)",
            r"(进度|表现|情况)",
        ]:
            match = re.search(pattern, text)
            if match:
                return str(match.group(1) or "").strip() or "业绩"
        return "业绩"

    def _cross_dataset_subject_queries(self, question: str, route_guard: Dict[str, Any]) -> List[Dict[str, Any]]:
        route = (route_guard or {}).get("organization_route") or {}
        suffix = self._cross_dataset_metric_suffix(question)
        subject_queries: List[Dict[str, Any]] = []
        seen_pairs = set()
        for item in route.get("organization_mentions") or []:
            if not isinstance(item, dict):
                continue
            subject_name = str(item.get("node_name") or "").strip()
            if not subject_name:
                continue
            query_text = f"{subject_name}的{suffix}" if suffix else f"{subject_name}的业绩"
            for dataset_id in item.get("dataset_ids") or []:
                try:
                    current_dataset_id = int(dataset_id)
                except Exception:
                    continue
                pair = (current_dataset_id, subject_name)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                subject_queries.append(
                    {
                        "dataset_id": current_dataset_id,
                        "subject_name": subject_name,
                        "query": query_text,
                    }
                )
        return subject_queries

    @staticmethod
    def _pick_cross_dataset_payload(result: Dict[str, Any], dataset_id: int, subject_name: str, sub_query: str) -> Dict[str, Any]:
        payload = None
        dataset_results = result.get("dataset_results") if isinstance(result, dict) else []
        if isinstance(dataset_results, list):
            for item in dataset_results:
                if not isinstance(item, dict):
                    continue
                try:
                    current_dataset_id = int(item.get("dataset_id") or item.get("id") or 0)
                except Exception:
                    current_dataset_id = 0
                if current_dataset_id == dataset_id:
                    payload = dict(item)
                    break
            if payload is None and dataset_results and isinstance(dataset_results[0], dict):
                payload = dict(dataset_results[0])
        if payload is None:
            payload = {
                "dataset_id": dataset_id,
                "dataset_name": "",
                "analysis": str((result or {}).get("analysis") or "").strip(),
                "columns": (result or {}).get("columns") or [],
                "rows": (result or {}).get("rows") or [],
                "row_count": (result or {}).get("row_count") or 0,
                "sql": (result or {}).get("sql") or "",
                "report_spec": (result or {}).get("report_spec") or {},
            }
        payload["dataset_id"] = payload.get("dataset_id") or dataset_id
        payload["comparison_subject_name"] = str(payload.get("comparison_subject_name") or subject_name).strip()
        payload["advanced_subject_query"] = sub_query
        return payload

    def _execute_cross_dataset_compare(
        self,
        question: str,
        fallback_kwargs: Dict[str, Any],
        route_guard: Dict[str, Any],
    ) -> Dict[str, Any]:
        subject_queries = self._cross_dataset_subject_queries(question, route_guard)
        if not subject_queries:
            fallback_kwargs["question"] = self._cross_dataset_execution_question(question, route_guard)
            return self.fallback_service.ask(**fallback_kwargs)

        merged_dataset_results: List[Dict[str, Any]] = []
        merged_analyses: List[str] = []
        errors: List[str] = []
        first_result: Dict[str, Any] | None = None
        for item in subject_queries:
            dataset_id = int(item["dataset_id"])
            subject_name = str(item.get("subject_name") or "").strip()
            sub_query = str(item.get("query") or question)
            sub_kwargs = dict(fallback_kwargs)
            sub_kwargs["question"] = sub_query
            sub_kwargs["preferred_dataset_ids"] = [dataset_id]
            result = self.fallback_service.ask(**sub_kwargs)
            if first_result is None and isinstance(result, dict):
                first_result = result
            if not isinstance(result, dict):
                errors.append(f"dataset_{dataset_id}: empty_result")
                continue
            analysis = str(result.get("analysis") or "").strip()
            if analysis and analysis not in merged_analyses:
                merged_analyses.append(analysis)
            if result.get("error"):
                errors.append(f"dataset_{dataset_id}: {result.get('error')}")
            merged_dataset_results.append(self._pick_cross_dataset_payload(result, dataset_id, subject_name, sub_query))

        merged: Dict[str, Any] = dict(first_result or {})
        merged["question"] = question
        merged["route"] = {
            "intent": "comparison",
            "dataset_ids": [int(item["dataset_id"]) for item in subject_queries],
            "organization_mentions": ((route_guard or {}).get("organization_route") or {}).get("organization_mentions") or [],
            "preferred_dataset_override": False,
        }
        merged["dataset_results"] = merged_dataset_results
        merged["analysis"] = "\n\n".join(merged_analyses).strip()
        merged["advanced_execution_question"] = {
            "mode": "cross_dataset_split",
            "queries": [
                {
                    "dataset_id": int(item["dataset_id"]),
                    "subject_name": item.get("subject_name"),
                    "query": item.get("query"),
                }
                for item in subject_queries
            ],
        }
        merged["requires_confirmation"] = False
        if merged_dataset_results:
            merged.pop("error", None)
        elif errors:
            merged["error"] = "；".join(errors)
        merged.setdefault("diagnostics", {})
        if isinstance(merged.get("diagnostics"), dict):
            merged["diagnostics"]["cross_dataset_execution"] = {
                "mode": "split_subject_queries",
                "queries": [
                    {
                        "dataset_id": int(item["dataset_id"]),
                        "subject_name": item.get("subject_name"),
                        "query": item.get("query"),
                    }
                    for item in subject_queries
                ],
                "errors": errors,
            }
        if not str(merged.get("final_answer") or "").strip():
            merged["final_answer"] = merged.get("analysis") or ""
        return merged

    @staticmethod
    def _number_value(value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value) if value == value else None
        text = str(value or "").strip()
        if not text:
            return None
        cleaned = re.sub(r"[^0-9.\-]", "", text)
        if not cleaned:
            return None
        try:
            number = float(cleaned)
        except Exception:
            return None
        if "亿" in text:
            number *= 100000000
        elif "万" in text:
            number *= 10000
        return number

    @staticmethod
    def _format_amount(value: Any) -> str:
        number = AdvancedAskService._number_value(value)
        if number is None:
            return ""
        abs_value = abs(number)
        if abs_value >= 100000000:
            return f"{number / 100000000:.2f}".rstrip("0").rstrip(".") + "亿"
        if abs_value >= 10000:
            return f"{number / 10000:.1f}".rstrip("0").rstrip(".") + "万"
        return f"{number:.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _format_rate(value: Any) -> str:
        number = AdvancedAskService._number_value(value)
        if number is None:
            return ""
        return f"{number:.2f}".rstrip("0").rstrip(".") + "%"

    @staticmethod
    def _kpi_value(dataset: Dict[str, Any], tokens: List[str]) -> Any:
        spec = dataset.get("report_spec") if isinstance(dataset.get("report_spec"), dict) else {}
        for item in spec.get("kpis") or []:
            if not isinstance(item, dict):
                continue
            text = f"{item.get('key', '')}{item.get('label', '')}"
            if any(token in text for token in tokens):
                return item.get("value") if item.get("value") is not None else item.get("displayValue")
        return None

    @staticmethod
    def _row_value(dataset: Dict[str, Any], tokens: List[str]) -> Any:
        rows = dataset.get("rows") if isinstance(dataset.get("rows"), list) else []
        if not rows:
            return None
        row = rows[0] if isinstance(rows[0], dict) else {}
        for key, value in row.items():
            text = str(key or "")
            if any(token in text for token in tokens):
                return value
        return None

    def _dataset_metric(self, dataset: Dict[str, Any], tokens: List[str]) -> float | None:
        overview = dataset.get("cross_dataset_subject_overview") if isinstance(dataset.get("cross_dataset_subject_overview"), dict) else {}
        overview_map = {
            "task": ["总任务", "任务金额", "目标", "task"],
            "actual": ["年度开单", "开单金额", "开单", "完成", "实际", "actual"],
            "rate": ["达成率", "完成率", "rate", "percent"],
            "remain": ["剩余", "缺口", "差额", "remain", "gap"],
        }
        for key, aliases in overview_map.items():
            if any(token in aliases for token in tokens):
                value = self._number_value(overview.get(key))
                if value is not None:
                    return value
                break
        return self._number_value(self._kpi_value(dataset, tokens) or self._row_value(dataset, tokens))

    @staticmethod
    def _dataset_subject_map(route_guard: Dict[str, Any] | None) -> Dict[int, str]:
        route = (route_guard or {}).get("organization_route") or {}
        result: Dict[int, str] = {}
        for item in route.get("organization_mentions") or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("node_name") or "").strip()
            if not name:
                continue
            for dataset_id in item.get("dataset_ids") or []:
                try:
                    result[int(dataset_id)] = name
                except Exception:
                    continue
        return result

    def _dataset_overview(self, dataset: Dict[str, Any], subject_map: Dict[int, str] | None = None) -> Dict[str, Any]:
        task = self._dataset_metric(dataset, ["总任务", "任务金额", "目标", "task"])
        actual = self._dataset_metric(dataset, ["年度开单", "开单金额", "开单", "完成", "实际", "actual"])
        rate = self._dataset_metric(dataset, ["达成率", "完成率", "rate", "percent"])
        remain = self._dataset_metric(dataset, ["剩余", "缺口", "差额", "remain", "gap"])
        if rate is None and task:
            rate = (actual or 0) / task * 100
        if remain is None and task is not None and actual is not None:
            remain = task - actual
        try:
            dataset_id = int(dataset.get("dataset_id") or dataset.get("id") or 0)
        except Exception:
            dataset_id = 0
        return {
            "dataset_id": dataset.get("dataset_id"),
            "name": str((subject_map or {}).get(dataset_id) or dataset.get("comparison_subject_name") or dataset.get("dataset_name") or "当前主体").strip(),
            "task": task,
            "actual": actual,
            "rate": rate,
            "remain": remain,
        }

    @staticmethod
    def _infer_subject_level(name: str) -> str:
        text = str(name or "").strip()
        if "事业部" in text:
            return "事业部"
        if "分公司" in text:
            return "分公司"
        if "业务部" in text:
            return "业务部"
        if "代表处" in text:
            return "代表处"
        if "业务代表" in text or "业务员" in text:
            return "业务代表"
        return "对象"

    def _build_subject_overview_from_rows(
        self,
        dataset: Dict[str, Any],
        subject_name: str,
        subject_level: str,
    ) -> Dict[str, Any]:
        rows = dataset.get("rows") if isinstance(dataset.get("rows"), list) else []
        if not rows or not subject_name:
            return {}

        normalized_level = str(subject_level or "").strip()
        candidates = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            node_name = str(row.get("节点名称") or "").strip()
            if node_name != subject_name:
                continue
            level = str(row.get("层级") or row.get("层级级别") or "").strip()
            track = str(row.get("条线") or "").strip()
            score = 0
            if normalized_level and level == normalized_level:
                score += 6
            if row.get("上级名称") in {None, ""}:
                score += 4
            if normalized_level and normalized_level in track:
                score += 3
            if "总体" in level or "总体" in track:
                score += 2
            candidates.append((score, row))

        if not candidates:
            return {}

        # 同一主体可能因为条线/汇总视图出现多行，同名根节点优先按层级和空上级打分，
        # 再用任务/实际金额排序，尽量选中最完整的主体总览行。
        best_row = sorted(
            candidates,
            key=lambda item: (
                item[0],
                self._number_value(item[1].get("总任务金额")) or -1,
                self._number_value(item[1].get("年度开单金额")) or -1,
                self._number_value(item[1].get("达成率")) or -1,
            ),
            reverse=True,
        )[0][1]

        task = self._number_value(best_row.get("总任务金额"))
        actual = self._number_value(best_row.get("年度开单金额"))
        rate = self._number_value(best_row.get("达成率"))
        remain = self._number_value(best_row.get("剩余任务金额"))
        if rate is None and task:
            rate = (actual or 0) / task * 100
        if remain is None and task is not None and actual is not None:
            remain = task - actual

        return {
            "name": subject_name,
            "level": normalized_level or self._infer_subject_level(subject_name),
            "task": task,
            "actual": actual,
            "rate": rate,
            "remain": remain,
            "row": best_row,
        }

    def _enrich_cross_dataset_subject_overviews(self, result: Dict[str, Any], route_guard: Dict[str, Any] | None = None) -> None:
        datasets = result.get("dataset_results") if isinstance(result, dict) else []
        if not isinstance(datasets, list) or len(datasets) < 2:
            return
        subject_map = self._dataset_subject_map(route_guard)
        for dataset in datasets:
            if not isinstance(dataset, dict):
                continue
            try:
                dataset_id = int(dataset.get("dataset_id") or dataset.get("id") or 0)
            except Exception:
                dataset_id = 0
            subject_name = str(subject_map.get(dataset_id) or dataset.get("comparison_subject_name") or "").strip()
            if not subject_name:
                continue
            subject_level = str(dataset.get("comparison_subject_level") or self._infer_subject_level(subject_name)).strip()
            dataset["comparison_subject_name"] = subject_name
            dataset["comparison_subject_level"] = subject_level
            overview = self._build_subject_overview_from_rows(dataset, subject_name, subject_level)
            if overview:
                dataset["cross_dataset_subject_overview"] = overview

    def _build_cross_dataset_conclusion(self, result: Dict[str, Any], route_guard: Dict[str, Any] | None = None) -> Dict[str, Any]:
        datasets = result.get("dataset_results") if isinstance(result, dict) else []
        subject_map = self._dataset_subject_map(route_guard)
        overviews = [
            item for item in (self._dataset_overview(dataset, subject_map) for dataset in datasets or [])
            if item.get("task") is not None or item.get("actual") is not None or item.get("rate") is not None
        ]
        if len(overviews) < 2:
            return {}

        ranked = sorted(
            overviews,
            key=lambda item: item.get("rate") if item.get("rate") is not None else -1,
            reverse=True,
        )
        leader = ranked[0]
        pressure = ranked[-1]
        lines = []
        if leader.get("rate") is not None and pressure.get("rate") is not None and leader["name"] != pressure["name"]:
            diff = abs(float(leader["rate"]) - float(pressure["rate"]))
            diff_text = f"{diff:.2f}".rstrip("0").rstrip(".")
            lines.append(
                f"{leader['name']}达成率{self._format_rate(leader['rate'])}，"
                f"高于{pressure['name']}{diff_text}个百分点"
            )
        actual_ranked = sorted(
            [item for item in overviews if item.get("actual") is not None],
            key=lambda item: item.get("actual") or 0,
            reverse=True,
        )
        if len(actual_ranked) >= 2:
            lines.append(
                f"{actual_ranked[0]['name']}开单{self._format_amount(actual_ranked[0]['actual'])}，"
                f"{actual_ranked[-1]['name']}开单{self._format_amount(actual_ranked[-1]['actual'])}"
            )
        task_ranked = sorted(
            [item for item in overviews if item.get("task") is not None],
            key=lambda item: item.get("task") or 0,
            reverse=True,
        )
        if len(task_ranked) >= 2:
            lines.append(
                f"任务体量分别为{task_ranked[0]['name']}{self._format_amount(task_ranked[0]['task'])}、"
                f"{task_ranked[-1]['name']}{self._format_amount(task_ranked[-1]['task'])}"
            )
        if not lines:
            return {}
        conclusion = "跨数据集对比结论：" + "；".join(lines) + "。"
        return {"conclusion": conclusion, "overviews": overviews}

    def _apply_cross_dataset_conclusion(self, result: Dict[str, Any], route_guard: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = self._build_cross_dataset_conclusion(result, route_guard)
        conclusion = str(payload.get("conclusion") or "").strip()
        if not conclusion:
            return payload
        prefix = f"## 跨数据集核心结论\n\n{conclusion}"
        result["analysis"] = f"{prefix}\n\n---\n\n{result.get('analysis') or ''}".strip()
        datasets = result.get("dataset_results") if isinstance(result.get("dataset_results"), list) else []
        if datasets and isinstance(datasets[0], dict):
            first_analysis = str(datasets[0].get("analysis") or "").strip()
            if conclusion not in first_analysis:
                datasets[0]["analysis"] = f"{prefix}\n\n{first_analysis}".strip()
        payload["applied"] = True
        return payload

    def _run_advanced_trace(self, question: str, preferred_dataset_ids, allowed_dataset_ids, live_callback) -> Dict[str, Any]:
        config = load_config()
        trace_id = str(uuid4())
        execution = config.get("execution") or {}
        emit_trace = bool(config.get("enabled")) and bool(execution.get("emitSkillTrace", True))
        live = live_callback if emit_trace else None
        context: Dict[str, Any] = {
            "trace_id": trace_id,
            "config": config,
            "skills": [],
            "candidates": [],
            "assets": [],
            "asset_contexts": {},
            "route_guard": {},
            "effective_preferred_dataset_ids": [],
            "allowed_dataset_ids": allowed_dataset_ids or [],
            "golden_sql": {},
            "intent": {},
            "enabled_map": {},
        }

        if not config.get("enabled"):
            return context

        started = time.time()
        skills = build_skill_plan(config)
        context["skills"] = skills
        context["enabled_map"] = self._skill_enabled_map(skills)
        preview_limit = int(execution.get("assetPreviewLimit") or 3)

        self._emit(
            live,
            trace_id=trace_id,
            question=question,
            stage="advanced.controller",
            status="request",
            title="进阶流程控制器",
            summary="正在装载进阶问数能力链路。",
            detail_lines=[
                "基础问数结果契约保持不变。",
                f"已启用 {len(skills)} 个 Skill/工具节点。",
            ],
            thought="先根据控制台配置装载进阶能力，再复用数据集资产组织执行链路。",
            tool_type="default",
            started=started,
            capability_summary=capability_summary(config),
        )

        if self._has_skill(skills, "dataset_route"):
            stage_started = time.time()
            candidates = DatasetRouteSkill(self.repository).run(question, preferred_dataset_ids, limit=preview_limit)
            context["candidates"] = candidates
            self._emit(
                live,
                trace_id=trace_id,
                question=question,
                stage="advanced.skill.dataset_route",
                status="response",
                title="数据集路由 Skill",
                summary=f"已识别 {len(candidates)} 个候选数据资产。",
                detail_lines=[
                    "按问题关键词、业务域、数据集别名与手动选择做综合匹配。",
                    "该节点只提供进阶链路的资产视角，不改变基础引擎最终选择。",
                    *[
                        f"{item.get('dataset_name') or item.get('dataset_code')}：资产匹配分 {item.get('advanced_score', 0)}"
                        for item in candidates[:preview_limit]
                    ],
                ],
                thought="用确定性资产打分解释自动路由，让用户能看到系统为什么优先考虑这些数据集。",
                tool_type="dataset",
                started=stage_started,
                candidates=[
                    {
                        "id": item.get("id"),
                        "dataset_name": item.get("dataset_name"),
                        "business_domain": item.get("business_domain"),
                        "score": item.get("advanced_score"),
                    }
                    for item in candidates
                ],
            )

        if self._has_skill(skills, "route_guard"):
            stage_started = time.time()
            route_guard = RouteGuardSkill(self.repository).run(
                question=question,
                candidates=context.get("candidates") or [],
                preferred_dataset_ids=preferred_dataset_ids,
                allowed_dataset_ids=context.get("allowed_dataset_ids") or None,
            )
            context["route_guard"] = route_guard
            context["effective_preferred_dataset_ids"] = route_guard.get("apply_dataset_ids") or []
            if route_guard.get("recommended_dataset_ids"):
                context["candidates"] = self._ensure_guard_candidates(context.get("candidates") or [], route_guard)
            org_route = route_guard.get("organization_route") or {}
            org_members = org_route.get("resolved_members") or []
            signal = route_guard.get("candidate_signal") or {}
            detail_lines = [
                route_guard.get("reason") or "已完成进阶路由守门判断。",
                f"守门动作：{route_guard.get('action')}，置信度：{route_guard.get('confidence')}",
            ]
            if route_guard.get("apply_dataset_ids"):
                detail_lines.append(f"进阶流程将受控锁定数据集 ID：{'、'.join(str(item) for item in route_guard.get('apply_dataset_ids') or [])}")
            if org_members:
                detail_lines.append(f"组织树命中：{'、'.join(str(item) for item in org_members[:5])}")
            if signal.get("top_dataset_name"):
                detail_lines.append(
                    f"语义候选：{signal.get('top_dataset_name')}，得分 {signal.get('top_score')}，领先 {signal.get('margin')}"
                )
            detail_lines.extend(route_guard.get("warnings") or [])
            self._emit(
                live,
                trace_id=trace_id,
                question=question,
                stage="advanced.skill.route_guard",
                status="warning" if route_guard.get("warnings") else "response",
                title="路由守门 Skill",
                summary=f"已完成路由守门判断：{route_guard.get('action')}",
                detail_lines=detail_lines,
                thought="参考数据集语义配置实践，优先使用可区分数据集的特征和组织树规则，避免无感知错绑数据源。",
                tool_type="dataset",
                started=stage_started,
                route_guard=route_guard,
            )

        if self._has_skill(skills, "asset_pack"):
            stage_started = time.time()
            candidates_for_asset = self._prioritize_candidates_by_guard(
                context.get("candidates") or [],
                context.get("route_guard") or {},
            )
            asset_pack = AssetPackSkill(self.repository).run(
                question,
                candidates_for_asset,
                limit=preview_limit,
            )
            assets = asset_pack.get("assets") or []
            context["assets"] = assets
            context["asset_contexts"] = asset_pack.get("contexts") or {}
            self._emit(
                live,
                trace_id=trace_id,
                question=question,
                stage="advanced.skill.asset_pack",
                status="response",
                title="资产打包 Skill",
                summary=f"已读取 {len(assets)} 个候选数据集的书架资产。",
                detail_lines=[
                    *[
                        (
                            f"{asset.get('dataset_name')}：字段 {asset.get('dictionary_count', 0)}，"
                            f"DDL {asset.get('schema_count', 0)}，Golden SQL {asset.get('golden_sql_count', 0)}，"
                            f"提示词 {asset.get('prompt_count', 0)}"
                        )
                        for asset in assets[:preview_limit]
                    ],
                    "资产包包含字段、DDL、LLD、Golden SQL、常见问题和 Agent 提示词。",
                ],
                thought="把企业沉淀的数据资产打包给进阶链路，而不是把用户问题限制在预设题库里。",
                tool_type="dataset",
                started=stage_started,
                assets=assets,
            )

        if self._has_skill(skills, "planner"):
            stage_started = time.time()
            intent = PlannerSkill.infer(question)
            context["intent"] = intent
            self._emit(
                live,
                trace_id=trace_id,
                question=question,
                stage="advanced.planner",
                status="response",
                title="任务规划 Planner",
                summary=f"已识别为 {intent.get('intent')} 类型问题。",
                detail_lines=[
                    f"问题意图：{intent.get('intent')}",
                    f"目标层级：{intent.get('targetLevel') or '未显式指定'}",
                    f"TopN：{intent.get('topN') or '未指定，跟随报告模板或默认 Top10'}",
                    "后续链路会优先保持组织层级、关键指标和风险信息完整。",
                ],
                thought="先判断用户真正要的业务动作，再让 SQL、Pandas 和报告节点围绕该动作组织分析。",
                tool_type="fact",
                started=stage_started,
                intent=intent,
            )

        if self._has_skill(skills, "golden_sql"):
            stage_started = time.time()
            golden_sql = GoldenSqlSkill.run(context.get("asset_contexts") or {})
            context["golden_sql"] = golden_sql
            examples = [
                item.get("question") or item.get("intent_type") or f"样例 {item.get('sample_id')}"
                for item in (golden_sql.get("top_samples") or [])
            ]
            self._emit(
                live,
                trace_id=trace_id,
                question=question,
                stage="advanced.skill.golden_sql",
                status="response",
                title="Golden SQL Skill",
                summary=f"已检索 {golden_sql.get('count', 0)} 条候选 Golden SQL。",
                detail_lines=[
                    "Golden SQL 用于提供可靠口径和 SQL 形态，不会限制用户只能问样例题。",
                    *[f"参考样例：{item}" for item in self._short_lines(examples, 3)],
                ],
                thought="把人工沉淀的好 SQL 当作可解释参照，而不是最终答案模板。",
                tool_type="sql",
                started=stage_started,
                golden_sql_count=golden_sql.get("count", 0),
                golden_sql=golden_sql,
            )

        builtin_stage_keys = {
            "dataset_route",
            "asset_pack",
            "planner",
            "golden_sql",
            "route_guard",
            "sql_generate",
            "sql_review",
            "sql_execute",
            "sql_quality",
            "template_policy",
            "pandas_analyze",
            "self_check",
            "answer_contract",
            "conclusion_advice",
            "evidence_vote",
            "report_compose",
        }
        for skill in [item for item in skills if item.get("custom") or item.get("key") not in builtin_stage_keys]:
            stage_started = time.time()
            detail_lines = [
                skill.get("description") or "导入 Skill 已装载为进阶链路节点。",
                "当前阶段只执行 Manifest 级编排和展示，不执行第三方代码。",
            ]
            if skill.get("source"):
                detail_lines.append(f"来源：{skill.get('source')}")
            if skill.get("safety"):
                detail_lines.append("已读取安全声明，后续执行前需要进入沙箱/审批链路。")
            self._emit(
                live,
                trace_id=trace_id,
                question=question,
                stage=skill.get("stage") or f"advanced.skill.custom.{skill.get('key')}",
                status="info",
                title=skill.get("label") or skill.get("key") or "导入 Skill",
                summary=f"已装载导入 Skill：{skill.get('label') or skill.get('key')}",
                detail_lines=detail_lines,
                thought=str(skill.get("prompt") or skill.get("instructions") or "导入 Skill 会作为进阶流程的提示和工具声明参与后续规划。")[:800],
                tool_type=str(skill.get("toolType") or "default"),
                started=stage_started,
                skill_manifest={
                    "key": skill.get("key"),
                    "label": skill.get("label"),
                    "toolType": skill.get("toolType"),
                    "source": skill.get("source"),
                    "tags": skill.get("tags") or [],
                },
            )

        extras = []
        if (config.get("mcp") or {}).get("enabled"):
            extras.append("MCP 工具已开启，将在后续版本接入外部工具调用。")
        if (config.get("sqlServer") or {}).get("enabled"):
            extras.append("SQL Server 工具已开启，将优先复用数据连接管理中的 SQL Server 数据源。")
        if extras:
            self._emit(
                live,
                trace_id=trace_id,
                question=question,
                stage="advanced.tooling",
                status="info",
                title="外部工具能力",
                summary="已读取 MCP/SQL Server 工具配置。",
                detail_lines=extras,
                thought="外部工具能力走配置化管理，避免把企业环境依赖写死进问数主链路。",
                tool_type="default",
                started=started,
            )

        self._emit(
            live,
            trace_id=trace_id,
            question=question,
            stage="advanced.handoff",
            status="response",
            title="交给稳定查询引擎",
            summary="进阶资产链路已准备完成，开始执行稳定问数引擎。",
            detail_lines=[
                "后续 SQL 生成、复核、执行继续由稳定引擎完成。",
                "查询返回后，进阶流程会追加 Pandas 加工、自检和报告契约核对。",
            ],
            thought="先让进阶链路提供更强上下文和可观测性，再保持结果交付稳定。",
            tool_type="default",
            started=started,
        )
        return context

    def _run_result_trace(
        self,
        *,
        question: str,
        result: Dict[str, Any],
        advanced_context: Dict[str, Any],
        live_callback,
    ) -> Dict[str, Any]:
        config = advanced_context.get("config") or {}
        if not config.get("enabled"):
            return {}

        skills = advanced_context.get("skills") or []
        execution = config.get("execution") or {}
        live = live_callback if execution.get("emitSkillTrace", True) else None
        trace_id = str(advanced_context.get("trace_id") or uuid4())
        intent = advanced_context.get("intent") or {}
        diagnostics: Dict[str, Any] = {}

        if self._has_skill(skills, "sql_quality"):
            stage_started = time.time()
            try:
                sql_quality = SqlQualitySkill().run(
                    result=result,
                    asset_contexts=advanced_context.get("asset_contexts") or {},
                )
                diagnostics["sql_quality"] = sql_quality
                warning_lines = [
                    item.get("message")
                    for item in (sql_quality.get("warnings") or [])
                    if isinstance(item, dict) and item.get("message")
                ]
                self._emit(
                    live,
                    trace_id=trace_id,
                    question=question,
                    stage="advanced.skill.sql_quality",
                    status="warning" if sql_quality.get("warning_count") else "response",
                    title="SQL 质量门 Skill",
                    summary=f"SQL 质量评分 {sql_quality.get('score', 0)}，发现 {sql_quality.get('warning_count', 0)} 个风险。",
                    detail_lines=self._short_lines(warning_lines, 8)
                    or ["SQL 只读安全、字段映射、表映射和首次结果质量检查通过。"],
                    thought="参考多路问数实践里“首次 SQL 结果质量最关键”的原则，先对稳定引擎返回的 SQL 与结果做质量门复核。",
                    tool_type="sql",
                    started=stage_started,
                    sql_quality_report=sql_quality,
                )
            except Exception as exc:
                diagnostics["sql_quality_error"] = str(exc)
                self._emit(
                    live,
                    trace_id=trace_id,
                    question=question,
                    stage="advanced.skill.sql_quality",
                    status="error",
                    title="SQL 质量门 Skill",
                    summary="SQL 质量检查失败，已保留基础报告结果。",
                    detail_lines=[str(exc)],
                    thought="质量门失败不阻断基础结果，先进诊断再逐步收紧。",
                    tool_type="sql",
                    started=stage_started,
                )

        if self._has_skill(skills, "template_policy"):
            stage_started = time.time()
            try:
                template_policy = TemplatePolicySkill().run(
                    question=question,
                    result=result,
                    intent=intent,
                )
                diagnostics["template_policy"] = template_policy
                if template_policy.get("expected_top_n") and not intent.get("topN"):
                    intent = {**intent, "topN": template_policy.get("expected_top_n")}
                warning_lines = [
                    item.get("message")
                    for item in (template_policy.get("warnings") or [])
                    if isinstance(item, dict) and item.get("message")
                ]
                suggestion_lines = [f"建议：{item}" for item in template_policy.get("suggestions") or []]
                visible = template_policy.get("visible") or {}
                self._emit(
                    live,
                    trace_id=trace_id,
                    question=question,
                    stage="advanced.skill.template_policy",
                    status="warning" if template_policy.get("warning_count") else "response",
                    title="模板策略 Skill",
                    summary=f"本轮 TopN 策略：Top{template_policy.get('expected_top_n')}，来源 {template_policy.get('source')}。",
                    detail_lines=self._short_lines(
                        [
                            f"报告配置 TopN：{template_policy.get('configured_top_n') or '未配置'}。",
                            f"queryIntent TopN：{template_policy.get('query_top_n') or '未生成'}。",
                            f"可见结构：图表 {visible.get('chart_rows', 0)} 行，卡片 {visible.get('accordion_count', 0)} 个。",
                        ]
                        + warning_lines
                        + suggestion_lines,
                        8,
                    ),
                    thought="模板策略作为进阶质量门，专门检查 TopN、报告模板和 queryIntent 是否一致，避免卡片展示被固定在 Top3。",
                    tool_type="report",
                    started=stage_started,
                    template_policy_report=template_policy,
                )
            except Exception as exc:
                diagnostics["template_policy_error"] = str(exc)
                self._emit(
                    live,
                    trace_id=trace_id,
                    question=question,
                    stage="advanced.skill.template_policy",
                    status="error",
                    title="模板策略 Skill",
                    summary="模板策略检查失败，已保留基础报告结果。",
                    detail_lines=[str(exc)],
                    thought="模板检查失败不改写最终报告。",
                    tool_type="report",
                    started=stage_started,
                )

        if self._has_skill(skills, "pandas_analyze"):
            stage_started = time.time()
            try:
                pandas_report = PandasAnalyzeSkill().run(result, intent=intent)
                diagnostics["pandas_analysis"] = pandas_report
                dataset_lines = [
                    item.get("summary")
                    for item in (pandas_report.get("datasets") or [])
                    if isinstance(item, dict) and item.get("summary")
                ]
                self._emit(
                    live,
                    trace_id=trace_id,
                    question=question,
                    stage="advanced.skill.pandas_analyze",
                    status="response",
                    title="Pandas 加工 Skill",
                    summary=f"已对 {len(pandas_report.get('datasets') or [])} 个结果集完成结构化加工。",
                    detail_lines=[
                        f"加工引擎：{pandas_report.get('engine')}",
                        *self._short_lines(dataset_lines, 5),
                    ],
                    thought="在不改写最终报告的前提下，对结果行做 TopN、汇总、缺口和风险辅助分析。",
                    tool_type="python",
                    started=stage_started,
                    pandas_report=pandas_report,
                )
            except Exception as exc:
                diagnostics["pandas_error"] = str(exc)
                self._emit(
                    live,
                    trace_id=trace_id,
                    question=question,
                    stage="advanced.skill.pandas_analyze",
                    status="error",
                    title="Pandas 加工 Skill",
                    summary="结果加工失败，已保留基础报告结果。",
                    detail_lines=[str(exc)],
                    thought="进阶加工失败也不能影响基础问数返回。",
                    tool_type="python",
                    started=stage_started,
                )

        if self._has_skill(skills, "answer_contract"):
            stage_started = time.time()
            pandas_report = diagnostics.get("pandas_analysis") or {}
            try:
                answer_contract = AnswerContractSkill().run(
                    question=question,
                    result=result,
                    pandas_report=pandas_report,
                    intent=intent,
                )
                diagnostics["answer_contract"] = answer_contract
                warning_lines = [
                    item.get("message")
                    for item in (answer_contract.get("warnings") or [])
                    if isinstance(item, dict) and item.get("message")
                ]
                suggestion_lines = [f"建议：{item}" for item in answer_contract.get("suggestions") or []]
                self._emit(
                    live,
                    trace_id=trace_id,
                    question=question,
                    stage="advanced.skill.answer_contract",
                    status="warning" if answer_contract.get("warning_count") else "response",
                    title="答案契约 Skill",
                    summary=f"已检查核心结论契约，发现 {answer_contract.get('warning_count', 0)} 个表达风险。",
                    detail_lines=self._short_lines(warning_lines + suggestion_lines, 8)
                    or ["核心结论表达顺序通过进阶契约检查。"],
                    thought="经营问数必须先回答用户真正问的问题，再展开证据、风险和明细。",
                    tool_type="report",
                    started=stage_started,
                    answer_contract_report=answer_contract,
                )
            except Exception as exc:
                diagnostics["answer_contract_error"] = str(exc)
                self._emit(
                    live,
                    trace_id=trace_id,
                    question=question,
                    stage="advanced.skill.answer_contract",
                    status="error",
                    title="答案契约 Skill",
                    summary="答案契约检查失败，已保留基础报告结果。",
                    detail_lines=[str(exc)],
                    thought="答案契约检查失败不改写最终报告。",
                    tool_type="report",
                    started=stage_started,
                )

        if self._has_skill(skills, "conclusion_advice"):
            stage_started = time.time()
            pandas_report = diagnostics.get("pandas_analysis") or {}
            answer_contract = diagnostics.get("answer_contract") or {}
            try:
                conclusion_advice = ConclusionAdviceSkill().run(
                    question=question,
                    intent=intent,
                    pandas_report=pandas_report,
                    answer_contract=answer_contract,
                )
                diagnostics["conclusion_advice"] = conclusion_advice
                detail_lines = []
                if conclusion_advice.get("suggested_conclusion"):
                    detail_lines.append(conclusion_advice.get("suggested_conclusion"))
                detail_lines.extend(conclusion_advice.get("bullets") or [])
                self._emit(
                    live,
                    trace_id=trace_id,
                    question=question,
                    stage="advanced.skill.conclusion_advice",
                    status="warning" if conclusion_advice.get("needs_rewrite") else "response",
                    title="结论建议 Skill",
                    summary="已基于结果证据生成核心结论建议。",
                    detail_lines=self._short_lines(detail_lines, 8) or ["当前报告核心结论无需额外重写建议。"],
                    thought="进阶流程先给出不改写报告的建议稿，后续可在灰度稳定后升级为自动结论重排。",
                    tool_type="report",
                    started=stage_started,
                    conclusion_advice_report=conclusion_advice,
                )
            except Exception as exc:
                diagnostics["conclusion_advice_error"] = str(exc)
                self._emit(
                    live,
                    trace_id=trace_id,
                    question=question,
                    stage="advanced.skill.conclusion_advice",
                    status="error",
                    title="结论建议 Skill",
                    summary="结论建议生成失败，已保留基础报告结果。",
                    detail_lines=[str(exc)],
                    thought="结论建议失败不改写最终报告。",
                    tool_type="report",
                    started=stage_started,
                )

        if self._has_skill(skills, "self_check"):
            stage_started = time.time()
            pandas_report = diagnostics.get("pandas_analysis") or {}
            try:
                check_report = SelfCheckSkill().run(
                    result=result,
                    assets=advanced_context.get("assets") or [],
                    pandas_report=pandas_report,
                    route_guard=advanced_context.get("route_guard") or {},
                )
                diagnostics["self_check"] = check_report
                warnings = check_report.get("warnings") or []
                warning_lines = [item.get("message") for item in warnings if isinstance(item, dict)]
                suggestion_lines = [f"建议：{item}" for item in check_report.get("suggestions") or []]
                mismatch_codes = {"asset_result_mismatch", "empty_rows", "empty_columns"}
                if any((item or {}).get("code") in mismatch_codes for item in warnings if isinstance(item, dict)):
                    suggestion_lines.insert(0, "数据集与业务场景可能不匹配，是否切换数据源？")
                self._emit(
                    live,
                    trace_id=trace_id,
                    question=question,
                    stage="advanced.skill.self_check",
                    status="warning" if check_report.get("warning_count") else "response",
                    title="结果自检 Skill",
                    summary=f"已完成结果自检，发现 {check_report.get('warning_count', 0)} 个风险提示。",
                    detail_lines=self._short_lines(warning_lines + suggestion_lines, 8)
                    or ["未发现高风险的数据集错配、空结果或红线异常。"],
                    thought="把空结果、路由错配和业务红线前置提示给用户，而不是静默产出空报告。",
                    tool_type="fact",
                    started=stage_started,
                    self_check_report=check_report,
                )
            except Exception as exc:
                diagnostics["self_check_error"] = str(exc)
                self._emit(
                    live,
                    trace_id=trace_id,
                    question=question,
                    stage="advanced.skill.self_check",
                    status="error",
                    title="结果自检 Skill",
                    summary="结果自检失败，已保留基础报告结果。",
                    detail_lines=[str(exc)],
                    thought="自检失败不影响最终问数结果。",
                    tool_type="fact",
                    started=stage_started,
                )

        if self._has_skill(skills, "evidence_vote"):
            stage_started = time.time()
            try:
                evidence_vote = EvidenceVoteSkill().run(
                    route_guard=advanced_context.get("route_guard") or {},
                    sql_quality=diagnostics.get("sql_quality") or {},
                    pandas_report=diagnostics.get("pandas_analysis") or {},
                    template_policy=diagnostics.get("template_policy") or {},
                    answer_contract=diagnostics.get("answer_contract") or {},
                    self_check=diagnostics.get("self_check") or {},
                )
                diagnostics["evidence_vote"] = evidence_vote
                vote_lines = [
                    f"{item.get('source')}：{item.get('decision')}（{item.get('weight')}）- {item.get('reason')}"
                    for item in evidence_vote.get("votes") or []
                ]
                warning_lines = [
                    item.get("message")
                    for item in evidence_vote.get("warnings") or []
                    if isinstance(item, dict) and item.get("message")
                ]
                self._emit(
                    live,
                    trace_id=trace_id,
                    question=question,
                    stage="advanced.skill.evidence_vote",
                    status="warning" if evidence_vote.get("decision") != "accept" else "response",
                    title="多信号择优 Skill",
                    summary=f"择优结论：{evidence_vote.get('decision')}，可信分 {evidence_vote.get('confidence_score')}。",
                    detail_lines=self._short_lines([evidence_vote.get("recommended_action") or ""] + warning_lines + vote_lines, 10),
                    thought="参考多路并行择优思想，把路由、SQL、结果、答案和自检信号汇总投票，形成本轮结果是否可采信的判断。",
                    tool_type="fact",
                    started=stage_started,
                    evidence_vote_report=evidence_vote,
                )
            except Exception as exc:
                diagnostics["evidence_vote_error"] = str(exc)
                self._emit(
                    live,
                    trace_id=trace_id,
                    question=question,
                    stage="advanced.skill.evidence_vote",
                    status="error",
                    title="多信号择优 Skill",
                    summary="多信号择优失败，已保留基础报告结果。",
                    detail_lines=[str(exc)],
                    thought="择优失败不影响最终报告。",
                    tool_type="fact",
                    started=stage_started,
                )

        if self._has_skill(skills, "report_compose"):
            stage_started = time.time()
            dataset_results = result.get("dataset_results") if isinstance(result, dict) else []
            primary = dataset_results[0] if dataset_results and isinstance(dataset_results[0], dict) else {}
            report_spec = result.get("report_spec") or primary.get("report_spec") if isinstance(result, dict) else None
            row_count = 0
            for item in dataset_results or []:
                if isinstance(item, dict) and isinstance(item.get("rows"), list):
                    row_count += len(item.get("rows") or [])
            contract = {
                "dataset_result_count": len(dataset_results or []),
                "row_count": row_count,
                "has_report_spec": bool(report_spec),
                "has_analysis": bool((result or {}).get("analysis") or primary.get("analysis")),
                "preserve_final_report_contract": True,
            }
            diagnostics["report_contract"] = contract
            self._emit(
                live,
                trace_id=trace_id,
                question=question,
                stage="advanced.skill.report_compose",
                status="response",
                title="报告组装 Skill",
                summary="已核对最终报告契约，报告展示继续沿用现有协议。",
                detail_lines=[
                    f"结果集：{contract['dataset_result_count']} 个，行数：{contract['row_count']} 行。",
                    f"report_spec：{'已生成' if contract['has_report_spec'] else '未生成'}。",
                    "报告结构和明细数据保持不变；跨数据集场景会补充对比总览结论。",
                ],
                thought="最终报告和现有前端保持一致，进阶流程只增强过程、可解释性和跨数据集结论。",
                tool_type="report",
                started=stage_started,
                report_contract=contract,
            )

        return diagnostics

    def ask(self, **kwargs) -> Dict[str, Any]:
        question = str(kwargs.get("question") or "")
        live_callback = kwargs.get("live_callback")
        preferred_dataset_ids = kwargs.get("preferred_dataset_ids")
        allowed_dataset_ids = kwargs.get("allowed_dataset_ids")
        try:
            advanced_context = self._run_advanced_trace(question, preferred_dataset_ids, allowed_dataset_ids, live_callback)
        except Exception as exc:
            trace_id = str(uuid4())
            self._emit(
                live_callback,
                trace_id=trace_id,
                question=question,
                stage="advanced.preflight_error",
                status="error",
                title="进阶预检异常",
                summary="进阶能力预检失败，已继续交给稳定基础引擎。",
                detail_lines=[str(exc), "该异常不会改变最终问数结果契约。"],
                thought="进阶链路必须可回退，不能因为工具预检影响基础问数。",
                tool_type="default",
                started=time.time(),
            )
            advanced_context = {
                "trace_id": trace_id,
                "config": {},
                "skills": [],
                "assets": [],
                "intent": {},
                "golden_sql": {},
                "route_guard": {},
                "error": str(exc),
            }

        fallback_kwargs = dict(kwargs)
        effective_dataset_ids = advanced_context.get("effective_preferred_dataset_ids") or []
        route_guard = advanced_context.get("route_guard") or {}
        if route_guard.get("action") == "needs_confirmation":
            org_route = route_guard.get("organization_route") or {}
            confirmation_options = org_route.get("confirmation_options") or []
            if not confirmation_options:
                recommended_ids = route_guard.get("recommended_dataset_ids") or []
                catalog = self.repository.get_agent1_catalog()
                by_id = {
                    int(item.get("id") or 0): item
                    for item in catalog
                    if int(item.get("id") or 0) > 0
                }
                confirmation_options = [
                    {
                        "id": f"dataset_{dataset_id}",
                        "label": str((by_id.get(int(dataset_id)) or {}).get("dataset_name") or f"数据集{dataset_id}"),
                        "description": "按该口径继续问数",
                        "dataset_ids": [int(dataset_id)],
                        "option_type": "dataset_disambiguation",
                        "confirmation_type": "dataset_disambiguation",
                        "resolved_members": [],
                        "resolved_dataset_name": str((by_id.get(int(dataset_id)) or {}).get("dataset_name") or f"数据集{dataset_id}"),
                    }
                    for dataset_id in recommended_ids
                    if int(dataset_id) > 0
                ]
            return {
                "question": question,
                "requires_confirmation": True,
                "confirmation_question": route_guard.get("reason") or "检测到当前问题存在统计口径歧义，请先确认后再继续执行。",
                "confirmation_options": confirmation_options,
                "dataset_results": [],
                "final_answer": "",
                "diagnostics": {
                    "advanced": {
                        "trace_id": advanced_context.get("trace_id"),
                        "route_guard": route_guard,
                        "effective_preferred_dataset_ids": effective_dataset_ids,
                        "cross_dataset_execution": False,
                        "preserve_final_report_contract": True,
                    }
                },
            }
        if effective_dataset_ids and not preferred_dataset_ids:
            fallback_kwargs["preferred_dataset_ids"] = effective_dataset_ids
        if route_guard.get("action") == "cross_dataset_compare":
            result = self._execute_cross_dataset_compare(question, fallback_kwargs, route_guard)
        else:
            result = self.fallback_service.ask(**fallback_kwargs)
        result_diagnostics: Dict[str, Any] = {}
        if isinstance(result, dict):
            if route_guard.get("action") == "cross_dataset_compare":
                result["question"] = question
                self._enrich_cross_dataset_subject_overviews(result, route_guard)
            try:
                result_diagnostics = self._run_result_trace(
                    question=question,
                    result=result,
                    advanced_context=advanced_context,
                    live_callback=live_callback,
                )
            except Exception as exc:
                result_diagnostics = {"result_trace_error": str(exc)}
            if route_guard.get("action") == "cross_dataset_compare":
                result_diagnostics["cross_dataset_conclusion"] = self._apply_cross_dataset_conclusion(result, route_guard)

            diagnostics = result.setdefault("diagnostics", {})
            if isinstance(diagnostics, dict):
                advanced_diagnostics = {
                    "trace_id": advanced_context.get("trace_id"),
                    "intent": advanced_context.get("intent"),
                    "asset_count": len(advanced_context.get("assets") or []),
                    "skill_count": len(advanced_context.get("skills") or []),
                    "assets": advanced_context.get("assets") or [],
                    "route_guard": advanced_context.get("route_guard") or {},
                    "effective_preferred_dataset_ids": effective_dataset_ids,
                    "cross_dataset_execution": route_guard.get("action") == "cross_dataset_compare",
                    "golden_sql": advanced_context.get("golden_sql") or {},
                    "preserve_final_report_contract": True,
                }
                if advanced_context.get("error"):
                    advanced_diagnostics["preflight_error"] = advanced_context.get("error")
                advanced_diagnostics.update(result_diagnostics)
                diagnostics["advanced"] = advanced_diagnostics
        return result

    def confirm_by_boss(self, **kwargs) -> Dict[str, Any]:
        live_callback = kwargs.get("live_callback")
        selected_option = str(kwargs.get("selected_option") or kwargs.get("session_id") or "")
        if live_callback:
            trace_id = str(uuid4())
            self._emit(
                live_callback,
                trace_id=trace_id,
                question=selected_option,
                stage="advanced.confirmation_handoff",
                status="info",
                title="进阶确认承接",
                summary="已收到确认口径，继续沿进阶流程承接执行。",
                detail_lines=[
                    "确认卡片和最终报告展示保持现有协议。",
                    "进阶流程会在后续节点继续补充 Skill 链路。",
                ],
                thought="用户确认的是业务口径，不改变最终报告契约。",
                tool_type="confirm",
                started=time.time(),
            )
        return self.fallback_service.confirm_by_boss(**kwargs)

    def route_with_agent1(self, *args, **kwargs) -> Dict[str, Any]:
        return self.fallback_service.route_with_agent1(*args, **kwargs)

    def write_controller_probe(self, payload: Dict[str, Any]) -> None:
        self.fallback_service.write_controller_probe(payload)


advanced_ask_service = AdvancedAskService()
