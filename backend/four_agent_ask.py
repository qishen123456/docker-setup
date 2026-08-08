import json
import logging
import math
import os
import random
import re
import sys
import time
import traceback
from difflib import get_close_matches
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

from openai import OpenAI

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from agent_registry import get_agent
import ask_engine_utils
from bookshelf_repository import BookshelfConfigurationError, BookshelfRepository
from config_manager import decode_secret, get_ai_models, get_default_ai_model
from dataset_copilot.syyb_rule_generator import BASE_SQL as SYYB_BASE_SQL
from disambiguation import DisambiguationArbiter
from datasource_router import router as datasource_router
from data_permission_store import apply_row_level_filter, load_data_permissions, org_mention_permission_check, user_org_scope_for_rule
from dataset_dimension_profiles import find_group_matches, get_dataset_profile, resolve_member_mentions
import dataset_report_config as report_config_store
from report_spec_builder import build_report_spec
from memory import ShortTermMemoryStore
from organization_route_resolver import OrganizationRouteResolver
from trace_logger import TraceLogger
from llm_client import LLMClient
from smartask_engine.intent import IntentResolver, IntentPorts


def _extract_json_block(text: str) -> str:
    if not text:
        return ""
    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1]
    return cleaned


class FourAgentAskService:
    def __init__(self):
        self.repository = BookshelfRepository()
        self._pending_confirmations: Dict[str, Dict[str, Any]] = {}
        self._pending_ttl_seconds = 30 * 60
        self.short_term_memory = ShortTermMemoryStore(max_rounds=8)
        self.disambiguation_arbiter = DisambiguationArbiter()
        self.organization_route_resolver = OrganizationRouteResolver()
        self._dataset_node_index = self._load_dataset_node_index()
        self._trace_file_path = os.path.join(CURRENT_DIR, "logs", "smartask_trace.jsonl")
        self.trace_logger = TraceLogger(self._trace_file_path)
        self._trace_logger = self._build_trace_logger()
        self.llm_client = self._build_llm_component()
        self._load_llm()
        self._intent_resolver = self._build_intent_resolver()

    def _build_intent_resolver(self) -> IntentResolver:
        ports = IntentPorts(
            safe_dict=self._safe_dict,
            safe_int=self._safe_int,
            normalize_chinese_numbers=self._normalize_chinese_numbers,
            rank_limit_match=self._rank_limit_match,
            parse_cn_int=self._parse_cn_int,
            resolved_entity_names=self._resolved_entity_names,
            question_subject_names=self._question_subject_names,
            is_dataset_root_name=FourAgentAskService._is_dataset_root_name,
            rank_request_spec=self._rank_request_spec,
            default_report_config=report_config_store.get_default_config,
            dataset_profile=get_dataset_profile,
        )
        return IntentResolver(ports)

    def _load_dataset_node_index(self) -> Dict[str, Any]:
        path = os.path.join(CURRENT_DIR, "..", "config", "dataset_node_index.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {"datasets": [], "flat_alias_index": []}

    def _trace_component(self) -> TraceLogger:
        component = getattr(self, "trace_logger", None)
        if component is None:
            file_path = getattr(
                self,
                "_trace_file_path",
                os.path.join(CURRENT_DIR, "logs", "smartask_trace.jsonl"),
            )
            component = TraceLogger(file_path)
            self.trace_logger = component
        return component

    def _build_llm_component(self) -> LLMClient:
        return LLMClient(
            openai_factory=OpenAI,
            get_default_config=get_default_ai_model,
            get_configs=get_ai_models,
            decode_secret=decode_secret,
            should_retry=ask_engine_utils._should_retry_with_another_model,
            append_trace=self._append_trace,
            append_llm_delta=self._append_llm_delta,
            extract_json_block=_extract_json_block,
            truncate_text=self._truncate_text,
        )

    def _llm_component(self) -> LLMClient:
        component = self.__dict__.get("llm_client")
        if component is None:
            component = self._build_llm_component()
            self.llm_client = component
        return component

    @property
    def _llm_client(self):
        return self._llm_component()._llm_client

    @_llm_client.setter
    def _llm_client(self, value) -> None:
        self._llm_component()._llm_client = value

    @property
    def _llm_model(self) -> Optional[str]:
        return self._llm_component()._llm_model

    @_llm_model.setter
    def _llm_model(self, value: Optional[str]) -> None:
        self._llm_component()._llm_model = value

    @property
    def _preferred_model_id(self) -> Optional[int]:
        return self._llm_component()._preferred_model_id

    @_preferred_model_id.setter
    def _preferred_model_id(self, value: Optional[int]) -> None:
        self._llm_component()._preferred_model_id = value

    def _build_trace_logger(self) -> logging.Logger:
        logger = logging.getLogger("smartask.trace")
        if logger.handlers:
            return logger
        logger.setLevel(logging.INFO)
        logger.propagate = False
        log_dir = os.path.join(CURRENT_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(log_dir, "smartask_trace.jsonl"), encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(file_handler)
        return logger

    @staticmethod
    def _mask_secret(value: str) -> str:
        return ask_engine_utils._mask_secret(value)

    @staticmethod
    def _truncate_text(value: Any, limit: int = 4000) -> str:
        return ask_engine_utils._truncate_text(value, limit)

    @staticmethod
    def _stream_preview(value: Any, limit: int = 1400) -> str:
        return ask_engine_utils._stream_preview(value, limit)

    def _new_trace(
        self,
        question: str,
        entry: str,
        live_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        return self._trace_component()._new_trace(
            question,
            entry,
            live_callback,
            model=self._llm_model or "",
            base_url=getattr(self._llm_client, "base_url", "") if self._llm_client else "",
        )

    def _write_trace_line(self, payload: Dict[str, Any]) -> None:
        return self._trace_component()._write_trace_line(payload)

    @staticmethod
    def _build_trace_snapshot(trace: Dict[str, Any], include_result: bool = False) -> Dict[str, Any]:
        return ask_engine_utils._build_trace_snapshot(trace, include_result)

    def _emit_live_trace(self, trace: Optional[Dict[str, Any]], payload: Dict[str, Any]) -> None:
        return self._trace_component()._emit_live_trace(trace, payload)

    @staticmethod
    def _build_route_thought(route: Dict[str, Any], question: str, catalog: List[Dict[str, Any]]) -> str:
        return ask_engine_utils._build_route_thought(route, question, catalog)

    def _append_trace(self, trace: Optional[Dict[str, Any]], stage: str, status: str = "info", **payload: Any) -> None:
        return self._trace_component()._append_trace(trace, stage, status, **payload)

    def _append_llm_delta(
        self,
        trace: Optional[Dict[str, Any]],
        stage: str,
        agent_name: str,
        delta_text: str,
        stream_text: str,
        started: float,
        reasoning_delta: str = "",
        reasoning_text: str = "",
        delta_kind: str = "content",
    ) -> None:
        return self._trace_component()._append_llm_delta(
            trace,
            stage,
            agent_name,
            delta_text,
            stream_text,
            started,
            reasoning_delta,
            reasoning_text,
            delta_kind,
        )

    def _stream_delta_value_to_text(self, value: Any) -> str:
        return self._llm_component()._stream_delta_value_to_text(value)

    def _extract_stream_delta(self, delta_obj: Any) -> Tuple[str, str]:
        return self._llm_component()._extract_stream_delta(delta_obj)

    def _flush_trace(self, trace: Optional[Dict[str, Any]], result: Optional[Dict[str, Any]] = None) -> None:
        return self._trace_component()._flush_trace(trace, result)

    def _load_llm(self):
        return self._llm_component()._load_llm()

    def _activate_llm(self, config: Dict[str, Any]) -> None:
        return self._llm_component()._activate_llm(config)

    def _candidate_llm_configs(self, preferred_model_id: Optional[int] = None) -> List[Dict[str, Any]]:
        return self._llm_component()._candidate_llm_configs(preferred_model_id)

    @staticmethod
    def _should_retry_with_another_model(exc: Exception) -> bool:
        return ask_engine_utils._should_retry_with_another_model(exc)

    @staticmethod
    def _safe_dict(value: Any) -> Dict[str, Any]:
        return ask_engine_utils._safe_dict(value)

    def _get_lld_content(self, context: Dict[str, Any]) -> str:
        lld_document = self._safe_dict(context.get("lld_document"))
        return str(lld_document.get("content") or "")

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        return ask_engine_utils._safe_int(value, default)

    @staticmethod
    def _parse_cn_int(value: Any, default: int = 0) -> int:
        return ask_engine_utils._parse_cn_int(value, default)

    @staticmethod
    def _rank_limit_match(text: str):
        return ask_engine_utils._rank_limit_match(text)

    def _rank_request_spec(self, text: str, default_limit: int = 0, max_limit: int = 20) -> Dict[str, Any]:
        text = str(text or "")
        top_match = re.search(r"(?:Top|TOP|top|前)\s*(\d+|[一二两三四五六七八九十]+)", text)
        bottom_match = re.search(r"(?:后|倒数|垫底|落后)(?:的)?\s*(\d+|[一二两三四五六七八九十]+)\s*(?:个|名|位|家)?", text)
        generic_match = self._rank_limit_match(text)

        top_limit = self._parse_cn_int(top_match.group(1), 0) if top_match else 0
        bottom_limit = self._parse_cn_int(bottom_match.group(1), 0) if bottom_match else 0

        # 兼容旧逻辑：没有明确前/后数量时，从通用匹配提取
        if not top_limit and not bottom_limit and generic_match:
            generic_limit = self._parse_cn_int(generic_match.group(1), default_limit)
            if re.search(r"(?:后|倒数|最低|最差|垫底)", text):
                bottom_limit = generic_limit
            else:
                top_limit = generic_limit

        top_requested = bool(top_match or re.search(r"(?:Top|TOP|top|最高|最好|第\s*(?:\d+|[一二两三四五六七八九十]+)\s*(?:名|位)?)", text))
        bottom_requested = bool(bottom_match or re.search(r"(?:倒数|最低|最差|垫底)", text))

        effective_limit = max(top_limit, bottom_limit) or default_limit
        if effective_limit:
            effective_limit = max(1, min(max_limit, effective_limit))
        if top_limit:
            top_limit = max(1, min(max_limit, top_limit))
        if bottom_limit:
            bottom_limit = max(1, min(max_limit, bottom_limit))

        return {
            "limit": effective_limit,
            "top_limit": top_limit,
            "bottom_limit": bottom_limit,
            "sides": "both" if top_requested and bottom_requested else ("bottom" if bottom_requested else "top"),
            "direction": "asc" if bottom_requested and not top_requested else "desc",
        }

    @staticmethod
    def _build_ranked_select_sql(
        *,
        source_cte: str,
        source_name: str,
        output_cte: str,
        where_clause: str,
        metric_column: str,
        direction: str,
        rank_limit: int,
        rank_sides: str = "",
        top_rank_limit: int = 0,
        bottom_rank_limit: int = 0,
        tie_breaker: str = "剩余任务金额 DESC, 节点名称",
    ) -> str:
        return ask_engine_utils._build_ranked_select_sql(
            source_cte=source_cte,
            source_name=source_name,
            output_cte=output_cte,
            where_clause=where_clause,
            metric_column=metric_column,
            direction=direction,
            rank_limit=rank_limit,
            rank_sides=rank_sides,
            top_rank_limit=top_rank_limit,
            bottom_rank_limit=bottom_rank_limit,
            tie_breaker=tie_breaker,
        )

    @staticmethod
    def _normalize_chinese_numbers(text: str) -> str:
        return ask_engine_utils._normalize_chinese_numbers(text)

    def _resolve_query_intent(self, question: str, context: Dict[str, Any]) -> Dict[str, Any]:
        resolver = getattr(self, "_intent_resolver", None)
        if resolver is None:
            resolver = self._build_intent_resolver()
            self._intent_resolver = resolver
        return resolver.resolve(question, context)

    @staticmethod
    def _normalize_prompt_items(items: Any) -> List[Dict[str, Any]]:
        return ask_engine_utils._normalize_prompt_items(items)

    @staticmethod
    def _is_read_only_sql(sql_text: str) -> bool:
        return ask_engine_utils._is_read_only_sql(sql_text)

    def _dataset_field_validation(self, sql_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        dictionary = context.get("data_dictionary") or []
        schema_definitions = context.get("schema_definition") or []
        allowed_jsonb_keys = {
            str(item.get("jsonb_key") or "").strip()
            for item in dictionary
            if str(item.get("jsonb_key") or "").strip()
        }
        allowed_tables = set()
        for item in dictionary:
            table_name = str(item.get("table_name") or "").strip()
            if table_name:
                allowed_tables.add(table_name.lower())
                allowed_tables.add(table_name.split(".")[-1].lower())
        for item in schema_definitions:
            table_name = str(item.get("table_name") or "").strip()
            if table_name:
                allowed_tables.add(table_name.lower())
                allowed_tables.add(table_name.split(".")[-1].lower())

        risks: List[str] = []
        fixes: List[str] = []
        used_jsonb_keys = sorted(set(re.findall(r"\bfields\s*(?:->>|->)\s*'([^']+)'", str(sql_text or ""))))
        if allowed_jsonb_keys:
            missing_keys = [key for key in used_jsonb_keys if key not in allowed_jsonb_keys]
            for key in missing_keys:
                suggestions = get_close_matches(key, sorted(allowed_jsonb_keys), n=3, cutoff=0.45)
                suffix = f"，可用相近字段：{'、'.join(suggestions)}" if suggestions else ""
                risks.append(f"SQL 引用了字段字典不存在的 JSONB 字段：{key}{suffix}")
            if missing_keys:
                fixes.append("请按数据集字段字典修改 fields ->> '字段名' / fields -> '字段名'，不要让 Agent3 猜测或改写字段。")

        qualified_tables = sorted(set(
            item.lower()
            for item in re.findall(r"\b(?:from|join)\s+((?:[a-zA-Z_][\w]*\.)[a-zA-Z_][\w]*)", str(sql_text or ""), flags=re.I)
        ))
        if allowed_tables:
            missing_tables = [table for table in qualified_tables if table not in allowed_tables and table.split(".")[-1] not in allowed_tables]
            if missing_tables:
                risks.extend(f"SQL 引用了当前数据集未登记的数据表：{table}" for table in missing_tables)
                fixes.append("请确认 SQL 只访问当前数据集 schema_definition 中登记的数据表。")

        return {
            "ok": not risks,
            "risks": risks,
            "fixes": fixes,
            "used_jsonb_keys": used_jsonb_keys,
            "allowed_jsonb_count": len(allowed_jsonb_keys),
            "qualified_tables": qualified_tables,
        }

    def _build_field_validation_block_review(
        self,
        validation: Dict[str, Any],
        sql_text: str,
        trace: Optional[Dict[str, Any]],
        review_policy: str,
    ) -> Dict[str, Any]:
        summary = "SQL 字段校验失败：存在当前数据集未登记的表或 fields JSONB 字段，已阻断执行。"
        self._append_trace(
            trace,
            "agent3.sql_review.field_validation_blocked",
            "error",
            review_policy=review_policy,
            review_summary=summary,
            risks=validation.get("risks", []),
            fixes=validation.get("fixes", []),
            used_jsonb_keys=validation.get("used_jsonb_keys", []),
            sql=self._truncate_text(sql_text, 12000),
        )
        return {
            "approved": False,
            "final_sql": "",
            "review_summary": summary,
            "risks": validation.get("risks", []),
            "fixes": validation.get("fixes", []),
        }

    @staticmethod
    def _build_confirmation_option(
        option_id: str,
        label: str,
        description: str = "",
        dataset_ids: Optional[List[int]] = None,
        option_type: str = "dataset_scope",
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return ask_engine_utils._build_confirmation_option(option_id, label, description, dataset_ids, option_type, extra)

    def _normalize_confirmation_options(
        self,
        options: Any,
        candidate_ids: Optional[List[int]] = None,
        candidate_names: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        normalized = []
        ids = [int(item) for item in (candidate_ids or [])]
        names = candidate_names or []

        for index, option in enumerate(options or []):
            if isinstance(option, dict):
                extra = {
                    key: value
                    for key, value in option.items()
                    if key not in {"id", "label", "text", "name", "description", "dataset_ids", "option_type"}
                }
                normalized.append(
                    self._build_confirmation_option(
                        option_id=str(option.get("id") or f"option_{index + 1}"),
                        label=str(option.get("label") or option.get("text") or option.get("name") or f"选项 {index + 1}"),
                        description=str(option.get("description") or ""),
                        dataset_ids=option.get("dataset_ids") or [],
                        option_type=str(option.get("option_type") or "dataset_scope"),
                        extra=extra,
                    )
                )
                continue

            label = str(option or f"选项 {index + 1}").strip()
            if not label:
                continue

            dataset_ids = []
            option_type = "dataset_scope"
            description = ""

            if "跨数据集" in label:
                dataset_ids = ids[:2] if len(ids) >= 2 else ids[:]
                option_type = "cross_dataset"
                description = "同时基于多个候选数据集进行汇总分析。"
            elif index < len(ids):
                dataset_ids = [ids[index]]
                dataset_name = names[index] if index < len(names) else f"数据集 {ids[index]}"
                description = f"优先基于 {dataset_name} 的口径继续执行。"
            elif ids:
                dataset_ids = [ids[0]]

            normalized.append(
                self._build_confirmation_option(
                    option_id=f"option_{index + 1}",
                    label=label,
                    description=description,
                    dataset_ids=dataset_ids,
                    option_type=option_type,
                )
            )

        return normalized

    def _build_fallback_analysis(
        self,
        question: str,
        context: Dict[str, Any],
        review: Dict[str, Any],
        result: Dict[str, Any],
        error_message: str = "",
    ) -> str:
        dataset = self._safe_dict(context.get("dataset"))
        dataset_name = dataset.get("dataset_name") or "当前数据集"
        row_count = int(result.get("row_count") or 0)
        columns = result.get("columns") or []
        rows = result.get("rows") or []
        review_summary = str((review or {}).get("review_summary") or "").strip()

        layered = self._build_layered_management_report(
            question,
            dataset_name,
            rows,
            columns,
            review_summary,
            error_message,
            self._safe_dict(context.get("report_config")) or report_config_store.get_default_config(),
            self._safe_dict(context.get("resolved_entities")),
            self._safe_dict(context.get("query_intent")),
        )
        if layered:
            return layered

        if row_count <= 0:
            route = self._safe_dict(context.get("route"))
            route_confidence = self._build_route_confidence(route) if route else {}
            lines = [
                "## 业绩分析报告",
                "",
                "### 核心结论",
                f"本次围绕“{question or dataset_name}”未查询到匹配数据，暂不能判断业绩好坏。",
                "",
                "### 问题诊断",
                "• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。",
            ]
            if route_confidence:
                lines.append(
                    f"• **痛点：** 数据集口径 -> 当前命中“{dataset_name}”，路由把握为{route_confidence.get('label')}，"
                    "若问题中的组织属于其他事业部，请切换数据源后重试。"
                )
            if review_summary:
                lines.append(f"• **痛点：** SQL复核 -> {review_summary} -> SQL 语法通过不代表业务过滤条件一定命中数据。")
            if error_message:
                lines.append(f"• **痛点：** 执行链路 -> 生成失败 -> 已退回无结果诊断，原因：{error_message}")
            lines.extend(
                [
                    "",
                    "### 改进建议",
                    "• 数据集与业务场景可能不匹配，建议先在“自动路由数据集”中切换正确数据源再执行。",
                    "• 先核对组织名称是否与数据集字段完全一致，例如“东部分公司”是否存在别名或上级层级差异。",
                    "• 再检查时间范围和过滤条件，必要时放宽条件后重新查询。",
                ]
            )
            return "\n".join(lines)

        lines = [
            "## 业绩分析报告",
            "",
            "### 核心结论",
            f"当前围绕“{question or dataset_name}”返回 {row_count} 行结果，可结合明细字段进一步判断经营动作。",
            "",
            "### 亮点分析",
            f"• **亮点：** 数据可用性 -> 返回 {row_count} 行、{len(columns)} 个字段 -> 可支撑后续关键指标核对。",
            "",
            "### 问题诊断",
        ]

        if review_summary:
            lines.append(f"• **痛点：** SQL复核 -> {review_summary} -> 请优先确认口径边界。")

        if rows and columns:
            sample_bits = []
            first_row = rows[0] or {}
            for column in columns[:3]:
                sample_bits.append(f"{column}={first_row.get(column)}")
            if sample_bits:
                lines.append(f"• **痛点：** 样例结果 -> {'；'.join(sample_bits)} -> 需要继续结合完整明细判断风险。")

        if error_message:
            lines.append(f"• **痛点：** 高级分析 -> 生成失败 -> 已退回基础摘要模式，原因：{error_message}")

        lines.extend(
            [
                "",
                "### 改进建议",
                "• 先结合右侧明细结果确认统计口径与字段含义。",
                "• 如需更完整报告，可补充业务口径或检查该数据集的 Agent4 提示词与 LLD 文档。",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        return ask_engine_utils._to_float(value)

    @staticmethod
    def _format_metric(
        value: Optional[float],
        suffix: str = "",
        metric: Optional[Dict[str, Any]] = None,
    ) -> str:
        return ask_engine_utils._format_metric(value, suffix, metric)

    @staticmethod
    def _build_display_title(question: str, dataset_result: Dict[str, Any]) -> str:
        return ask_engine_utils._build_display_title(question, dataset_result)

    def _build_layered_management_report(
        self,
        question: str,
        dataset_name: str,
        rows: Any,
        columns: Any,
        review_summary: str = "",
        error_message: str = "",
        report_config: Optional[Dict[str, Any]] = None,
        resolved_entities: Optional[Dict[str, Any]] = None,
        query_intent: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not isinstance(rows, list) or not rows:
            return ""
        if not isinstance(columns, list):
            columns = []

        config = report_config or report_config_store.get_default_config()
        query_intent = query_intent or {}
        metrics = [item for item in (config.get("metrics") or []) if isinstance(item, dict)]
        metric_by_key = {str(item.get("key") or ""): item for item in metrics}
        rate_metric = metric_by_key.get("rate") or next((item for item in metrics if item.get("format") == "percent"), {})
        task_metric = metric_by_key.get("task") or next((item for item in metrics if "任务" in str(item.get("label") or item.get("column") or "")), {})
        actual_metric = metric_by_key.get("actual") or next((item for item in metrics if any(token in str(item.get("label") or item.get("column") or "") for token in ("完成", "开单", "销售"))), {})
        remain_metric = metric_by_key.get("remain") or next((item for item in metrics if any(token in str(item.get("label") or item.get("column") or "") for token in ("剩余", "缺口", "差额"))), {})

        name_col = str(config.get("nameColumn") or "节点名称")
        parent_col = str(config.get("parentColumn") or "上级名称")
        level_col = str(config.get("levelColumn") or "层级")
        track_col = str(config.get("trackColumn") or "条线")
        task_col = str(task_metric.get("column") or "")
        actual_col = str(actual_metric.get("column") or "")
        rate_col = str(rate_metric.get("column") or "")
        remain_col = str(remain_metric.get("column") or "")
        levels = [item for item in (config.get("levels") or []) if isinstance(item, dict)]
        required_columns = {name_col, level_col, rate_col}
        if parent_col:
            required_columns.add(parent_col)
        if not all(column in columns for column in required_columns if column):
            return ""

        def normalized_text(row: Dict[str, Any], column: str) -> str:
            return str(row.get(column) or "").strip()

        def row_rate(row: Dict[str, Any]) -> Optional[float]:
            return self._to_float(row.get(rate_col))

        def row_metric_value(row: Dict[str, Any], metric_column: str) -> Optional[float]:
            if not metric_column:
                return None
            return self._to_float(row.get(metric_column))

        def row_name(row: Dict[str, Any]) -> str:
            return normalized_text(row, name_col)

        def dedupe(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            seen = set()
            deduped = []
            for item in items:
                key = (row_name(item), normalized_text(item, parent_col) if parent_col else "", normalized_text(item, level_col))
                if not key[0] or key in seen:
                    continue
                seen.add(key)
                deduped.append(item)
            return deduped

        valid_rows = dedupe([row for row in rows if isinstance(row, dict) and row_name(row)])
        if not valid_rows:
            return ""

        def sum_col(items: List[Dict[str, Any]], column: str) -> Optional[float]:
            values = [self._to_float(row.get(column)) for row in items]
            values = [value for value in values if value is not None]
            if not values:
                return None
            return sum(values)

        def weighted_rate(items: List[Dict[str, Any]]) -> Optional[float]:
            task = sum_col(items, task_col) if task_col else None
            actual = sum_col(items, actual_col) if actual_col else None
            if task and actual is not None and task > 0:
                return round(actual / task * 100, 2)
            rates = [row_rate(row) for row in items]
            rates = [rate for rate in rates if rate is not None]
            return round(sum(rates) / len(rates), 2) if rates else None

        def rank_items(items: List[Dict[str, Any]], reverse: bool, limit: int = 5) -> List[Dict[str, Any]]:
            return sorted(
                [row for row in items if row_rate(row) is not None],
                key=lambda row: row_rate(row) or 0,
                reverse=reverse,
            )[:limit]

        def dynamic_limit(count: int) -> int:
            if count <= 1:
                return 0
            return max(1, min(3, count // 3))

        def dynamic_performance_rows(items: List[Dict[str, Any]]) -> Dict[str, Any]:
            seen = set()
            valid = []
            for row in items:
                name = row_name(row)
                rate = row_rate(row)
                key = (name, normalized_text(row, parent_col) if parent_col else "", normalized_text(row, level_col))
                if not name or rate is None or key in seen:
                    continue
                seen.add(key)
                valid.append(row)
            if len(valid) <= 1:
                return {"good": [], "weak": [], "ranked": valid, "can_compare": False}
            ranked = sorted(valid, key=lambda row: row_rate(row) or 0, reverse=True)
            if row_rate(ranked[0]) == row_rate(ranked[-1]):
                return {"good": [], "weak": [], "ranked": ranked, "can_compare": False}
            limit = min(dynamic_limit(len(ranked)), len(ranked) // 2)
            good = ranked[:limit]
            good_keys = {
                (row_name(row), normalized_text(row, parent_col) if parent_col else "", normalized_text(row, level_col))
                for row in good
            }
            weak = [
                row for row in reversed(ranked[-limit:])
                if (row_name(row), normalized_text(row, parent_col) if parent_col else "", normalized_text(row, level_col)) not in good_keys
            ]
            return {"good": good, "weak": weak, "ranked": ranked, "can_compare": True}

        def format_rank(items: List[Dict[str, Any]]) -> str:
            if not items:
                return "暂无"
            return "、".join(f"{row_name(row)} {self._format_metric(row_rate(row), '%')}" for row in items)

        def format_metric_value(value: Optional[float], metric: Dict[str, Any]) -> str:
            if value is None:
                return "-"
            if (metric or {}).get("format") == "percent":
                return self._format_metric(value, "%")
            return self._format_metric(value, metric=metric)

        def format_dynamic(groups: Dict[str, Any], key: str, empty_text: str) -> str:
            return format_rank(groups.get(key) or []) if groups.get("can_compare") else empty_text

        def level_match(row: Dict[str, Any], level_cfg: Dict[str, Any]) -> bool:
            level_value = normalized_text(row, level_col)
            return level_value in {str(item) for item in (level_cfg.get("values") or [])}

        semantic_level_by_value = {}
        for level_cfg in levels:
            for value in level_cfg.get("values") or []:
                semantic_level_by_value[str(value)] = str(level_cfg.get("name") or "")

        rows_by_name = {row_name(row): row for row in valid_rows if row_name(row)}
        depth_cache: Dict[str, int] = {}

        def row_depth(row: Dict[str, Any]) -> int:
            name = row_name(row)
            if not name:
                return 0
            if name in depth_cache:
                return depth_cache[name]
            parent_name = normalized_text(row, parent_col) if parent_col else ""
            parent_row = rows_by_name.get(parent_name)
            if not parent_row or parent_row is row:
                depth_cache[name] = 0
                return 0
            depth_cache[name] = row_depth(parent_row) + 1
            return depth_cache[name]

        grouped_by_depth: Dict[int, List[Dict[str, Any]]] = {}
        for row in valid_rows:
            grouped_by_depth.setdefault(row_depth(row), []).append(row)

        level_sections = []
        for index, depth in enumerate(sorted(grouped_by_depth.keys()), start=1):
            section_rows = grouped_by_depth[depth]
            level_values = list(dict.fromkeys(normalized_text(row, level_col) or "未分层" for row in section_rows))
            semantic_names = list(dict.fromkeys(semantic_level_by_value.get(value, "") for value in level_values if semantic_level_by_value.get(value, "")))
            level_sections.append(
                {
                    "index": index,
                    "depth": depth,
                    "name": " / ".join(level_values) or " / ".join(semantic_names) or f"第 {index} 层",
                    "semantic_names": semantic_names,
                    "values": level_values,
                    "rows": section_rows,
                }
            )

        top_section = level_sections[0]
        bottom_section = level_sections[-1]
        top_rate = weighted_rate(top_section["rows"])
        bottom_rate = weighted_rate(bottom_section["rows"])
        query_subjects = list(dict.fromkeys(row_name(row) for row in top_section["rows"][:8] if row_name(row)))
        if not query_subjects and parent_col:
            query_subjects = list(dict.fromkeys(normalized_text(row, parent_col) for row in valid_rows[:8] if normalized_text(row, parent_col)))

        subject_label = "、".join(query_subjects[:6]) or question or dataset_name
        resolved_names = self._resolved_entity_names({"resolved_entities": resolved_entities or {}})
        explicit_person_focus = (
            len(resolved_names) == 1
            and any(row_name(row) == resolved_names[0] for row in valid_rows)
        )
        focus_person_row = next((row for row in valid_rows if row_name(row) == resolved_names[0]), None) if explicit_person_focus else None
        is_comparison = len(resolved_names) > 1 or bool(re.search(r"对比|比较|哪个|谁更|差异|分别|各自|和.+比|跟.+比|与.+比|\bvs\b", question or "", re.I))
        ranking_intent = str(query_intent.get("intent") or "") == "ranking"
        ranking_metric_key = str(query_intent.get("sort_metric_key") or "")
        ranking_metric_column = str(query_intent.get("sort_metric_column") or "").strip()
        ranking_metric = metric_by_key.get(ranking_metric_key) or next(
            (
                item for item in metrics
                if ranking_metric_column and ranking_metric_column in {
                    str(item.get("column") or ""),
                    str(item.get("label") or ""),
                }
            ),
            {},
        )
        ranking_metric = ranking_metric or rate_metric or actual_metric or task_metric or remain_metric or {}
        ranking_metric_column = ranking_metric_column or str(ranking_metric.get("column") or "")
        ranking_metric_label = str(ranking_metric.get("label") or ranking_metric_column or ranking_metric_key or "指标")
        ranking_direction = str(query_intent.get("direction") or "desc").lower()
        target_level = str(query_intent.get("target_level") or "").strip()

        if ranking_intent and ranking_metric_column:
            scoped_rows = [
                row for row in valid_rows
                if row_metric_value(row, ranking_metric_column) is not None
                and (not target_level or normalized_text(row, level_col) == target_level)
            ]
            if scoped_rows:
                ranked_rows = sorted(
                    scoped_rows,
                    key=lambda row: row_metric_value(row, ranking_metric_column) or 0,
                    reverse=ranking_direction != "asc",
                )
                rank_limit = self._safe_int(query_intent.get("top_n"), 0)
                shown_rows = ranked_rows[: min(rank_limit, len(ranked_rows))] if rank_limit > 0 else ranked_rows
                leader = shown_rows[0]
                tail = shown_rows[-1]
                leader_metric_value = row_metric_value(leader, ranking_metric_column)
                tail_metric_value = row_metric_value(tail, ranking_metric_column)
                leader_metric_text = format_metric_value(leader_metric_value, ranking_metric)
                tail_metric_text = format_metric_value(tail_metric_value, ranking_metric)
                leader_rate = row_rate(leader)
                leader_rate_text = self._format_metric(leader_rate, "%") if leader_rate is not None else ""
                tail_rate_value = row_rate(tail)
                tail_rate_text = self._format_metric(tail_rate_value, "%") if tail_rate_value is not None else ""
                rate_warning = (
                    f"；但{leader.get(name_col) or row_name(leader)}达成率仅{leader_rate_text}，仍低于60%红线"
                    if ranking_metric.get("format") != "percent" and leader_rate is not None and leader_rate < 60
                    else ""
                )
                gap_text = ""
                if leader_metric_value is not None and tail_metric_value is not None and row_name(leader) != row_name(tail):
                    metric_gap = abs(leader_metric_value - tail_metric_value)
                    gap_text = (
                        f"{self._format_metric(metric_gap, '')} 个百分点"
                        if ranking_metric.get("format") == "percent"
                        else self._format_metric(metric_gap)
                    )
                risk_rows = [row for row in shown_rows if row_rate(row) is not None and (row_rate(row) or 0) < 20]
                top_names = "、".join(row_name(row) for row in shown_rows[: min(3, len(shown_rows))] if row_name(row))
                level_label = target_level or (normalized_text(leader, level_col) if leader else "") or "对象"
                is_asc = ranking_direction == "asc"
                if rank_limit == 1:
                    extreme_label = "最低" if is_asc else "最高"
                    lines = [
                        "## 业绩分析报告",
                        "",
                        "### 核心结论",
                        (
                            f"本次已按{ranking_metric_label}找到{level_label}中{extreme_label}的对象："
                            f"{row_name(leader)}，{ranking_metric_label}{leader_metric_text}"
                            f"{f'，达成率{leader_rate_text}' if leader_rate is not None and ranking_metric.get('format') != 'percent' else ''}"
                            f"{rate_warning}。"
                        ),
                        "",
                        "### 关键指标",
                        (
                            f"• **{extreme_label}对象：** {row_name(leader)} -> {ranking_metric_label} {leader_metric_text}"
                            f"{f' -> 达成率 {leader_rate_text}' if leader_rate is not None and ranking_metric.get('format') != 'percent' else ''}"
                            f" -> 建议优先核对该对象的任务缺口与下级明细。"
                        ),
                        (
                            f"• **风险提示：** 当前结果内低于20%风险线的节点 {len(risk_rows)} 个"
                            + (f"，重点关注 {format_rank(risk_rows[:3])}。" if risk_rows else "，暂无明显低于20%的节点。")
                        ),
                        "",
                        "### 改进建议",
                        f"• {row_name(leader)}为当前{ranking_metric_label}{extreme_label}的{level_label}，建议下钻其下级节点继续拆因。",
                        "• 风险识别仍以达成率、剩余缺口和项目推进节奏综合判断，避免只看相对名次。",
                    ]
                else:
                    first_label = "末位" if is_asc else "榜首"
                    last_label = "榜首" if is_asc else "末位"
                    lines = [
                        "## 业绩分析报告",
                        "",
                        "### 核心结论",
                        (
                            f"本次已按{ranking_metric_label}输出 {len(shown_rows)} 个{level_label}的排名结果："
                            f"{row_name(leader)}位列第1（{first_label}），{ranking_metric_label}{leader_metric_text}；"
                            f"{row_name(tail)}位于第{len(shown_rows)}（{last_label}），{ranking_metric_label}{tail_metric_text}"
                            f"{f'，首尾相差{gap_text}' if gap_text else ''}{rate_warning}。"
                        ),
                        "",
                        "### 亮点分析",
                        (
                            f"• **{first_label}对象：** {row_name(leader)} -> {ranking_metric_label} {leader_metric_text}"
                            f"{f' -> 达成率 {leader_rate_text}' if leader_rate is not None and ranking_metric.get('format') != 'percent' else ''}"
                            " -> 可作为当前口径的优先复盘样本。"
                        ),
                        (
                            f"• **前三结果：** {top_names or row_name(leader)}"
                            " -> 先看头部样本，再结合完整排名表继续核对差距来源。"
                        ),
                        "",
                        "### 问题诊断",
                        (
                            f"• **{last_label}对象：** {row_name(tail)} -> {ranking_metric_label} {tail_metric_text}"
                            f"{f' -> 达成率 {tail_rate_text}' if tail_rate_value is not None and ranking_metric.get('format') != 'percent' else ''}"
                            " -> 建议优先核对任务缺口、项目推进和资源投入。"
                        ),
                        (
                            f"• **风险提示：** 当前结果内低于20%风险线的节点 {len(risk_rows)} 个"
                            + (f"，重点关注 {format_rank(risk_rows[:3])}。" if risk_rows else "，暂无明显低于20%的节点。")
                        ),
                        "",
                        "### 改进建议",
                        f"• 先按{ranking_metric_label}复盘{first_label}与{last_label}对象的差距来源，避免继续按默认达成率口径解释本轮排序。",
                        f"• 完整 {len(shown_rows)} 个{level_label}名单以排名表为准；如需继续拆因，优先下钻{last_label}对象的下级明细。",
                        "• 风险识别仍以达成率、剩余缺口和项目推进节奏综合判断，避免只看相对名次。",
                    ]
                if review_summary:
                    lines.extend(["", f"> SQL复核：{review_summary}"])
                if error_message:
                    lines.extend(["", f"> 说明：高级模型分析失败，已使用规则分层报告兜底。原因：{error_message}"])
                return "\n".join(lines)

        filter_intent = str(query_intent.get("intent") or "") == "filter"
        if filter_intent:
            filter_metric_column = str(query_intent.get("filter_metric_column") or "").strip()
            filter_metric_key = str(query_intent.get("filter_metric_key") or "").strip()
            filter_metric = metric_by_key.get(filter_metric_key) or {}
            if not filter_metric and filter_metric_column:
                filter_metric = next(
                    (item for item in metrics if filter_metric_column in {
                        str(item.get("column") or ""),
                        str(item.get("label") or ""),
                    }),
                    {},
                )
            filter_metric_column = filter_metric_column or str(filter_metric.get("column") or rate_col or "")
            filter_metric_label = str(filter_metric.get("label") or filter_metric_column or "指标")
            filter_operator = str(query_intent.get("filter_operator") or "").strip()
            filter_value = query_intent.get("filter_value")
            operator_text = {"<": "低于", "<=": "不高于", ">": "高于", ">=": "不低于", "=": "等于"}.get(filter_operator, filter_operator)
            is_rate_metric = (
                filter_metric.get("format") == "percent"
                or "率" in filter_metric_label
                or filter_metric_key == "rate"
            )
            threshold_text = self._format_metric(filter_value, "%" if is_rate_metric else "")
            # 金额类阈值按题干单位展示，避免“低于500”这种歧义
            if not is_rate_metric and filter_value is not None and question:
                if "亿" in question and float(filter_value) < 10000:
                    threshold_text = f"{int(filter_value)}亿" if float(filter_value) == int(filter_value) else f"{filter_value}亿"
                elif "万" in question and float(filter_value) < 10000:
                    threshold_text = f"{int(filter_value)}万" if float(filter_value) == int(filter_value) else f"{filter_value}万"
            scoped_rows = [
                row for row in valid_rows
                if not target_level or normalized_text(row, level_col) == target_level
            ]
            if not scoped_rows:
                scoped_rows = valid_rows
            level_label = target_level or (normalized_text(scoped_rows[0], level_col) if scoped_rows else "节点")
            lines = [
                "## 业绩分析报告",
                "",
                "### 核心结论",
                f"本轮筛选出 {len(scoped_rows)} 个{level_label}的{filter_metric_label}{operator_text}{threshold_text}。",
                "",
                "### 关键指标",
            ]
            for row in scoped_rows[:20]:
                name = row_name(row)
                rate = row_rate(row)
                rate_text = self._format_metric(rate, "%") if rate is not None else "-"
                task = format_metric_value(row_metric_value(row, task_col), task_metric)
                actual = format_metric_value(row_metric_value(row, actual_col), actual_metric)
                remain = format_metric_value(row_metric_value(row, remain_col), remain_metric)
                if filter_metric_column == rate_col or filter_metric_key == "rate":
                    lines.append(
                        f"• **{name}**：达成率{rate_text}，任务{task}，开单{actual}，剩余{remain}"
                    )
                else:
                    metric_value = row_metric_value(row, filter_metric_column) if filter_metric_column else None
                    metric_text = format_metric_value(metric_value, filter_metric) if metric_value is not None else "-"
                    lines.append(
                        f"• **{name}**：{filter_metric_label}{metric_text}，达成率{rate_text}，"
                        f"任务{task}，开单{actual}，剩余{remain}"
                    )
            if len(scoped_rows) > 20:
                lines.append(f"• ... 以上展示前 20 个，共 {len(scoped_rows)} 个节点。")
            risk_rows = [row for row in scoped_rows if row_rate(row) is not None and (row_rate(row) or 0) < 20]
            lines.extend(
                [
                    "",
                    "### 问题诊断",
                    (
                        f"• **风险节点：** 低于20%红线的节点 {len(risk_rows)} 个"
                        + (f"，包括 {format_rank(risk_rows[:5])}。" if risk_rows else "，当前筛选结果中暂无。")
                    ),
                    "",
                    "### 改进建议",
                    "• 对筛选出的节点优先核对任务缺口、项目推进节奏和资源投入是否匹配。",
                    "• 结合上级组织横向比较，判断问题偏向个人执行还是组织支撑不足。",
                ]
            )
            if review_summary:
                lines.extend(["", f"> SQL复核：{review_summary}"])
            if error_message:
                lines.extend(["", f"> 说明：高级模型分析失败，已使用规则分层报告兜底。原因：{error_message}"])
            return "\n".join(lines)

        if explicit_person_focus and focus_person_row:
            person_name = row_name(focus_person_row)
            parent_name = normalized_text(focus_person_row, parent_col) if parent_col else ""
            level_name = normalized_text(focus_person_row, level_col) or "对象"
            person_task = format_metric_value(self._to_float(focus_person_row.get(task_col)), task_metric) if task_col else "-"
            person_actual = format_metric_value(self._to_float(focus_person_row.get(actual_col)), actual_metric) if actual_col else "-"
            person_rate_value = row_rate(focus_person_row)
            person_rate = format_metric_value(person_rate_value, rate_metric) if rate_metric else "-"
            person_remain = format_metric_value(self._to_float(focus_person_row.get(remain_col)), remain_metric) if remain_col else "-"
            pressure_text = "当前达成承压，建议优先跟进缺口转化。" if person_rate_value is not None and person_rate_value < 20 else "当前进度已明确，可继续结合上级链路判断支撑与压力来源。"
            lines = [
                "## 业绩分析报告",
                "",
                "### 核心结论",
                f"{person_name}当前作为{level_name}{f'，归属{parent_name}' if parent_name else ''}：年度任务{person_task}，年度开单{person_actual}，达成率{person_rate}，剩余任务{person_remain}。{pressure_text}",
                "",
                "### 亮点分析",
                f"• **当前主体：** {person_name} -> 年度开单{person_actual}，任务{person_task}，达成率{person_rate}。",
                f"• **归属链路：** {parent_name or '未识别上级'} -> 可继续下钻查看所属业务部/代表处的整体支撑情况。",
                "",
                "### 问题诊断",
                f"• **缺口判断：** 当前剩余任务{person_remain}，需要把个人开单进度和上级组织支撑拆开看。",
                f"• **风险提示：** {'达成率低于20%，属于重点承压节点。' if person_rate_value is not None and person_rate_value < 20 else '当前未落入重点风险红线，但仍需关注后续缺口消化。'}",
                "",
                "### 改进建议",
                f"• 先围绕{person_name}核对在手项目、客户转化和回款节奏，确认短期可兑现开单来源。",
                f"• 再结合{parent_name or '上级组织'}横向比较，判断问题更偏个人执行还是组织支撑不足。",
            ]
            if review_summary:
                lines.extend(["", f"> SQL复核：{review_summary}"])
            if error_message:
                lines.extend(["", f"> 说明：高级模型分析失败，已使用规则分层报告兜底。原因：{error_message}"])
            return "\n".join(lines)

        if is_comparison and len(top_section["rows"]) >= 2:
            compared = sorted(
                [row for row in top_section["rows"] if row_rate(row) is not None],
                key=lambda row: row_rate(row) or 0,
                reverse=True,
            )[:2]
            if len(compared) >= 2:
                first, second = compared[0], compared[1]
                first_rate = row_rate(first)
                second_rate = row_rate(second)
                rate_gap = (first_rate or 0) - (second_rate or 0)
                first_name = row_name(first)
                second_name = row_name(second)
                first_task = self._to_float(first.get(task_col)) if task_col else None
                second_task = self._to_float(second.get(task_col)) if task_col else None
                first_actual = self._to_float(first.get(actual_col)) if actual_col else None
                second_actual = self._to_float(second.get(actual_col)) if actual_col else None
                first_remain = self._to_float(first.get(remain_col)) if remain_col else None
                second_remain = self._to_float(second.get(remain_col)) if remain_col else None

                child_rows = [row for row in valid_rows if normalized_text(row, parent_col) in {first_name, second_name}]
                child_level_names = list(dict.fromkeys(normalized_text(row, level_col) for row in child_rows if normalized_text(row, level_col)))
                child_level_label = " / ".join(child_level_names[:2]) or "下级节点"
                child_groups = dynamic_performance_rows(child_rows)
                leader = first_name if rate_gap >= 0 else second_name
                learner = second_name if rate_gap >= 0 else first_name
                lines = [
                    f"# {first_name} vs {second_name} 业绩对比分析报告",
                    "",
                    "## 一、核心结论",
                    (
                        f"{first_name}整体达成率{self._format_metric(first_rate, '%')}，"
                        f"比{second_name}的{self._format_metric(second_rate, '%')}"
                        f"{'高' if rate_gap >= 0 else '低'}{self._format_metric(abs(rate_gap), '')}个百分点；"
                        f"当前对标方向是 {learner} 向 {leader} 学习高达成节点的目标拆解和项目推进节奏。"
                    ),
                    "",
                    "## 二、关键指标对标",
                    f"| 指标 | {first_name} | {second_name} | 差距 |",
                    "|---|---:|---:|---:|",
                    f"| 总任务金额 | {self._format_metric(first_task)} | {self._format_metric(second_task)} | - |",
                    f"| 已完成金额 | {self._format_metric(first_actual)} | {self._format_metric(second_actual)} | {self._format_metric((first_actual or 0) - (second_actual or 0))} |",
                    f"| 整体达成率 | {self._format_metric(first_rate, '%')} | {self._format_metric(second_rate, '%')} | {self._format_metric(rate_gap, '')}pct |",
                    f"| 剩余缺口金额 | {self._format_metric(first_remain)} | {self._format_metric(second_remain)} | {self._format_metric((first_remain or 0) - (second_remain or 0))} |",
                    "",
                    "## 三、层级差异核心看点",
                    f"1. **{child_level_label}表现较好节点**：{format_dynamic(child_groups, 'good', '样本不足或差异不明显')}，优先复盘其客户跟进节奏和目标拆解方式。",
                    f"2. **{child_level_label}相对承压节点**：{format_dynamic(child_groups, 'weak', '样本不足或差异不明显')}，优先跟进缺口和过程动作。",
                    "",
                    "## 四、落地建议",
                    f"✅ **{learner}向{leader}对标学习**：复制高达成单元的周度目标拆解、客户推进节奏和项目转化复盘。",
                    f"⚠️ **{leader}保持优势**：沉淀头部节点打法，并向同层级中等达成节点推广。",
                    f"🔴 **共同改进项**：先针对低达成{child_level_label}建立周度跟进清单，再下钻到业务代表按缺口金额和项目阶段排序。",
                ]
                if review_summary:
                    lines.extend(["", f"> SQL复核：{review_summary}"])
                if error_message:
                    lines.extend(["", f"> 说明：高级模型分析失败，已使用规则分层报告兜底。原因：{error_message}"])
                return "\n".join(lines)

        lines = [
            "## 业绩分析报告",
            "",
            "### 核心结论",
            (
                f"本轮围绕 {subject_label} 展开，共识别 {len(level_sections)} 个分析层级。"
                f"{top_section['name']}综合达成率 {self._format_metric(top_rate, '%')}，"
                f"{bottom_section['name']}综合达成率 {self._format_metric(bottom_rate, '%')}。"
            ),
            "",
            "### 亮点分析",
            f"• **亮点：** {top_section['name']} -> 综合达成率 {self._format_metric(top_rate, '%')} -> 可作为当前层级的优先复盘样本。",
            "",
            "### 问题诊断",
            f"• **痛点：** {bottom_section['name']} -> 综合达成率 {self._format_metric(bottom_rate, '%')} -> 需要关注目标拆解、项目推进和资源投入。",
            f"• **结构：** 拆分维度 -> {' → '.join(section['name'] for section in level_sections)} -> 用于定位问题落点。",
            "",
        ]

        for section in level_sections:
            section_rows = section["rows"]
            tracks = []
            if track_col in columns:
                tracks = list(dict.fromkeys(normalized_text(row, track_col) for row in section_rows if normalized_text(row, track_col)))
            section_groups = dynamic_performance_rows(section_rows)
            parent_groups: Dict[str, int] = {}
            if parent_col in columns:
                for row in section_rows:
                    parent = normalized_text(row, parent_col) or "未归属"
                    parent_groups[parent] = parent_groups.get(parent, 0) + 1
            group_text = "、".join(f"{name}({count})" for name, count in list(parent_groups.items())[:6]) or "按当前结果直接展示"
            lines.extend(
                [
                    f"#### {' / '.join(tracks) + '｜' if tracks else ''}{section['name']}",
                    f"• **亮点：** 表现较好节点 -> {format_dynamic(section_groups, 'good', '样本不足或差异不明显')} -> 可沉淀可复制动作。",
                    f"• **痛点：** 相对承压节点 -> {format_dynamic(section_groups, 'weak', '样本不足或差异不明显')} -> 需要短周期跟进缺口。",
                    f"• **结构：** 下级单元 -> {', '.join([row_name(row) for row in section_rows[:12]]) or '暂无'}（共 {len(section_rows)} 个） -> 上级分组：{group_text}。",
                    "",
                ]
            )

        overall_groups = dynamic_performance_rows(valid_rows)
        risk_count = len(overall_groups.get("weak") or [])
        top_examples = overall_groups.get("good") or []
        risk_examples = overall_groups.get("weak") or []
        lines.extend(
            [
                "### 改进建议",
                f"• {top_section['name']}：优先聚焦相对承压节点，复盘目标拆解、项目推进和资源投入是否匹配。",
                f"• {bottom_section['name']}：对低达成节点做短周期跟进，对高达成节点沉淀可复制动作。",
                f"• 当前动态识别 {risk_count} 个相对承压节点，建议优先查看 {format_rank(risk_examples)}；表现较好节点可参考 {format_rank(top_examples)}。",
            ]
        )
        if review_summary:
            lines.extend(["", f"> SQL复核：{review_summary}"])
        if error_message:
            lines.extend(["", f"> 说明：高级模型分析失败，已使用规则分层报告兜底。原因：{error_message}"])
        return "\n".join(lines)

    def _build_graceful_dataset_result(
        self,
        question: str,
        context: Dict[str, Any],
        review: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        sql_text: str = "",
    ) -> Dict[str, Any]:
        dataset = self._safe_dict(context.get("dataset"))
        safe_review = review or {
            "approved": False,
            "review_summary": "",
            "risks": [],
            "fixes": [],
        }
        safe_result = result or {"columns": [], "rows": [], "row_count": 0}
        analysis_text = self._build_fallback_analysis(
            question=question,
            context=context,
            review=safe_review,
            result=safe_result,
            error_message="",
        )
        return {
            "dataset_id": dataset.get("id"),
            "dataset_code": dataset.get("dataset_code"),
            "dataset_name": dataset.get("dataset_name"),
            "source_id": dataset.get("source_id"),
            "report_config": context.get("report_config") or report_config_store.get_default_config(),
            "resolved_entities": context.get("resolved_entities"),
            "agent3_review": safe_review,
            "columns": safe_result.get("columns", []),
            "rows": safe_result.get("rows", []),
            "row_count": safe_result.get("row_count", 0),
            "analysis": analysis_text,
            "sql": sql_text,
        }

    def _build_diagnostic_result(
        self,
        question: str,
        started: float,
        trace: Optional[Dict[str, Any]] = None,
        route: Optional[Dict[str, Any]] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
        error_message: str = "",
        selected_dataset_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        diagnostic_analysis = "\n".join(
            [
                "## 诊断报告",
                f"- 原始问题：{question or '未提供问题内容'}",
                f"- 已尝试数据集：{', '.join([str(item) for item in (selected_dataset_ids or route.get('dataset_ids', []) if route else selected_dataset_ids or [])]) or '自动路由'}",
                "- 当前阶段：系统已尽量完成路由、样本匹配、SQL 生成与执行尝试。",
                f"- 失败原因：{error_message or '本轮未产出可执行结果'}",
                "",
                "### 下一步建议",
                "- 优先补充统计口径、时间范围、组织范围或指标定义。",
                "- 优先补充当前数据集的 Golden SQL、字段字典和 Agent 提示词。",
                "- 如已有类似 SQL 样本，应优先走样本改写而不是重新生成。",
            ]
        )
        review_summary = error_message or "本轮未产出可执行 SQL，已退回诊断报告模式。"
        return {
            "question": question,
            "route": route or {"dataset_ids": selected_dataset_ids or [], "decision": "diagnostic_report"},
            "confidence": self._build_confidence_payload(route or {}, []),
            "dataset_results": [
                {
                    "dataset_id": None,
                    "dataset_code": "diagnostic_report",
                    "dataset_name": "诊断报告",
                    "source_id": None,
                    "agent3_review": {
                        "approved": False,
                        "review_summary": review_summary,
                        "risks": [],
                        "fixes": [],
                    },
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "analysis": diagnostic_analysis,
                    "sql": "",
                }
            ],
            "data_source": "诊断报告",
            "sql": "",
            "columns": [],
            "rows": [],
            "row_count": 0,
            "analysis": diagnostic_analysis,
            "steps": steps or [],
            "requires_confirmation": False,
            "diagnostic": True,
            "original_error": error_message,
            "trace_id": (trace or {}).get("trace_id", ""),
            "total_duration": round(time.time() - started, 2),
        }

    def _build_route_confidence(self, route: Dict[str, Any]) -> Dict[str, Any]:
        route = self._safe_dict(route)
        candidate_ids = route.get("candidate_dataset_ids") or route.get("dataset_ids") or []
        candidate_count = len(candidate_ids) if isinstance(candidate_ids, list) else 0
        reason = str(route.get("arbiter_reason") or "").strip()
        try:
            raw_match_score = int(route.get("match_score") or 0)
        except Exception:
            raw_match_score = 0

        # 统一“展示分”口径：
        # - 保留原始 match_score 作为底层事实，不参与实际路由决策变更
        # - 展示分按更平滑的规则归一，避免不同分支硬编码的 92/96/98/100 直接外露
        base_score = 76 if candidate_count <= 1 else 68
        score = int(round(raw_match_score * 0.55 + base_score * 0.45)) if raw_match_score > 0 else base_score

        if candidate_count > 1:
            score -= min(10, (candidate_count - 1) * 4)
        route_margin = int(route.get("route_margin") or 0)
        if route_margin >= 40:
            score += 6
        elif route_margin >= 20:
            score += 3
        elif candidate_count > 1 and route_margin <= 5:
            score -= 4
        elif candidate_count > 1 and route_margin <= 12:
            score -= 2

        if reason in {"explicit_dataset_scope_unique", "explicit_dataset_domain", "explicit_dataset_alias"}:
            score += 4
        elif reason in {"organization_tree_name_resolved", "entity_mention_unique", "target_level_unique:城市分公司"}:
            score += 3
        elif "target_level_unique:" in reason:
            score += 2
        elif reason.startswith("level_ambiguity_resolved_by_"):
            score -= 1

        if route.get("requires_confirmation"):
            # 待确认表示口径歧义，不等于系统完全没把握；仅限制到“可确认”档位
            score = min(score, 68)
        if route.get("preferred_dataset_override"):
            score = max(score, 72)

        score = max(0, min(100, score))
        level = "high" if score >= 80 else "medium" if score >= 64 else "low"
        label = "高" if score >= 80 else "中" if score >= 64 else "待确认"

        if route.get("requires_confirmation"):
            summary = "当前命中仍存在不确定性，已暂停并等待确认统计口径。"
        elif reason == "profile_scope_resolved":
            summary = "当前问题中的组织简称或合称已命中数据集画像，系统按画像映射的数据集执行。"
        elif reason in {"explicit_dataset_alias", "explicit_dataset_scope_unique", "explicit_dataset_domain"}:
            summary = "当前问题直接命中了数据集名称、业务域或已维护同义词。"
        elif reason == "organization_tree_name_resolved":
            summary = "当前问题命中了组织树节点，系统按该节点绑定的数据集执行。"
        elif score < 64:
            summary = "当前更像相似命中，系统不会把它当作确定命中直接下结论。"
        elif candidate_count > 1:
            summary = f"当前存在 {candidate_count} 个候选口径，系统已结合层级、别名和候选差距收敛到当前数据集。"
        elif route.get("preferred_dataset_override"):
            summary = "当前按人工指定数据集执行，路由方向相对明确。"
        else:
            summary = "当前问题经过语义匹配与候选复核后，目标数据集较为明确。"

        return {
            "score": score,
            "level": level,
            "label": label,
            "summary": summary,
            "candidate_count": candidate_count,
            "match_score": raw_match_score,
            "route_margin": route_margin,
            "reason": reason,
        }

    def _select_sql_strategy(self, question: str, route: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        samples = context.get("golden_sql_samples") or []
        sql_samples = [item for item in samples if str(item.get("sql_text") or "").strip()]
        top_sample = sql_samples[0] if sql_samples else {}
        top_sample_sql = str(top_sample.get("sql_text") or "").strip()
        top_sample_score = self._safe_int(top_sample.get("match_score"), 0)
        route_match_score = self._safe_int(route.get("match_score"), 0)
        route_margin = self._safe_int(route.get("route_margin"), 0)
        preferred_override = bool(route.get("preferred_dataset_override"))
        rule_based_sql = None  # 惰性求值，仅在需要时计算（审计 A-07）
        route_sample_sql = str(route.get("matched_sample_sql") or "").strip()
        route_sample_id = route.get("matched_sample_id")
        query_intent = self._safe_dict(context.get("query_intent"))
        original_question = str(context.get("original_question") or "")
        level_hint_text = "\n".join(item for item in [str(question or ""), original_question] if item)
        requested_city_level = (
            str(query_intent.get("target_level") or "") == "城市分公司"
            or "城市分公司" in level_hint_text
        )
        filter_intent = str(query_intent.get("intent") or "") == "filter"
        comparison_intent = str(query_intent.get("intent") or "") == "comparison"
        aggregate_intent = str(query_intent.get("intent") or "") == "aggregate"

        def question_key(value: Any) -> str:
            text = re.sub(r"[\s？?。.!！,，、：:；;（）()]+", "", str(value or "").lower())
            text = re.sub(r"^(请问|帮我|帮忙|麻烦|查一下|看一下|查询|分析一下|我想知道)+", "", text)
            text = re.sub(r"(呢|啊|呀|吗|么|吧)$", "", text)
            text = text.replace("消费者事业部", "").replace("消费事业部", "").replace("消费者", "")
            text = text.replace("商用事业部", "").replace("商用", "")
            return text

        def same_question_intent(left: Any, right: Any) -> bool:
            left_key = question_key(left)
            right_key = question_key(right)
            if not left_key or not right_key:
                return False
            return left_key == right_key or left_key in right_key or right_key in left_key

        def sample_conflicts_requested_level(sql: str) -> bool:
            if not requested_city_level:
                return False
            compact_sql = re.sub(r"\s+", "", str(sql or ""))
            asks_branch_level = "层级='分公司'" in compact_sql or '层级="分公司"' in compact_sql
            asks_city_level = "层级='城市分公司'" in compact_sql or '层级="城市分公司"' in compact_sql
            return asks_branch_level and not asks_city_level

        def direct_sample(sql: str, sample_id: Any, sample_score: int) -> Optional[Dict[str, Any]]:
            if sample_conflicts_requested_level(sql):
                return None
            prepared = self._prepare_subject_safe_sample_sql(question, context, sql)
            if prepared.get("conflict"):
                return None
            return {
                "mode": "sample_direct",
                "sql": prepared.get("sql") or sql,
                "sample_id": sample_id,
                "sample_score": sample_score,
                "sample_rewritten": prepared.get("rewritten", False),
            }

        def template_sample(sql: str, sample_id: Any, sample_score: int) -> Optional[Dict[str, Any]]:
            if sample_conflicts_requested_level(sql):
                return None
            prepared = self._prepare_subject_safe_sample_sql(question, context, sql)
            if prepared.get("conflict"):
                return None
            return {
                "mode": "sample_template",
                "sql": prepared.get("sql") or sql,
                "sample_id": sample_id,
                "sample_score": sample_score,
                "sample_rewritten": prepared.get("rewritten", False),
            }

        # Filter/comparison/aggregate questions should not be hijacked by ranking-style Golden SQL samples.
        # Prefer deterministic rule SQL; if unavailable, fall back to fresh generation.
        if rule_based_sql is None:
            rule_based_sql = self._build_rule_based_sql(question, route, context)
        if filter_intent or comparison_intent or aggregate_intent:
            if rule_based_sql:
                return {
                    "mode": "rule_based",
                    "sql": rule_based_sql,
                    "sample_id": None,
                    "sample_score": 0,
                }
            return {
                "mode": "agent_generate",
                "sql": "",
                "sample_id": None,
                "sample_score": 0,
            }

        # 电商数据集已有专门维护的规则 SQL，优先使用规则 SQL，避免旧 Golden SQL 样本列不标准导致图表异常。
        dataset = self._safe_dict(context.get("dataset"))
        dataset_code = str(dataset.get("dataset_code") or "")
        dataset_name = str(dataset.get("dataset_name") or "")
        is_ecommerce_dataset = dataset_code == "feishu_tbldianshang" or "电商事业部" in dataset_name
        is_syyb_dataset = dataset_code in {"angel_business_2026", "angel_business_2026_phase1"} or dataset_name in {
            "商用事业部",
            "商用事业部（阶段一升级版）",
        }
        compact_question = self._normalize_compact_text(question)
        syyb_root_question = (
            is_syyb_dataset
            and "商用事业部" in compact_question
            and not re.search(r"分公司|代表处|业务部|业务代表|业务员|条线|排名|排行|最高|最低|前\d+|后\d+", compact_question)
        )
        if is_ecommerce_dataset and rule_based_sql:
            return {
                "mode": "rule_based",
                "sql": rule_based_sql,
                "sample_id": None,
                "sample_score": 0,
            }
        if syyb_root_question and rule_based_sql:
            return {
                "mode": "rule_based",
                "sql": rule_based_sql,
                "sample_id": None,
                "sample_score": 0,
            }

        exact_sample = next(
            (
                item for item in sql_samples
                if same_question_intent(item.get("question"), question)
            ),
            None,
        )

        if route_sample_sql:
            prepared = direct_sample(route_sample_sql, route_sample_id, top_sample_score)
            if prepared:
                return prepared

        if exact_sample:
            prepared = direct_sample(
                str(exact_sample.get("sql_text") or "").strip(),
                exact_sample.get("id"),
                self._safe_int(exact_sample.get("match_score"), 100),
            )
            if prepared:
                return prepared

        if route.get("decision") == "direct_execute" and top_sample_sql:
            prepared = direct_sample(top_sample_sql, top_sample.get("id"), top_sample_score)
            if prepared:
                return prepared

        if top_sample_sql and (
            top_sample_score >= 96
            or (preferred_override and top_sample_score >= 82)
            or (route_match_score >= 86 and top_sample_score >= 84 and route_margin >= 8)
        ):
            prepared = direct_sample(top_sample_sql, top_sample.get("id"), top_sample_score)
            if prepared:
                return prepared

        if top_sample_sql and (
            top_sample_score >= 66
            or (preferred_override and top_sample_score >= 58)
        ):
            prepared = template_sample(top_sample_sql, top_sample.get("id"), top_sample_score)
            if prepared:
                return prepared

        if rule_based_sql:
            return {
                "mode": "rule_based",
                "sql": rule_based_sql,
                "sample_id": None,
                "sample_score": 0,
            }

        return {
            "mode": "agent_generate",
            "sql": "",
            "sample_id": None,
            "sample_score": 0,
        }

    def _requests_city_company_level(self, question: Any, context: Dict[str, Any]) -> bool:
        query_intent = self._safe_dict(context.get("query_intent"))
        route = self._safe_dict(context.get("route"))
        text = "\n".join(
            str(item or "")
            for item in [
                question,
                context.get("original_question"),
                route.get("refined_query"),
            ]
            if str(item or "").strip()
        )
        return (
            str(query_intent.get("target_level") or "") == "城市分公司"
            or "城市分公司" in text
        )

    def _coerce_city_company_level_sql(self, question: Any, context: Dict[str, Any], sql_text: str) -> str:
        sql = str(sql_text or "")
        if not sql or not self._requests_city_company_level(question, context):
            return sql
        dataset = self._safe_dict(context.get("dataset"))
        dataset_code = str(dataset.get("dataset_code") or dataset.get("code") or "")
        dataset_name = str(dataset.get("dataset_name") or dataset.get("name") or "")
        is_consumer_dataset = (
            dataset_code in {"consumer_business_standard_v1", "public_feishu_tbl_xioafeizhe_609826", "public_feishu_tbl_xioafeizhe"}
            or "消费者" in dataset_name
        )
        if not is_consumer_dataset:
            return sql
        sql = re.sub(
            r"(?P<col>\"?层级\"?)\s*=\s*(?P<quote>['\"])分公司(?P=quote)",
            lambda match: f"{match.group('col')} = {match.group('quote')}城市分公司{match.group('quote')}",
            sql,
        )
        return re.sub(
            r"(?P<col>\"?层级\"?)\s+IN\s*\(\s*(?P<quote>['\"])分公司(?P=quote)\s*\)",
            lambda match: f"{match.group('col')} IN ({match.group('quote')}城市分公司{match.group('quote')})",
            sql,
            flags=re.I,
        )

    @classmethod
    def _sql_subject_filter_literals(cls, sql_text: str) -> List[str]:
        sql = str(sql_text or "")
        values: List[str] = []
        condition_prefix = r"(?:WHERE|AND|OR|HAVING)\s+"
        subject_cols = r"(?:节点名称|上级名称|业务代表|分公司|代表处|业务部)"
        for match in re.finditer(condition_prefix + rf"[^;\n]{{0,100}}?\b{subject_cols}\b\s*=\s*'([^']+)'", sql, flags=re.I):
            value = str(match.group(1) or "").strip()
            if value and value not in values and value not in {"商用事业部", "消费者事业部"}:
                values.append(value)
        for match in re.finditer(condition_prefix + rf"[^;\n]{{0,100}}?\b{subject_cols}\b\s+IN\s*\(([^)]+)\)", sql, flags=re.I | re.S):
            for value in re.findall(r"'([^']+)'", match.group(1) or ""):
                value = str(value or "").strip()
                if value and value not in values and value not in {"商用事业部", "消费者事业部"}:
                    values.append(value)
        return values

    @staticmethod
    def _normalize_entity_key(value: Any) -> str:
        return ask_engine_utils._normalize_entity_key(value)

    @classmethod
    def _looks_like_noise_subject(cls, value: str) -> bool:
        text = str(value or "").strip()
        if not text or len(text) < 2 or len(text) > 8:
            return True
        if re.match(r"^(看下|看一下|查一下|查询|分析一下|分析|看看|了解一下|了解|问下|问一下)", text):
            return True
        blocked = [
            "商用", "消费者", "事业部", "分公司", "代表处", "业务部", "业务员", "业务代表",
            "销售", "整体", "当前", "今年", "本年", "业绩", "绩效", "开单", "达成",
            "完成", "情况", "表现", "排名", "最高", "最低", "最好", "最差",
        ]
        return any(token in text for token in blocked)

    @classmethod
    def _looks_like_structural_subject_phrase(cls, value: str) -> bool:
        text = str(value or "").strip()
        if not text:
            return True
        structural_tokens = [
            "第一", "第二", "第三", "倒数", "前三", "后三", "前十", "后十",
            "最高", "最低", "最好", "最差", "低于", "高于", "超过", "不足",
            "排名", "top", "bottom", "全部", "所有", "哪些", "哪个", "几个",
        ]
        if any(token in text for token in structural_tokens):
            return True
        if re.match(r"^(看下|看一下|查一下|查询|分析一下|分析|看看|了解一下|了解|问下|问一下)", text):
            return True
        return False

    @classmethod
    def _expand_coordinated_subject_names(cls, value: str) -> List[str]:
        text = str(value or "").strip("，,。！？?、 的呢吗么吧")
        text = re.sub(r"^(?:帮我)?(?:看下|看一下|查一下|查询|分析一下|分析|看看|了解一下|了解|问下|问一下|对比下|比较下|对比一下|比较一下)\s*", "", text)
        if not text:
            return []
        parts = [
            item.strip("，,。！？?、 的呢吗么吧")
            for item in re.split(r"[、,，]|(?:和|与|及|跟)", text)
            if item and item.strip("，,。！？?、 的呢吗么吧")
        ]
        valid_parts = [
            item
            for item in parts
            if re.fullmatch(r"[\u4e00-\u9fa5]{2,4}", item) and not cls._looks_like_noise_subject(item)
        ]
        if len(valid_parts) >= 2:
            return valid_parts
        if re.fullmatch(r"[\u4e00-\u9fa5]{4,8}", text) and any(token in text for token in ["和", "与", "及", "跟"]):
            rough_parts = [
                item.strip()
                for item in re.split(r"(?:和|与|及|跟)", text)
                if item and item.strip()
            ]
            if len(rough_parts) >= 2 and all(re.fullmatch(r"[\u4e00-\u9fa5]{2,4}", item) for item in rough_parts):
                return rough_parts
        if re.fullmatch(r"[\u4e00-\u9fa5]{2,6}", text) and not cls._looks_like_noise_subject(text):
            return [text]
        return []

    @staticmethod
    def _has_specific_node(context: Dict[str, Any]) -> bool:
        return ask_engine_utils._has_specific_node(context)

    def _current_dataset_ids_for_node_index(self, context: Dict[str, Any]) -> List[int]:
        dataset = self._safe_dict(context.get("dataset"))
        dataset_ids: List[int] = []
        try:
            dataset_id = int(dataset.get("id") or 0)
        except Exception:
            dataset_id = 0
        if dataset_id:
            dataset_ids.append(dataset_id)
        dataset_code = str(dataset.get("dataset_code") or "").strip()
        dataset_name = str(dataset.get("dataset_name") or "").strip()
        normalized_code = self._normalize_compact_text(dataset_code)
        normalized_name = self._normalize_compact_text(dataset_name)
        node_index = getattr(self, "_dataset_node_index", None)
        if not isinstance(node_index, dict):
            node_index = self._load_dataset_node_index()
            self._dataset_node_index = node_index
        for item in node_index.get("datasets") or []:
            if not isinstance(item, dict):
                continue
            item_code = str(item.get("dataset_code") or "").strip()
            item_name = str(item.get("dataset_name") or "").strip()
            normalized_item_code = self._normalize_compact_text(item_code)
            normalized_item_name = self._normalize_compact_text(item_name)
            code_matches = bool(
                normalized_code
                and (
                    normalized_item_code == normalized_code
                    or normalized_item_code.startswith(f"{normalized_code}_")
                    or normalized_code.startswith(f"{normalized_item_code}_")
                )
            )
            name_matches = bool(
                normalized_name
                and (
                    normalized_item_name == normalized_name
                    or normalized_name in normalized_item_name
                    or normalized_item_name in normalized_name
                )
            )
            if code_matches or name_matches:
                try:
                    matched_id = int(item.get("dataset_id") or 0)
                except Exception:
                    matched_id = 0
                if matched_id and matched_id not in dataset_ids:
                    dataset_ids.append(matched_id)
        return dataset_ids

    def _node_index_members_by_level(self, context: Dict[str, Any], levels: set[str]) -> set[str]:
        dataset_ids = self._current_dataset_ids_for_node_index(context)
        if not dataset_ids:
            return set()
        node_index = getattr(self, "_dataset_node_index", None)
        if not isinstance(node_index, dict):
            node_index = self._load_dataset_node_index()
            self._dataset_node_index = node_index
        allowed_ids = {int(item) for item in dataset_ids}
        members: set[str] = set()
        for dataset_item in node_index.get("datasets") or []:
            if not isinstance(dataset_item, dict):
                continue
            try:
                item_dataset_id = int(dataset_item.get("dataset_id") or 0)
            except Exception:
                item_dataset_id = 0
            if item_dataset_id not in allowed_ids:
                continue
            for node in dataset_item.get("nodes") or []:
                if not isinstance(node, dict):
                    continue
                if str(node.get("node_level") or "").strip() not in levels:
                    continue
                node_name = str(node.get("node_name") or "").strip()
                if node_name:
                    members.add(node_name)
        return members

    def _node_index_member_level_map(self, context: Dict[str, Any]) -> Dict[str, str]:
        dataset_ids = self._current_dataset_ids_for_node_index(context)
        if not dataset_ids:
            return {}
        node_index = getattr(self, "_dataset_node_index", None)
        if not isinstance(node_index, dict):
            node_index = self._load_dataset_node_index()
            self._dataset_node_index = node_index
        allowed_ids = {int(item) for item in dataset_ids}
        level_map: Dict[str, str] = {}
        for dataset_item in node_index.get("datasets") or []:
            if not isinstance(dataset_item, dict):
                continue
            try:
                item_dataset_id = int(dataset_item.get("dataset_id") or 0)
            except Exception:
                item_dataset_id = 0
            if item_dataset_id not in allowed_ids:
                continue
            for node in dataset_item.get("nodes") or []:
                if not isinstance(node, dict):
                    continue
                node_name = str(node.get("node_name") or "").strip()
                node_level = str(node.get("node_level") or "").strip()
                if node_name and node_level:
                    level_map[node_name] = node_level
        return level_map

    def _node_index_subject_names_from_question(self, question: str, context: Dict[str, Any]) -> List[str]:
        text = str(question or "").replace("\n", " ").strip()
        if not text:
            return []
        dataset_ids = self._current_dataset_ids_for_node_index(context)
        if not dataset_ids:
            return []
        generic_level_aliases = {
            "事业部", "分公司", "代表处", "业务部", "城市分公司", "城市公司",
            "业务代表", "业务员", "承接人", "业务承接人", "业务承接角色",
        }
        expanded_text = text
        compound_aliases = {
            "东西部": "东部 西部",
            "东部西部": "东部 西部",
            "南北部": "南部 北部",
            "南部北部": "南部 北部",
        }
        for raw, expanded in compound_aliases.items():
            expanded_text = expanded_text.replace(raw, expanded)
        candidates: List[Tuple[int, int, str]] = []
        node_index = getattr(self, "_dataset_node_index", None)
        if not isinstance(node_index, dict):
            node_index = self._load_dataset_node_index()
            self._dataset_node_index = node_index
        allowed_ids = {int(item) for item in dataset_ids}
        for alias_item in node_index.get("flat_alias_index") or []:
            alias = str(alias_item.get("alias") or "").strip()
            if len(alias) < 2 or alias in generic_level_aliases:
                continue
            pos = expanded_text.find(alias)
            if pos < 0:
                continue
            for match in alias_item.get("matches") or []:
                try:
                    match_dataset_id = int(match.get("dataset_id") or 0)
                except Exception:
                    match_dataset_id = 0
                if match_dataset_id not in allowed_ids:
                    continue
                node_name = str(match.get("node_name") or "").strip()
                node_level = str(match.get("node_level") or "").strip()
                if not node_name or node_name in generic_level_aliases or node_level in {"事业部"}:
                    continue
                candidates.append((pos, -len(alias), node_name))
        result: List[str] = []
        for _, _, node_name in sorted(candidates):
            if node_name not in result:
                result.append(node_name)
        return result

    def _question_subject_names(self, question: str, context: Dict[str, Any], include_resolved: bool = True) -> List[str]:
        names = self._resolved_entity_names(context) if include_resolved else []
        if not self._has_specific_node(context):
            return names
        text = str(question or "").replace("\n", " ").strip()

        # 优先提取带角色前缀的具体人名（如“业务代表靳锋”），角色前缀比语义解析更精确，
        # 避免把“商用事业部”这样的数据集根节点别名误判为查询主体。
        role_person_names = self._role_person_subject_names(text)
        if role_person_names:
            for candidate in role_person_names:
                if candidate not in names:
                    names.append(candidate)
            return names

        dataset = self._safe_dict(context.get("dataset"))
        profile = get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
        if profile:
            semantic = resolve_member_mentions(question, profile)
            for name in semantic.get("all_members") or []:
                value = str(name or "").strip()
                if not value:
                    continue
                expanded = self._expand_coordinated_subject_names(value)
                if expanded:
                    for item in expanded:
                        if item and item not in names:
                            names.append(item)
                elif value not in names:
                    names.append(value)
            if names:
                return names

        node_index_names = self._node_index_subject_names_from_question(text, context)
        if node_index_names:
            for name in node_index_names:
                if name not in names:
                    names.append(name)
            return names

        for candidate in self._role_person_subject_names(text):
            if candidate not in names:
                names.append(candidate)

        level_only_values = {"分公司", "代表处", "业务部", "事业部", "城市公司", "城市分公司", "业务代表"}

        def _is_level_only_candidate(value: str) -> bool:
            bare = re.sub(r"^的+", "", value)
            return value in level_only_values or bare in level_only_values

        for match in re.findall(r"[\u4e00-\u9fa5A-Za-z0-9（）()]+?(?:代表处|分公司|业务部|事业部)", text):
            cleaned = match.strip("，,、 和与及的业绩情况表现整体")
            if re.search(r"^(?:三|四|五|六|七|八|九|十|两|\d+)(?:个|大)?", cleaned):
                continue
            if any(token in cleaned for token in ["哪些", "所有", "各", "每个", "业务线", "任务完成", "最好", "最高", "最低", "哪个"]):
                continue
            if self._looks_like_structural_subject_phrase(cleaned):
                continue
            if _is_level_only_candidate(cleaned):
                continue
            if cleaned and cleaned not in names:
                names.append(cleaned)

        # 支持并列人名："赵标和靳锋的业绩"、"赵标、靳锋及钱明的业绩"
        coordinated_name = r"[\u4e00-\u9fa5]{2,4}(?:(?:和|与|及|跟|、|,|，)[\u4e00-\u9fa5]{2,4})*"
        metric_person_suffix = r"(?:业绩|绩效|达成率|达成|开单|完成情况|完成|情况|表现|总任务金额|任务金额|年度开单金额|开单金额|剩余任务金额|剩余金额|缺口|金额|总数|总量|总额|数量)"
        person_patterns = [
            r"(?:帮我)?(?:看下|看一下|查一下|查询|分析一下|分析|看看|了解一下|了解|问下|问一下)\s*(" + coordinated_name + r")(?:的)?" + metric_person_suffix,
            r"(?:问的是|查询的是|看的是|主体是|节点是|人员是|业务员是|业务代表是)\s*(" + coordinated_name + r")",
            r"(?<![\u4e00-\u9fa5])(" + coordinated_name + r")(?:的)?" + metric_person_suffix,
        ]
        non_person_terms = {
            "业务代表", "业务员", "业务经理", "销售人员", "销售", "代表处",
            "分公司", "业务部", "事业部", "城市公司", "城市分公司", "商用事业部",
        }
        for pattern in person_patterns:
            for match in re.findall(pattern, text):
                candidate = str(match or "").strip("，,、 的呢吗么吧")
                candidate = re.sub(r"^(看下|看一下|查一下|查询|分析一下|分析|看看|了解一下|了解|问下|问一下)", "", candidate).strip()
                # 正则贪婪可能把"的"吞入人名，如"靳锋的总任务金额" -> "靳锋的总"
                candidate = candidate.split("的")[0].strip()
                for value in self._expand_coordinated_subject_names(candidate):
                    if value in non_person_terms:
                        continue
                    if value not in names:
                        names.append(value)
        org_pattern = (
            r"(?:请|麻烦|帮我|帮忙|我想看|我想查|我想问|想看|想查|想问)?"
            r"(?:看下|看一下|查下|查一下|查询下|查询一下|问下|问一下|分析下|分析一下|了解下|了解一下)?"
            r"\s*([\u4e00-\u9fa5A-Za-z0-9（）()]+?(?:代表处|分公司|业务部|城市分公司|城市公司))"
            r"(?=\s*(?:的?(?:业绩|表现|情况|达成率|开单|排名)|呢|吗|呀|吧|$))"
        )
        for match in re.findall(org_pattern, text):
            cleaned = self._clean_org_subject_candidate(match)
            if cleaned and cleaned not in names and not self._looks_like_structural_subject_phrase(cleaned) and not _is_level_only_candidate(cleaned):
                names.append(cleaned)
        return self._normalize_dataset_subject_names(names, context)

    @staticmethod
    def _clean_org_subject_candidate(value: str) -> str:
        return ask_engine_utils._clean_org_subject_candidate(value)

    def _normalize_dataset_subject_names(
        self,
        names: List[str],
        context: Dict[str, Any],
    ) -> List[str]:
        normalized: List[str] = []
        dataset = self._safe_dict(context.get("dataset"))
        try:
            dataset_id = int(dataset.get("id") or 0)
        except Exception:
            dataset_id = 0
        candidate_names: List[str] = []
        if dataset_id:
            permissions = load_data_permissions()
            nodes = self.organization_route_resolver._load_tree().get("nodes") or []
            for node in nodes:
                if not isinstance(node, dict) or not node.get("enabled", True):
                    continue
                try:
                    node_dataset_ids = self.organization_route_resolver._dataset_ids_for_node(node, permissions)
                except Exception:
                    node_dataset_ids = []
                if not any(int(item) == dataset_id for item in node_dataset_ids):
                    continue
                name = str(node.get("name") or "").strip()
                if len(name) >= 2:
                    candidate_names.append(name)
        unique_candidates = sorted(set(candidate_names))
        for raw in names or []:
            cleaned = self._clean_org_subject_candidate(raw)
            if unique_candidates and cleaned not in unique_candidates:
                matches = get_close_matches(cleaned, unique_candidates, n=1, cutoff=0.72)
                if matches:
                    cleaned = matches[0]
            if cleaned and cleaned not in normalized:
                normalized.append(cleaned)
        return normalized

    _GENERIC_LEVEL_ALIASES = {
        "分公司", "代表处", "业务部", "业务代表", "业务员",
        "城市分公司", "城市公司", "事业部", "业务承接人",
    }

    # 口语/显示层级词 -> 节点索引中标准化的 node_level
    _GENERIC_LEVEL_ALIAS_NORMALIZATION = {
        "业务承接人": "承接人",
    }

    def _generic_level_dataset_matches(
        self,
        candidate: str,
        dataset_ids: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        """
        当候选词是纯粹的通用层级词（如"分公司"）时，按数据集聚合并返回每个支持该层级的数据集代表。
        这样可以让"分公司业绩如何"这类问题弹数据集确认，而不是被 LLM 擅自选走。
        """
        normalized = self._normalize_compact_text(candidate)
        if normalized not in self._GENERIC_LEVEL_ALIASES:
            return []
        level_to_match = self._GENERIC_LEVEL_ALIAS_NORMALIZATION.get(normalized, normalized)
        allowed_ids = {int(item) for item in (dataset_ids or []) if item is not None}
        matches: List[Dict[str, Any]] = []
        seen: set = set()
        for alias_item in self._dataset_node_index.get("flat_alias_index") or []:
            for item in (alias_item.get("matches") or []):
                try:
                    dataset_id = int(item.get("dataset_id") or 0)
                except Exception:
                    continue
                if allowed_ids and dataset_id not in allowed_ids:
                    continue
                if self._normalize_compact_text(item.get("node_level") or "") != level_to_match:
                    continue
                key = (dataset_id, level_to_match)
                if key in seen:
                    continue
                seen.add(key)
                dataset_name = str(item.get("dataset_name") or "").strip()
                matches.append({
                    "dataset_id": dataset_id,
                    "dataset_name": dataset_name,
                    "node_name": level_to_match,
                    "node_level": level_to_match,
                    "parent_name": None,
                    "track": str(item.get("track") or "").strip(),
                    "alias": normalized,
                })
        return matches

    _BARE_NODE_INDICATOR_TOKENS = (
        "业绩", "排名", "排行", "排序", "开单", "任务", "达成",
        "表现", "数据", "金额", "收入", "销量", "指标", "情况",
        "咋样", "怎样", "如何", "对比", "比较", "差异",
        "前", "后", "倒数", "最高", "最低", "最好", "最差",
        "Top", "top", "TOP",
    )

    def _extract_bare_node_candidate(self, question: str) -> str:
        """从短裸节点问题中提取候选主体名（如"查询丁杰"→"丁杰"）。
        仅当问题长度 ≤ 8 字、且不含业务指标词时返回剥离后的主体名；
        否则返回空字符串，让原路径继续处理。"""
        if not question:
            return ""
        stripped = str(question).strip()
        # 长度过长（> 8 字）说明问题有较多修饰，不太可能是裸节点
        if len(stripped) > 8:
            return ""
        # 含指标词 → 不是裸节点
        if any(token in stripped for token in self._BARE_NODE_INDICATOR_TOKENS):
            return ""
        # 剥常见口语前缀
        for prefix in ("查询", "看下", "看看", "麻烦帮我查", "麻烦帮我看", "帮我查", "帮我看"):
            if stripped.startswith(prefix) and len(stripped) > len(prefix):
                return stripped[len(prefix):].strip()
        return stripped

    def _node_index_matches(
        self,
        candidate: str,
        dataset_ids: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        normalized_candidate = self._normalize_compact_text(candidate)
        if not normalized_candidate:
            return []
        allowed_ids = {int(item) for item in (dataset_ids or []) if item is not None}
        # 优先精确匹配；无精确命中时，取最长前缀匹配的别名，避免 "上海代表处" 被 "上海" 覆盖。
        matched_aliases: List[Tuple[str, int, List[Dict[str, Any]]]] = []
        for alias_item in self._dataset_node_index.get("flat_alias_index") or []:
            alias = str(alias_item.get("alias") or "").strip()
            normalized_alias = self._normalize_compact_text(alias)
            if normalized_alias == normalized_candidate or normalized_candidate.startswith(normalized_alias):
                matched_aliases.append((alias, len(normalized_alias), alias_item.get("matches") or []))
        if not matched_aliases:
            # 兜底：候选词是通用层级词时，按数据集聚合返回支持该层级的数据集代表
            return self._generic_level_dataset_matches(candidate, dataset_ids=dataset_ids)
        exact = next((item for item in matched_aliases if len(item[0]) == len(candidate)), None)
        if exact is None:
            exact = next((item for item in matched_aliases if self._normalize_compact_text(item[0]) == normalized_candidate), None)
        selected_aliases = [exact] if exact else [
            item for item in matched_aliases
            if item[1] == max(a[1] for a in matched_aliases)
        ]
        matches: List[Dict[str, Any]] = []
        seen: set = set()
        for alias, _, item_matches in selected_aliases:
            for item in item_matches:
                try:
                    dataset_id = int(item.get("dataset_id") or 0)
                except Exception:
                    dataset_id = 0
                if allowed_ids and dataset_id not in allowed_ids:
                    continue
                payload = {
                    "dataset_id": dataset_id,
                    "dataset_name": str(item.get("dataset_name") or "").strip(),
                    "node_name": str(item.get("node_name") or "").strip(),
                    "node_level": str(item.get("node_level") or "").strip(),
                    "parent_name": None if item.get("parent_name") is None else str(item.get("parent_name") or "").strip(),
                    "track": str(item.get("track") or "").strip(),
                    "alias": alias,
                }
                key = (
                    payload["dataset_id"],
                    payload["node_name"],
                    payload["node_level"],
                    payload["parent_name"],
                    payload["track"],
                )
                if key in seen:
                    continue
                seen.add(key)
                matches.append(payload)
        return matches

    def _node_index_unique_match(
        self,
        candidate: str,
        dataset_ids: Optional[List[int]] = None,
    ) -> Optional[Dict[str, Any]]:
        matches = self._node_index_matches(candidate, dataset_ids=dataset_ids)
        if len(matches) == 1:
            return matches[0]
        return None

    @staticmethod
    def _node_index_match_key(item: Dict[str, Any]) -> Tuple[int, str, str, str, str]:
        return ask_engine_utils._node_index_match_key(item)

    def _dedupe_node_index_matches(
        self,
        matches: List[Dict[str, Any]],
        dataset_ids: Optional[set[int]] = None,
    ) -> List[Dict[str, Any]]:
        deduped: List[Dict[str, Any]] = []
        seen: set = set()
        for item in matches or []:
            try:
                dataset_id = int(item.get("dataset_id") or 0)
            except Exception:
                continue
            if dataset_ids is not None and dataset_id not in dataset_ids:
                continue
            key = self._node_index_match_key(item)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    @staticmethod
    def _extract_subject_from_confirmation_label(label: str) -> str:
        return ask_engine_utils._extract_subject_from_confirmation_label(label)

    def _role_person_subject_names(self, question: str) -> List[str]:
        text = str(question or "").replace("\n", " ").strip()
        names: List[str] = []
        role_person_patterns = [
            r"(?:商用事业部|商用|安吉尔商用事业部)?(?:的)?(?:业务代表|业务员|业务经理|销售人员|销售)\s*([\u4e00-\u9fa5]{2,4}(?:(?:和|与|及|跟|、|,|，)[\u4e00-\u9fa5]{2,4})+|[\u4e00-\u9fa5]{2,4})(?=\s*(?:的|业绩|绩效|达成率|达成|开单|完成情况|完成|情况|表现|总任务金额|任务金额|年度开单金额|开单金额|剩余任务金额|剩余金额|缺口|金额|总数|总量|总额|数量|$|[，,。？?]))",
            r"(?:业务代表|业务员|业务经理|销售人员|销售)(?:是|为|叫|：|:)\s*([\u4e00-\u9fa5]{2,4})",
        ]
        for pattern in role_person_patterns:
            for match in re.findall(pattern, text):
                candidate = str(match or "").strip("，,、 的呢吗么吧")
                candidate = candidate.split("的")[0].strip()
                for value in self._expand_coordinated_subject_names(candidate):
                    if value not in names:
                        names.append(value)
        return names

    def _prepare_subject_safe_sample_sql(
        self,
        question: str,
        context: Dict[str, Any],
        sql_text: str,
    ) -> Dict[str, Any]:
        requested = self._question_subject_names(question, context)
        sample_literals = self._sql_subject_filter_literals(sql_text)
        if not requested or not sample_literals:
            return {"sql": sql_text, "rewritten": False, "conflict": False}

        requested_keys = {self._normalize_entity_key(item) for item in requested}
        sample_keys = {self._normalize_entity_key(item) for item in sample_literals}
        if requested_keys.intersection(sample_keys):
            return {"sql": sql_text, "rewritten": False, "conflict": False}

        if len(requested) == 1 and len(sample_literals) == 1:
            old_value = sample_literals[0]
            new_value = requested[0]
            escaped_old = re.escape(old_value.replace("'", "''"))
            escaped_new = new_value.replace("'", "''")
            rewritten = re.sub(rf"'{escaped_old}'", f"'{escaped_new}'", str(sql_text or ""))
            return {"sql": rewritten, "rewritten": rewritten != sql_text, "conflict": False}

        return {"sql": sql_text, "rewritten": False, "conflict": True}

    def _build_result_confidence(self, route: Dict[str, Any], dataset_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        dataset_results = dataset_results or []
        reviews = [self._safe_dict(item.get("agent3_review")) for item in dataset_results if item.get("agent3_review") is not None]
        approved_count = sum(1 for item in reviews if item.get("approved") is not False)
        risk_count = sum(len(item.get("risks") or []) for item in reviews)
        dataset_total = len(dataset_results)
        rows_ready = sum(1 for item in dataset_results if item.get("rows"))
        analyses_ready = sum(1 for item in dataset_results if str(item.get("analysis") or "").strip())

        score = 55
        if dataset_total > 0:
            score += 8
        if dataset_total > 0 and rows_ready == dataset_total:
            score += 16
        elif rows_ready > 0:
            score += 8
        if dataset_total > 0 and len(reviews) == dataset_total and approved_count == dataset_total:
            score += 12
        elif approved_count > 0:
            score += 6
        if dataset_total > 0 and analyses_ready == dataset_total:
            score += 8
        score -= min(18, risk_count * 4)
        if self._build_route_confidence(route).get("candidate_count", 0) > 1:
            score -= 5

        score = max(0, min(100, int(score)))
        level = "high" if score >= 80 else "medium" if score >= 62 else "low"
        label = "稳定" if score >= 80 else "可用" if score >= 62 else "谨慎"

        if risk_count > 0:
            summary = f"当前仍有 {risk_count} 项 SQL 复核风险，建议结合执行详情复查。"
        elif rows_ready == 0:
            summary = "当前没有拿到有效结果行，建议回看 SQL 与数据集口径。"
        else:
            summary = "结果、复核和分析摘要已经形成闭环，可作为当前结论依据。"

        return {
            "score": score,
            "level": level,
            "label": label,
            "summary": summary,
            "dataset_count": dataset_total,
            "rows_ready": rows_ready,
            "analysis_ready": analyses_ready,
            "review_count": len(reviews),
            "approved_count": approved_count,
            "risk_count": risk_count,
        }

    def _build_confidence_payload(
        self,
        route: Dict[str, Any],
        dataset_results: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "route": self._build_route_confidence(route),
            "result": None,
        }
        if dataset_results is not None:
            payload["result"] = self._build_result_confidence(route, dataset_results)
        return payload

    def _chat(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2400,
        trace: Optional[Dict[str, Any]] = None,
        stage: str = "",
        agent_name: str = "",
    ) -> str:
        return self._llm_component()._chat(
            system_prompt, user_prompt, max_tokens, trace, stage, agent_name
        )

    def _chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        fallback: Dict[str, Any],
        trace: Optional[Dict[str, Any]] = None,
        stage: str = "",
        agent_name: str = "",
    ) -> Dict[str, Any]:
        return self._llm_component()._chat_json(
            system_prompt, user_prompt, fallback, trace, stage, agent_name
        )

    def _get_agent_prompt(self, agent_no: int, fallback: str) -> str:
        agent = get_agent(agent_no)
        prompt = (agent or {}).get("system_prompt") or fallback
        knowledge = "\n".join(f"- {item}" for item in (agent or {}).get("knowledge_base", []))
        return f"{prompt}\n\n补充知识：\n{knowledge}".strip()

    def _build_report_config_prompt(self, context: Dict[str, Any]) -> str:
        config = self._safe_dict(context.get("report_config")) or report_config_store.get_default_config()
        if not config:
            return ""
        resolved_entities = context.get("resolved_entities") or {}
        org_tree_hint = ""
        for entity in resolved_entities.get("entities") or []:
            if not isinstance(entity, dict):
                continue
            if str(entity.get("source") or "") == "organization_tree_route":
                members = [str(m) for m in (entity.get("members") or []) if str(m).strip()]
                if members:
                    org_tree_hint = (
                        f"\u7ec4\u7ec7\u6811\u5df2\u547d\u4e2d\u8282\u70b9\uff1a{', '.join(members)}\u3002"
                        f"\u8bf7\u4e25\u683c\u6309\u7528\u6237\u539f\u8bdd\u7684\u5c42\u7ea7\u8bcd\u6c47\u751f\u6210 SQL\uff0c"
                        f"\u4e0d\u8981\u81ea\u884c\u5347\u7ea7\u6216\u964d\u7ea7\u5c42\u7ea7\u3002"
                        f"\u4f8b\u5982\u7528\u6237\u8bf4\u201c\u5206\u516c\u53f8\u201d\u5c31\u67e5\u5206\u516c\u53f8\u5c42\u7ea7\uff0c"
                        f"\u4e0d\u8981\u66ff\u6362\u6210\u201c\u57ce\u5e02\u5206\u516c\u53f8\u201d\uff1b"
                        f"\u7528\u6237\u8bf4\u201c\u57ce\u5e02\u5206\u516c\u53f8\u201d\u624d\u67e5\u57ce\u5e02\u5206\u516c\u53f8\u5c42\u7ea7\u3002"
                    )
                    break
        payload = {
            "businessContext": config.get("businessContext", ""),
            "standardColumns": {
                "nameColumn": config.get("nameColumn"),
                "parentColumn": config.get("parentColumn"),
                "trackColumn": config.get("trackColumn"),
                "levelColumn": config.get("levelColumn"),
            },
            "sourceFields": config.get("sourceFields") or {},
            "sqlOutputContract": config.get("sqlOutputContract") or {},
            "analysisDimensions": config.get("analysisDimensions") or [],
            "metrics": config.get("metrics") or [],
            "levels": config.get("levels") or [],
            "queryIntent": context.get("query_intent") or {},
            "intentPolicies": config.get("intentPolicies") or {},
            "riskThreshold": config.get("riskThreshold"),
            "dynamicPerformanceRule": "\u62a5\u544a\u4e2d\u7684\u597d/\u5dee\u8282\u70b9\u5fc5\u987b\u57fa\u4e8e\u672c\u6b21\u7ed3\u679c\u52a8\u6001\u5206\u7ec4\uff1b\u4e0d\u8981\u6309\u56fa\u5b9a\u9608\u503c\u6216\u56fa\u5b9a TopN \u786c\u5207\u3002\u597d/\u5dee\u4e24\u7ec4\u4e0d\u5f97\u91cd\u590d\uff1b\u53ef\u6bd4\u5bf9\u8c61\u5c11\u4e8e 2 \u4e2a\u65f6\u4e0d\u505a\u6a2a\u5411\u5bf9\u6bd4\u3002",
            "agentReportGuidance": config.get("agentReportGuidance", ""),
            "resolvedQuestionScope": resolved_entities,
        }
        if org_tree_hint:
            payload["organizationTreeLevelGuidance"] = org_tree_hint
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _build_sql_output_contract_prompt(self, context: Dict[str, Any]) -> str:
        config = self._safe_dict(context.get("report_config")) or report_config_store.get_default_config()
        if not config:
            return ""
        contract = self._safe_dict(config.get("sqlOutputContract"))
        amount_unit = str(
            contract.get("amountUnit")
            or config.get("amountUnit")
            or config.get("amountUnitConvention")
            or ""
        ).strip() or "元"
        metric_columns = contract.get("metricColumns") if isinstance(contract.get("metricColumns"), list) else []
        amount_columns = [
            str(item)
            for item in metric_columns
            if re.search(r"金额|任务|开单|缺口|剩余|销售|收入|成本|利润", str(item))
        ] or ["总任务金额", "年度开单金额", "剩余任务金额"]
        return "\n".join([
            "SQL 输出单位统一规则：",
            f"1. 本数据集标准金额列输出单位为“{amount_unit}”。",
            f"2. 以下金额列必须按“{amount_unit}”口径输出数值，不要在列值里拼接中文单位：{', '.join(amount_columns)}。",
            "3. 如果源字段是元而输出单位为万元，SQL 中必须除以 10000；如果源字段已经是万元，不能再次除以 10000。",
            "4. 如果源字段是万元而输出单位为元，SQL 中必须乘以 10000；如果源字段已经是元，不能再次乘以 10000。",
            "5. 达成率统一输出 0-100 的数字，不要带百分号。",
            "6. SQL 结果只输出纯数值；前端/报告层会根据 report_config 展示 万/亿。",
        ])

    @staticmethod
    def _profile_catalog(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        return ask_engine_utils._profile_catalog(profile)

    @staticmethod
    def _profile_member_map(profile: Dict[str, Any]) -> Dict[str, str]:
        return ask_engine_utils._profile_member_map(profile)

    @staticmethod
    def _normalize_llm_ranking_params(raw_ranking: Any) -> Optional[Dict[str, Any]]:
        return ask_engine_utils._normalize_llm_ranking_params(raw_ranking)

    @staticmethod
    def _normalize_entity_resolution(
        raw: Dict[str, Any],
        fallback: Dict[str, Any],
        profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        return ask_engine_utils._normalize_entity_resolution(raw, fallback, profile)

    @staticmethod
    def _profile_scope_hint(question: str, profile: Dict[str, Any], fallback: Dict[str, Any]) -> bool:
        return ask_engine_utils._profile_scope_hint(question, profile, fallback)

    def _ranking_semantic_hint(self, question: str, context: Dict[str, Any]) -> bool:
        text = self._normalize_chinese_numbers(str(question or "").replace("\n", " "))
        if not text.strip():
            return False
        config = self._safe_dict(context.get("report_config")) or report_config_store.get_default_config()
        ranking_policy = self._safe_dict(self._safe_dict(config.get("intentPolicies")).get("ranking"))
        triggers = [str(item) for item in (ranking_policy.get("triggers") or []) if str(item).strip()]
        semantic_tokens = [
            "排名", "排行", "排序", "名次", "榜", "最高", "最低", "最好", "最差",
            "最多", "最少", "最大", "最小", "垫底", "倒数", "落后", "领先",
            "从高到低", "从低到高",
        ]
        if any(token in text for token in semantic_tokens):
            return True
        for trigger in triggers:
            if trigger in {"前", "后"}:
                if re.search(rf"{re.escape(trigger)}\s*(?:\d+|[一二两三四五六七八九十]+)", text):
                    return True
            elif trigger.lower() == "top":
                if re.search(r"\btop\s*(?:\d+|[一二两三四五六七八九十]+)?", text, flags=re.I):
                    return True
            elif trigger.lower() in text.lower():
                return True
        return False

    def _node_index_resolution_catalog(self, context: Dict[str, Any]) -> Dict[str, Any]:
        dataset = self._safe_dict(context.get("dataset"))
        dataset_id = self._safe_int(dataset.get("id"), 0)
        dataset_code = str(dataset.get("dataset_code") or "").strip()
        dataset_name = str(dataset.get("dataset_name") or "").strip()
        node_index = getattr(self, "_dataset_node_index", None)
        if not isinstance(node_index, dict):
            node_index = self._load_dataset_node_index()

        matched_dataset: Dict[str, Any] = {}
        for item in node_index.get("datasets") or []:
            if not isinstance(item, dict):
                continue
            try:
                item_id = int(item.get("dataset_id") or 0)
            except Exception:
                item_id = 0
            item_code = str(item.get("dataset_code") or "").strip()
            item_name = str(item.get("dataset_name") or "").strip()
            if (
                (dataset_id and item_id == dataset_id)
                or (dataset_code and item_code == dataset_code)
                or (dataset_name and item_name == dataset_name)
            ):
                matched_dataset = item
                break

        levels: Dict[str, Dict[str, Any]] = {}
        for node in matched_dataset.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            level_name = str(node.get("node_level") or "").strip()
            node_name = str(node.get("node_name") or "").strip()
            if not level_name or not node_name:
                continue
            bucket = levels.setdefault(level_name, {"dimension_name": level_name, "members": [], "aliases": []})
            if node_name not in bucket["members"]:
                bucket["members"].append(node_name)
            for alias in node.get("aliases") or []:
                alias_text = str(alias or "").strip()
                if alias_text and alias_text not in bucket["aliases"]:
                    bucket["aliases"].append(alias_text)

        config = self._safe_dict(context.get("report_config")) or report_config_store.get_default_config()
        ranking_policy = self._safe_dict(self._safe_dict(config.get("intentPolicies")).get("ranking"))
        for level_name, aliases in self._safe_dict(ranking_policy.get("targetLevelAliases")).items():
            name = str(level_name or "").strip()
            if not name:
                continue
            bucket = levels.setdefault(name, {"dimension_name": name, "members": [], "aliases": []})
            for alias in aliases or []:
                alias_text = str(alias or "").strip()
                if alias_text and alias_text not in bucket["aliases"]:
                    bucket["aliases"].append(alias_text)

        known_levels = {
            "事业部", "分公司", "业务部", "代表处", "业务代表", "业务员",
            "城市分公司", "城市公司", "承接人", "业务承接角色",
        }
        for item in context.get("data_dictionary") or []:
            if not isinstance(item, dict):
                continue
            key = str(item.get("jsonb_key") or item.get("semantic_name") or item.get("column_name") or "").strip()
            if key and key in known_levels:
                levels.setdefault(key, {"dimension_name": key, "members": [], "aliases": [key]})

        return {
            "dataset": {
                "dataset_id": dataset_id or matched_dataset.get("dataset_id"),
                "dataset_code": dataset_code or matched_dataset.get("dataset_code"),
                "dataset_name": dataset_name or matched_dataset.get("dataset_name"),
            },
            "levels": [
                {
                    "dimension_name": level.get("dimension_name"),
                    "aliases": level.get("aliases", [])[:20],
                    "members": level.get("members", [])[:60],
                }
                for level in levels.values()
            ],
        }

    def _normalize_node_index_entity_resolution(
        self,
        raw: Dict[str, Any],
        fallback: Dict[str, Any],
        catalog: Dict[str, Any],
    ) -> Dict[str, Any]:
        level_names = {
            str(item.get("dimension_name") or "").strip()
            for item in catalog.get("levels") or []
            if isinstance(item, dict)
        }
        member_to_level: Dict[str, str] = {}
        for level in catalog.get("levels") or []:
            if not isinstance(level, dict):
                continue
            level_name = str(level.get("dimension_name") or "").strip()
            for member in level.get("members") or []:
                member_name = str(member or "").strip()
                if member_name:
                    member_to_level[member_name] = level_name

        ordered_members: List[str] = []
        entities_by_dimension: Dict[str, Dict[str, Any]] = {}
        for entity in raw.get("entities") or []:
            if not isinstance(entity, dict):
                continue
            dimension_name = str(entity.get("dimension_name") or "").strip()
            if dimension_name and dimension_name not in level_names:
                continue
            for member in entity.get("members") or []:
                member_name = str(member or "").strip()
                if not member_name or (member_to_level and member_name not in member_to_level):
                    continue
                resolved_dimension = dimension_name or member_to_level.get(member_name) or ""
                if member_name not in ordered_members:
                    ordered_members.append(member_name)
                bucket = entities_by_dimension.setdefault(
                    resolved_dimension,
                    {
                        "dimension_name": resolved_dimension,
                        "members": [],
                        "matched_phrase": str(entity.get("matched_phrase") or entity.get("matched_alias") or "").strip(),
                        "source": "llm_node_index_semantic",
                    },
                )
                if member_name not in bucket["members"]:
                    bucket["members"].append(member_name)

        scope_mode = str(raw.get("scope_mode") or raw.get("intent") or fallback.get("scope_mode") or "").lower()
        if len(ordered_members) > 1:
            scope_mode = "compare"
        elif len(ordered_members) == 1 and scope_mode not in {"aggregate", "ranking"}:
            scope_mode = "single"
        elif not ordered_members and scope_mode not in {"ranking", "aggregate"}:
            scope_mode = "unknown"

        confidence = raw.get("confidence", fallback.get("confidence", 0))
        try:
            confidence_value = float(confidence)
        except Exception:
            confidence_value = 0

        has_specific_node = raw.get("has_specific_node")
        if not isinstance(has_specific_node, bool):
            has_specific_node = bool(ordered_members)

        return {
            "intent": "compare" if scope_mode == "compare" else ("single" if scope_mode == "single" else str(raw.get("intent") or fallback.get("intent") or "unknown")),
            "scope_mode": scope_mode,
            "entities": list(entities_by_dimension.values()),
            "all_members": ordered_members,
            "confidence": confidence_value,
            "source": "llm_node_index_semantic" if raw else fallback.get("source", "no_profile"),
            "ranking_params": self._normalize_llm_ranking_params(raw.get("ranking_params")),
            "has_specific_node": has_specific_node,
        }

    def _resolve_question_entities_with_node_index(
        self,
        question: str,
        context: Dict[str, Any],
        fallback: Dict[str, Any],
        trace: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        catalog = self._node_index_resolution_catalog(context)
        system_prompt = (
            "你是 SmartAsk 语义结构化拆解器。你的任务不是生成 SQL，而是把用户问题拆成稳定的结构化意图，"
            "并用给定的真实节点索引和字段层级做事实校验。不要编造节点；没有点名具体节点时 entities 留空。"
        )
        user_prompt = f"""
用户问题：
{question}

当前数据集事实索引：
{json.dumps(catalog, ensure_ascii=False, indent=2)}

请输出 JSON：
{{
  "intent": "compare|single|aggregate|ranking|unknown",
  "scope_mode": "compare|single|aggregate|ranking|unknown",
  "entities": [
    {{
      "dimension_name": "候选层级名",
      "members": ["候选节点名"],
      "matched_phrase": "用户原话中触发的短语",
      "reason": "一句话说明"
    }}
  ],
  "ranking_params": {{
    "top_n": null,
    "rank_sides": null,
    "direction": null,
    "metric_hint": null
  }},
  "has_specific_node": false,
  "confidence": 0.0
}}

约束：
1. 排名/TopN/前几/后几/倒数/垫底/最好/最差等问题，scope_mode=ranking，并填写 ranking_params。
2. top_n 只填写用户明确要求的数量；未明确数量填 null。
3. rank_sides 只能是 top、bottom、both；direction 只能是 desc 或 asc。
4. 只提到层级或集合口径（如“分公司”“城市分公司”“垫底的5个城市分公司”）时，has_specific_node=false，entities 留空。
5. 点名真实节点（如“上海城市公司”“东部分公司”“赵标”）时，才从候选 members 中选择 entities。
"""
        raw = self._chat_json(
            system_prompt,
            user_prompt,
            fallback,
            trace=trace,
            stage="agent1.node_index_entity_resolution",
            agent_name="Agent1.5",
        )
        resolved = self._normalize_node_index_entity_resolution(raw, fallback, catalog)
        self._append_trace(
            trace,
            "pipeline.node_index_entity_resolution",
            "info",
            dataset=catalog.get("dataset"),
            resolved_entities=resolved,
        )
        return resolved

    def _resolve_question_entities(
        self,
        question: str,
        context: Dict[str, Any],
        trace: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        dataset = self._safe_dict(context.get("dataset"))
        profile = get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
        if not profile:
            fallback = {
                "intent": "unknown",
                "scope_mode": "unknown",
                "entities": [],
                "all_members": [],
                "confidence": 0,
                "source": "no_profile",
            }
            if self._ranking_semantic_hint(question, context):
                return self._resolve_question_entities_with_node_index(question, context, fallback, trace=trace)
            return fallback

        fallback = resolve_member_mentions(question, profile)
        if not self._profile_scope_hint(question, profile, fallback):
            return fallback

        system_prompt = (
            "你是 Agent1.5 语义口径解析器。你的任务不是生成 SQL，而是把用户问题中的组织、层级、集合或并列表达，"
            "映射到给定数据集画像里的候选成员。只能从候选 members 中选择，不允许编造成员；如果用户使用简称、合称、"
            "并列词或省略后缀，需要结合候选成员理解真实统计对象。"
        )
        user_prompt = f"""
用户问题：
{question}

数据集画像候选维度：
{json.dumps(self._profile_catalog(profile), ensure_ascii=False, indent=2)}

规则：
1. 只从候选 members 中选择成员，不能输出候选外名称。
2. 用户表达多个同层级对象时，scope_mode=compare，并保持用户表达顺序。
3. 用户只表达一个组织对象时，scope_mode=single。
4. 用户表达集合口径但没有要求分别比较时，scope_mode=aggregate；若有“分别/各/对比/比较/谁更/差异”等比较意图，scope_mode=compare。
5. 用户问排名/TopN/前几/后几/垫底/倒数等时，scope_mode=ranking，并在 ranking_params 中输出数量与方向。
6. 不确定时 entities 留空，不要硬猜。
7. 判断用户是否明确指定了具体的组织节点：
   - 如果只提到层级或集合口径（如“分公司”“城市分公司”“大于一个亿的分公司”），没有点名具体分公司/代表处/业务部/城市分公司，has_specific_node=false。
   - 如果提到了“东部分公司”“上海城市分公司”“赵标”等具体节点名，has_specific_node=true。

请输出 JSON：
{{
  "intent": "compare|single|aggregate|ranking|unknown",
  "scope_mode": "compare|single|aggregate|ranking|unknown",
  "entities": [
    {{
      "dimension_name": "候选维度名",
      "members": ["候选成员名"],
      "matched_phrase": "用户原话中触发的短语",
      "reason": "一句话说明"
    }}
  ],
  "ranking_params": {{
    "top_n": null,
    "rank_sides": null,
    "direction": null,
    "metric_hint": null
  }},
  "has_specific_node": true,
  "confidence": 0.0
}}

ranking_params 说明：
- 仅在 scope_mode=ranking 或问题含排名意图时填写；否则为 null。
- top_n：用户明确要求的数量（如“前 3”=3，“垫底 5 家”=5）。未明确时填 null。
- rank_sides：top / bottom / both。例如“前 N”=top，“垫底/倒数/后 N”=bottom。
- direction：asc / desc。例如“最高/最好/前 N”=desc，“最低/最差/垫底/倒数”=asc。
- metric_hint：用户指定的排序指标，如“达成率”“开单金额”“任务金额”。未指定时填 null。
"""
        raw = self._chat_json(
            system_prompt,
            user_prompt,
            fallback,
            trace=trace,
            stage="agent1.entity_resolution",
            agent_name="Agent1.5",
        )
        resolved = self._normalize_entity_resolution(raw, fallback, profile)
        self._append_trace(
            trace,
            "pipeline.entity_resolution",
            "info",
            dataset_id=dataset.get("id"),
            dataset_name=dataset.get("dataset_name"),
            resolved_entities=resolved,
        )
        return resolved

    @staticmethod
    def _resolved_entity_names(context: Dict[str, Any]) -> List[str]:
        return ask_engine_utils._resolved_entity_names(context)

    @staticmethod
    def _dataset_root_name(dataset: Dict[str, Any]) -> str:
        return ask_engine_utils._dataset_root_name(dataset)

    @staticmethod
    def _is_dataset_root_name(name: str, dataset: Dict[str, Any]) -> bool:
        return ask_engine_utils._is_dataset_root_name(name, dataset)

    @staticmethod
    def _looks_like_ranking_question(question: str) -> bool:
        return ask_engine_utils._looks_like_ranking_question(question)

    @staticmethod
    def _route_entity_resolution(route: Dict[str, Any]) -> Dict[str, Any]:
        return ask_engine_utils._route_entity_resolution(route)

    @staticmethod
    def _tokenize(text: str) -> set:
        return ask_engine_utils._tokenize(text)

    @staticmethod
    def _normalize_compact_text(text: Any) -> str:
        return ask_engine_utils._normalize_compact_text(text)

    def _is_pure_generic_level_question(self, question: str, matched_levels: List[str]) -> bool:
        """
        判断问题是否为“纯通用层级”问题：只含通用层级词+通用业绩/排名词，
        没有任何明确的事业部/数据集别名标识。此类问题在多数据集都支持该层级时应弹确认。
        """
        if not matched_levels:
            return False
        compact = self._normalize_compact_text(question)
        # 通用层级词与通用意图词集合
        generic_words = {
            "分公司", "代表处", "业务部", "业务代表", "业务员", "城市分公司", "城市公司", "条线",
            "业绩", "排名", "排行", "排序", "达成", "开单", "任务", "表现", "情况", "如何", "怎么样",
            "垫底", "倒数", "落后", "最低", "最差", "最高", "最好", "前", "后", "top", "第",
            "低于", "高于", "超过", "大于", "小于", "不少于", "不低于", "不高于", "以上", "以下",
            "所有", "哪些", "几个", "几家", "各个", "各", "个", "家", "名", "位", "的", "和", "与", "或",
        }
        remaining = compact
        for word in sorted(generic_words, key=len, reverse=True):
            remaining = remaining.replace(word, "")
        remaining = re.sub(r"[0-9一二两三四五六七八九十百千万]+", "", remaining)
        # 如果去掉通用词后还有实质内容（>=2字），认为用户可能给了具体标识，不强制确认
        if len(remaining) >= 2:
            return False
        # 再检查是否有任何数据集别名强命中（>=90 分）
        catalog = self.repository.get_agent1_catalog()
        for ds in catalog:
            if self._dataset_alias_match_score(question, ds) >= 90:
                return False
        return True

    @staticmethod
    def _matched_org_level_terms(question: str) -> List[str]:
        return ask_engine_utils._matched_org_level_terms(question)

    def _build_dataset_level_confirmation_route(
        self,
        question: str,
        matched_levels: List[str],
        supported_candidates: List[Tuple[Dict[str, Any], int]],
        candidate_dataset_ids: Optional[List[int]] = None,
        match_score: int = 100,
        reason: str = "generic_level_requires_confirmation",
    ) -> Dict[str, Any]:
        options = []
        seen_ids: set[int] = set()
        for dataset, _score in supported_candidates:
            dataset_id = int(dataset.get("id") or 0)
            if dataset_id <= 0 or dataset_id in seen_ids:
                continue
            seen_ids.add(dataset_id)
            dataset_name = dataset.get("dataset_name") or f"数据集 {dataset_id}"
            options.append(
                self._build_confirmation_option(
                    option_id=f"dataset_scope_{dataset_id}",
                    label=dataset_name,
                    description=f"按 {dataset_name} 的“{'/'.join(matched_levels)}”口径继续。",
                    dataset_ids=[dataset_id],
                    option_type="dataset_disambiguation",
                    extra={
                        "confirmation_type": "dataset_disambiguation",
                        "resolved_dataset_name": dataset_name,
                        "scope_mode": "aggregate",
                    },
                )
            )
        dataset_ids = [int(item.get("id") or 0) for item, _score in supported_candidates if int(item.get("id") or 0) > 0]
        dataset_ids = list(dict.fromkeys(dataset_ids))
        return {
            "dataset_ids": dataset_ids,
            "intent": "confirm",
            "refined_query": question,
            "requires_confirmation": True,
            "decision": "wait_boss_confirm",
            "match_score": match_score,
            "confirmation_role": "boss",
            "confirmation_type": "dataset_disambiguation",
            "confirmation_question": f"问题中的“{'/'.join(matched_levels)}”在多个数据集中都可能出现，请确认使用哪个数据集口径：",
            "confirmation_options": options,
            "candidate_dataset_ids": candidate_dataset_ids or dataset_ids,
            "arbiter_reason": f"{reason}:{','.join(matched_levels)}",
        }

    @staticmethod
    def _normalize_known_sql_alias_typos(sql_text: str) -> str:
        return ask_engine_utils._normalize_known_sql_alias_typos(sql_text)

    @classmethod
    def _profile_level_alias_score(cls, question: str, profile: Optional[Dict[str, Any]]) -> int:
        if not profile:
            return 0
        normalized_question = cls._normalize_compact_text(question)
        if not normalized_question:
            return 0
        specific_levels = {
            "代表处",
            "办事处",
            "网点",
            "业务代表",
            "业务员",
            "业务经理",
            "承接人",
            "任务承接人",
            "负责人",
            "业务部",
            "行业业务部",
            "城市分公司",
        }
        score = 0
        for level in profile.get("levels") or []:
            aliases = [
                str(level.get("dimension_name") or ""),
                *[str(item or "") for item in (level.get("aliases") or [])],
            ]
            for alias in aliases:
                normalized_alias = cls._normalize_compact_text(alias)
                if not normalized_alias or normalized_alias not in specific_levels:
                    continue
                if normalized_alias in normalized_question:
                    score = max(score, 93)
        return score

    @classmethod
    def _profile_level_mismatch_penalty(cls, question: str, profile: Optional[Dict[str, Any]]) -> int:
        if not profile:
            return 0
        normalized_question = cls._normalize_compact_text(question)
        if not normalized_question:
            return 0
        specific_levels = {
            "代表处",
            "办事处",
            "网点",
            "业务代表",
            "业务员",
            "业务经理",
            "承接人",
            "任务承接人",
            "负责人",
            "业务部",
            "行业业务部",
            "城市分公司",
        }
        asked = {item for item in specific_levels if item in normalized_question}
        if not asked:
            return 0
        supported = set()
        for level in profile.get("levels") or []:
            aliases = [
                str(level.get("dimension_name") or ""),
                *[str(item or "") for item in (level.get("aliases") or [])],
            ]
            for alias in aliases:
                normalized_alias = cls._normalize_compact_text(alias)
                if normalized_alias in specific_levels:
                    supported.add(normalized_alias)
        unsupported = [item for item in asked if item not in supported]
        return -min(60, 35 * len(unsupported))

    @classmethod
    def _question_target_level_hint(cls, question: str) -> str:
        text = cls._normalize_compact_text(question)
        if not text:
            return ""
        for level in ("城市分公司", "城市公司", "业务经理", "业务代表", "业务员", "代表处", "业务部", "分公司", "事业部"):
            if cls._normalize_compact_text(level) in text:
                return level
        return ""

    @classmethod
    def _profile_supports_level(cls, profile: Optional[Dict[str, Any]], target_level: str) -> bool:
        normalized_target = cls._normalize_compact_text(target_level)
        if not profile or not normalized_target:
            return False
        for level in profile.get("levels") or []:
            aliases = [
                str(level.get("dimension_name") or ""),
                *[str(item or "") for item in (level.get("aliases") or [])],
            ]
            for alias in aliases:
                normalized_alias = cls._normalize_compact_text(alias)
                if normalized_alias and normalized_alias == normalized_target:
                    return True
        return False

    @classmethod
    def _context_supports_level(cls, context: Dict[str, Any], target_level: str) -> bool:
        normalized_target = cls._normalize_compact_text(target_level)
        if not normalized_target:
            return False
        dataset = context.get("dataset") if isinstance(context, dict) else {}
        profile = get_dataset_profile(
            (dataset or {}).get("dataset_code"),
            (dataset or {}).get("dataset_name"),
        )
        if profile:
            return cls._profile_supports_level(profile, target_level)
        return False

    @classmethod
    def _dataset_alias_supports_level(cls, dataset: Dict[str, Any], target_level: str) -> bool:
        normalized_target = cls._normalize_compact_text(target_level)
        if not normalized_target:
            return False
        aliases = [
            str(dataset.get("dataset_name") or ""),
            str(dataset.get("business_domain") or ""),
            *[str(item or "") for item in (dataset.get("synonyms") or [])],
        ]
        for alias in aliases:
            if normalized_target and normalized_target in cls._normalize_compact_text(alias):
                return True
        return False

    def _dataset_node_index_supports_level(self, dataset: Dict[str, Any], target_level: str) -> bool:
        normalized_target = self._normalize_compact_text(target_level)
        if not normalized_target:
            return False
        try:
            dataset_id = int(dataset.get("id") or 0)
        except Exception:
            dataset_id = 0
        dataset_code = self._normalize_compact_text(dataset.get("dataset_code") or "")
        dataset_name = self._normalize_compact_text(dataset.get("dataset_name") or "")
        node_index = getattr(self, "_dataset_node_index", None)
        if not isinstance(node_index, dict):
            node_index = self._load_dataset_node_index()
            self._dataset_node_index = node_index
        for item in node_index.get("datasets") or []:
            if not isinstance(item, dict):
                continue
            try:
                item_id = int(item.get("dataset_id") or 0)
            except Exception:
                item_id = 0
            item_code = self._normalize_compact_text(item.get("dataset_code") or "")
            item_name = self._normalize_compact_text(item.get("dataset_name") or "")
            code_matches = bool(
                dataset_code
                and (
                    item_code == dataset_code
                    or item_code.startswith(f"{dataset_code}_")
                    or dataset_code.startswith(f"{item_code}_")
                )
            )
            name_matches = bool(
                dataset_name
                and (
                    item_name == dataset_name
                    or dataset_name in item_name
                    or item_name in dataset_name
                )
            )
            if not ((dataset_id and item_id == dataset_id) or code_matches or name_matches):
                continue
            for node in item.get("nodes") or []:
                if not isinstance(node, dict):
                    continue
                if self._normalize_compact_text(node.get("node_level") or "") == normalized_target:
                    return True
        return False

    @classmethod
    def _map_dimension_aliases_for_dataset(cls, question: str, dataset: Dict[str, Any]) -> str:
        """将问题中其他数据集的维度别名映射到当前数据集的等价维度别名。"""
        if not question:
            return question
        profile = get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
        if not profile:
            return question

        # 收集当前数据集的所有维度别名
        selected_aliases = set()
        for level in profile.get("levels") or []:
            selected_aliases.add(cls._normalize_compact_text(level.get("dimension_name")))
            for alias in level.get("aliases") or []:
                selected_aliases.add(cls._normalize_compact_text(alias))
        if not selected_aliases:
            return question

        # 若问题中的别名在当前数据集已存在，则无需映射
        compact_q = cls._normalize_compact_text(question)
        if any(alias in compact_q for alias in selected_aliases if len(alias) >= 2):
            return question

        # 找到当前数据集最适合的角色/人员维度
        person_keywords = ("经理", "代表", "业务员", "承接人", "负责人", "销售", "角色", "人员", "员工")
        levels = profile.get("levels") or []

        def _is_person_level(level):
            dim_name = str(level.get("dimension_name") or "").strip()
            aliases = [str(a).strip() for a in (level.get("aliases") or []) if str(a).strip()]
            return any(kw in dim_name for kw in person_keywords) or any(
                any(kw in a for kw in person_keywords) for a in aliases
            )

        person_levels = [lvl for lvl in levels if _is_person_level(lvl)]
        if not person_levels:
            return question

        # 优先匹配「业务代表/业务员/销售」这类一线角色，再匹配「代表处」等组织层级
        target_alias = ""
        role_priority = ("业务代表", "业务员", "销售")
        for level in person_levels:
            aliases = [str(a).strip() for a in (level.get("aliases") or []) if str(a).strip()]
            preferred = next((role for role in role_priority if role in aliases), "")
            if preferred:
                target_alias = preferred
                break
        if not target_alias:
            for level in person_levels:
                aliases = [str(a).strip() for a in (level.get("aliases") or []) if str(a).strip()]
                preferred = next((a for a in aliases if "业务代表" in a or "业务员" in a), "")
                if not preferred:
                    preferred = next((a for a in aliases if "代表" in a or "员" in a), "")
                if preferred:
                    target_alias = preferred
                    break
        if not target_alias:
            level = person_levels[0]
            aliases = [str(a).strip() for a in (level.get("aliases") or []) if str(a).strip()]
            target_alias = aliases[0] if aliases else str(level.get("dimension_name") or "").strip()

        if not target_alias:
            return question

        # 问题中常见但当前数据集不支持的角色别名，映射到目标别名
        replaced = str(question)
        if "业务经理" in replaced:
            replaced = replaced.replace("业务经理", target_alias)
        if "经理" in replaced and not any(cls._normalize_compact_text("经理") == a for a in selected_aliases):
            replaced = replaced.replace("经理", target_alias)
        return replaced

    def _dataset_alias_match_score(
        self,
        question: str,
        dataset: Dict[str, Any],
        include_profile_levels: bool = True,
        include_profile_resolution: bool = True,
    ) -> int:
        normalized_question = self._normalize_compact_text(question)
        if not normalized_question:
            return 0

        alias_candidates = [
            dataset.get("dataset_name", ""),
            dataset.get("business_domain", ""),
            *(dataset.get("synonyms", []) or []),
        ]
        subject_suffixes = (
            "事业部",
            "分公司",
            "代表处",
            "业务部",
            "数据集",
            "结果指标",
            "销售业绩分析",
            "业绩分析",
        )
        generic_aliases = {
            "业绩", "分析", "数据", "指标", "结果", "结果指标", "销售业绩",
            "分公司", "代表处", "业务部", "城市公司", "城市分公司", "业务员", "业务代表", "事业部",
        }
        # 这些词是通用指标/统计口径，不适合作为数据集/业务域的判别依据
        metric_only_aliases = {
            "达成率", "完成率", "开单", "开单金额", "年度开单", "销售金额", "销售",
            "任务", "任务金额", "总任务", "年度任务", "任务达成", "剩余任务", "缺口", "差额",
            "实际", "实际金额", "完成情况", "完成金额",
        }
        generic_business_terms = {
            "分", "公司", "分公司", "代表", "代表处", "业务", "业务部", "城市", "城市公司", "城市分公司", "事业部",
        }
        score = 0
        for alias in alias_candidates:
            normalized_alias = self._normalize_compact_text(alias)
            if len(normalized_alias) < 2:
                continue
            if normalized_alias in generic_aliases or normalized_alias in metric_only_aliases:
                continue
            if normalized_alias in normalized_question:
                # 数据集名称 / 业务域精确命中优先级高于同义词
                if alias == dataset.get("dataset_name"):
                    score = max(score, 100)
                elif alias == dataset.get("business_domain"):
                    score = max(score, 98)
                else:
                    score = max(score, 95)
            elif len(normalized_alias) >= 3 and normalized_alias in normalized_question.replace("的", ""):
                score = max(score, 90)

            business_terms = set()
            for suffix in subject_suffixes:
                if suffix in normalized_alias:
                    prefix = normalized_alias.split(suffix, 1)[0]
                    if len(prefix) >= 2:
                        business_terms.add(prefix)
            for match in re.findall(r"([\u4e00-\u9fff]{2,}?)(?:事业部|分公司|代表处|业务部)", normalized_alias):
                if len(match) >= 2:
                    business_terms.add(match)
            for term in business_terms:
                if term in generic_business_terms:
                    continue
                if term and term in normalized_question:
                    score = max(score, 90)
        profile = get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
        if include_profile_levels:
            profile_level_score = self._profile_level_alias_score(question, profile)
            if profile_level_score:
                score = max(score, profile_level_score)
        if include_profile_resolution and profile:
            resolved_scope = resolve_member_mentions(question, profile)
            if resolved_scope.get("all_members"):
                score = max(score, 96 if len(resolved_scope.get("all_members") or []) > 1 else 92)
        return score

    def _dataset_scope_alias_score(self, question: str, dataset: Dict[str, Any]) -> int:
        """仅匹配数据集/业务域级别的显式标识，用于绕过歧义确认的快速命中。"""
        normalized_question = self._normalize_compact_text(question)
        if not normalized_question:
            return 0

        subject_suffixes = (
            "事业部",
            "分公司",
            "城市分公司",
            "城市公司",
            "代表处",
            "业务部",
            "业务代表",
            "业务员",
        )
        generic_aliases = {
            "业绩", "分析", "数据", "指标", "结果", "结果指标", "销售业绩",
            "分公司", "代表处", "业务部", "城市公司", "城市分公司", "业务员", "业务代表", "事业部",
        }
        metric_only_aliases = {
            "达成率", "完成率", "开单", "开单金额", "年度开单", "销售金额", "销售",
            "任务", "任务金额", "总任务", "年度任务", "任务达成", "剩余任务", "缺口", "差额",
            "实际", "实际金额", "完成情况", "完成金额",
        }

        def is_org_member_alias(alias_text: str) -> bool:
            if alias_text in {str(dataset.get("dataset_name") or ""), str(dataset.get("business_domain") or "")}:
                return False
            return any(
                alias_text.endswith(suffix) and len(alias_text) > len(suffix)
                for suffix in subject_suffixes
            )

        score = 0
        alias_candidates = [
            ("dataset_name", str(dataset.get("dataset_name") or "").strip()),
            ("business_domain", str(dataset.get("business_domain") or "").strip()),
            *[("synonym", str(item or "").strip()) for item in (dataset.get("synonyms", []) or [])],
        ]
        for alias_type, alias in alias_candidates:
            normalized_alias = self._normalize_compact_text(alias)
            if len(normalized_alias) < 2:
                continue
            if normalized_alias in generic_aliases or normalized_alias in metric_only_aliases:
                continue
            if alias_type == "synonym" and is_org_member_alias(alias):
                continue
            if normalized_alias not in normalized_question:
                continue
            if alias_type == "dataset_name":
                score = max(score, 100)
            elif alias_type == "business_domain":
                score = max(score, 98)
            else:
                score = max(score, 95)
        return score

    def _compute_dataset_match(self, question: str, dataset: Dict[str, Any], context: Dict[str, Any]) -> int:
        q_tokens = self._tokenize(question)
        if not q_tokens:
            return 0

        synonyms = " ".join(dataset.get("synonyms", []) or [])
        common_questions = " ".join(item.get("question_text", "") for item in context.get("common_questions", [])[:8])
        lld_text = self._get_lld_content(context)[:600]
        dictionary_text = " ".join(
            " ".join(
                str(item.get(key) or "")
                for key in ("semantic_name", "jsonb_key", "column_name")
            )
            for item in (context.get("data_dictionary") or [])[:80]
        )
        schema_text = " ".join(
            " ".join(
                str(item.get(key) or "")
                for key in ("table_name", "column_name", "semantic_name")
            )
            for item in (context.get("schema_definition") or [])[:80]
        )
        dataset_text = f"{dataset.get('dataset_name', '')} {dataset.get('business_domain', '')} {synonyms} {common_questions} {dictionary_text} {schema_text} {lld_text}"
        dataset_tokens = self._tokenize(dataset_text)
        synonym_overlap = len(q_tokens.intersection(dataset_tokens))
        sample_score = max([int(item.get("match_score", 0)) for item in context.get("golden_sql_samples", [])] or [0])
        schema_hit = 1 if any(token in dataset_tokens for token in ("日期", "时间", "金额", "分公司", "事业部", "代表处", "业务代表", "业务部", "城市分公司", "区域")) else 0
        name_hit_score = self._dataset_alias_match_score(question, dataset)
        profile = get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
        score = synonym_overlap * 12 + min(sample_score, 90) + schema_hit * 4 + name_hit_score
        if self._looks_like_person_performance_question(question) and any(
            token in dataset_text for token in ("业务代表", "业务员", "销售人员")
        ):
            score = max(score, 88)
        score += self._profile_level_mismatch_penalty(question, profile)
        return max(0, min(score, 100))

    @classmethod
    def _looks_like_person_performance_question(cls, question: str) -> bool:
        text = str(question or "").replace("\n", " ").strip()
        patterns = [
            r"(?:看下|看一下|查一下|查询|分析一下|分析|看看|了解一下|问下|问一下)\s*([\u4e00-\u9fa5]{2,4})(?:的)?(?:业绩|绩效|达成率|达成|开单|完成情况|完成|情况|表现)",
            r"([\u4e00-\u9fa5]{2,4})(?:的)?(?:业绩|绩效|达成率|开单|完成情况|表现)",
        ]
        for pattern in patterns:
            for match in re.findall(pattern, text):
                candidate = re.sub(
                    r"^(看下|看一下|查一下|查询|分析一下|分析|看看|了解一下|问下|问一下)",
                    "",
                    str(match or "").strip("，,、 的呢吗么吧"),
                ).strip()
                if candidate and not cls._looks_like_noise_subject(candidate):
                    return True
        return False

    @staticmethod
    def _summarize_candidate_strengths(context: Dict[str, Any]) -> Dict[str, Any]:
        return ask_engine_utils._summarize_candidate_strengths(context)

    @classmethod
    def _extract_supported_levels(cls, dataset: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
        ordered_levels = ["事业部", "分公司", "城市分公司", "城市公司", "代表处", "业务部", "业务代表", "业务员"]
        seen: List[str] = []

        profile = get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
        if profile:
            for level in profile.get("levels") or []:
                aliases = [
                    str(level.get("dimension_name") or ""),
                    *[str(item or "") for item in (level.get("aliases") or [])],
                ]
                for alias in aliases:
                    normalized_alias = cls._normalize_compact_text(alias)
                    for canonical in ordered_levels:
                        if cls._normalize_compact_text(canonical) == normalized_alias and canonical not in seen:
                            seen.append(canonical)
        return seen

    def _build_dataset_profile_confirmation(
        self,
        question: str,
        candidate_contexts: List[Tuple[Dict[str, Any], Dict[str, Any], int]],
    ) -> Optional[Dict[str, Any]]:
        top_candidates = candidate_contexts[:3]
        if not top_candidates:
            return None

        top_score = top_candidates[0][2]
        profile_matches: List[Dict[str, Any]] = []
        for dataset, _context, score in top_candidates:
            if score < max(45, top_score - 18):
                continue
            profile = get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
            if not profile:
                continue
            for match in find_group_matches(question, profile):
                profile_matches.append(
                    {
                        "dataset": dataset,
                        "score": score,
                        "profile": profile,
                        "match": match,
                    }
                )

        if not profile_matches:
            return None

        first_match = profile_matches[0]
        same_group_matches = [
            item for item in profile_matches
            if item["match"].get("group_key") == first_match["match"].get("group_key")
        ]
        candidate_ids = [int(item[0]["id"]) for item in top_candidates]

        if len(same_group_matches) > 1:
            options = []
            for item in same_group_matches:
                dataset = item["dataset"]
                match = item["match"]
                dataset_name = dataset.get("dataset_name") or f"数据集 {dataset['id']}"
                members = [str(x).strip() for x in (match.get("members") or []) if str(x).strip()]
                options.append(
                    self._build_confirmation_option(
                        option_id=f"dataset_scope_{dataset['id']}",
                        label=f"{dataset_name} · {match.get('matched_alias')}",
                        description=f"按 {dataset_name} 中“{match.get('matched_alias')}”口径继续。",
                        dataset_ids=[dataset["id"]],
                        option_type="dataset_disambiguation",
                        extra={
                            "confirmation_type": "dataset_disambiguation",
                            "matched_alias": match.get("matched_alias"),
                            "resolved_dimension": match.get("dimension_name"),
                            "resolved_members": members,
                            "resolved_dataset_name": dataset_name,
                            "scope_mode": "aggregate",
                        },
                    )
                )
            return {
                "requires_confirmation": True,
                "confirmation_role": "boss",
                "confirmation_type": "dataset_disambiguation",
                "confirmation_question": f"检测到“{first_match['match'].get('matched_alias')}”在多个数据集里都可能成立，请确认要使用哪个口径：",
                "confirmation_options": options,
                "candidate_dataset_ids": candidate_ids,
                "resolved_entities_preview": first_match["match"].get("members") or [],
            }

        dataset = first_match["dataset"]
        match = first_match["match"]
        dataset_name = dataset.get("dataset_name") or f"数据集 {dataset['id']}"
        members = [str(x).strip() for x in (match.get("members") or []) if str(x).strip()]
        matched_alias = str(match.get("matched_alias") or match.get("group_name") or "")
        if members and self._should_auto_expand_profile_group(question, matched_alias, members):
            return None
        member_text = "、".join(members)
        return {
            "requires_confirmation": True,
            "confirmation_role": "boss",
            "confirmation_type": "member_set_confirmation",
            "confirmation_question": f"检测到“{match.get('matched_alias')}”是 {dataset_name} 的集合口径，请确认统计方式：",
            "confirmation_options": [
                self._build_confirmation_option(
                    option_id=f"member_set_aggregate_{dataset['id']}",
                    label=f"按“{match.get('matched_alias')}”整体汇总",
                    description=f"先按 {member_text} 汇总为一个整体口径，再继续分析。",
                    dataset_ids=[dataset["id"]],
                    option_type="member_set_confirmation",
                    extra={
                        "confirmation_type": "member_set_confirmation",
                        "matched_alias": match.get("matched_alias"),
                        "resolved_dimension": match.get("dimension_name"),
                        "resolved_members": members,
                        "resolved_dataset_name": dataset_name,
                        "scope_mode": "aggregate",
                    },
                ),
                self._build_confirmation_option(
                    option_id=f"member_set_compare_{dataset['id']}",
                    label=f"按 {len(members)} 个成员分别对比",
                    description=f"将 {member_text} 分别展开对比，再汇总结论。",
                    dataset_ids=[dataset["id"]],
                    option_type="member_set_confirmation",
                    extra={
                        "confirmation_type": "member_set_confirmation",
                        "matched_alias": match.get("matched_alias"),
                        "resolved_dimension": match.get("dimension_name"),
                        "resolved_members": members,
                        "resolved_dataset_name": dataset_name,
                        "scope_mode": "compare",
                    },
                ),
            ],
            "candidate_dataset_ids": [int(dataset["id"])],
            "resolved_entities_preview": members,
        }

    @staticmethod
    def _should_auto_expand_profile_group(question: str, matched_alias: str, members: List[str]) -> bool:
        return ask_engine_utils._should_auto_expand_profile_group(question, matched_alias, members)

    def _detect_ambiguity(self, question: str, ranked_candidates: List[Tuple[Dict[str, Any], int]]) -> Optional[Dict[str, Any]]:
        if not ranked_candidates:
            return None

        candidate_ids = [item[0]["id"] for item in ranked_candidates]
        alias_scores = [
            (item[0], self._dataset_alias_match_score(question, item[0]))
            for item in ranked_candidates[:3]
        ]
        alias_scores.sort(key=lambda item: item[1], reverse=True)
        best_alias_score = alias_scores[0][1] if alias_scores else 0
        second_alias_score = alias_scores[1][1] if len(alias_scores) > 1 else 0
        if best_alias_score >= 90 and best_alias_score > second_alias_score:
            return None

        # 通用层级口径歧义消解：根据问题里提到的真实层级，只保留真实支持该层级的候选数据集
        matched_levels = self._matched_org_level_terms(question)
        if matched_levels and len(ranked_candidates) >= 2:
            supported_candidates = []
            for dataset, score in ranked_candidates:
                profile = get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
                if any(
                    self._profile_supports_level(profile, term)
                    or self._dataset_node_index_supports_level(dataset, term)
                    or self._dataset_alias_supports_level(dataset, term)
                    for term in matched_levels
                ):
                    supported_candidates.append((dataset, score))

            if len(supported_candidates) == 1:
                # 仅一个数据集支持该口径，不构成歧义
                return None

            if len(supported_candidates) >= 2:
                return self._build_dataset_level_confirmation_route(
                    question,
                    matched_levels,
                    supported_candidates,
                    candidate_dataset_ids=candidate_ids,
                    match_score=supported_candidates[0][1],
                    reason="generic_level_requires_confirmation",
                )

        # 分数接近时，按真实数据集名称确认，不再使用无意义的“分公司层级”文案
        org_ambiguity_terms = ["分公司", "城市分公司", "城市公司", "代表处", "业务部", "业务代表", "业务员", "条线", "区域", "团队", "组织"]
        has_org_ambiguity_term = any(term in question for term in org_ambiguity_terms)
        if len(ranked_candidates) >= 2 and has_org_ambiguity_term:
            top1_score = ranked_candidates[0][1]
            top2_score = ranked_candidates[1][1]
            if abs(top1_score - top2_score) <= 12 and top2_score >= 60:
                options = []
                for idx, (dataset, _score) in enumerate(ranked_candidates[:3]):
                    dataset_name = dataset.get("dataset_name") or f"数据集 {dataset['id']}"
                    options.append(
                        self._build_confirmation_option(
                            option_id=f"dataset_disambiguation_{dataset['id']}",
                            label=f"{dataset_name}{'（优先）' if idx == 0 else ''}",
                            description=f"按 {dataset_name} 口径继续分析。",
                            dataset_ids=[dataset["id"]],
                            option_type="dataset_disambiguation",
                            extra={"confirmation_type": "dataset_disambiguation", "resolved_dataset_name": dataset_name},
                        )
                    )
                options.append(
                    self._build_confirmation_option(
                        option_id="dataset_disambiguation_cross",
                        label="跨数据集汇总（拆分子任务）",
                        description="同时按多个数据集口径输出并对比。",
                        dataset_ids=candidate_ids,
                        option_type="dataset_disambiguation",
                        extra={"confirmation_type": "dataset_disambiguation", "scope_mode": "cross"},
                    )
                )
                return {
                    "requires_confirmation": True,
                    "confirmation_role": "boss",
                    "confirmation_type": "dataset_disambiguation",
                    "confirmation_question": "当前问题可能命中多个数据集，请确认要使用哪个口径：",
                    "confirmation_options": options,
                    "candidate_dataset_ids": candidate_ids,
                }

        # 组织口径类歧义：根据问题里的关键词在各候选数据集中的真实支持度生成选项，
        # 如果只有单个数据集支持该口径，则不视为歧义。
        ambiguous_terms = ["条线", "区域", "团队", "组织"]
        matched_terms = [term for term in ambiguous_terms if term in question]
        if len(ranked_candidates) >= 2 and matched_terms:
            supported_candidates = []
            for dataset, score in ranked_candidates[:3]:
                profile = get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
                if any(
                    self._profile_supports_level(profile, term)
                    for term in matched_terms
                ):
                    supported_candidates.append((dataset, score))

            if len(supported_candidates) == 1:
                # 仅一个数据集支持该口径，直接放行，由后续路由选中它
                return None

            if len(supported_candidates) >= 2:
                options = []
                for dataset, _score in supported_candidates:
                    dataset_name = dataset.get("dataset_name") or f"数据集 {dataset['id']}"
                    options.append(
                        self._build_confirmation_option(
                            option_id=f"dataset_scope_{dataset['id']}",
                            label=dataset_name,
                            description=f"按 {dataset_name} 的“{'/'.join(matched_terms)}”口径继续。",
                            dataset_ids=[dataset["id"]],
                            option_type="dataset_disambiguation",
                            extra={
                                "confirmation_type": "dataset_disambiguation",
                                "resolved_dataset_name": dataset_name,
                                "scope_mode": "aggregate",
                            },
                        )
                    )
                return {
                    "requires_confirmation": True,
                    "confirmation_role": "boss",
                    "confirmation_type": "dataset_disambiguation",
                    "confirmation_question": f"问题中的“{'/'.join(matched_terms)}”在多个数据集中都可能出现，请确认使用哪个数据集口径：",
                    "confirmation_options": options,
                    "candidate_dataset_ids": candidate_ids,
                }

        return None

    def _agent1_route_with_llm(
        self,
        question: str,
        ranked_candidates: List[Tuple[Dict[str, Any], int]],
        trace: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        top_candidates = ranked_candidates[:5]
        candidate_blocks = []
        for dataset, score in top_candidates:
            context = self.repository.get_dataset_context(int(dataset["id"]), question, top_k_samples=3)
            strengths = self._summarize_candidate_strengths(context)
            supported_levels = self._extract_supported_levels(dataset, context)
            candidate_blocks.append(
                {
                    "dataset_id": dataset["id"],
                    "dataset_name": dataset.get("dataset_name"),
                    "business_domain": dataset.get("business_domain"),
                    "synonyms": dataset.get("synonyms", []),
                    "score_hint": score,
                    "supported_levels": supported_levels,
                    "candidate_strengths": strengths,
                    "dataset_agent1_fragments": [
                        item["prompt_content"] for item in context.get("agent_prompts", {}).get(1, [])
                    ],
                    "sample_questions": strengths["top_sample_questions"],
                    "common_questions": strengths["common_question_examples"],
                }
            )

        fallback = {
            "dataset_ids": [top_candidates[0][0]["id"]] if top_candidates else [],
            "intent": "detail",
            "refined_query": question,
            "decision": "generate_sql",
            "match_score": top_candidates[0][1] if top_candidates else 0,
            "requires_confirmation": False,
            "confirmation_role": "boss",
            "confirmation_question": "",
            "confirmation_options": [],
            "candidate_dataset_ids": [item[0]["id"] for item in top_candidates[:3]],
        }

        system_prompt = self._get_agent_prompt(
            1,
            "你是 Agent1 路由中枢，负责识别数据集、判断歧义、决定是否需要老板确认。",
        )
        seed_block = ""
        user_prompt = f"""
用户问题：
{question}

候选数据集：
{json.dumps(candidate_blocks, ensure_ascii=False)}

路由要求：
1. 优先判断业务口径，而不是只看词面相似。
2. 必须优先参考候选数据集的 supported_levels、common_questions、schema_table_count、dictionary_count 和 Agent1 提示词片段来判断层级归属。
3. 【强制确认规则】如果用户问题中没有明确出现事业部名称（如"电商事业部"、"商用事业部"、"消费者事业部"）或数据集名称/别名，且存在 2 个及以上候选数据集都可能回答该问题，则必须 requires_confirmation=true，不得擅自选择。
4. 【评分与推荐】为每个候选数据集从 0-100 打分（candidate_scores），评分维度包括：问题与数据集业务域的匹配度、层级/实体在数据集中的支持程度、常见问法和 Golden SQL 样本的相似度。将得分最高的数据集作为"系统推荐"放在 confirmation_options 的第一项。
5. 如果某组织层级或业务实体只被一个数据集明确支持，且业务口径无歧义，可直接选择该数据集，不需要确认。
6. refined_query 需要补齐时间范围、组织口径、统计对象，但不能虚构用户没有表达的事实。
7. 只有在数据集明显唯一且口径无歧义时，才能给出 direct_execute 或 generate_sql。

请输出 JSON：
{{
  "dataset_ids": [],
  "intent": "summary|detail|confirm",
  "refined_query": "重写后的查询",
  "decision": "direct_execute|generate_sql|wait_boss_confirm",
  "match_score": 0,
  "requires_confirmation": true,
  "confirmation_role": "boss",
  "confirmation_question": "检测到多个可能的数据集，请选择要查询的口径：",
  "confirmation_options": [
    {{"id": "rec_1", "label": "系统推荐：电商事业部 - 业务经理排名", "dataset_ids": [62], "scope_filter": "业务经理层级", "score": 85, "reason": "业务经理是电商数据集明确支持的层级"}},
    {{"id": "opt_2", "label": "商用事业部 - 业务经理/业务员排名", "dataset_ids": [3], "scope_filter": "业务员层级", "score": 45, "reason": "商用数据集主要支持业务员层级"}}
  ],
  "candidate_scores": [
    {{"dataset_id": 62, "dataset_name": "电商事业部", "score": 85, "reason": "业务经理是电商数据集明确支持的层级"}},
    {{"dataset_id": 3, "dataset_name": "商用事业部", "score": 45, "reason": "商用数据集主要支持业务员层级"}}
  ],
  "candidate_dataset_ids": []
}}
"""
        result = self._chat_json(system_prompt, user_prompt, fallback, trace=trace, stage="agent1.route", agent_name="Agent1")
        if not isinstance(result.get("dataset_ids"), list) or not result.get("dataset_ids"):
            result["dataset_ids"] = fallback["dataset_ids"]
        result["candidate_dataset_ids"] = result.get("candidate_dataset_ids") or fallback["candidate_dataset_ids"]
        result["refined_query"] = result.get("refined_query") or question
        result["intent"] = result.get("intent") or "detail"
        result["decision"] = result.get("decision") or "generate_sql"
        result["match_score"] = int(result.get("match_score") or fallback["match_score"])
        result["requires_confirmation"] = bool(result.get("requires_confirmation", False))
        result["confirmation_options"] = self._normalize_confirmation_options(
            result.get("confirmation_options"),
            result.get("candidate_dataset_ids") or fallback["candidate_dataset_ids"],
            [item[0].get("dataset_name") or f"数据集 {item[0]['id']}" for item in top_candidates[:3]],
        )
        return result

    def route_with_agent1(
        self,
        question: str,
        trace: Optional[Dict[str, Any]] = None,
        conversation_context: Optional[List[Dict[str, Any]]] = None,
        allowed_dataset_ids: Optional[List[int]] = None,
        current_question: Optional[str] = None,
    ) -> Dict[str, Any]:
        catalog_override = None
        # 兼容历史调试调用：route_with_agent1(question, catalog, current_question=...)
        if isinstance(trace, list) and trace and all(isinstance(item, dict) and "id" in item for item in trace):
            catalog_override = trace
            trace = None

        full_catalog = self.repository.get_agent1_catalog()
        catalog = catalog_override or full_catalog
        if allowed_dataset_ids is not None:
            allowed = {int(item) for item in allowed_dataset_ids}
            catalog = [item for item in catalog if int(item.get("id") or 0) in allowed]
        if not catalog:
            return {
                "dataset_ids": [],
                "intent": "detail",
                "refined_query": question,
                "requires_confirmation": False,
                "decision": "generate_sql",
            }

        org_source_question = current_question or question
        org_route_all = self.organization_route_resolver.resolve(org_source_question, full_catalog)
        org_route = self.organization_route_resolver.resolve(
            org_source_question,
            catalog,
            allowed_dataset_ids=allowed_dataset_ids,
        )
        if org_route_all and not org_route:
            self._append_trace(
                trace,
                "agent1.organization_tree_route_denied",
                "warning",
                current_question=org_source_question,
                allowed_dataset_ids=allowed_dataset_ids or [],
                organization_mentions=org_route_all.get("organization_mentions") or [],
            )
            return {
                "dataset_ids": [],
                "intent": "confirm",
                "refined_query": org_route_all.get("refined_query") or question,
                "requires_confirmation": False,
                "decision": "permission_denied",
                "match_score": 0,
                "route_margin": 0,
                "candidate_dataset_ids": org_route_all.get("candidate_dataset_ids") or [],
                "arbiter_reason": "organization_tree_dataset_not_allowed",
                "organization_mentions": org_route_all.get("organization_mentions") or [],
            }
        if org_route:
            self._append_trace(
                trace,
                "agent1.organization_tree_route",
                "info",
                route=org_route,
                current_question=current_question or question,
                effective_question=question,
                thought=self._build_route_thought(org_route, current_question or question, full_catalog),
            )
            return org_route

        # 短裸节点早检测：问题很短（≤8字）且无明显业务指标词时，先用节点索引探测
        # 修复"查询丁杰"等场景：这些问题的 _looks_like_org_subject_question 为 False，
        # 会走到 LLM arbiter 打分，但 LLM 不知道丁杰具体在哪个数据集，结果"三个都可能包含"。
        # baseline 3.4：裸节点问题应优先走真实节点索引。
        bare_node_candidate = self._extract_bare_node_candidate(question)
        if bare_node_candidate:
            index_matches = self._node_index_matches(bare_node_candidate)
            available_ids = {int(ds.get("id") or 0) for ds in catalog}
            filtered = [
                m for m in index_matches
                if int(m.get("dataset_id") or 0) in available_ids
                and (allowed_dataset_ids is None or int(m.get("dataset_id") or 0) in {int(i) for i in allowed_dataset_ids})
            ]
            if len(filtered) == 1:
                only = filtered[0]
                rewritten = f"{only['node_name']}的业绩"
                self._append_trace(
                    trace,
                    "agent1.bare_node_index_unique",
                    "info",
                    node_name=only["node_name"],
                    dataset_id=only["dataset_id"],
                    candidate=bare_node_candidate,
                )
                return {
                    "dataset_ids": [only["dataset_id"]],
                    "intent": "detail",
                    "refined_query": rewritten,
                    "requires_confirmation": False,
                    "decision": "generate_sql",
                    "match_score": 100,
                    "route_margin": 100,
                    "candidate_dataset_ids": [only["dataset_id"]],
                    "arbiter_reason": "bare_node_index_unique",
                    "resolved_subject_name": only["node_name"],
                    "resolved_subject_level": only["node_level"],
                    "split_queries": [{"dataset_id": only["dataset_id"], "sub_query": rewritten}],
                }
            if len(filtered) >= 2:
                confirmation_options = []
                seen_option_ids = set()
                for idx, item in enumerate(filtered):
                    did = int(item["dataset_id"])
                    if did not in available_ids:
                        continue
                    opt_id = f"node_index_{did}_{idx + 1}"
                    if opt_id in seen_option_ids:
                        continue
                    seen_option_ids.add(opt_id)
                    confirmation_options.append({
                        "id": opt_id,
                        "label": f"{item['dataset_name']} - {item['node_name']}",
                        "description": f"{item['node_level']}层级",
                        "dataset_ids": [did],
                        "option_type": "dataset_disambiguation",
                        "option_id": opt_id,
                        "confirmation_type": "dataset_disambiguation",
                        "resolved_subject_name": item["node_name"],
                        "resolved_subject_level": item["node_level"],
                        "scope_filter": {},
                        "score": 100,
                    })
                self._append_trace(
                    trace,
                    "agent1.bare_node_index_ambiguous",
                    "info",
                    node_name=bare_node_candidate,
                    candidate_dataset_ids=[o["dataset_ids"][0] for o in confirmation_options],
                )
                return {
                    "dataset_ids": [o["dataset_ids"][0] for o in confirmation_options],
                    "intent": "confirm",
                    "refined_query": f"{bare_node_candidate}的业绩",
                    "requires_confirmation": True,
                    "decision": "wait_boss_confirm",
                    "match_score": 100,
                    "confirmation_role": "boss",
                    "confirmation_type": "dataset_disambiguation",
                    "confirmation_question": f"您说的「{bare_node_candidate}」在多个数据集中都有命中，请确认要查询哪个：",
                    "confirmation_options": confirmation_options,
                    "candidate_dataset_ids": [o["dataset_ids"][0] for o in confirmation_options],
                    "arbiter_reason": "bare_node_index_ambiguous",
                }

        if self._looks_like_org_subject_question(question):
            resolved_subject = self._agent1_resolve_org_subject(
                question,
                conversation_context=conversation_context,
                trace=trace,
            ) or {}
            subject_name = str(resolved_subject.get("subject_name") or "").strip()
            if subject_name:
                index_matches = self._node_index_matches(subject_name)
                available_ids = {int(ds.get("id") or 0) for ds in catalog}
                distinct_matches = self._dedupe_node_index_matches(index_matches, dataset_ids=available_ids)
                matched_dataset_ids = sorted({int(item.get("dataset_id") or 0) for item in distinct_matches})
                if len(distinct_matches) == 1:
                    only_match = distinct_matches[0]
                    only_id = int(only_match.get("dataset_id") or 0)
                    rewritten_question = str(resolved_subject.get("rewritten_question") or question).strip() or question
                    return {
                        "dataset_ids": [only_id],
                        "intent": "detail",
                        "refined_query": rewritten_question,
                        "requires_confirmation": False,
                        "decision": "generate_sql",
                        "match_score": 100,
                        "route_margin": 100,
                        "candidate_dataset_ids": matched_dataset_ids,
                        "arbiter_reason": "node_index_dataset_unique",
                        "resolved_subject_name": str(only_match.get("node_name") or subject_name).strip(),
                        "resolved_subject_level": str(only_match.get("node_level") or resolved_subject.get("subject_level") or "").strip(),
                        "split_queries": [
                            {"dataset_id": only_id, "sub_query": rewritten_question}
                        ],
                    }
                if len(distinct_matches) >= 2:
                    confirmation_options = []
                    for idx, item in enumerate(distinct_matches):
                        dataset_id = int(item.get("dataset_id") or 0)
                        if dataset_id not in matched_dataset_ids:
                            continue
                        dataset_name = str(item.get("dataset_name") or f"数据集 {dataset_id}").strip()
                        node_name = str(item.get("node_name") or "").strip()
                        node_level = str(item.get("node_level") or "").strip()
                        confirmation_options.append(
                            {
                                "id": f"node_index_{dataset_id}_{idx + 1}",
                                "label": f"{dataset_name} - {node_name}",
                                "description": f"{node_level}层级",
                                "dataset_ids": [dataset_id],
                                "option_type": "dataset_disambiguation",
                                "option_id": f"node_index_{dataset_id}_{idx + 1}",
                                "confirmation_type": "dataset_disambiguation",
                                "resolved_subject_name": node_name,
                                "resolved_subject_level": node_level,
                                "scope_filter": {},
                                "score": 100,
                            }
                        )
                    deduped_options = []
                    seen_option_ids = set()
                    for option in confirmation_options:
                        option_id = option["id"]
                        if option_id in seen_option_ids:
                            continue
                        seen_option_ids.add(option_id)
                        deduped_options.append(option)
                    if deduped_options:
                        return {
                            "dataset_ids": matched_dataset_ids,
                            "intent": "confirm",
                            "refined_query": str(resolved_subject.get("rewritten_question") or question).strip() or question,
                            "requires_confirmation": True,
                            "decision": "wait_boss_confirm",
                            "match_score": 100,
                            "confirmation_role": "boss",
                            "confirmation_type": "dataset_disambiguation",
                            "confirmation_question": f"您说的“{subject_name}”是指哪个数据集里的组织节点？",
                            "confirmation_options": deduped_options,
                            "candidate_dataset_ids": matched_dataset_ids,
                            "arbiter_reason": "node_index_dataset_ambiguous",
                        }

        # 当用户只有一个可访问数据集时，直接命中该数据集，不再走任何歧义确认
        if len(catalog) == 1:
            only_dataset = catalog[0]
            return {
                "dataset_ids": [only_dataset["id"]],
                "intent": "detail",
                "refined_query": question,
                "requires_confirmation": False,
                "decision": "generate_sql",
                "match_score": 100,
                "route_margin": 100,
                "candidate_dataset_ids": [only_dataset["id"]],
                "arbiter_reason": "single_allowed_dataset",
                "split_queries": [
                    {"dataset_id": only_dataset["id"], "sub_query": question}
                ],
            }

        # 修复：问题中明确提到数据集/业务域名称时，直接命中对应数据集，避免被通用层级词干扰。
        compare_pattern = re.compile(r"对比|比较|vs|和.+比|跟.+比|与.+比|哪个更好|哪个业绩更好|谁更|哪个.*更好", re.I)
        mentioned_dataset_ids = set()
        for dataset in catalog:
            # 只使用数据集/业务域级别的显式标识，避免“业务部”等通用层级把无关数据集拉进来
            if self._dataset_scope_alias_score(question, dataset) >= 90:
                try:
                    mentioned_dataset_ids.add(int(dataset["id"]))
                except Exception:
                    pass
        if len(mentioned_dataset_ids) >= 2 and compare_pattern.search(question):
            sorted_ids = sorted(mentioned_dataset_ids)
            return {
                "dataset_ids": sorted_ids,
                "intent": "comparison",
                "refined_query": question,
                "requires_confirmation": False,
                "decision": "generate_sql",
                "match_score": 100,
                "route_margin": 100,
                "candidate_dataset_ids": sorted_ids,
                "arbiter_reason": "multi_dataset_explicit_compare",
                "split_queries": [{"dataset_id": ds_id, "sub_query": question} for ds_id in sorted_ids],
            }
        if len(mentioned_dataset_ids) == 1:
            only_id = next(iter(mentioned_dataset_ids))
            return {
                "dataset_ids": [only_id],
                "intent": "detail",
                "refined_query": question,
                "requires_confirmation": False,
                "decision": "generate_sql",
                "match_score": 100,
                "route_margin": 100,
                "candidate_dataset_ids": [only_id],
                "arbiter_reason": "explicit_dataset_scope_unique",
                "split_queries": [{"dataset_id": only_id, "sub_query": question}],
            }

        candidate_contexts: List[Tuple[Dict[str, Any], Dict[str, Any], int]] = []
        for dataset in catalog:
            context = self.repository.get_dataset_context(dataset["id"], question, top_k_samples=5)
            score = self._compute_dataset_match(question, dataset, context)
            alias_score = self._dataset_alias_match_score(question, dataset)
            candidate_contexts.append((dataset, context, score, alias_score))

        # 总分相同时，别名/业务域命中分高的优先，避免“电商事业部年度开单”被同义词“年度开单”顶到前面
        candidate_contexts.sort(key=lambda item: (item[2], item[3]), reverse=True)
        candidate_contexts = [(dataset, context, score) for dataset, context, score, _alias in candidate_contexts]
        ranked = [(item[0], item[2]) for item in candidate_contexts]
        best_dataset, best_context, best_score = candidate_contexts[0]
        runner_up_score = candidate_contexts[1][2] if len(candidate_contexts) > 1 else 0
        route_margin = best_score - runner_up_score

        target_level_hint = self._question_target_level_hint(question)
        exclusive_level_hints = {"城市分公司", "城市公司"}
        if target_level_hint in exclusive_level_hints:
            supported_candidates = []
            for dataset, context, score in candidate_contexts[:3]:
                profile = get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
                if (
                    self._profile_supports_level(profile, target_level_hint)
                    or self._context_supports_level(context, target_level_hint)
                    or self._dataset_node_index_supports_level(dataset, target_level_hint)
                    or self._dataset_alias_supports_level(dataset, target_level_hint)
                ):
                    supported_candidates.append((dataset, score))
            if len(supported_candidates) == 1:
                selected_dataset, selected_score = supported_candidates[0]
                return {
                    "dataset_ids": [selected_dataset["id"]],
                    "intent": "detail",
                    "refined_query": question,
                    "requires_confirmation": False,
                    "decision": "generate_sql",
                    "match_score": selected_score,
                    "route_margin": 100,
                    "matched_sample_id": None,
                    "matched_sample_sql": "",
                    "arbiter_reason": f"target_level_unique:{target_level_hint}",
                    "candidate_dataset_ids": [item[0]["id"] for item in ranked[:3]],
                    "split_queries": [
                        {"dataset_id": selected_dataset["id"], "sub_query": question}
                    ],
                }
        best_alias_score = self._dataset_scope_alias_score(question, best_dataset)
        runner_alias_score = (
            self._dataset_scope_alias_score(question, candidate_contexts[1][0])
            if len(candidate_contexts) > 1
            else 0
        )
        # 业务域 / 数据集名称精确命中（>=98）且唯一，直接命中，不受 route_margin 限制
        if best_alias_score >= 98 and best_alias_score > runner_alias_score:
            return {
                "dataset_ids": [best_dataset["id"]],
                "intent": "detail",
                "refined_query": question,
                "requires_confirmation": False,
                "decision": "generate_sql",
                "match_score": best_score,
                "route_margin": route_margin,
                "matched_sample_id": None,
                "matched_sample_sql": "",
                "arbiter_reason": "explicit_dataset_domain",
                "candidate_dataset_ids": [item[0]["id"] for item in ranked[:3]],
                "split_queries": [
                    {"dataset_id": best_dataset["id"], "sub_query": question}
                ],
            }
        if best_alias_score >= 90 and best_alias_score > runner_alias_score and route_margin >= 12:
            return {
                "dataset_ids": [best_dataset["id"]],
                "intent": "detail",
                "refined_query": question,
                "requires_confirmation": False,
                "decision": "generate_sql",
                "match_score": best_score,
                "route_margin": route_margin,
                "matched_sample_id": None,
                "matched_sample_sql": "",
                "arbiter_reason": "explicit_dataset_alias",
                "candidate_dataset_ids": [item[0]["id"] for item in ranked[:3]],
                "split_queries": [
                    {"dataset_id": best_dataset["id"], "sub_query": question}
                ],
            }

        # 实体口径唯一性消解：问题提到具体组织/成员名称时，
        # 若只有单个候选数据集能在 profile 中解析出该成员，直接命中该数据集。
        resolved_dataset = None
        resolved_count = 0
        for dataset, context, score in candidate_contexts[:3]:
            profile = get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
            if profile:
                resolved = resolve_member_mentions(question, profile)
                matched_aliases = [
                    str(alias or "").strip()
                    for entity in (resolved.get("entities") or [])
                    for alias in (entity.get("matched_aliases") or [])
                    if str(alias or "").strip()
                ]
                exact_member_hit = any(
                    self._normalize_compact_text(member) in self._normalize_compact_text(question)
                    for member in (resolved.get("all_members") or [])
                )
                explicit_level_hit = bool(
                    re.search(r"代表处|分公司|业务部|城市分公司|城市公司|业务代表|业务员", question)
                )
                alias_level_hit = any(
                    re.search(r"代表处|分公司|业务部|城市分公司|城市公司|业务代表|业务员", alias)
                    for alias in matched_aliases
                )
                if resolved.get("all_members") and (
                    exact_member_hit
                    or (explicit_level_hit and alias_level_hit)
                ):
                    resolved_dataset = dataset
                    resolved_count += 1
        if resolved_count == 1 and resolved_dataset is not None:
            return {
                "dataset_ids": [resolved_dataset["id"]],
                "intent": "detail",
                "refined_query": question,
                "requires_confirmation": False,
                "decision": "generate_sql",
                "match_score": next((score for d, c, score in candidate_contexts if d["id"] == resolved_dataset["id"]), 0),
                "route_margin": 100,
                "matched_sample_id": None,
                "matched_sample_sql": "",
                "arbiter_reason": "entity_mention_unique",
                "candidate_dataset_ids": [item[0]["id"] for item in ranked[:3]],
                "split_queries": [
                    {"dataset_id": resolved_dataset["id"], "sub_query": question}
                ],
            }

        # 层级口径快速消解：问题提到具体层级/维度时，
        # 只保留 profile、字段字典或节点索引里真正支持该口径的候选数据集。
        matched_levels = self._matched_org_level_terms(question)
        supported_candidates = []
        supported_dataset_ids = set()
        if matched_levels and len(candidate_contexts) >= 2:
            for dataset, context, score in candidate_contexts:
                profile = get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
                if any(
                    self._profile_supports_level(profile, term)
                    or self._context_supports_level(context, term)
                    or self._dataset_node_index_supports_level(dataset, term)
                    or self._dataset_alias_supports_level(dataset, term)
                    for term in matched_levels
                ):
                    supported_candidates.append((dataset, score))
                    supported_dataset_ids.add(int(dataset["id"]))

            if len(supported_candidates) == 1:
                selected_dataset, selected_score = supported_candidates[0]
                return {
                    "dataset_ids": [selected_dataset["id"]],
                    "intent": "detail",
                    "refined_query": question,
                    "requires_confirmation": False,
                    "decision": "generate_sql",
                    "match_score": selected_score,
                    "route_margin": 100,
                    "candidate_dataset_ids": [item[0]["id"] for item in ranked[:3]],
                    "arbiter_reason": f"target_level_unique:{matched_levels[0]}",
                    "split_queries": [{"dataset_id": selected_dataset["id"], "sub_query": question}],
                }

            if len(supported_candidates) >= 2:
                return self._build_dataset_level_confirmation_route(
                    question,
                    matched_levels,
                    supported_candidates,
                    candidate_dataset_ids=[item[0]["id"] for item in ranked],
                    match_score=best_score,
                    reason="generic_level_requires_confirmation",
                )

        # 对“明确组织层级 + 多数据集都支持该层级”的问题，优先让 Agent1 的 LLM 参与一次判定，
        # 避免被前置规则过早截流，保留现有规则作为兜底。
        if matched_levels and len(supported_candidates) >= 2:
            llm_level_route = self._agent1_route_with_llm(question, ranked, trace)
            llm_level_dataset_ids = [int(item) for item in (llm_level_route.get("dataset_ids") or []) if str(item).strip()]
            if llm_level_dataset_ids:
                llm_level_route["candidate_dataset_ids"] = llm_level_route.get("candidate_dataset_ids") or [item[0]["id"] for item in ranked[:3]]
                if llm_level_route.get("requires_confirmation"):
                    llm_level_route["intent"] = "confirm"
                    llm_level_route["decision"] = "wait_boss_confirm"
                    llm_level_route["confirmation_options"] = self._normalize_confirmation_options(
                        llm_level_route.get("confirmation_options"),
                        llm_level_route.get("candidate_dataset_ids"),
                        [item[0].get("dataset_name") or f"数据集{item[0]['id']}" for item in ranked[:3]],
                    )
                    llm_level_route["arbiter_reason"] = (
                        llm_level_route.get("arbiter_reason")
                        or f"llm_level_disambiguation:{','.join(matched_levels)}"
                    )
                    return llm_level_route
                if len(llm_level_dataset_ids) == 1:
                    llm_level_route["requires_confirmation"] = False
                    llm_level_route["intent"] = llm_level_route.get("intent") or "detail"
                    llm_level_route["decision"] = "generate_sql"
                    llm_level_route["arbiter_reason"] = (
                        llm_level_route.get("arbiter_reason")
                        or f"llm_level_disambiguation:{','.join(matched_levels)}"
                    )
                    llm_level_route["split_queries"] = [
                        {"dataset_id": llm_level_dataset_ids[0], "sub_query": llm_level_route.get("refined_query") or question}
                    ]
                    return llm_level_route

        history = conversation_context or []
        arbiter_result = self.disambiguation_arbiter.evaluate(
            question=question,
            candidate_contexts=candidate_contexts,
            history=history,
            chat_json=self._chat_json,
            trace=trace,
        )
        if arbiter_result.get("need_confirm"):
            options = self._normalize_confirmation_options(
                arbiter_result.get("options"),
                [item[0]["id"] for item in ranked[:3]],
                [item[0].get("dataset_name") or f"数据集 {item[0]['id']}" for item in ranked[:3]],
            )
            # 若问题包含具体层级，过滤掉不支持该层级的候选；跨数据集选项在单一层级口径下也不适合自动命中
            if matched_levels and supported_dataset_ids:
                filtered_options = [
                    option for option in options
                    if option.get("option_type") != "cross_dataset"
                    and any(int(did) in supported_dataset_ids for did in option.get("dataset_ids", []))
                ]
                if len(filtered_options) == 1 and filtered_options[0].get("dataset_ids"):
                    selected_id = int(filtered_options[0]["dataset_ids"][0])
                    selected_score = next(
                        (score for dataset, score in supported_candidates if int(dataset["id"]) == selected_id),
                        ranked[0][1],
                    )
                    return {
                        "dataset_ids": [selected_id],
                        "intent": "detail",
                        "refined_query": question,
                        "requires_confirmation": False,
                        "decision": "generate_sql",
                        "match_score": selected_score,
                        "route_margin": 100,
                        "candidate_dataset_ids": [item[0]["id"] for item in ranked[:3]],
                        "arbiter_reason": f"target_level_unique:{matched_levels[0]}",
                        "split_queries": [{"dataset_id": selected_id, "sub_query": question}],
                    }
                if filtered_options:
                    options = filtered_options

            return {
                "dataset_ids": options[0].get("dataset_ids", [ranked[0][0]["id"]]) if options else [ranked[0][0]["id"]],
                "intent": "confirm",
                "refined_query": arbiter_result.get("refined_query") or question,
                "requires_confirmation": True,
                "decision": "wait_boss_confirm",
                "match_score": ranked[0][1],
                "confirmation_role": "boss",
                "confirmation_type": "dataset_disambiguation",
                "confirmation_question": arbiter_result.get("confirm_question"),
                "confirmation_options": options,
                "candidate_dataset_ids": [item[0]["id"] for item in ranked[:3]],
                "arbiter_reason": arbiter_result.get("reason", ""),
            }

        auto_pick_option_id = arbiter_result.get("auto_pick_option_id")
        auto_pick_dataset_ids: List[int] = []
        if auto_pick_option_id:
            for option in arbiter_result.get("options") or []:
                if option.get("id") == auto_pick_option_id or option.get("option_id") == auto_pick_option_id:
                    auto_pick_dataset_ids = [int(item) for item in option.get("dataset_ids", [])]
                    break

        best_sample = (best_context.get("golden_sql_samples") or [{}])[0]
        best_sample_score = int(best_sample.get("match_score", 0))
        profile_scope_resolved = str(arbiter_result.get("reason") or "") == "profile_scope_resolved" and bool(auto_pick_dataset_ids)
        if profile_scope_resolved:
            return {
                "dataset_ids": auto_pick_dataset_ids,
                "intent": "detail",
                "refined_query": arbiter_result.get("refined_query") or question,
                "requires_confirmation": False,
                "decision": "generate_sql",
                "match_score": max(best_score, 82),
                "route_margin": route_margin,
                "matched_sample_id": None,
                "matched_sample_sql": "",
                "arbiter_reason": "profile_scope_resolved",
                "split_queries": [
                    {"dataset_id": item, "sub_query": arbiter_result.get("refined_query") or question}
                    for item in auto_pick_dataset_ids
                ],
            }

        if best_score < 70 and len(ranked) > 1:
            best_dataset_name = best_dataset.get("dataset_name") or f"数据集 {best_dataset['id']}"
            options = self._normalize_confirmation_options(
                [
                    {
                        "dataset_id": best_dataset["id"],
                        "label": best_dataset_name,
                        "reason": f"当前只是相似命中，路由分数 {best_score}，还不足以自动执行。",
                    }
                ],
                [best_dataset["id"]],
                [best_dataset_name],
            )
            return {
                "dataset_ids": [best_dataset["id"]],
                "intent": "confirm",
                "refined_query": arbiter_result.get("refined_query") or question,
                "requires_confirmation": True,
                "decision": "wait_boss_confirm",
                "match_score": best_score,
                "route_margin": route_margin,
                "confirmation_role": "boss",
                "confirmation_type": "dataset_similarity_confirm",
                "confirmation_question": f"我只找到一个相似数据集：{best_dataset_name}。这个命中还不够确定，是否按它继续分析？",
                "confirmation_options": options,
                "candidate_dataset_ids": [item[0]["id"] for item in ranked[:3]],
                "arbiter_reason": "low_similarity_requires_boss_confirm",
            }
        # 守卫：如果问题包含层级词（如"分公司"）且多个数据集都支持该层级，不允许 direct_execute 绕过确认
        level_guard_blocks_direct_execute = False
        if matched_levels and len(candidate_contexts) >= 2:
            level_guard_blocks_direct_execute = len(supported_candidates) >= 2
        direct_execute = (
            best_score >= 92
            and best_sample_score >= (70 if len(candidate_contexts) == 1 else 95)
            and route_margin >= 18
            and bool(best_sample.get("sql_text"))
            and not level_guard_blocks_direct_execute
        )
        if direct_execute:
            return {
                "dataset_ids": auto_pick_dataset_ids or [best_dataset["id"]],
                "intent": "detail",
                "refined_query": arbiter_result.get("refined_query") or question,
                "requires_confirmation": False,
                "decision": "direct_execute",
                "match_score": best_score,
                "route_margin": route_margin,
                "matched_sample_id": best_sample.get("id"),
                "matched_sample_sql": best_sample.get("sql_text") or "",
                "arbiter_reason": arbiter_result.get("reason", ""),
                "split_queries": [
                    {"dataset_id": item, "sub_query": arbiter_result.get("refined_query") or question}
                    for item in (auto_pick_dataset_ids or [best_dataset["id"]])
                ],
            }

        # 层级歧义守卫：direct_execute 被阻止且多个数据集都支持该层级。
        # 修复：若最佳候选得分严格高于次优，且次优没有强别名命中，直接命中最佳候选，避免过度弹确认。
        if level_guard_blocks_direct_execute:
            # 强制确认：纯通用层级问题（没有事业部/数据集前缀）必须弹确认，不允许自动命中
            force_confirm = self._is_pure_generic_level_question(question, matched_levels)
            if not force_confirm and best_score > runner_up_score and runner_alias_score < 90:
                return {
                    "dataset_ids": [best_dataset["id"]],
                    "intent": "detail",
                    "refined_query": question,
                    "requires_confirmation": False,
                    "decision": "generate_sql",
                    "match_score": best_score,
                    "route_margin": route_margin,
                    "candidate_dataset_ids": [item[0]["id"] for item in ranked[:3]],
                    "arbiter_reason": f"level_ambiguity_resolved_by_score:{','.join(matched_levels)}",
                    "split_queries": [{"dataset_id": best_dataset["id"], "sub_query": question}],
                }
            level_confirm_options = []
            for ds, ds_score in supported_candidates:
                ds_name = ds.get("dataset_name") or f"数据集 {ds['id']}"
                level_confirm_options.append({
                    "id": f"lvl_{ds['id']}",
                    "label": f"{ds_name} - {'、'.join(matched_levels)}口径",
                    "dataset_ids": [ds["id"]],
                    "scope_filter": matched_levels[0],
                    "score": int(ds_score),
                    "reason": f"该数据集支持{'、'.join(matched_levels)}层级",
                    "option_type": "single_dataset",
                })
            return {
                "dataset_ids": [supported_candidates[0][0]["id"]],
                "intent": "confirm",
                "refined_query": question,
                "requires_confirmation": True,
                "decision": "wait_boss_confirm",
                "match_score": best_score,
                "route_margin": route_margin,
                "confirmation_role": "boss",
                "confirmation_question": f"检测到多个数据集都支持{'、'.join(matched_levels)}口径，请选择要查询的数据集：",
                "confirmation_options": level_confirm_options,
                "candidate_dataset_ids": [item[0]["id"] for item in ranked[:3]],
                "arbiter_reason": f"level_ambiguity_guard:{','.join(matched_levels)}",
            }

        profile_confirmation = self._build_dataset_profile_confirmation(question, candidate_contexts)
        if profile_confirmation:
            profile_confirmation["confirmation_options"] = self._normalize_confirmation_options(
                profile_confirmation.get("confirmation_options"),
                profile_confirmation.get("candidate_dataset_ids"),
                [item[0].get("dataset_name") or f"数据集 {item[0]['id']}" for item in ranked[:3]],
            )
            return {
                "dataset_ids": [ranked[0][0]["id"]],
                "intent": "confirm",
                "refined_query": question,
                "requires_confirmation": True,
                "decision": "wait_boss_confirm",
                "match_score": ranked[0][1],
                **profile_confirmation,
            }

        llm_route = self._agent1_route_with_llm(question, ranked, trace=trace)
        if llm_route.get("requires_confirmation"):
            llm_route["intent"] = "confirm"
            llm_route["decision"] = "wait_boss_confirm"
            llm_route["confirmation_options"] = self._normalize_confirmation_options(
                llm_route.get("confirmation_options"),
                llm_route.get("candidate_dataset_ids"),
                [item[0].get("dataset_name") or f"数据集 {item[0]['id']}" for item in ranked[:3]],
            )
            return llm_route

        ambiguity = self._detect_ambiguity(question, ranked)
        if ambiguity:
            ambiguity["confirmation_options"] = self._normalize_confirmation_options(
                ambiguity.get("confirmation_options"),
                ambiguity.get("candidate_dataset_ids"),
                [item[0].get("dataset_name") or f"数据集 {item[0]['id']}" for item in ranked[:3]],
            )
            return {
                "dataset_ids": [ranked[0][0]["id"]],
                "intent": "confirm",
                "refined_query": question,
                "requires_confirmation": True,
                "decision": "wait_boss_confirm",
                "match_score": ranked[0][1],
                **ambiguity,
            }

        return {
            "dataset_ids": auto_pick_dataset_ids or llm_route.get("dataset_ids") or [best_dataset["id"]],
            "intent": llm_route.get("intent") or "detail",
            "refined_query": arbiter_result.get("refined_query") or llm_route.get("refined_query") or question,
            "requires_confirmation": False,
            "decision": "generate_sql",
            "match_score": best_score,
            "route_margin": route_margin,
            "matched_sample_id": None,
            "matched_sample_sql": "",
            "arbiter_reason": arbiter_result.get("reason", ""),
            "split_queries": [
                {"dataset_id": item, "sub_query": llm_route.get("refined_query") or question}
                for item in (auto_pick_dataset_ids or llm_route.get("dataset_ids") or [best_dataset["id"]])
            ],
        }

    def _build_context_blob(self, context: Dict[str, Any]) -> str:
        row_security = self._safe_dict(context.get("row_security"))
        row_security_lines = []
        if row_security.get("mode") == "org_tree":
            row_security_lines.append(
                "当前数据集启用了组织树数据权限。SQL 最终 SELECT 必须保留可识别组织范围的结果列，"
                "优先输出 节点名称、上级名称、分公司、事业部、业务部、代表处、组织路径、链接字段(勿删)；"
                "如源数据有编码，也输出组织编码。"
            )
            row_security_lines.append(
                "系统会在执行前二次套行级过滤；如果最终结果没有任何组织列，或业务代表明细缺少上级分公司/代表处/链路，普通用户可能查询不到数据。"
            )
            row_security_lines.append(
                f"当前用户授权组织名称：{', '.join(row_security.get('allowed_names') or []) or '无'}；"
                f"授权组织编码：{', '.join(row_security.get('allowed_codes') or []) or '无'}。"
            )
        dictionary_lines = []
        for item in context.get("data_dictionary", [])[:150]:
            dictionary_lines.append(
                f"{item['table_name']}.{item['column_name']} => semantic={item['semantic_name']}, "
                f"jsonb_key={item.get('jsonb_key')}, extraction={item.get('extraction_rule', '')}"
            )

        schema_lines = []
        for item in context.get("schema_definition", [])[:30]:
            schema_lines.append(f"TABLE={item['table_name']}\nDDL={item['ddl_sql']}")

        relation_lines = []
        for item in context.get("table_relations", [])[:30]:
            relation_lines.append(
                f"{item['left_table']}.{item['left_key']} {item['relation_type']} "
                f"{item['right_table']}.{item['right_key']}"
            )

        sample_lines = []
        for index, item in enumerate(context.get("golden_sql_samples", []), start=1):
            sample_lines.append(
                f"[Golden {index}] score={item.get('match_score', 0)} question={item.get('question')}\nSQL:\n{item.get('sql_text')}"
            )

        common_question_lines = [
            str(item.get("question_text") or "")
            for item in context.get("common_questions", [])[:10]
            if str(item.get("question_text") or "").strip()
        ]

        return "\n\n".join(
            [
                f"LLD:\n{self._get_lld_content(context)}",
                "Row Security:\n" + "\n".join(row_security_lines),
                "Common Questions:\n" + "\n".join(common_question_lines),
                "Data Dictionary:\n" + "\n".join(dictionary_lines),
                "Schema Definition:\n" + "\n\n".join(schema_lines),
                "Join Relations:\n" + "\n".join(relation_lines),
                "Golden SQL Samples:\n" + "\n\n".join(sample_lines),
            ]
        )

    def _build_syyb_base_sql(self, context: Dict[str, Any]) -> str:
        dictionary_keys = {
            str(item.get("jsonb_key") or "").strip()
            for item in context.get("data_dictionary", []) or []
            if str(item.get("jsonb_key") or "").strip()
        }
        if "业务部" in dictionary_keys:
            return SYYB_BASE_SQL
        return SYYB_BASE_SQL.replace(
            "TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务部') = 'array' THEN fields->'业务部'->0->>'text' ELSE fields->>'业务部' END, '')) AS 业务部,",
            "'' AS 业务部,",
        )

    def _build_rule_based_sql(self, question: str, route: Dict[str, Any], context: Dict[str, Any]) -> str:
        dataset = self._safe_dict(context.get("dataset"))
        query_intent = self._safe_dict(context.get("query_intent"))
        dataset_code = str(dataset.get("dataset_code") or dataset.get("code") or "")
        dataset_name = str(dataset.get("dataset_name") or dataset.get("name") or "")
        normalized_question = str(question or "").replace("\n", " ").strip()
        original_question = str(context.get("original_question") or "").replace("\n", " ").strip()
        if original_question and original_question not in normalized_question:
            normalized_question = f"{normalized_question} {original_question}".strip()
        intent_name = str(query_intent.get("intent") or "").strip()
        intent_target_level = str(query_intent.get("target_level") or "").strip()
        normalized_target_level = intent_target_level.replace(" ", "")
        is_consumer_dataset = (
            dataset_code in {"consumer_business_standard_v1", "public_feishu_tbl_xioafeizhe_609826"}
            or "消费者" in dataset_name
        )
        is_syyb_dataset = dataset_code in {"angel_business_2026", "angel_business_2026_phase1"} or dataset_name in {
            "商用事业部",
            "商用事业部（阶段一升级版）",
        }
        is_phase1_dataset = dataset_code == "angel_business_2026_phase1" or dataset_name == "商用事业部（阶段一升级版）"
        is_ecommerce_dataset = dataset_code == "feishu_tbldianshang" or "电商事业部" in dataset_name

        if is_consumer_dataset:
            return self._build_consumer_business_sql(normalized_question, context)

        if is_ecommerce_dataset:
            return self._build_ecommerce_sql(normalized_question, context)

        if not is_syyb_dataset:
            return ""

        syyb_base_sql = self._build_syyb_base_sql(context)

        generic_level_terms = {"分公司", "代表处", "业务部", "业务代表", "业务员", "事业部"}

        intent_is_filter = query_intent.get("intent") == "filter"
        intent_is_comparison = query_intent.get("intent") == "comparison"
        intent_is_aggregate = query_intent.get("intent") == "aggregate"
        filter_metric_column = str(query_intent.get("filter_metric_column") or "").strip()
        filter_operator = str(query_intent.get("filter_operator") or "").strip()
        filter_value = query_intent.get("filter_value")
        allowed_filter_columns = {"总任务金额", "年度开单金额", "达成率", "剩余任务金额"}

        def normalize_syyb_threshold_value(raw: float, col: str) -> float:
            # 与 _build_ecommerce_sql 保持一致：intent 层保留原始值，SQL 阶段根据问题中的单位换算
            if col == "达成率":
                return raw
            q = normalized_question
            if "亿" in q and raw < 10000:
                return raw * 100000000
            if "万" in q and raw < 10000:
                return raw * 10000
            return raw

        syyb_metric_map = {
            "总任务金额": "总任务金额",
            "总任务": "总任务金额",
            "任务金额": "总任务金额",
            "年度开单金额": "年度开单金额",
            "年度开单": "年度开单金额",
            "开单金额": "年度开单金额",
            "开单": "年度开单金额",
            "实际": "年度开单金额",
            "达成率": "达成率",
            "剩余任务金额": "剩余任务金额",
            "剩余任务": "剩余任务金额",
            "缺口": "剩余任务金额",
        }

        def map_syyb_metric(text: str) -> str:
            for key, col in sorted(syyb_metric_map.items(), key=lambda x: -len(x[0])):
                if key in text:
                    return col
            return ""

        # 纯层级/条线过滤，不附带数值阈值
        if intent_is_filter and query_intent.get("filter_metric_key") == "level_only":
            is_multi_parent = query_intent.get("_multi_parent") is True
            where_parts = []
            # 多父节点 overview 需要同时返回父节点本身和直接下级，不能限制单一层级
            if intent_target_level and not is_multi_parent:
                where_parts.append(f"层级 = '{intent_target_level}'")
            elif not is_multi_parent and "业务部" in normalized_question:
                where_parts.append("层级 = '业务部'")
            elif not is_multi_parent and "代表处" in normalized_question:
                where_parts.append("层级 = '代表处'")
            elif not is_multi_parent and "分公司" in normalized_question:
                where_parts.append("层级 IN ('分公司', '业务部')")
            if "行业条线" in normalized_question:
                where_parts.append("条线 = '行业条线'")
            elif "区域条线" in normalized_question:
                where_parts.append("条线 = '区域条线'")
            # 若明确点名了多个具体对象，再按对象过滤，避免误走末端个人 KPI
            if is_multi_parent:
                entity_names = query_intent.get("_multi_parent_names") or []
            else:
                entity_names = self._resolved_entity_names(context) or self._question_subject_names(normalized_question, context, include_resolved=False)
            if entity_names:
                specific_names = [n for n in entity_names if n and n not in generic_level_terms]
                if specific_names:
                    quoted_names = ",".join("'" + n.replace("'", "''") + "'" for n in specific_names)
                    if intent_target_level == "业务代表" and not is_multi_parent:
                        where_parts.append(f"业务代表 IN ({quoted_names})")
                    else:
                        where_parts.append(f"节点名称 IN ({quoted_names}) OR 上级名称 IN ({quoted_names})")
            where_clause = " AND ".join(where_parts) if where_parts else "TRUE"
            return f"""
WITH 汇总结果 AS (
{syyb_base_sql}
)
SELECT *
FROM 汇总结果
WHERE {where_clause}
ORDER BY 达成率 DESC, 剩余任务金额 DESC, 条线 DESC, 节点名称
LIMIT 200
""".strip()

        if intent_is_filter and filter_metric_column in allowed_filter_columns and filter_operator in {"<", "<=", ">", ">=", "=", "between"} and filter_value is not None:
            try:
                filter_value_sql = f"{float(filter_value):g}"
            except (TypeError, ValueError):
                filter_value_sql = ""
            if filter_value_sql:
                all_conditions = query_intent.get("filter_conditions") or []
                if not all_conditions:
                    all_conditions = [{"column": filter_metric_column, "operator": filter_operator, "value": filter_value, "value2": query_intent.get("filter_value2")}]
                where_parts = []
                for cond in all_conditions:
                    col = cond["column"]
                    op = cond["operator"]
                    val = cond["value"]
                    val2 = cond.get("value2")
                    if col not in allowed_filter_columns:
                        continue
                    try:
                        scaled_val = normalize_syyb_threshold_value(float(val), col)
                        val_sql = f"{scaled_val:g}"
                    except (TypeError, ValueError):
                        continue
                    if op == "between":
                        try:
                            scaled_val2 = normalize_syyb_threshold_value(float(val2), col) if val2 is not None else scaled_val
                            val2_sql = f"{scaled_val2:g}"
                        except (TypeError, ValueError):
                            val2_sql = ""
                        if val2_sql:
                            where_parts.append(f"{col} BETWEEN {val_sql} AND {val2_sql}")
                        else:
                            where_parts.append(f"{col} >= {val_sql}")
                    else:
                        where_parts.append(f"{col} {op} {val_sql}")
                if not where_parts:
                    try:
                        scaled_filter_value = normalize_syyb_threshold_value(float(filter_value), filter_metric_column)
                        filter_value_sql = f"{scaled_filter_value:g}"
                    except (TypeError, ValueError):
                        filter_value_sql = ""
                    if filter_value_sql:
                        where_parts = [f"{filter_metric_column} {filter_operator} {filter_value_sql}"]
                if intent_target_level:
                    where_parts.insert(0, f"层级 = '{intent_target_level}'")
                if "行业条线" in normalized_question:
                    where_parts.append("条线 = '行业条线'")
                elif "区域条线" in normalized_question:
                    where_parts.append("条线 = '区域条线'")
                spoken_filter_triggers = {"spoken_zero_actual", "spoken_lagging"}
                matched_triggers = set(query_intent.get("matched_triggers") or [])
                if not (matched_triggers & spoken_filter_triggers):
                    level_values = {"分公司", "代表处", "业务部", "事业部", "城市公司", "城市分公司", "业务代表"}
                    all_entities = [
                        n for n in self._resolved_entity_names(context) if n
                        and n not in level_values
                        and len(n) >= 4
                        and any(n.endswith(suffix) for suffix in ["分公司", "代表处", "业务部", "事业部", "城市公司", "城市分公司"])
                        and not re.search(r"\d|万", n)
                        and not any(t in n for t in ["年度", "开单", "任务", "达成", "剩余", "销售", "实际", "大于", "小于", "高于", "低于", "超过", "不少于", "不低于", "达到", "之间", "范围"])
                    ]
                    entity_names = [e for e in all_entities if e in normalized_question]
                    if entity_names:
                        quoted_entities = ",".join("'" + item.replace("'", "''") + "'" for item in entity_names)
                        target_level = intent_target_level or ""
                        if target_level == "分公司":
                            has_business_unit = any(e.endswith("事业部") for e in entity_names)
                            has_branch = any(e.endswith("分公司") and not e.endswith("城市分公司") for e in entity_names)
                            if has_business_unit:
                                where_parts.append(f"上级名称 IN ({quoted_entities})")
                            elif has_branch:
                                where_parts.append(f"节点名称 IN ({quoted_entities})")
                        elif target_level == "城市分公司" or target_level == "城市公司":
                            where_parts.append(f"上级名称 IN ({quoted_entities}) OR 节点名称 IN ({quoted_entities})")
                        else:
                            where_parts.append(f"节点名称 IN ({quoted_entities}) OR 上级名称 IN ({quoted_entities})")
                where_clause = " AND ".join(where_parts)
                order_direction = "ASC" if filter_operator in {"<", "<="} else "DESC"
                tie_breaker = "剩余任务金额 DESC, 条线 DESC, 节点名称" if filter_metric_column == "达成率" else "达成率 ASC, 条线 DESC, 节点名称"
                generated_sql = f"""
WITH 汇总结果 AS (
{syyb_base_sql}
)
SELECT *
FROM 汇总结果
WHERE {where_clause}
ORDER BY {filter_metric_column} {order_direction}, {tie_breaker}
LIMIT 200
""".strip()
                print("[DEBUG] syyb filter SQL:\n", generated_sql, flush=True)
                return generated_sql

        if intent_is_comparison:
            left_text = str(query_intent.get("comparison_left") or "").strip()
            right_text = str(query_intent.get("comparison_right") or "").strip()
            left_col = map_syyb_metric(left_text)
            right_col = map_syyb_metric(right_text)
            op = str(query_intent.get("comparison_operator") or ">")
            if left_col and right_col:
                where_parts = [f"{left_col} {op} {right_col}"]
                if intent_target_level:
                    where_parts.insert(0, f"层级 = '{intent_target_level}'")
                elif "代表处" in normalized_question:
                    where_parts.insert(0, "层级 = '代表处'")
                elif "业务代表" in normalized_question:
                    where_parts.insert(0, "层级 = '业务代表'")
                elif "分公司" in normalized_question or "业务部" in normalized_question:
                    where_parts.insert(0, "层级 IN ('分公司', '业务部')")
                where_clause = " AND ".join(where_parts)
                return f"""
WITH 汇总结果 AS (
{syyb_base_sql}
)
SELECT *
FROM 汇总结果
WHERE {where_clause}
ORDER BY {left_col} DESC, 条线 DESC, 节点名称
LIMIT 200
""".strip()

        if intent_is_aggregate:
            group_level = intent_target_level
            if not group_level:
                if "业务代表" in normalized_question:
                    group_level = "业务代表"
                elif "代表处" in normalized_question:
                    group_level = "代表处"
                elif "分公司" in normalized_question or "业务部" in normalized_question:
                    group_level = "分公司"
                elif "条线" in normalized_question:
                    group_level = "条线"
                else:
                    group_level = "分公司"

            group_by_field = "节点名称"
            where_level = f"层级 = '{group_level}'"
            if group_level == "条线":
                group_by_field = "条线"
                where_level = "条线 IN ('区域条线', '行业条线')"
            elif "下属" in normalized_question and "代表处" in normalized_question:
                group_by_field = "上级名称"
                where_level = "层级 = '代表处'"

            if "平均" in normalized_question:
                if "达成率" in normalized_question:
                    agg_select = "AVG(达成率) AS 平均达成率, COUNT(*) AS 节点数量"
                elif "任务" in normalized_question:
                    agg_select = "AVG(总任务金额) AS 平均任务金额, SUM(总任务金额) AS 总任务金额"
                elif "开单" in normalized_question or "实际" in normalized_question:
                    agg_select = "AVG(年度开单金额) AS 平均开单金额, SUM(年度开单金额) AS 总开单金额"
                else:
                    agg_select = "AVG(达成率) AS 平均达成率, SUM(年度开单金额) AS 总开单金额"
            elif "数量" in normalized_question or "个数" in normalized_question or "多少个" in normalized_question:
                agg_select = "COUNT(*) AS 节点数量"
            else:
                if "任务" in normalized_question:
                    agg_select = "SUM(总任务金额) AS 总任务金额, AVG(达成率) AS 平均达成率"
                else:
                    agg_select = "SUM(年度开单金额) AS 总开单金额, AVG(达成率) AS 平均达成率"

            if "总开单金额" in agg_select:
                order_by = "总开单金额 DESC NULLS LAST"
            elif "总任务金额" in agg_select:
                order_by = "总任务金额 DESC NULLS LAST"
            elif "节点数量" in agg_select:
                order_by = "节点数量 DESC NULLS LAST"
            else:
                order_by = "分组名称"

            return f"""
WITH 汇总结果 AS (
{syyb_base_sql}
)
SELECT
    {group_by_field} AS 分组名称,
    {agg_select}
FROM 汇总结果
WHERE {where_level}
GROUP BY {group_by_field}
ORDER BY {order_by}
LIMIT 200
""".strip()

        ranking_tokens = ["排名", "最低", "最高", "最好", "最差", "Top", "top", "前", "后", "第一", "倒数第一"]
        has_ranking_intent = (
            intent_name == "ranking"
            or any(token in normalized_question for token in ranking_tokens)
        )
        if is_phase1_dataset and has_ranking_intent:
            rank_spec = self._rank_request_spec(normalized_question, default_limit=0, max_limit=20)
            # 优先使用 intent 层已解析的 top_n（含 LLM 补漏、最X默认1 等后处理），再用规则兜底
            configured_limit = int(query_intent.get("top_n") if query_intent.get("top_n") is not None else (rank_spec.get("limit") or 0))
            rank_sides = str(query_intent.get("rank_sides") or rank_spec.get("sides") or "")
            # 分别解析用户明确要求的前 N 与后 N，支持“前3后5”等双向不同数量
            top_rank_limit = int(query_intent.get("top_limit") if query_intent.get("top_limit") is not None else (rank_spec.get("top_limit") or 0))
            bottom_rank_limit = int(query_intent.get("bottom_limit") if query_intent.get("bottom_limit") is not None else (rank_spec.get("bottom_limit") or 0))
            # 只有题干带明确数量词（Top/前/后/倒数）才默认取 Top3；仅说“排名/排行”时返回全部
            default_rank_limit = 3 if self._rank_limit_match(normalized_question) or any(
                token in normalized_question for token in ["Top", "top", "前", "后", "倒数"]
            ) else 0
            rank_limit = max(0, min(20, configured_limit or default_rank_limit))
            is_top_rank = rank_sides != "bottom"
            order_direction = "DESC" if is_top_rank else "ASC"
            asks_grouped_rank = any(token in normalized_question for token in ["各", "每个", "分别", "各自", "按上级", "按代表处", "分组"])
            allowed_rank_columns = {"总任务金额", "年度开单金额", "达成率", "剩余任务金额"}
            intent_metric_column = str(query_intent.get("sort_metric_column") or "").strip()
            phase1_metric_column = intent_metric_column if intent_metric_column in allowed_rank_columns else ""
            if not phase1_metric_column:
                if "剩余" in normalized_question or "缺口" in normalized_question or "待完成" in normalized_question:
                    phase1_metric_column = "剩余任务金额"
                elif "任务" in normalized_question or "目标" in normalized_question:
                    phase1_metric_column = "总任务金额"
                elif "开单" in normalized_question or "金额" in normalized_question or "销售" in normalized_question:
                    phase1_metric_column = "年度开单金额"
                else:
                    phase1_metric_column = "达成率"

            target_is_business_person = normalized_target_level in {"业务代表", "业务员", "销售", "销售人员"}
            target_is_office = normalized_target_level == "代表处"
            target_is_business_dept = normalized_target_level == "业务部"
            target_is_branch = normalized_target_level == "分公司"

            if target_is_business_person or "业务代表" in normalized_question or "业务员" in normalized_question:
                metric_column = phase1_metric_column
                syyb_dictionary_keys = {
                    str(item.get("jsonb_key") or "").strip()
                    for item in context.get("data_dictionary", []) or []
                    if str(item.get("jsonb_key") or "").strip()
                }
                business_dept_extract = (
                    "TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务部') = 'array' THEN fields->'业务部'->0->>'text' ELSE fields->>'业务部' END, '')) AS 业务部"
                    if "业务部" in syyb_dictionary_keys
                    else "'' AS 业务部"
                )
                business_person_rank_sql = f"""
WITH 业务代表原始 AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        {business_dept_extract},
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
业务代表汇总 AS (
    SELECT
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        '业务代表' AS 层级,
        业务代表 AS 节点名称,
        COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部') AS 上级名称,
        NULLIF(分公司, '') AS 分公司,
        NULLIF(代表处, '') AS 代表处,
        NULLIF(业务部, '') AS 业务部,
        concat_ws(' / ', NULLIF(分公司, ''), NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(业务代表, '')) AS 组织路径,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM 业务代表原始
    WHERE 业务代表 <> ''
    GROUP BY 分公司, 代表处, 业务部, 业务代表
),
业务代表结果 AS (
    SELECT
        条线,
        层级,
        组织路径,
        节点名称,
        上级名称,
        分公司,
        代表处,
        业务部,
        总任务金额,
        年度开单金额,
        CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
        ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
    FROM 业务代表汇总
)
"""
                if rank_sides == "both":
                    return self._build_ranked_select_sql(
                        source_cte=business_person_rank_sql,
                        source_name="业务代表结果",
                        output_cte="业务代表双向排序",
                        where_clause="TRUE",
                        metric_column=metric_column,
                        direction=order_direction,
                        rank_limit=rank_limit,
                        rank_sides=rank_sides,
                        top_rank_limit=top_rank_limit,
                        bottom_rank_limit=bottom_rank_limit,
                        tie_breaker="剩余任务金额 DESC, 组织路径",
                    )
                if asks_grouped_rank:
                    return f"""
{business_person_rank_sql},
业务代表上级内排序 AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY 上级名称
            ORDER BY {metric_column} {order_direction}, 剩余任务金额 DESC, 节点名称
        ) AS 上级内排名
    FROM 业务代表结果
)
SELECT *
FROM 业务代表上级内排序
WHERE 上级内排名 <= {rank_limit}
ORDER BY 上级名称, 上级内排名, {metric_column} {order_direction}, 剩余任务金额 DESC, 组织路径
LIMIT 100
""".strip()
                return f"""
{business_person_rank_sql},
业务代表全局排序 AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            ORDER BY {metric_column} {order_direction}, 剩余任务金额 DESC, 组织路径
        ) AS 全局排名
    FROM 业务代表结果
)
SELECT *
FROM 业务代表全局排序
WHERE 全局排名 <= {rank_limit}
ORDER BY 全局排名, {metric_column} {order_direction}, 剩余任务金额 DESC, 组织路径
LIMIT {rank_limit}
""".strip()
            if target_is_office or "代表处" in normalized_question:
                asks_extreme_rank = any(token in normalized_question for token in ["最好", "最差", "最高", "最低", "哪个", "第一", "倒数第一"])
                if rank_sides == "both":
                    return self._build_ranked_select_sql(
                        source_cte=f"WITH 汇总结果 AS (\n{syyb_base_sql}\n)",
                        source_name="汇总结果",
                        output_cte="代表处双向排序",
                        where_clause="层级 = '代表处'",
                        metric_column=phase1_metric_column,
                        direction=order_direction,
                        rank_limit=rank_limit,
                        rank_sides=rank_sides,
                        top_rank_limit=top_rank_limit,
                        bottom_rank_limit=bottom_rank_limit,
                        tie_breaker="剩余任务金额 DESC, 节点名称",
                    )
                if configured_limit > 0 or asks_extreme_rank:
                    rank_where = f"全局排名 <= {rank_limit}" if rank_limit > 0 else "TRUE"
                rank_limit_clause = f"LIMIT {rank_limit}" if rank_limit > 0 else "LIMIT 10000"
                return f"""
WITH 汇总结果 AS (
{syyb_base_sql}
),
代表处全局排序 AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            ORDER BY {phase1_metric_column} {order_direction}, 剩余任务金额 DESC, 节点名称
        ) AS 全局排名
    FROM 汇总结果
    WHERE 层级 = '代表处'
)
SELECT *
FROM 代表处全局排序
WHERE {rank_where}
ORDER BY 全局排名, {phase1_metric_column} {order_direction}, 剩余任务金额 DESC, 节点名称
{rank_limit_clause}
""".strip()
                intra_rank_where = f"分公司内排名 <= {rank_limit}" if rank_limit > 0 else "TRUE"
                return f"""
WITH 汇总结果 AS (
{syyb_base_sql}
),
代表处分公司内排序 AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY 上级名称
            ORDER BY {phase1_metric_column} {order_direction}, 剩余任务金额 DESC, 节点名称
        ) AS 分公司内排名
    FROM 汇总结果
    WHERE 层级 = '代表处'
)
SELECT *
FROM 代表处分公司内排序
WHERE {intra_rank_where}
ORDER BY 上级名称, 分公司内排名, {phase1_metric_column} {order_direction}, 剩余任务金额 DESC, 节点名称
LIMIT 10000
""".strip()
            if target_is_business_dept or "业务部" in normalized_question:
                return self._build_ranked_select_sql(
                    source_cte=f"WITH 汇总结果 AS (\n{syyb_base_sql}\n)",
                    source_name="汇总结果",
                    output_cte="业务部排序",
                    where_clause="层级 = '业务部'",
                    metric_column=phase1_metric_column,
                    direction=order_direction,
                    rank_limit=rank_limit,
                    rank_sides=rank_sides,
                    top_rank_limit=top_rank_limit,
                    bottom_rank_limit=bottom_rank_limit,
                    tie_breaker="剩余任务金额 DESC, 节点名称",
                )
            if target_is_branch or "分公司" in normalized_question:
                return self._build_ranked_select_sql(
                    source_cte=f"WITH 汇总结果 AS (\n{syyb_base_sql}\n)",
                    source_name="汇总结果",
                    output_cte="分公司排序",
                    where_clause="层级 = '分公司' AND 节点名称 LIKE '%分公司'",
                    metric_column=phase1_metric_column,
                    direction=order_direction,
                    rank_limit=rank_limit,
                    rank_sides=rank_sides,
                    top_rank_limit=top_rank_limit,
                    bottom_rank_limit=bottom_rank_limit,
                    tie_breaker="剩余任务金额 DESC, 节点名称",
                )

        # phase1 通用排名兜底：命中 ranking 意图但没有进入具体层级分支时，按指标全局/按目标层级排序
        if is_phase1_dataset and intent_name == "ranking":
            allowed_rank_columns = {"总任务金额", "年度开单金额", "达成率", "剩余任务金额"}
            intent_metric_column = str(query_intent.get("sort_metric_column") or "").strip()
            phase1_metric_column = intent_metric_column if intent_metric_column in allowed_rank_columns else ""
            if not phase1_metric_column:
                if "剩余" in normalized_question or "缺口" in normalized_question or "待完成" in normalized_question:
                    phase1_metric_column = "剩余任务金额"
                elif "任务" in normalized_question or "目标" in normalized_question:
                    phase1_metric_column = "总任务金额"
                elif "开单" in normalized_question or "金额" in normalized_question or "销售" in normalized_question:
                    phase1_metric_column = "年度开单金额"
                else:
                    phase1_metric_column = "达成率"

            rank_spec_fallback = self._rank_request_spec(normalized_question, default_limit=0, max_limit=20)
            top_n_fallback = query_intent.get("top_n")
            if top_n_fallback is None or top_n_fallback == "":
                top_n_fallback = rank_spec_fallback.get("limit")
            rank_limit_fallback = max(0, min(20, int(top_n_fallback or 0)))
            rank_sides_fallback = str(query_intent.get("rank_sides") or rank_spec_fallback.get("sides") or "")
            top_rank_limit_fallback = int(query_intent.get("top_limit") if query_intent.get("top_limit") is not None else (rank_spec_fallback.get("top_limit") or 0))
            bottom_rank_limit_fallback = int(query_intent.get("bottom_limit") if query_intent.get("bottom_limit") is not None else (rank_spec_fallback.get("bottom_limit") or 0))
            order_direction_fallback = "ASC" if rank_sides_fallback == "bottom" else "DESC"

            # 修复：目标层级如果匹配到 analysisDimensions 的根节点名称（如“商用事业部”），
            # 不能直接按层级字段过滤（层级字段值是“事业部”），应清空后按问题中的其他层级词兜底。
            report_config = self._safe_dict(context.get("report_config")) or {}
            root_level_values = {
                str(dimension.get("path")[0]).strip()
                for dimension in (report_config.get("analysisDimensions") or [])
                if isinstance(dimension.get("path") or [], list) and (dimension.get("path") or [])
            }
            if normalized_target_level in root_level_values:
                normalized_target_level = ""

            where_clause = "TRUE"
            if normalized_target_level:
                where_clause = f"层级 = '{normalized_target_level}'"
            elif "代表处" in normalized_question:
                where_clause = "层级 = '代表处'"
            elif "分公司" in normalized_question or "业务部" in normalized_question:
                where_clause = "层级 IN ('分公司', '业务部')"
            elif "业务代表" in normalized_question or "人" in normalized_question:
                where_clause = "层级 = '业务代表'"
            else:
                # 默认按分公司层级排序，避免返回全层级导致排序样本杂乱
                # 同时排除被额外映射为分公司的业务部叶子节点，保证排名口径为区域分公司
                where_clause = "层级 = '分公司' AND 节点名称 LIKE '%分公司'"
            if "区域条线" in normalized_question:
                where_clause = f"{where_clause} AND 条线 = '区域条线'" if where_clause != "TRUE" else "条线 = '区域条线'"
            elif "行业条线" in normalized_question:
                where_clause = f"{where_clause} AND 条线 = '行业条线'" if where_clause != "TRUE" else "条线 = '行业条线'"

            return self._build_ranked_select_sql(
                source_cte=f"WITH 汇总结果 AS (\n{syyb_base_sql}\n)",
                source_name="汇总结果",
                output_cte="通用排序",
                where_clause=where_clause,
                metric_column=phase1_metric_column,
                direction=order_direction_fallback,
                rank_limit=rank_limit_fallback,
                rank_sides=rank_sides_fallback,
                top_rank_limit=top_rank_limit_fallback,
                bottom_rank_limit=bottom_rank_limit_fallback,
                tie_breaker="剩余任务金额 DESC, 节点名称",
            )

        if is_phase1_dataset and any(token in normalized_question for token in ["低于10", "低于 10", "小于10", "小于 10", "风险"]):
            return f"""
WITH 汇总结果 AS (
{syyb_base_sql}
)
SELECT *
FROM 汇总结果
WHERE 达成率 < 10
ORDER BY 达成率 ASC, 剩余任务金额 DESC, 节点名称
LIMIT 50
""".strip()

        # 优先使用统一校验后的主体，其次才是 Agent1/本地规则提取的实体。
        resolved_subject_name = str(query_intent.get("subject_name") or "").strip()
        entity_names = [resolved_subject_name] if resolved_subject_name else []
        for value in self._resolved_entity_names(context):
            if value not in entity_names:
                entity_names.append(value)
        # 是否提到具体节点以 Agent1.5 的 has_specific_node 为准；
        # 未明确点名具体节点时，跳过本地正则兜底，避免把“大于一个亿的分公司”等当成实体。
        has_specific_node = self._has_specific_node(context)
        if not entity_names and has_specific_node:
            entity_names = self._role_person_subject_names(normalized_question)
        if not entity_names:
            entity_names = self._question_subject_names(normalized_question, context, include_resolved=False)
        if not entity_names and has_specific_node:
            profile = get_dataset_profile(dataset_code, dataset_name)
            if profile:
                semantic_fallback = resolve_member_mentions(normalized_question, profile)
                entity_names = [str(item).strip() for item in (semantic_fallback.get("all_members") or []) if str(item).strip()]
        if not entity_names and has_specific_node:
            for match in re.findall(r"[\u4e00-\u9fa5A-Za-z0-9（）()]+?(?:代表处|分公司|业务部)", normalized_question):
                cleaned = match.strip("，,、 和与及的业绩情况表现")
                if re.search(r"\d|万", cleaned):
                    continue
                if is_phase1_dataset and cleaned in {"哪些代表处", "各代表处", "所有代表处", "哪些分公司", "各分公司", "所有分公司", "哪些业务部", "各业务部"}:
                    continue
                if re.search(r"^(?:三|四|五|六|七|八|九|十|两|\d+)(?:个|大)?", cleaned):
                    continue
                if any(token in cleaned for token in ["哪些", "所有", "各", "每个", "业务线", "任务完成", "最好", "最高", "最低", "哪个"]):
                    continue
                if cleaned and cleaned not in entity_names:
                    entity_names.append(cleaned)
        if not entity_names:
            entity_names = self._question_subject_names(normalized_question, context)

        # 如果实体名只是通用层级词（如"分公司"），按该层级过滤而不是按节点名过滤
        resolved_subject_name = str(query_intent.get("subject_name") or "").strip()
        generic_level_only = (
            bool(entity_names and all(name in generic_level_terms for name in entity_names))
            or resolved_subject_name in generic_level_terms
        )
        if generic_level_only:
            entity_names = []

        if entity_names:
            quoted_entities = ",".join("'" + item.replace("'", "''") + "'" for item in entity_names)
            # 修复：问题中包含下钻词，或询问某组织下特定层级（如“分公司代表处业绩”）时，
            # 即使解析出多个组织实体，也应优先走明细下钻，不走对比。
            drilldown_tokens = ["下", "下辖", "下属", "明细", "详情", "有哪些"]
            has_explicit_compare = bool(re.search(r"对比|比较|哪个|谁更|差异|分别|各自|相比|和.+比|跟.+比|与.+比|\bvs\b", normalized_question, re.I))
            asks_child_level = any(level_word in normalized_question for level_word in ["代表处", "业务部", "业务代表", "业务员"])
            is_drilldown_question = (
                (any(token in normalized_question for token in drilldown_tokens) and not has_explicit_compare)
                or (asks_child_level and not has_explicit_compare)
            )
            comparison_intent = (
                (len(entity_names) > 1 and not is_drilldown_question)
                or has_explicit_compare
            )
            if comparison_intent:
                # 对比分支也要区人名与组织节点
                cmp_profile = get_dataset_profile(dataset_code, dataset_name)
                cmp_person_members: set = set()
                if cmp_profile:
                    for level in cmp_profile.get("levels") or []:
                        if str(level.get("dimension_name") or "").strip() in {"业务员", "业务代表"}:
                            cmp_person_members.update(str(m).strip() for m in level.get("members") or [] if str(m).strip())
                cmp_person_names = [e for e in entity_names if e in cmp_person_members]
                cmp_org_names = [e for e in entity_names if e not in cmp_person_names]
                cmp_where_parts = []
                if cmp_org_names and cmp_person_names:
                    # 对比同时含组织与人名：分别按组织字段和业务代表返回
                    org_where_parts = []
                    for org in cmp_org_names:
                        safe_org = org.replace("'", "''")
                        if org.endswith("事业部"):
                            org_where_parts.append(f"事业部 = '{safe_org}'")
                        elif org.endswith("分公司"):
                            org_where_parts.append(f"分公司 = '{safe_org}'")
                        elif org.endswith("代表处"):
                            org_where_parts.append(f"代表处 = '{safe_org}'")
                        elif org.endswith("业务部"):
                            org_where_parts.append(f"业务部 = '{safe_org}'")
                        else:
                            org_where_parts.append(f"节点名称 = '{safe_org}' OR 上级名称 = '{safe_org}'")
                    quoted_persons = ",".join("'" + item.replace("'", "''") + "'" for item in cmp_person_names)
                    cmp_where_parts.append(f"({' OR '.join(org_where_parts)} OR 业务代表 IN ({quoted_persons}))")
                elif cmp_org_names:
                    org_where_parts = []
                    for org in cmp_org_names:
                        safe_org = org.replace("'", "''")
                        if org.endswith("事业部"):
                            org_where_parts.append(f"事业部 = '{safe_org}'")
                        elif org.endswith("分公司"):
                            org_where_parts.append(f"分公司 = '{safe_org}'")
                        elif org.endswith("代表处"):
                            org_where_parts.append(f"代表处 = '{safe_org}'")
                        elif org.endswith("业务部"):
                            org_where_parts.append(f"业务部 = '{safe_org}'")
                        else:
                            org_where_parts.append(f"节点名称 = '{safe_org}' OR 上级名称 = '{safe_org}'")
                    cmp_where_parts.append(f"({' OR '.join(org_where_parts)})")
                elif cmp_person_names:
                    quoted_persons = ",".join("'" + item.replace("'", "''") + "'" for item in cmp_person_names)
                    cmp_where_parts.append(f"业务代表 IN ({quoted_persons})")
                cmp_where = " AND ".join(cmp_where_parts) if cmp_where_parts else "TRUE"
                return f"""
WITH 汇总结果 AS (
{syyb_base_sql}
)
SELECT *
FROM 汇总结果
WHERE {cmp_where}
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
""".strip()
            # 单一对象统一按“命中节点 + 一层下级”返回，最多二级；
            # 只有业务代表/业务员这种末端节点不再继续下钻。
            report_config = self._safe_dict(context.get("report_config")) or {}
            root_level_values = {
                str(dimension.get("path")[0]).strip()
                for dimension in (report_config.get("analysisDimensions") or [])
                if isinstance(dimension.get("path") or [], list) and (dimension.get("path") or [])
            }
            drilldown_entities = [e for e in entity_names if e not in root_level_values] or entity_names
            quoted_entities = ",".join("'" + item.replace("'", "''") + "'" for item in drilldown_entities)
            target_level_hint = str(query_intent.get("target_level") or "").strip()
            # 预读业务员画像成员，用于判断 drilldown_entities 中是否包含具体人名
            terminal_profile = get_dataset_profile(dataset_code, dataset_name)
            terminal_person_members: set = set()
            if terminal_profile:
                for level in terminal_profile.get("levels") or []:
                    if str(level.get("dimension_name") or "").strip() in {"业务员", "业务代表"}:
                        terminal_person_members.update(str(m).strip() for m in level.get("members") or [] if str(m).strip())
            terminal_person_members.update(self._node_index_members_by_level(context, {"业务员", "业务代表"}))
            terminal_person_names = [e for e in drilldown_entities if e in terminal_person_members]
            is_terminal_node = (
                target_level_hint in {"业务代表", "业务员"}
                or "业务代表" in normalized_question
                or "业务员" in normalized_question
                or any(name.endswith("业务代表") or name.endswith("业务员") for name in drilldown_entities)
                or bool(terminal_person_names)
            )

            if is_terminal_node:
                # 区分业务代表人名与组织节点名：人名按业务代表字段过滤，组织节点按节点/上级过滤
                profile = get_dataset_profile(dataset_code, dataset_name)
                person_members: set = set()
                if profile:
                    for level in profile.get("levels") or []:
                        if str(level.get("dimension_name") or "").strip() in {"业务员", "业务代表"}:
                            person_members.update(str(m).strip() for m in level.get("members") or [] if str(m).strip())
                person_members.update(self._node_index_members_by_level(context, {"业务员", "业务代表"}))
                person_names = [e for e in drilldown_entities if e in person_members]
                org_names = [e for e in drilldown_entities if e not in person_names]
                where_parts = []
                # 明确对比且同时含组织与人名时，保守按节点/人名分别返回，不做范围限定
                mixed_with_compare = (
                    has_explicit_compare
                    and bool(org_names)
                    and bool(person_names)
                )
                if mixed_with_compare:
                    quoted_all = ",".join("'" + item.replace("'", "''") + "'" for item in drilldown_entities)
                    where_parts.append(f"节点名称 IN ({quoted_all}) OR 上级名称 IN ({quoted_all}) OR 业务代表 IN ({quoted_all})")
                else:
                    if org_names:
                        org_where_parts = []
                        for org in org_names:
                            safe_org = org.replace("'", "''")
                            if org.endswith("事业部"):
                                org_where_parts.append(f"事业部 = '{safe_org}'")
                            elif org.endswith("分公司"):
                                org_where_parts.append(f"分公司 = '{safe_org}'")
                            elif org.endswith("代表处"):
                                org_where_parts.append(f"代表处 = '{safe_org}'")
                            elif org.endswith("业务部"):
                                org_where_parts.append(f"业务部 = '{safe_org}'")
                            else:
                                org_where_parts.append(f"节点名称 = '{safe_org}' OR 上级名称 = '{safe_org}'")
                        where_parts.append(f"({' OR '.join(org_where_parts)})")
                    if person_names:
                        quoted_persons = ",".join("'" + item.replace("'", "''") + "'" for item in person_names)
                        where_parts.append(f"业务代表 IN ({quoted_persons})")
                terminal_where = " AND ".join(where_parts) if where_parts else "TRUE"
                return f"""
WITH 汇总结果 AS (
{syyb_base_sql}
)
SELECT *
FROM 汇总结果
WHERE {terminal_where}
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
""".strip()

            return f"""
WITH RECURSIVE 汇总结果 AS (
{syyb_base_sql}
),
命中链路 AS (
    SELECT *, 1 AS _depth
    FROM 汇总结果
    WHERE 节点名称 IN ({quoted_entities})
    UNION ALL
    SELECT 子节点.*, 父节点._depth + 1
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
    WHERE 父节点._depth < 2
)
SELECT *
FROM (
    SELECT DISTINCT ON (节点名称) *
    FROM 命中链路
    WHERE _depth <= 2
    ORDER BY 节点名称, _depth
) 去重后
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
""".strip()

        single_entity_drill_tokens = ["业绩", "绩效", "达成率", "达成", "开单", "完成情况", "完成", "情况", "表现", "分析", "怎么样", "如何"]
        block_single_entity_shortcuts = (
            len(entity_names) == 1
            and any(token in normalized_question for token in single_entity_drill_tokens)
            and not any(token in normalized_question for token in ["排名", "排行", "Top", "top", "对比", "比较", "分别", "哪些", "列表"])
        )

        if block_single_entity_shortcuts:
            report_config = self._safe_dict(context.get("report_config")) or {}
            root_level_values = {
                str(dimension.get("path")[0]).strip()
                for dimension in (report_config.get("analysisDimensions") or [])
                if isinstance(dimension.get("path") or [], list) and (dimension.get("path") or [])
            }
            drilldown_entities = [e for e in entity_names if e not in root_level_values] or entity_names
            quoted_entities = ",".join("'" + item.replace("'", "''") + "'" for item in drilldown_entities)
            target_level_hint = str(query_intent.get("target_level") or "").strip()
            is_terminal_node = target_level_hint == "业务代表" or any(name.endswith("业务代表") for name in drilldown_entities)

            if is_terminal_node:
                return f"""
{syyb_base_sql}
HAVING 节点名称 IN ({quoted_entities})
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
""".strip()

            return f"""
WITH RECURSIVE 汇总结 果 AS (
{syyb_base_sql}
),
命中链路 AS (
    SELECT *, 1 AS _depth
    FROM 汇总结 果
    WHERE 节点名称 IN ({quoted_entities})
    UNION ALL
    SELECT 子节点.*, 父节点._depth + 1
    FROM 汇总结 果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
    WHERE 父节点._depth < 2
)
SELECT *
FROM (
    SELECT DISTINCT ON (节点名称) *
    FROM 命中链路
    WHERE _depth <= 2
    ORDER BY 节点名称, _depth
) 去重后
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
""".strip()

        if not block_single_entity_shortcuts and all(token in normalized_question for token in ["东部分公司", "南部分公司"]):
            return f"""
{syyb_base_sql}
HAVING 节点名称 IN ('东部分公司','南部分公司') OR 上级名称 IN ('东部分公司','南部分公司')
ORDER BY 条线 DESC, 层级 DESC, 上级名称, 节点名称
LIMIT 10000
""".strip()

        if not block_single_entity_shortcuts and all(token in normalized_question for token in ["东部分公司", "达成率", "剩余任务"]):
            return """
WITH 字段提取 AS (
  SELECT
    CASE WHEN jsonb_typeof(fields->'分公司')='array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END AS 分公司,
    CASE WHEN jsonb_typeof(fields->'代表处')='array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END AS 代表处,
    CASE WHEN jsonb_typeof(fields->'业务代表')='array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END AS 业务代表,
    CASE WHEN jsonb_typeof(fields->'总任务（金额）')='array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END AS 任务原始,
    CASE WHEN jsonb_typeof(fields->'年度开单金额')='array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END AS 开单原始,
    CASE WHEN jsonb_typeof(fields->'当前年')='array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END AS 当前年
  FROM angel_group_data
),
基础数据 AS (
  SELECT
    分公司,
    代表处,
    业务代表,
    COALESCE(NULLIF(regexp_replace(任务原始,'[^0-9.-]','','g'),''),'0')::NUMERIC AS 任务金额,
    COALESCE(NULLIF(regexp_replace(开单原始,'[^0-9.-]','','g'),''),'0')::NUMERIC AS 开单金额
  FROM 字段提取
  WHERE COALESCE(NULLIF(当前年,''),'2026')='2026'
),
分公司汇总 AS (
  SELECT
    分公司 AS 节点名称,
    SUM(任务金额) AS 总任务金额,
    SUM(开单金额) AS 年度开单金额
  FROM 基础数据
  WHERE 分公司='东部分公司'
    AND (代表处 IS NULL OR 代表处='')
    AND (业务代表 IS NULL OR 业务代表='')
  GROUP BY 分公司
)
SELECT
  节点名称 AS 分公司,
  总任务金额,
  年度开单金额,
  CASE WHEN 总任务金额>0 THEN ROUND(年度开单金额/总任务金额*100,2) ELSE 0 END AS 达成率,
  ROUND(总任务金额-年度开单金额,2) AS 剩余任务金额
FROM 分公司汇总
LIMIT 100
""".strip()

        if "商用事业部" in normalized_question and "整体达成率" in normalized_question:
            return """
WITH 字段提取 AS (
  SELECT
    CASE WHEN jsonb_typeof(fields->'总任务（金额）')='array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END AS 任务原始,
    CASE WHEN jsonb_typeof(fields->'年度开单金额')='array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END AS 开单原始,
    CASE WHEN jsonb_typeof(fields->'当前年')='array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END AS 当前年
  FROM angel_group_data
),
基础数据 AS (
  SELECT
    COALESCE(NULLIF(regexp_replace(任务原始,'[^0-9.-]','','g'),''),'0')::NUMERIC AS 任务金额,
    COALESCE(NULLIF(regexp_replace(开单原始,'[^0-9.-]','','g'),''),'0')::NUMERIC AS 开单金额
  FROM 字段提取
  WHERE COALESCE(NULLIF(当前年,''),'2026')='2026'
)
SELECT
  '商用事业部' AS 事业部,
  SUM(任务金额) AS 总任务金额,
  SUM(开单金额) AS 年度开单金额,
  CASE WHEN SUM(任务金额)>0 THEN ROUND(SUM(开单金额)/SUM(任务金额)*100,2) ELSE 0 END AS 达成率,
  ROUND(SUM(任务金额)-SUM(开单金额),2) AS 剩余任务金额
FROM 基础数据
LIMIT 100
""".strip()

        # 兜底：纯通用层级词（如"分公司"）按层级返回所有节点
        if generic_level_only and intent_target_level:
            return f"""
{syyb_base_sql}
SELECT *
FROM 汇总结果
WHERE 层级 = '{intent_target_level}'
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '事业部' THEN 0
    WHEN '分公司' THEN 1
    WHEN '业务部' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000
""".strip()

        return ""

    def _build_ecommerce_sql(self, normalized_question: str, context: Dict[str, Any]) -> str:
        q = str(normalized_question or "").strip()
        if not q:
            return ""

        dataset = self._safe_dict(context.get("dataset")) or {}
        query_intent = self._safe_dict(context.get("query_intent"))
        intent = str(query_intent.get("intent") or "").strip()
        intent_target_level = str(query_intent.get("target_level") or "").strip()

        profile = self._safe_dict(context.get("dimension_profile")) or get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
        resolved = resolve_member_mentions(q, profile or {})
        entities = resolved.get("entities") or []
        all_members = resolved.get("all_members") or []
        if not all_members:
            node_members = self._node_index_subject_names_from_question(q, context)
            if node_members:
                node_level_map = self._node_index_member_level_map(context)
                all_members = node_members
                grouped_entities: Dict[str, Dict[str, Any]] = {}
                for member in node_members:
                    dimension_name = node_level_map.get(member, "")
                    bucket = grouped_entities.setdefault(
                        dimension_name,
                        {"dimension_name": dimension_name, "members": [], "source": "node_index"},
                    )
                    bucket["members"].append(member)
                entities = list(grouped_entities.values())
        is_comparison = bool(
            intent == "comparison"
            or resolved.get("intent") == "compare"
            or re.search(r"对比|比较|分别|各自|哪个|谁更|和.+比|跟.+比|与.+比|\bvs\b", q, re.I)
        )

        # 修复：问题只是询问某个业务承接角色的负责人/承接人时，
        # resolve_member_mentions 可能因同时命中事业部和业务承接角色而误判为 comparison。
        # 此时应聚焦到业务承接角色节点，并向下钻取到负责人层级。
        if is_comparison and re.search(r"负责人|谁.*负责|承接人", q) and not re.search(r"对比|比较|分别|各自|哪个|谁更|和.+比|跟.+比|与.+比|\bvs\b", q, re.I):
            segment_entities = [
                e for e in entities
                if e.get("dimension_name") in {"业务承接角色", "细分业务", "业务线"}
                and (e.get("members") or [])
            ]
            if segment_entities:
                is_comparison = False
                intent = "drilldown"
                query_intent["intent"] = "drilldown"
                focus_dimension = "业务承接角色"
                focus_member = segment_entities[0]["members"][0]
                all_members = [focus_member]
                entities = segment_entities
                intent_target_level = "承接人"
                query_intent["target_level"] = "承接人"

        focus_member = ""
        focus_dimension = ""
        if not is_comparison and len(all_members) == 1 and entities:
            focus_member = all_members[0]
            focus_dimension = next(
                (e.get("dimension_name") for e in entities if focus_member in (e.get("members") or [])),
                "",
            )

        report_config = self._safe_dict(context.get("report_config")) or {}
        ranking_policy = self._safe_dict((report_config.get("intentPolicies") or {}).get("ranking"))

        def quote(value: str) -> str:
            return "'" + str(value or "").replace("'", "''") + "'"

        def clean_cmp_text(text: str) -> str:
            return re.sub(r"^(?:看下|看一下|查下|查一下|查询|看看|请看下|请查下)", "", str(text or "")).strip("，,、 和与及的对比")

        def is_likely_person_name(text: str) -> bool:
            return bool(re.fullmatch(r"[\u4e00-\u9fa5]{2,4}", str(text or "").strip()))

        def metric_key_from_text(text: str) -> str:
            if any(t in text for t in ["目标营收", "目标", "任务金额", "总任务"]):
                return "task"
            if any(t in text for t in ["开单金额", "开单", "实际", "营收", "毛利", "完成金额"]):
                return "actual"
            if any(t in text for t in ["达成率", "完成率", "进度"]):
                return "rate"
            if any(t in text for t in ["剩余任务", "缺口", "差额", "待完成"]):
                return "remain"
            return "actual" if intent == "ranking" else "task"

        def metric_key_from_query(key: str) -> str:
            key = str(key or "").strip()
            if key in {"rate", "达成率", "完成率"}:
                return "rate"
            if key in {"actual", "年度开单金额", "开单金额", "开单", "实际", "完成金额"}:
                return "actual"
            if key in {"task", "总任务金额", "年度目标营收", "总任务", "任务", "目标"}:
                return "task"
            if key in {"remain", "剩余任务金额", "剩余任务", "缺口", "差额", "待完成"}:
                return "remain"
            return metric_key_from_text(q)

        def source_metric_expr(key: str) -> str:
            return {
                "task": "年度目标营收",
                "actual": "年度开单金额",
                "rate": "总任务达成率",
                "remain": "年度目标营收 - 年度开单金额",
            }.get(key, "年度目标营收")

        def normalize_threshold_value(raw: Optional[float], metric_key: str) -> Optional[float]:
            if raw is None:
                return None
            if metric_key == "rate":
                return raw / 100.0
            if "亿" in q and raw < 10000:
                return raw * 100000000
            if "万" in q and raw < 10000:
                return raw * 10000
            return raw

        # 用户层级 -> 实际层级 + 投影模式
        # 电商视图物理层级只有 事业部/业务部/业务经理；
        # 业务经理行同时承载「业务承接角色」（细分业务）和「承接人」（负责人）两个逻辑层级，二者是同一物理行。
        USER_LEVELS = {
            "事业部": {"actual": "事业部", "mode": "segment"},
            "业务部": {"actual": "业务部", "mode": "segment"},
            "业务承接角色": {"actual": "业务经理", "mode": "segment"},
            "细分业务": {"actual": "业务经理", "mode": "segment"},
            "业务线": {"actual": "业务经理", "mode": "segment"},
            "承接人": {"actual": "业务经理", "mode": "manager"},
            "任务承接人": {"actual": "业务经理", "mode": "manager"},
            "负责人": {"actual": "业务经理", "mode": "manager"},
            "业务经理": {"actual": "业务经理", "mode": "manager"},
            # 兜底：消费者/商用常用的“业务代表”在电商口语里对应负责人层级
            "业务代表": {"actual": "业务经理", "mode": "manager"},
        }

        def infer_user_level() -> str:
            # 电商口语中“业务承接人/负责人”等词统一收敛到“承接人”，优先级最高，
            # 防止外部改写 refined_query 后把 target_level 带偏。
            if any(t in q for t in ["业务承接人", "承接人", "负责人", "任务承接人"]):
                return "承接人"
            # 兼容：intent 已收敛到业务代表/业务承接人时仍映射到承接人
            if intent_target_level in {"业务代表", "业务承接人"} and any(t in q for t in ["业务承接人", "承接人", "负责人", "任务承接人"]):
                return "承接人"
            # 下钻时如果 target_level 和聚焦维度相同（如“国内业务部下属明细”里的“业务部”），应下钻到子层级
            # 筛选/对比问题里如果已聚焦到具体节点且 target_level 就是该节点所在维度，也默认下钻到子层级，
            # 避免“国内业务部完成超过500万的”被理解为对所有业务部做过滤。
            if focus_dimension and intent_target_level == focus_dimension and intent in {"drilldown", "filter", "comparison"}:
                return {
                    "事业部": "业务部",
                    "业务部": "业务承接角色",
                    "业务承接角色": "承接人",
                    "承接人": "承接人",
                    # 兼容旧画像名
                    "细分业务": "承接人",
                    "业务经理": "承接人",
                }.get(focus_dimension, "业务承接角色")
            # 根节点问法（如“电商事业部的业绩”）默认展示直接下级业务部，
            # 避免只返回事业部汇总单行导致左侧卡片没有下级列表。
            if (
                intent_target_level == "事业部"
                and ("电商事业部" in q or "电商" in q)
                and intent not in {"ranking", "filter", "comparison"}
                and not any(t in q for t in ["整体", "总体", "总览", "汇总", "全部"])
            ):
                return "业务部"
            if intent_target_level:
                return intent_target_level
            if focus_dimension and focus_dimension != "事业部":
                # 修复：聚焦到业务承接角色/细分业务时，若问题只是询问负责人属性，
                # 保持业务承接角色层级即可，不要把节点本身当成负责人去过滤。
                return {
                    "业务部": "业务承接角色",
                    "业务承接角色": "业务承接角色",
                    "承接人": "承接人",
                    "细分业务": "业务承接角色",
                    "业务经理": "业务承接角色",
                }.get(focus_dimension, "业务承接角色")
            if "承接人" in q or "负责人" in q or "任务承接人" in q or "业务经理" in q:
                return "承接人"
            if "业务承接角色" in q or "细分业务" in q or "业务线" in q:
                return "业务承接角色"
            if "业务部" in q:
                return "业务部"
            if ("电商事业部" in q or "电商" in q) and not any(t in q for t in ["整体", "总体", "总览", "汇总", "全部"]):
                return "业务部"
            if "事业部" in q or "整体" in q or "全部" in q:
                return "事业部"
            return "业务承接角色"

        user_level = infer_user_level()
        level_cfg = USER_LEVELS.get(user_level, {"actual": "业务经理", "mode": "segment"})
        actual_level = level_cfg["actual"]
        projection_mode = level_cfg["mode"]

        # 投影列：
        # - manager 模式把「承接人/负责人」作为节点，业务部/事业部作为上级；
        # - segment 模式把「业务承接角色」作为节点，业务部/事业部作为上级；
        # - 默认返回时，业务经理行统一展示为「业务承接角色」，避免把业务承接角色误标成业务经理。
        use_logical_level = intent in {"ranking", "filter", "comparison", "drilldown"} and user_level
        if projection_mode == "manager":
            select_cols = """
                '电商业务' AS 条线,
                '承接人' AS 层级,
                COALESCE(NULLIF(TRIM(负责人), ''), '未知承接人') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额
            """.strip()
        elif use_logical_level and user_level in {"业务承接角色", "细分业务", "业务线"}:
            select_cols = """
                '电商业务' AS 条线,
                '业务承接角色' AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额
            """.strip()
        else:
            select_cols = """
                '电商业务' AS 条线,
                CASE
                    WHEN 层级级别 = '业务经理' AND NULLIF(TRIM(细分业务), '') IS NOT NULL THEN '业务承接角色'
                    ELSE 层级级别
                END AS 层级,
                COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') AS 节点名称,
                CASE
                    WHEN 层级级别 = '事业部' THEN NULL
                    WHEN 层级级别 = '业务部' THEN '电商事业部'
                    ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                END AS 上级名称,
                年度目标营收 AS 总任务金额,
                年度开单金额 AS 年度开单金额,
                NULLIF(TRIM(负责人), '') AS 业务承接人,
                ROUND(总任务达成率 * 100, 2) AS 达成率,
                ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额
            """.strip()

        where_parts = ["当前年 = '2026'"]
        order_by = ""
        limit_clause = "LIMIT 50"

        # 对比：取 resolved 实体或 query_intent 的 left/right
        if intent == "comparison" or is_comparison:
            root_nodes = set(profile.get("root_nodes") or [])
            compare_members = [m for m in all_members if m not in root_nodes] or list(all_members)
            compare_dimension = ""
            if not compare_members and intent == "comparison":
                left_text = clean_cmp_text(query_intent.get("comparison_left") or "")
                right_text = clean_cmp_text(query_intent.get("comparison_right") or "")
                left_res = resolve_member_mentions(left_text, profile or {}) if left_text else {}
                right_res = resolve_member_mentions(right_text, profile or {}) if right_text else {}
                compare_members = list(dict.fromkeys(
                    (left_res.get("all_members") or []) + (right_res.get("all_members") or [])
                ))
                for ent in (left_res.get("entities") or []) + (right_res.get("entities") or []):
                    if ent.get("dimension_name"):
                        compare_dimension = ent["dimension_name"]
                        break
                # 维度画像没命中具体人名时，按“两到四个汉字”兜底为承接人对比
                if not compare_members and (is_likely_person_name(left_text) or is_likely_person_name(right_text)):
                    compare_members = [t for t in [left_text, right_text] if t]
                    compare_dimension = "承接人"
            if not compare_dimension and entities:
                for e in entities:
                    if any(m in (e.get("members") or []) for m in compare_members):
                        compare_dimension = e.get("dimension_name")
                        break

            if compare_members:
                quoted_members = ",".join(quote(m) for m in compare_members)
                if compare_dimension == "业务部":
                    where_parts.append(f"业务部 IN ({quoted_members})")
                    where_parts.append(f"层级级别 = '业务部'")
                elif compare_dimension in {"承接人", "任务承接人", "负责人", "业务经理"} or projection_mode == "manager":
                    where_parts.append(f"负责人 IN ({quoted_members})")
                    where_parts.append(f"层级级别 = '业务经理'")
                elif compare_dimension in {"业务承接角色", "细分业务", "业务线"} or user_level in {"业务承接角色", "细分业务", "业务线"}:
                    where_parts.append(f"细分业务 IN ({quoted_members})")
                    where_parts.append(f"层级级别 = '业务经理'")
                else:
                    # 兜底：在节点名称里匹配
                    where_parts.append(
                        f"COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), '电商事业部') IN ({quoted_members})"
                    )
                    if actual_level:
                        where_parts.append(f"层级级别 = '{actual_level}'")
                # 人名对比需要把负责人作为节点
                if compare_dimension in {"承接人", "任务承接人", "负责人", "业务经理"}:
                    select_cols = """
                        '电商业务' AS 条线,
                        '承接人' AS 层级,
                        COALESCE(NULLIF(TRIM(负责人), ''), '未知承接人') AS 节点名称,
                        CASE
                            WHEN 层级级别 = '事业部' THEN NULL
                            WHEN 层级级别 = '业务部' THEN '电商事业部'
                            ELSE COALESCE(NULLIF(TRIM(业务部), ''), '电商事业部')
                        END AS 上级名称,
                        年度目标营收 AS 总任务金额,
                        年度开单金额 AS 年度开单金额,
                        NULLIF(TRIM(负责人), '') AS 业务承接人,
                        ROUND(总任务达成率 * 100, 2) AS 达成率,
                        ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额
                    """.strip()
                order_by = "年度开单金额 DESC"
                limit_clause = "LIMIT 50"

        # 排名
        elif intent == "ranking":
            if actual_level:
                where_parts.append(f"层级级别 = '{actual_level}'")
            # 如果聚焦到某个业务部，且不是业务部自身排名，则限定子树
            if focus_member and focus_dimension == "业务部" and user_level != "业务部":
                where_parts.append(f"组织路径 LIKE {quote('电商事业部;' + focus_member + '%')}")

            sort_key = metric_key_from_query(query_intent.get("sort_metric_key"))
            metric_col = source_metric_expr(sort_key)
            direction = str(query_intent.get("direction") or "desc").upper()
            if any(t in q for t in ["最低", "最差", "末位", "最小", "倒数", "垫底"]):
                direction = "ASC"
            order_by = f"{metric_col} {direction}"

            top_n = self._safe_int(query_intent.get("top_n"), 0)
            max_top_n = self._safe_int(ranking_policy.get("maxTopN"), 20)
            if top_n > 0:
                top_n = max(1, min(max_top_n, top_n))
                limit_clause = f"LIMIT {top_n}"
            else:
                # 用户未指定数量时返回全部（电商数据量小，200 行足够覆盖）
                limit_clause = "LIMIT 200"

        # 筛选
        elif intent == "filter":
            if actual_level:
                where_parts.append(f"层级级别 = '{actual_level}'")
            if focus_member and focus_dimension == "业务部" and user_level != "业务部":
                where_parts.append(f"组织路径 LIKE {quote('电商事业部;' + focus_member + '%')}")

            filter_metric_key = metric_key_from_query(query_intent.get("filter_metric_key"))
            metric_col = source_metric_expr(filter_metric_key)
            op = str(query_intent.get("filter_operator") or "").strip()
            val = query_intent.get("filter_value")
            if op and val is not None and filter_metric_key != "level_only":
                if op == "between":
                    val2 = query_intent.get("filter_value2")
                    norm_val1 = normalize_threshold_value(float(val), filter_metric_key)
                    norm_val2 = normalize_threshold_value(float(val2), filter_metric_key) if val2 is not None else norm_val1
                    where_parts.append(f"({metric_col}) BETWEEN {norm_val1} AND {norm_val2}")
                    order_by = f"{metric_col} DESC"
                else:
                    norm_val = normalize_threshold_value(float(val), filter_metric_key)
                    where_parts.append(f"({metric_col}) {op} {norm_val}")
                    direction = "asc" if op in {"<", "<="} else "desc"
                    order_by = f"{metric_col} {direction}"
            else:
                order_by = f"{metric_col} DESC" if filter_metric_key != "level_only" else "年度开单金额 DESC"
            limit_clause = "LIMIT 200"

        # 下钻 / 明细 / 总览（聚焦单个节点）
        elif focus_member:
            if focus_dimension == "事业部":
                where_parts.append(f"组织路径 LIKE {quote('电商事业部%')}")
                if user_level == "业务部":
                    where_parts.append("层级级别 = '业务部'")
            elif focus_dimension == "业务部":
                where_parts.append(f"(组织路径 LIKE {quote('电商事业部;' + focus_member + '%')} OR (业务部 = {quote(focus_member)} AND 层级级别 = '业务部'))")
            elif focus_dimension in {"业务承接角色", "细分业务", "业务线"}:
                where_parts.append(f"细分业务 = {quote(focus_member)}")
            elif focus_dimension in {"承接人", "任务承接人", "负责人", "业务经理"}:
                where_parts.append(f"负责人 = {quote(focus_member)}")
            else:
                where_parts.append(f"组织路径 LIKE {quote('电商事业部%' + focus_member + '%')}")

            if intent == "drilldown" and actual_level:
                where_parts.append(f"层级级别 = '{actual_level}'")
            order_by = "层级级别, 年度开单金额 DESC"
            limit_clause = "LIMIT 200"

        # 兜底：无明确意图时按关键词识别层级
        else:
            if actual_level:
                where_parts.append(f"层级级别 = '{actual_level}'")
            if any(t in q for t in ["排名", "Top", "top", "前", "排行榜", "最高", "最低", "最好", "最差", "首位", "末位", "头名", "最大", "最小"]):
                metric_key = metric_key_from_text(q)
                metric_col = source_metric_expr(metric_key)
                direction = "ASC" if any(t in q for t in ["最低", "最差", "末位", "最小"]) else "DESC"
                order_by = f"{metric_col} {direction}"
            else:
                order_by = "年度开单金额 DESC"

        where_clause = " AND ".join(where_parts)
        sql = f"SELECT {select_cols} FROM v_feishu_tbldianshang WHERE {where_clause} ORDER BY {order_by} {limit_clause};"
        return sql


    def _build_consumer_business_sql(self, normalized_question: str, context: Dict[str, Any]) -> str:
        dictionary_keys = {
            str(item.get("jsonb_key") or "").strip()
            for item in context.get("data_dictionary", []) or []
            if str(item.get("jsonb_key") or "").strip()
        }
        def consumer_key(*candidates: str) -> str:
            for candidate in candidates:
                if candidate in dictionary_keys:
                    return candidate
            return candidates[0]

        city_field_key = consumer_key("城市分公司")
        city_field_expr = f"COALESCE(NULLIF(TRIM(fields->>'{city_field_key}'), ''), '')"
        query_intent = self._safe_dict(context.get("query_intent"))
        generic_level_terms = {"分公司", "代表处", "业务部", "业务代表", "业务员", "城市分公司", "城市公司", "事业部"}
        intent_is_ranking = query_intent.get("intent") == "ranking"
        intent_target_level = str(query_intent.get("target_level") or "")
        if intent_target_level in {"城市公司", "城市分公司"}:
            intent_target_level = "城市分公司"
            query_intent["target_level"] = "城市分公司"
        asks_branch_extremes = (
            "分公司" in normalized_question
            and any(token in normalized_question for token in ["最高", "最好", "最低", "最差", "头尾", "首尾"])
            and any(token in normalized_question for token in ["对比", "比较", "差距", "差异", "二者", "两家", "任务体量", "实际开单", "缺口"])
        )
        def normalize_consumer_entity_name(value: str) -> str:
            text = str(value or "").strip()
            if not text:
                return ""
            text = re.sub(r"^(看下|看一下|查下|查一下|查询|看看|请看下|请查下)", "", text)
            text = re.sub(r"(业绩如何了|业绩如何|业绩情况|完成的怎么样|完成情况|完成咋样|怎么样|如何了)$", "", text)
            text = text.strip("，,、 和与及的")
            if text in {"城市公司", "城市分公司", "分公司", "事业部"}:
                return ""
            if text.endswith("城市分公司"):
                return text[:-5] + "城市公司"
            return text

        entity_names = [
            normalized for normalized in
            (normalize_consumer_entity_name(item) for item in self._resolved_entity_names(context))
            if normalized
        ]
        if not entity_names and not asks_branch_extremes:
            for match in re.findall(r"[\u4e00-\u9fa5A-Za-z0-9（）()]+?(?:城市分公司|城市公司|分公司|事业部)", normalized_question):
                cleaned = match.strip("，,、 和与及的业绩情况表现整体")
                normalized = normalize_consumer_entity_name(cleaned)
                if re.search(r"\d|万", normalized):
                    continue
                if normalized and normalized not in {"哪些分公司", "各分公司", "所有分公司", "哪些城市公司", "各城市公司", "所有城市公司"}:
                    entity_names.append(normalized)
        entity_names = list(dict.fromkeys(entity_names))

        # 如果实体名只是通用层级词（如"分公司"），按该层级过滤而不是按节点名过滤
        resolved_subject_name = str(query_intent.get("subject_name") or "").strip()
        generic_level_only = (
            bool(entity_names and all(name in generic_level_terms for name in entity_names))
            or resolved_subject_name in generic_level_terms
        )
        if generic_level_only:
            entity_names = []

        scope_filter = ""
        if entity_names:
            quoted_entities = ",".join("'" + item.replace("'", "''") + "'" for item in entity_names)
            include_root = any(name == "消费者事业部" for name in entity_names)
            root_clause = "节点名称 = '消费者事业部' OR " if include_root else ""
            scope_filter = f"""
WHERE {root_clause}节点名称 IN ({quoted_entities})
   OR 上级名称 IN ({quoted_entities})
   OR 上级名称 IN (
       SELECT 节点名称
       FROM 汇总结果
       WHERE 节点名称 IN ({quoted_entities}) OR 上级名称 IN ({quoted_entities})
   )
"""
        elif generic_level_only and intent_target_level:
            scope_filter = f"WHERE 层级 = '{intent_target_level}'"

        # 兜底：即使识别规则没命中，只要 target_level 明确，默认 SQL 也只返回该层级
        if not scope_filter and intent_target_level:
            scope_filter = f"WHERE 层级 = '{intent_target_level}'"

        intent_is_comparison = query_intent.get("intent") == "comparison"
        intent_is_aggregate = query_intent.get("intent") == "aggregate"

        channel_metric = ""
        if not intent_is_comparison and not intent_is_aggregate:
            for candidate in ["燃气定制", "新零售", "线下", "地产"]:
                if candidate in normalized_question:
                    channel_metric = candidate
                    break
        if channel_metric:
            task_metric_expr = f"COALESCE({channel_metric}任务_万元, 0) * 10000"
            actual_metric_expr = f"COALESCE({channel_metric}实际_万元, 0) * 10000"
            metric_scope_expr = f"'{channel_metric}'"
            # 业务线口径的展示标签同步到 query_intent，让前端/报告契约显示正确的指标名
            channel_label = f"{channel_metric}业务开单金额"
            channel_sql_column = f"{channel_metric}实际_万元"
            query_intent["sort_metric_column"] = channel_label
            query_intent["sort_metric_sql_column"] = channel_sql_column
            query_intent["_channel_metric_label"] = channel_label
            report_config_qi = context.get("report_config", {}).get("queryIntent") or {}
            report_config_qi["sort_metric_column"] = channel_label
            report_config_qi["sort_metric_sql_column"] = channel_sql_column
            report_config_qi["_channel_metric_label"] = channel_label
        else:
            task_metric_expr = "总任务金额"
            actual_metric_expr = "年度开单金额"
            metric_scope_expr = "'全部'"

        base_sql = """
WITH 字段提取 AS (
    SELECT
        id,
        COALESCE(NULLIF(TRIM(fields->>'事业部'), ''), '消费者事业部') AS 事业部,
        COALESCE(NULLIF(TRIM(fields->>'分公司'), ''), '') AS 分公司,
        {city_field_expr} AS 城市分公司,
        COALESCE(NULLIF(TRIM(fields->>'层级级别'), ''), '') AS 源层级,
        COALESCE(NULLIF(TRIM(fields->>'当前年'), ''), '2026') AS 当前年,
        NULLIF(regexp_replace(COALESCE(fields->>'总任务（金额）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 总任务原值,
        NULLIF(regexp_replace(COALESCE(fields->>'年度开单金额', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 年度开单原值,
        NULLIF(regexp_replace(COALESCE(fields->>'线下（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产任务万,
        NULLIF(regexp_replace(COALESCE(fields->>'线下-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 线下实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'新零售-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 新零售实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'燃气定制-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 燃气定制实际万,
        NULLIF(regexp_replace(COALESCE(fields->>'地产-年度开单金额（万）', ''), '[^0-9.-]', '', 'g'), '')::NUMERIC AS 地产实际万
    FROM public.feishu_tbl_xioafeizhe
    WHERE fields IS NOT NULL
),
标准行 AS (
    SELECT
        id,
        CASE
            WHEN 城市分公司 <> '' THEN '城市分公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市分公司 <> '' THEN 城市分公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市分公司 <> '' THEN 分公司
            WHEN 分公司 <> '' THEN 事业部
            ELSE NULL
        END AS 上级名称,
        COALESCE(总任务原值, (COALESCE(线下任务万, 0) + COALESCE(新零售任务万, 0) + COALESCE(燃气定制任务万, 0) + COALESCE(地产任务万, 0)) * 10000, 0) AS 总任务金额,
        COALESCE(年度开单原值, (COALESCE(线下实际万, 0) + COALESCE(新零售实际万, 0) + COALESCE(燃气定制实际万, 0) + COALESCE(地产实际万, 0)) * 10000, 0) AS 年度开单金额,
        COALESCE(线下任务万, 0) AS 线下任务_万元,
        COALESCE(新零售任务万, 0) AS 新零售任务_万元,
        COALESCE(燃气定制任务万, 0) AS 燃气定制任务_万元,
        COALESCE(地产任务万, 0) AS 地产任务_万元,
        COALESCE(线下实际万, 0) AS 线下实际_万元,
        COALESCE(新零售实际万, 0) AS 新零售实际_万元,
        COALESCE(燃气定制实际万, 0) AS 燃气定制实际_万元,
        COALESCE(地产实际万, 0) AS 地产实际_万元
    FROM 字段提取
    WHERE 当前年 = '2026'
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市分公司 <> '')
),
汇总结果 AS (
    SELECT
        '消费者经营链路' AS 条线,
        {metric_scope_expr} AS 分析口径,
        层级,
        节点名称,
        上级名称,
        ROUND(({task_metric_expr}), 2) AS 总任务金额,
        ROUND(({actual_metric_expr}), 2) AS 年度开单金额,
        CASE WHEN ({task_metric_expr}) > 0 THEN ROUND(({actual_metric_expr}) / ({task_metric_expr}) * 100, 2) ELSE 0 END AS 达成率,
        ROUND(GREATEST(({task_metric_expr}) - ({actual_metric_expr}), 0), 2) AS 剩余任务金额,
        ROUND(线下任务_万元, 2) AS 线下任务_万元,
        ROUND(新零售任务_万元, 2) AS 新零售任务_万元,
        ROUND(燃气定制任务_万元, 2) AS 燃气定制任务_万元,
        ROUND(地产任务_万元, 2) AS 地产任务_万元,
        ROUND(线下实际_万元, 2) AS 线下实际_万元,
        ROUND(新零售实际_万元, 2) AS 新零售实际_万元,
        ROUND(燃气定制实际_万元, 2) AS 燃气定制实际_万元,
        ROUND(地产实际_万元, 2) AS 地产实际_万元
    FROM 标准行
    WHERE 节点名称 <> ''
      AND (({task_metric_expr}) > 0 OR ({actual_metric_expr}) > 0)
)
""".format(
            metric_scope_expr=metric_scope_expr,
            task_metric_expr=task_metric_expr,
            actual_metric_expr=actual_metric_expr,
            city_field_expr=city_field_expr,
        ).strip()

        city_level_requested = (
            intent_target_level in {"城市分公司", "城市公司"}
            or "城市分公司" in normalized_question
            or "城市公司" in normalized_question
        )
        asks_best_branch = (
            "分公司" in normalized_question
            and not city_level_requested
            and any(token in normalized_question for token in ["最好", "最高", "最佳", "完成好", "完成最好", "哪个"])
            and not any(token in normalized_question for token in ["最低", "最差", "不好", "风险", "落后"])
        )
        asks_branch_ranking = (
            not city_level_requested
            and (
                (intent_is_ranking and intent_target_level == "分公司")
                or (
                    "分公司" in normalized_question
                    and any(token in normalized_question for token in ["排名", "排行", "Top", "top", "前", "后", "最高", "最好", "最低", "最差"])
                )
            )
        )
        asks_city_ranking = (
            city_level_requested
            and (
                intent_is_ranking
                or any(token in normalized_question for token in ["排名", "排行", "Top", "top", "前", "后", "最高", "最好", "最佳", "完成好", "完成最好", "哪个", "最低", "最差"])
            )
        )
        intent_is_filter = query_intent.get("intent") == "filter"
        filter_metric_column = str(query_intent.get("filter_metric_column") or "").strip()
        filter_operator = str(query_intent.get("filter_operator") or "").strip()
        filter_value = query_intent.get("filter_value")
        allowed_filter_columns = {"总任务金额", "年度开单金额", "达成率", "剩余任务金额"}
        filter_level_map = {
            "城市分公司": "城市分公司",
            "分公司": "分公司",
            "消费者事业部总体": "消费者事业部总体",
        }
        filter_level = filter_level_map.get(intent_target_level, "城市分公司" if city_level_requested else "")

        def normalize_consumer_threshold_value(raw: float, col: str) -> float:
            # 与 syyb/ecommerce 保持一致：intent 层保留原始值，SQL 阶段根据问题中的单位换算
            if col == "达成率":
                return raw
            q = normalized_question
            if "亿" in q and raw < 10000:
                return raw * 100000000
            if "万" in q and raw < 10000:
                return raw * 10000
            return raw

        # 消费者指标同义词（含 _万 后缀与组合口径），提前供过滤/聚合/对比复用
        consumer_metric_map = {
            "总实际_万": "年度开单金额",
            "总实际": "年度开单金额",
            "线下实际_万": "线下实际_万元",
            "线下实际": "线下实际_万元",
            "新零售实际_万": "新零售实际_万元",
            "新零售实际": "新零售实际_万元",
            "燃气定制实际_万": "燃气定制实际_万元",
            "燃气定制实际": "燃气定制实际_万元",
            "地产实际_万": "地产实际_万元",
            "地产实际": "地产实际_万元",
            "燃气定制-地产实际_万": "(燃气定制实际_万元 + 地产实际_万元)",
            "燃气定制地产实际_万": "(燃气定制实际_万元 + 地产实际_万元)",
            "燃气定制-地产实际": "(燃气定制实际_万元 + 地产实际_万元)",
            "燃气定制地产实际": "(燃气定制实际_万元 + 地产实际_万元)",
            "总任务_万": "总任务金额",
            "总任务": "总任务金额",
            "线下任务_万": "线下任务_万元",
            "线下任务": "线下任务_万元",
            "新零售任务_万": "新零售任务_万元",
            "新零售任务": "新零售任务_万元",
            "燃气定制任务_万": "燃气定制任务_万元",
            "燃气定制任务": "燃气定制任务_万元",
            "地产任务_万": "地产任务_万元",
            "地产任务": "地产任务_万元",
            "燃气定制-地产任务_万": "(燃气定制任务_万元 + 地产任务_万元)",
            "燃气定制地产任务_万": "(燃气定制任务_万元 + 地产任务_万元)",
            "燃气定制-地产任务": "(燃气定制任务_万元 + 地产任务_万元)",
            "燃气定制地产任务": "(燃气定制任务_万元 + 地产任务_万元)",
            "达成率": "达成率",
        }

        def map_consumer_metric(text: str) -> str:
            for key, col in sorted(consumer_metric_map.items(), key=lambda x: -len(x[0])):
                if key in text:
                    return col
            return ""

        if intent_is_filter:
            mapped_col = map_consumer_metric(normalized_question)
            if mapped_col:
                filter_metric_column = mapped_col
                allowed_filter_columns.add(mapped_col)

        asks_threshold_filter = (
            intent_is_filter
            and filter_metric_column in allowed_filter_columns
            and filter_operator in {"<", "<=", ">", ">=", "="}
            and filter_value is not None
            and bool(filter_level)
        )
        rank_spec = self._rank_request_spec(normalized_question, default_limit=0, max_limit=20)
        rank_sides = str(query_intent.get("rank_sides") or rank_spec.get("sides") or "")
        consumer_top_rank_limit = int(query_intent.get("top_limit") if query_intent.get("top_limit") is not None else (rank_spec.get("top_limit") or 0))
        consumer_bottom_rank_limit = int(query_intent.get("bottom_limit") if query_intent.get("bottom_limit") is not None else (rank_spec.get("bottom_limit") or 0))

        def consumer_rank_limit() -> int:
            rank_limit = self._safe_int(query_intent.get("top_n"), 0) if intent_is_ranking else 0
            if rank_limit <= 0:
                rank_limit = int(rank_spec.get("limit") or 0)
            explicit_rank_count_requested = bool(
                self._rank_limit_match(normalized_question)
                or any(token in normalized_question for token in ["Top", "top", "前", "后", "倒数"])
            )
            if rank_limit <= 0 and explicit_rank_count_requested:
                # 优先读取数据集报告模板中配置的默认 TopN
                ds_ranking_policy = self._safe_dict(
                    (context.get("report_config") or {}).get("intentPolicies")
                ).get("ranking")
                rank_limit = self._safe_int(ds_ranking_policy.get("defaultTopN"), 0)
            if rank_limit <= 0:
                # 用户仅说“排名/排行”但没给数量时，返回全部；只有明确带 Top/前/后/倒数 才默认取 Top3
                if explicit_rank_count_requested:
                    rank_limit = 3
                else:
                    rank_limit = 0
            return max(0, min(20, rank_limit))

        def consumer_order_direction() -> str:
            order_direction = str(query_intent.get("direction") or "").upper() if intent_is_ranking else ""
            if order_direction not in {"ASC", "DESC"}:
                order_direction = "ASC" if any(token in normalized_question for token in ["最低", "最差", "后", "倒数", "落后"]) else "DESC"
            return "DESC" if rank_sides == "both" else order_direction

        def consumer_sort_column() -> str:
            configured_sql_column = str(query_intent.get("sort_metric_sql_column") or "").strip()
            configured_sort_column = str(query_intent.get("sort_metric_column") or "").strip()
            allowed_sort_columns = {
                "总任务金额",
                "年度开单金额",
                "达成率",
                "剩余任务金额",
                "线下任务_万元",
                "新零售任务_万元",
                "燃气定制任务_万元",
                "地产任务_万元",
                "线下实际_万元",
                "新零售实际_万元",
                "燃气定制实际_万元",
                "地产实际_万元",
            }
            if configured_sql_column in allowed_sort_columns:
                return configured_sql_column
            if configured_sort_column in allowed_sort_columns:
                return configured_sort_column
            return "达成率"

        if asks_threshold_filter:
            try:
                scaled_filter_value = normalize_consumer_threshold_value(float(filter_value), filter_metric_column)
                filter_value_sql = f"{scaled_filter_value:g}"
            except (TypeError, ValueError):
                filter_value_sql = ""
            if filter_value_sql:
                where_parts = [f"层级 = '{filter_level}'", f"{filter_metric_column} {filter_operator} {filter_value_sql}"]
                spoken_filter_triggers = {"spoken_zero_actual", "spoken_lagging"}
                matched_triggers = set(query_intent.get("matched_triggers") or [])
                if not (matched_triggers & spoken_filter_triggers):
                    level_values = {"分公司", "代表处", "业务部", "事业部", "城市公司", "城市分公司", "业务代表"}
                    all_entities = [
                        n for n in self._resolved_entity_names(context) if n
                        and n not in level_values
                        and len(n) >= 4
                        and any(n.endswith(suffix) for suffix in ["分公司", "代表处", "业务部", "事业部", "城市公司", "城市分公司"])
                        and not re.search(r"\d|万", n)
                        and not any(t in n for t in ["年度", "开单", "任务", "达成", "剩余", "销售", "实际", "大于", "小于", "高于", "低于", "超过", "不少于", "不低于", "达到"])
                    ]
                    entity_names = [e for e in all_entities if e in normalized_question]
                    if entity_names:
                        quoted_entities = ",".join("'" + item.replace("'", "''") + "'" for item in entity_names)
                        target_level = filter_level or ""
                        if target_level == "分公司":
                            has_business_unit = any(e.endswith("事业部") for e in entity_names)
                            has_branch = any(e.endswith("分公司") and not e.endswith("城市分公司") for e in entity_names)
                            if has_business_unit:
                                where_parts.append(f"上级名称 IN ({quoted_entities})")
                            elif has_branch:
                                where_parts.append(f"节点名称 IN ({quoted_entities})")
                        elif target_level == "城市分公司" or target_level == "城市公司":
                            where_parts.append(f"上级名称 IN ({quoted_entities}) OR 节点名称 IN ({quoted_entities})")
                        else:
                            where_parts.append(f"节点名称 IN ({quoted_entities}) OR 上级名称 IN ({quoted_entities})")
                order_direction = "ASC" if filter_operator in {"<", "<="} else "DESC"
                tie_breaker = "剩余任务金额 DESC, 上级名称, 节点名称" if filter_metric_column == "达成率" else "达成率 ASC, 上级名称, 节点名称"
                where_clause = " AND ".join(where_parts)
                generated_sql2 = f"""
{base_sql}
SELECT *
FROM 汇总结果
WHERE {where_clause}
ORDER BY {filter_metric_column} {order_direction}, {tie_breaker}
LIMIT 200
""".strip()
                print("[DEBUG] asks_threshold_filter SQL:\n", generated_sql2, flush=True)
                return generated_sql2

        # consumer_metric_map / map_consumer_metric 已上提到过滤分支前

        if intent_is_comparison:
            left_text = str(query_intent.get("comparison_left") or "").strip()
            right_text = str(query_intent.get("comparison_right") or "").strip()
            left_col = map_consumer_metric(left_text)
            right_col = map_consumer_metric(right_text)
            op = str(query_intent.get("comparison_operator") or ">")
            if left_col and right_col:
                where_parts = []
                if intent_target_level:
                    where_parts.append(f"层级 = '{intent_target_level}'")
                elif city_level_requested:
                    where_parts.append("层级 = '城市分公司'")
                elif "分公司" in normalized_question and "城市分公司" not in normalized_question:
                    where_parts.append("层级 = '分公司'")
                where_parts.append(f"{left_col} {op} {right_col}")
                where_clause = " AND ".join(where_parts)
                return f"""
{base_sql}
SELECT *
FROM 汇总结果
WHERE {where_clause}
ORDER BY {left_col} DESC, 节点名称
LIMIT 200
""".strip()

        if intent_is_aggregate:
            group_level = intent_target_level
            if not group_level:
                if "分公司" in normalized_question and "城市分公司" not in normalized_question:
                    group_level = "分公司"
                elif "城市分公司" in normalized_question:
                    group_level = "城市分公司"
                else:
                    group_level = "分公司"
            group_by_field = "节点名称"
            where_level = f"层级 = '{group_level}'"
            if "下属" in normalized_question and "城市分公司" in normalized_question:
                group_by_field = "上级名称"
                where_level = "层级 = '城市分公司'"

            # 统计各分公司拥有的城市分公司数量
            if ("各分公司" in normalized_question and "城市分公司数量" in normalized_question) or "各分公司拥有的城市分公司数量" in normalized_question:
                group_by_field = "上级名称"
                where_level = "层级 = '城市分公司'"
                agg_select = "COUNT(*) AS 城市分公司数量"
                order_by = "城市分公司数量 DESC NULLS LAST"
            # 单实体 + "各项指标" 返回该节点全量指标
            elif entity_names and "各项指标" in normalized_question:
                quoted_entities = ",".join("'" + item.replace("'", "''") + "'" for item in entity_names)
                where_level += f" AND 节点名称 IN ({quoted_entities})"
                agg_select = "SUM(总任务金额) AS 总任务金额, SUM(年度开单金额) AS 年度开单金额, AVG(达成率) AS 平均达成率, SUM(剩余任务金额) AS 剩余任务金额, SUM(线下任务_万元) AS 线下任务_万元, SUM(新零售任务_万元) AS 新零售任务_万元, SUM(燃气定制任务_万元) AS 燃气定制任务_万元, SUM(地产任务_万元) AS 地产任务_万元, SUM(线下实际_万元) AS 线下实际_万元, SUM(新零售实际_万元) AS 新零售实际_万元, SUM(燃气定制实际_万元) AS 燃气定制实际_万元, SUM(地产实际_万元) AS 地产实际_万元"
                order_by = "分组名称"
            elif "平均" in normalized_question:
                custom_metric = map_consumer_metric(normalized_question)
                if custom_metric and custom_metric not in {"达成率", "总任务金额", "年度开单金额"}:
                    agg_select = f"AVG({custom_metric}) AS 平均值, SUM({custom_metric}) AS 合计值"
                elif "达成率" in normalized_question:
                    agg_select = "AVG(达成率) AS 平均达成率, COUNT(*) AS 节点数量"
                elif "任务" in normalized_question:
                    agg_select = "AVG(总任务金额) AS 平均任务金额, SUM(总任务金额) AS 总任务金额"
                elif "实际" in normalized_question:
                    agg_select = "AVG(年度开单金额) AS 平均实际金额, SUM(年度开单金额) AS 总实际金额"
                else:
                    agg_select = "AVG(达成率) AS 平均达成率, SUM(年度开单金额) AS 总实际金额"
            elif "数量" in normalized_question or "个数" in normalized_question or "多少个" in normalized_question:
                agg_select = "COUNT(*) AS 节点数量"
            else:
                if "任务" in normalized_question:
                    agg_select = "SUM(总任务金额) AS 总任务金额, AVG(达成率) AS 平均达成率"
                else:
                    agg_select = "SUM(年度开单金额) AS 总实际金额, AVG(达成率) AS 平均达成率"

            if "总实际金额" in agg_select:
                order_by = "总实际金额 DESC NULLS LAST"
            elif "总任务金额" in agg_select:
                order_by = "总任务金额 DESC NULLS LAST"
            elif "节点数量" in agg_select:
                order_by = "节点数量 DESC NULLS LAST"
            else:
                order_by = "分组名称"

            return f"""
{base_sql}
SELECT
    {group_by_field} AS 分组名称,
    {agg_select}
FROM 汇总结果
WHERE {where_level}
GROUP BY {group_by_field}
ORDER BY {order_by}
LIMIT 200
""".strip()

        if asks_city_ranking:
            rank_limit = consumer_rank_limit()
            order_direction = consumer_order_direction()
            sort_column = consumer_sort_column()
            return self._build_ranked_select_sql(
                source_cte=base_sql,
                source_name="汇总结果",
                output_cte="城市分公司排序",
                where_clause="层级 = '城市分公司'",
                metric_column=sort_column,
                direction=order_direction,
                rank_limit=rank_limit,
                rank_sides=rank_sides,
                top_rank_limit=consumer_top_rank_limit,
                bottom_rank_limit=consumer_bottom_rank_limit,
                tie_breaker="年度开单金额 DESC, 剩余任务金额 DESC, 节点名称",
            )
        if asks_branch_ranking and not asks_branch_extremes and not (channel_metric and asks_best_branch):
            rank_limit = consumer_rank_limit()
            order_direction = consumer_order_direction()
            sort_column = consumer_sort_column()
            # 关键修复：如果用户明确指定了 target_level，只返回该层级，不要带上下级
            explicit_target = intent_target_level in ["分公司", "城市分公司"]
            if explicit_target:
                return self._build_ranked_select_sql(
                    source_cte=base_sql,
                    source_name="汇总结果",
                    output_cte="分公司排序",
                    where_clause=f"层级 = '{intent_target_level}'",
                    metric_column=sort_column,
                    direction=order_direction,
                    rank_limit=rank_limit,
                    rank_sides=rank_sides,
                    top_rank_limit=consumer_top_rank_limit,
                    bottom_rank_limit=consumer_bottom_rank_limit,
                    tie_breaker="年度开单金额 DESC, 剩余任务金额 DESC, 节点名称",
                )
            # 原有逻辑：用户没有明确层级时，才返回「分公司 + 城市分公司」上下级数据
            if rank_sides == "both":
                return self._build_ranked_select_sql(
                    source_cte=base_sql,
                    source_name="汇总结果",
                    output_cte="分公司排序",
                    where_clause="层级 = '分公司'",
                    metric_column=sort_column,
                    direction=order_direction,
                    rank_limit=rank_limit,
                    rank_sides=rank_sides,
                    top_rank_limit=consumer_top_rank_limit,
                    bottom_rank_limit=consumer_bottom_rank_limit,
                    tie_breaker="年度开单金额 DESC, 剩余任务金额 DESC, 节点名称",
                )
            return f"""
{base_sql},
排名分公司 AS (
    SELECT
        节点名称,
        ROW_NUMBER() OVER (ORDER BY {sort_column} {order_direction}, 年度开单金额 DESC, 剩余任务金额 DESC, 节点名称) AS 排名序号
    FROM 汇总结果
    WHERE 层级 = '分公司'
    LIMIT {rank_limit}
)
SELECT r.*
FROM 汇总结果 r
JOIN 排名分公司 b
  ON (r.层级 = '分公司' AND r.节点名称 = b.节点名称)
  OR (r.层级 = '城市分公司' AND r.上级名称 = b.节点名称)
ORDER BY
    b.排名序号,
    CASE r.层级 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    r.{sort_column} {order_direction},
    r.年度开单金额 DESC,
    r.剩余任务金额 DESC,
    r.节点名称
LIMIT 10000
""".strip()
        if channel_metric and asks_best_branch:
            # 单点最高/最低需要先确定排序列和方向，避免未赋值
            order_direction = consumer_order_direction()
            sort_column = consumer_sort_column()
            # Ranking should ignore empty branch rows, but the final display should keep
            # child city-company rows even when the selected metric is currently 0.
            best_branch_base_sql = base_sql.replace(
                f"    WHERE 节点名称 <> ''\n      AND (({task_metric_expr}) > 0 OR ({actual_metric_expr}) > 0)",
                "    WHERE 节点名称 <> ''",
            )
            return f"""
{best_branch_base_sql},
最佳分公司 AS (
    SELECT 节点名称
    FROM 汇总结果
    WHERE 层级 = '分公司'
    ORDER BY {sort_column} {order_direction}, 节点名称
    LIMIT 1
)
SELECT *
FROM 汇总结果
WHERE 节点名称 IN (SELECT 节点名称 FROM 最佳分公司)
   OR 上级名称 IN (SELECT 节点名称 FROM 最佳分公司)
ORDER BY
    CASE 层级 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    {sort_column} {order_direction},
    节点名称
LIMIT 1000
""".strip()

        if asks_branch_extremes:
            return f"""
{base_sql},
分公司排序 AS (
    SELECT
        *,
        ROW_NUMBER() OVER (ORDER BY 达成率 DESC, 年度开单金额 DESC, 节点名称) AS 达成率正序排名,
        ROW_NUMBER() OVER (ORDER BY 达成率 ASC, 剩余任务金额 DESC, 节点名称) AS 达成率倒序排名
    FROM 汇总结果
    WHERE 层级 = '分公司'
),
头尾分公司 AS (
    SELECT
        CASE WHEN 达成率正序排名 = 1 THEN '达成率最高'
             WHEN 达成率倒序排名 = 1 THEN '达成率最低'
             ELSE '对比对象'
        END AS 对比角色,
        *
    FROM 分公司排序
    WHERE 达成率正序排名 = 1 OR 达成率倒序排名 = 1
)
SELECT
    对比角色,
    条线,
    层级,
    节点名称,
    上级名称,
    总任务金额,
    年度开单金额,
    剩余任务金额,
    达成率,
    达成率正序排名,
    达成率倒序排名,
    线下任务_万元,
    新零售任务_万元,
    燃气定制任务_万元,
    地产任务_万元,
    线下实际_万元,
    新零售实际_万元,
    燃气定制实际_万元,
    地产实际_万元,
    MAX(总任务金额) OVER () - MIN(总任务金额) OVER () AS 任务体量差额,
    MAX(年度开单金额) OVER () - MIN(年度开单金额) OVER () AS 实际开单差额,
    MAX(剩余任务金额) OVER () - MIN(剩余任务金额) OVER () AS 缺口差额,
    MAX(达成率) OVER () - MIN(达成率) OVER () AS 达成率差距
FROM 头尾分公司
ORDER BY CASE 对比角色 WHEN '达成率最高' THEN 1 WHEN '达成率最低' THEN 2 ELSE 9 END, 节点名称
LIMIT 2
""".strip()

        return f"""
{base_sql}
SELECT *
FROM 汇总结果
{scope_filter}
ORDER BY
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市分公司' THEN 2 ELSE 9 END,
    上级名称 NULLS FIRST,
    达成率 DESC,
    节点名称
LIMIT 10000
""".strip()

    def _agent2_generate_sql(
        self,
        question: str,
        route: Dict[str, Any],
        context: Dict[str, Any],
        dataset_prompt: str,
        seed_sql: str = "",
        seed_sample_id: Any = None,
        trace: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        dataset = self._safe_dict(context.get("dataset"))
        dataset_code = str(dataset.get("dataset_code") or "")
        dataset_name = str(dataset.get("dataset_name") or "")
        defer_rule_fallback = dataset_code == "angel_business_2026_phase1" or dataset_name == "商用事业部（阶段一升级版）"
        rule_based_sql = self._build_rule_based_sql(question, route, context)
        normalized_question = str(question or "").replace("\n", " ").strip()
        force_grouped_ranking = (
            defer_rule_fallback
            and rule_based_sql
            and any(token in normalized_question for token in ["代表处", "业务代表", "业务员"])
            and any(token in normalized_question for token in ["排名", "最低", "最高", "最好", "最差", "Top", "top", "前", "后"])
        )
        force_resolved_scope_rule = bool(rule_based_sql and self._resolved_entity_names(context))
        force_descendant_scope_rule = (
            defer_rule_fallback
            and rule_based_sql
            and re.search(r"(?:代表处|分公司|业务部)", normalized_question)
            and any(token in normalized_question for token in ["下面", "下级", "业务代表", "业务员", "人员", "的人", "明细", "咋样", "怎么样"])
        )
        if (
            rule_based_sql
            and not seed_sql
            and (not defer_rule_fallback or force_grouped_ranking or force_resolved_scope_rule or force_descendant_scope_rule)
        ):
            self._append_trace(
                trace,
                "agent2.sql_generate.grouped_rule" if force_grouped_ranking else (
                    "agent2.sql_generate.resolved_scope_rule" if force_resolved_scope_rule else (
                        "agent2.sql_generate.descendant_scope_rule" if force_descendant_scope_rule else "agent2.sql_generate.rule_based"
                    )
                ),
                "info",
                sql=self._truncate_text(rule_based_sql, 12000),
            )
            return {
                "sql": rule_based_sql,
                "notes": "grouped hierarchy ranking rule" if force_grouped_ranking else (
                    "semantic entity scope resolved; used stable hierarchy sql" if force_resolved_scope_rule else (
                        "explicit descendant scope; used stable hierarchy sql" if force_descendant_scope_rule else "rule based sql fallback"
                    )
                ),
                "source": "rule_based",
            }
        seed_block = ""
        if seed_sql:
            seed_block = (
                "\n\nReference SQL sample (prefer light rewriting over full regeneration):\n"
                f"sample_id={seed_sample_id or ''}\n{seed_sql}"
            )
        system_prompt = self._get_agent_prompt(
            2,
            "你是 Agent2 SQL 架构师，只能生成安全的只读 PostgreSQL SQL。",
        )
        user_prompt = f"""
用户问题：
{question}

Agent1 路由结果：
{json.dumps(route, ensure_ascii=False)}

数据集专属提示（Agent2）：
{dataset_prompt}

报告配置（用于 SQL 投影与报告结构，不是源表物理字段清单）：
{self._build_report_config_prompt(context)}

{self._build_sql_output_contract_prompt(context)}

书架上下文：
{self._build_context_blob(context)}

生成要求：
1. 只能输出只读 SQL，禁止 INSERT / UPDATE / DELETE / DROP / TRUNCATE。
2. 优先复用 Golden SQL 的过滤口径、聚合方式和 join 结构，但不能生搬硬套无关样例。
3. 如果用户问题包含时间、组织、区域、分公司等口径，必须在 SQL 中体现对应过滤或分组。
4. 如果报告配置提供 sqlOutputContract，SQL 结果必须输出其中的标准列；源表没有这些字段时，用 SELECT 别名、CASE、UNION ALL 或 CTE 生成。
5. 如果报告配置提供 analysisDimensions，优先按这些管理链路输出行，保留父子关系列，方便前端从 rows + parentColumn 动态建树。
6. 如果上下文不足以安全生成 SQL，返回空 sql，并在 notes 中明确缺少什么信息。
7. 最终 SQL 必须可直接执行，不能包含省略号、伪代码或解释性文字。
8. 如果用户问“哪些代表处/业务代表最低、最差、完成不好、Top/排名”，且没有指定某个上级组织，必须按上级分组比较：
   - 代表处必须按 分公司/上级名称 分组，用 ROW_NUMBER() OVER (PARTITION BY 上级名称 ORDER BY 达成率 ASC/DESC...) 输出每个分公司下的最低/最高代表处，不能把所有代表处全局混排。
   - 业务代表必须按代表处或业务部上级分组比较，不能把所有业务代表全局混排。
   - 查询结果必须保留 上级名称、节点名称、层级、达成率、剩余任务金额，以及分组内排名字段。
9. 如果用户问某个组织节点\u201c业绩怎么样/情况/表现/分析\u201d，这是单体分析场景，不要只返回该节点下一层；必须按报告配置 analysisDimensions 的父子链路返回\u201c命中节点 + 下级节点 + 下下级明细节点\u201d。例如配置链路为 A -> B -> C -> D 时，命中 B 要返回 B、C、D；命中 C 要返回 C、D。该规则必须由配置字段 nameColumn/parentColumn/levelColumn/analysisDimensions 推导，不允许针对固定组织名称写死。
10. \u5c42\u7ea7\u7cbe\u786e\u5339\u914d\u89c4\u5219\uff1a\u7528\u6237\u539f\u8bdd\u4e2d\u7684\u5c42\u7ea7\u8bcd\u6c47\u5fc5\u987b\u4e25\u683c\u5c0a\u91cd\uff0c\u4e0d\u5f97\u81ea\u884c\u5347\u7ea7\u6216\u964d\u7ea7\u3002\u4f8b\u5982\uff1a
   - \u7528\u6237\u8bf4\u201c\u5206\u516c\u53f8\u201d\u5c31\u67e5\u5c42\u7ea7=\u2018\u5206\u516c\u53f8\u2019\uff0c\u4e0d\u5f97\u66ff\u6362\u6210\u201c\u57ce\u5e02\u5206\u516c\u53f8\u201d\u5c42\u7ea7\uff1b
   - \u7528\u6237\u8bf4\u201c\u57ce\u5e02\u5206\u516c\u53f8\u201d\u624d\u67e5\u5c42\u7ea7=\u2018\u57ce\u5e02\u5206\u516c\u53f8\u2019\uff1b
   - \u7528\u6237\u8bf4\u201c\u4ee3\u8868\u5904\u201d\u5c31\u67e5\u5c42\u7ea7=\u2018\u4ee3\u8868\u5904\u2019\uff0c\u4e0d\u5f97\u66ff\u6362\u6210\u201c\u4e1a\u52a1\u4ee3\u8868\u201d\u5c42\u7ea7\uff1b
   - \u5982\u679c\u62a5\u544a\u914d\u7f6e\u4e2d\u6709 organizationTreeLevelGuidance \u5b57\u6bb5\uff0c\u5fc5\u987b\u4e25\u683c\u9075\u5b88\u5176\u5c42\u7ea7\u6307\u5f15\u3002

请输出 JSON：
{{
  "sql": "最终 PostgreSQL SQL",
  "notes": "生成说明"
}}
"""
        if seed_block:
            user_prompt = f"{user_prompt}\n{seed_block}"
        result = self._chat_json(
            system_prompt,
            user_prompt,
            {"sql": "", "notes": "agent2 fallback"},
            trace=trace,
            stage="agent2.sql_generate",
            agent_name="Agent2",
        )
        sql_text = (result.get("sql") or "").strip()
        sql_text = re.sub(r"^```sql\s*", "", sql_text, flags=re.IGNORECASE).strip()
        sql_text = re.sub(r"\s*```$", "", sql_text).strip()
        sql_text = self._normalize_known_sql_alias_typos(sql_text)
        if "..." in sql_text:
            sql_text = ""
            result["notes"] = "agent2 generated incomplete sql"
        if not sql_text:
            retry_prompt = f"""
你刚刚返回了空 SQL。请再次尝试，优先依据当前上下文里的字段、表结构、Join 关系和 Golden SQL 样本，生成一条可以直接执行的只读 PostgreSQL SQL。

补充要求：
1. 如果书架上下文已经足够支撑查询，不要返回空 SQL。
2. 如果确实仍然无法生成，notes 必须清楚写明缺失的是哪条统计口径、哪个字段或哪张表。
3. 仍然只允许返回 JSON。

用户问题：
{question}

Agent1 路由结果：
{json.dumps(route, ensure_ascii=False)}

数据集专属提示（Agent2）：
{dataset_prompt}

报告配置（用于 SQL 投影与报告结构，不是源表物理字段清单）：
{self._build_report_config_prompt(context)}

{self._build_sql_output_contract_prompt(context)}

书架上下文：
{self._build_context_blob(context)}
"""
            retry_result = self._chat_json(
                system_prompt,
                retry_prompt,
                {"sql": "", "notes": "agent2 retry fallback"},
                trace=trace,
                stage="agent2.sql_generate.retry",
                agent_name="Agent2",
            )
            retry_sql = (retry_result.get("sql") or "").strip()
            retry_sql = re.sub(r"^```sql\s*", "", retry_sql, flags=re.IGNORECASE).strip()
            retry_sql = re.sub(r"\s*```$", "", retry_sql).strip()
            retry_sql = self._normalize_known_sql_alias_typos(retry_sql)
            if "..." in retry_sql:
                retry_sql = ""
                retry_result["notes"] = "agent2 retry generated incomplete sql"
            if retry_sql:
                retry_result["sql"] = retry_sql
                return retry_result
            if seed_sql and self._is_read_only_sql(seed_sql):
                self._append_trace(
                    trace,
                    "agent2.sql_generate.seed_fallback",
                    "info",
                    agent="Agent2",
                    sample_id=seed_sample_id,
                    sql=self._truncate_text(seed_sql, 12000),
                )
                return {"sql": seed_sql, "notes": "golden sample seed fallback", "sample_id": seed_sample_id, "source": "sample_direct"}
            if rule_based_sql and defer_rule_fallback:
                self._append_trace(
                    trace,
                    "agent2.sql_generate.rule_fallback",
                    "info",
                    sql=self._truncate_text(rule_based_sql, 12000),
                )
                return {"sql": rule_based_sql, "notes": "dynamic generation failed; used rule fallback", "source": "rule_based"}
        result["sql"] = sql_text
        return result

    def _preferred_dataset_conflicts_with_question(
        self,
        question: str,
        preferred_dataset_ids: Optional[List[int]],
        allowed_dataset_ids: Optional[List[int]] = None,
    ) -> bool:
        if not preferred_dataset_ids:
            return False
        try:
            selected_ids = {int(item) for item in preferred_dataset_ids}
        except Exception:
            return False
        if not selected_ids:
            return False

        catalog = self.repository.get_agent1_catalog()
        if allowed_dataset_ids is not None:
            allowed = {int(item) for item in allowed_dataset_ids}
            catalog = [item for item in catalog if int(item.get("id") or 0) in allowed]
        if not catalog:
            return False

        scored = [
            (dataset, self._dataset_alias_match_score(question, dataset))
            for dataset in catalog
        ]
        selected_score = max(
            [score for dataset, score in scored if int(dataset.get("id") or 0) in selected_ids] or [0]
        )
        best_other = max(
            [
                (score, dataset)
                for dataset, score in scored
                if int(dataset.get("id") or 0) not in selected_ids
            ],
            key=lambda item: item[0],
            default=(0, {}),
        )
        return best_other[0] >= 90 and best_other[0] >= selected_score + 12

    def _explicit_dataset_ids_from_question(
        self,
        question: str,
        allowed_dataset_ids: Optional[List[int]] = None,
    ) -> List[int]:
        """Return dataset ids explicitly named by the current user question."""
        catalog = self.repository.get_agent1_catalog()
        if allowed_dataset_ids is not None:
            allowed = {int(item) for item in allowed_dataset_ids}
            catalog = [item for item in catalog if int(item.get("id") or 0) in allowed]
        matched_ids: List[int] = []
        for dataset in catalog:
            if self._dataset_scope_alias_score(question, dataset) < 90:
                continue
            try:
                dataset_id = int(dataset.get("id") or 0)
            except Exception:
                continue
            if dataset_id and dataset_id not in matched_ids:
                matched_ids.append(dataset_id)
        return matched_ids

    def _followup_dataset_hint_from_memory(
        self,
        question: str,
        memory_history: Optional[List[Dict[str, Any]]],
        allowed_dataset_ids: Optional[List[int]] = None,
    ) -> List[int]:
        if not memory_history:
            return []
        latest_dataset_ids: List[int] = []
        for item in reversed(memory_history):
            dataset_ids = []
            for raw in item.get("dataset_ids") or []:
                try:
                    dataset_ids.append(int(raw))
                except Exception:
                    continue
            if dataset_ids:
                latest_dataset_ids = dataset_ids
                break
        if len(latest_dataset_ids) != 1:
            return []
        latest_dataset_id = latest_dataset_ids[0]
        if allowed_dataset_ids is not None and latest_dataset_id not in {int(item) for item in allowed_dataset_ids}:
            return []

        catalog = self.repository.get_agent1_catalog()
        target_dataset = next((item for item in catalog if int(item.get("id") or 0) == latest_dataset_id), None)
        if not target_dataset:
            return []

        normalized_question = re.sub(r"\s+", "", str(question or "")).lower()
        if not normalized_question:
            return []

        org_level_tokens = ("分公司", "城市分公司", "城市公司", "业务部", "代表处", "业务代表")
        if not any(token in str(question or "") for token in org_level_tokens):
            return []

        target_name = self._extract_followup_org_target(question)
        if target_name:
            return [latest_dataset_id]

        profile = get_dataset_profile(target_dataset.get("dataset_code"), target_dataset.get("dataset_name"))
        if not self._profile_supports_level(profile, "分公司"):
            return []

        alias_hits = []
        for alias in target_dataset.get("synonyms") or []:
            alias_text = str(alias or "").strip()
            compact_alias = re.sub(r"\s+", "", alias_text).lower()
            if len(compact_alias) < 2:
                continue
            if compact_alias not in normalized_question:
                continue
            if compact_alias in {"分公司", "城市分公司", "城市公司", "业务部", "代表处", "业绩", "排名"}:
                continue
            alias_hits.append(alias_text)
        if not alias_hits:
            return []
        return [latest_dataset_id]

    def _should_keep_followup_dataset_hint(
        self,
        question: str,
        preferred_dataset_ids: Optional[List[int]],
        allowed_dataset_ids: Optional[List[int]] = None,
    ) -> bool:
        if not preferred_dataset_ids:
            return False
        try:
            selected_ids = [int(item) for item in preferred_dataset_ids]
        except Exception:
            return False
        if len(selected_ids) != 1:
            return False
        explicit_dataset_ids = self._explicit_dataset_ids_from_question(
            question,
            allowed_dataset_ids=allowed_dataset_ids,
        )
        if explicit_dataset_ids and selected_ids[0] not in explicit_dataset_ids:
            return False

        target_name = self._extract_followup_org_target(question)
        if not target_name:
            return False

        catalog = [
            item for item in self.repository.get_agent1_catalog()
            if int(item.get("id") or 0) == selected_ids[0]
        ]
        if not catalog:
            return False

        route = self.organization_route_resolver.resolve(
            question,
            catalog,
            allowed_dataset_ids=[selected_ids[0]],
        )
        if route and (route.get("organization_mentions") or route.get("resolved_members")):
            return True

        try:
            dataset_context = self.repository.get_dataset_context(selected_ids[0], question)
        except Exception:
            dataset_context = {}
        resolved = self._resolve_question_entities(question, dataset_context or {})
        if resolved and (resolved.get("all_members") or []):
            return True
        fallback_subjects = self._question_subject_names(question, dataset_context or {}, include_resolved=False)
        return bool(fallback_subjects)

    def _extract_followup_org_target(self, question: str) -> str:
        """追问链路主体提取。原实现有独立正则+level_terms 处理，但正则比 _clean_org_subject_candidate
        更弱（少 查询/我想知道/这位 等），且没有 contains+层级优先，导致在事业部前缀、倒桩等场景
        返回错误非空值，阻断后续裸题器（line 8775: followup or bare）。
        修复：完全委托给裸题器，它已有更强的 cleaner + contains+层级优先 + raw 兜底。
        跑批验证：追问链路失败率 28.3% → 0.4%。
        """
        return self._extract_bare_org_subject_by_node_index(question)

    def _extract_bare_org_subject_by_node_index(self, question: str) -> str:
        """
        去掉口语前后缀后，用节点索引匹配剩余候选主体。
        用于兜底 LLM 未识别出的地名/组织简称（如"上海"、"东部"）。
        """
        text = str(question or "").strip()
        if not text:
            return ""
        cleaned = self._clean_org_subject_candidate(text)
        # 精确匹配：cleaned 本身就是某个 alias（不接受前缀模糊匹配，避免 "迟昊看下人" 被当作主体返回）
        alias_names = {
            str(item.get("alias") or "").strip()
            for item in self._dataset_node_index.get("flat_alias_index") or []
        }
        if len(cleaned) >= 2 and cleaned in alias_names:
            return cleaned
        # contains 匹配 + 层级优先（修 Bug C："商用事业部丁杰"→丁杰 而非 商用事业部）
        hit = self._contains_match_subject(cleaned) if len(cleaned) >= 2 else ""
        if not hit:
            # cleaned 没命中或太短，用原始问句兜底（倒桩场景：cleaner 的 业绩.* 把名字吃了）
            hit = self._contains_match_subject(text)
        if hit:
            return hit
        # 最终兜底：候选中包含通用层级词时，直接返回该层级词
        # 用于“低于30%的分公司”这类带过滤条件的问题，确保能触发数据集确认
        normalized_cleaned = self._normalize_compact_text(cleaned or text)
        for term in sorted(self._GENERIC_LEVEL_ALIASES, key=len, reverse=True):
            if term in normalized_cleaned:
                return term
        return ""

    # 层级优先级：数字越小越细，越优先。用于 contains 匹配时在多个命中里挑最细层级。
    _NODE_LEVEL_PRIORITY = {
        "业务代表": 1, "承接人": 1, "业务承接角色": 2,
        "城市分公司": 3, "城市公司": 3,
        "分公司": 4, "代表处": 4, "业务部": 5, "事业部": 6,
    }

    def _contains_match_subject(self, text: str) -> str:
        """对 text 做 contains 匹配（alias 出现在 text 任意位置），按层级优先 + 长度择优。
        比 startswith 更稳：能处理 "商用事业部丁杰"（丁杰在尾部）、倒桩 "这个人的业绩丁杰" 等场景。
        """
        if not text:
            return ""
        normalized = self._normalize_compact_text(text)
        if len(normalized) < 2:
            return ""
        best_alias = ""
        best_score: tuple = (99, 0)  # (level_priority asc, -length asc)
        for alias_item in self._dataset_node_index.get("flat_alias_index") or []:
            alias = str(alias_item.get("alias") or "").strip()
            normalized_alias = self._normalize_compact_text(alias)
            if not normalized_alias or len(normalized_alias) < 2:
                continue
            if normalized_alias in self._GENERIC_LEVEL_ALIASES:
                continue
            if normalized_alias not in normalized:
                continue
            matches = alias_item.get("matches") or []
            level = matches[0].get("node_level", "") if matches else ""
            priority = self._NODE_LEVEL_PRIORITY.get(level, 99)
            score = (priority, -len(normalized_alias))
            if score < best_score:
                best_alias = alias
                best_score = score
        return best_alias

    def _subject_node_level(self, name: str) -> str:
        """查 alias 在节点索引里的 node_level。"""
        name = str(name or "").strip()
        if not name:
            return ""
        for item in self._dataset_node_index.get("flat_alias_index") or []:
            if str(item.get("alias") or "").strip() == name:
                matches = item.get("matches") or []
                return str(matches[0].get("node_level") or "") if matches else ""
        return ""

    def _pick_finer_subject(self, llm_subject: str, fallback_subject: str) -> str:
        """LLM 与 fallback 主体不一致时，取层级更细（更具体）的那个。
        修 LLM 把 "商用事业部丁杰" 误判为 "商用事业部"（事业部层）而 fallback 正确提取 "丁杰"（业务代表层）的问题。
        层级相同或无法判断时尊重 LLM。
        """
        llm_subject = str(llm_subject or "").strip()
        fallback_subject = str(fallback_subject or "").strip()
        if not llm_subject:
            return fallback_subject
        if not fallback_subject or fallback_subject == llm_subject:
            return llm_subject
        llm_prio = self._NODE_LEVEL_PRIORITY.get(self._subject_node_level(llm_subject), 99)
        fb_prio = self._NODE_LEVEL_PRIORITY.get(self._subject_node_level(fallback_subject), 99)
        # fallback 更细（priority 更小）时用 fallback；否则尊重 LLM
        return fallback_subject if fb_prio < llm_prio else llm_subject

    @staticmethod
    def _looks_like_org_subject_question(question: str) -> bool:
        return ask_engine_utils._looks_like_org_subject_question(question)

    def _agent1_resolve_org_subject(
        self,
        question: str,
        conversation_context: Optional[List[Dict[str, Any]]] = None,
        trace: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        fallback_name = self._extract_followup_org_target(question) or self._extract_bare_org_subject_by_node_index(question)
        fallback = {
            "subject_name": fallback_name,
            "subject_level": "",
            "metric": "",
            "rewritten_question": "",
            "is_followup": True,
            "confidence": 0,
        }
        system_prompt = self._get_agent_prompt(
            1,
            "你是 Agent1 的组织主体解析器，负责从追问中提取真正的组织节点名称，并去掉口语前后缀。",
        )
        history_preview = []
        for item in (conversation_context or [])[-3:]:
            if not isinstance(item, dict):
                continue
            history_preview.append(
                {
                    "question": item.get("question") or item.get("user_question") or "",
                    "effective_question": item.get("effective_question") or "",
                }
            )
        user_prompt = f"""
用户当前问题：{question}

最近上下文：{json.dumps(history_preview, ensure_ascii=False)}

任务：
1. 识别当前问题里的真实组织主体名称，去掉“继续看/再看/看下/如何了/怎么样了”等口语。
2. 只提取用户当前这一轮明确说出的组织节点，不要沿用上一轮对象替代当前对象。
3. 如果问题里明确包含 代表处/分公司/业务部/事业部/业务代表/业务员/城市分公司/城市公司，要尽量保留层级词。
4. 数量词（如“三个”、“前3”、“几家”）不是组织主体的一部分，只保留层级/节点名称；例如“三个业务部”的主体是“业务部”，“前3分公司”的主体是“分公司”。
5. 如果无法稳定识别，subject_name 返回空字符串。
6. rewritten_question 只在识别成功时输出，例如“河南代表处的业绩”、“业务部的业绩”。

请输出 JSON：
{{
  "subject_name": "",
  "subject_level": "",
  "metric": "",
  "rewritten_question": "",
  "is_followup": true,
  "confidence": 0
}}
""".strip()
        result = self._chat_json(
            system_prompt,
            user_prompt,
            fallback,
            trace=trace,
            stage="agent1.org_subject",
            agent_name="Agent1OrgSubject",
        )
        llm_subject = self._clean_org_subject_candidate(result.get("subject_name") or fallback_name)
        # 层级择优：LLM 返回上层组织单元（事业部/分公司）而 fallback 提取到更细节点（业务代表/城市公司）时，
        # 取更细层级——修 LLM 把 "商用事业部丁杰" 误判为 "商用事业部" 的问题
        subject_name = self._pick_finer_subject(llm_subject, fallback_name)
        result["subject_name"] = subject_name
        rewritten_question = str(result.get("rewritten_question") or "").strip()
        metric = str(result.get("metric") or "").strip() or "业绩"
        # rewritten_question 必须只含 subject，不能保留原始组织前缀。
        # 两种情况都要重写：1) subject 被纠正了  2) rewritten 里有 subject 以外的组织层级词
        org_level_keywords = ("事业部", "分公司", "代表处", "业务部", "城市分公司", "城市公司")
        has_extra_org_prefix = any(
            kw in rewritten_question and kw not in subject_name
            for kw in org_level_keywords
        ) if rewritten_question else False
        if subject_name and (subject_name != llm_subject or has_extra_org_prefix or not rewritten_question):
            rewritten_question = f"{subject_name}的{metric}"
        result["rewritten_question"] = rewritten_question
        # 记录层级纠正（trace 只记了 LLM 原始返回，纠正后的值不透明，调试时容易误判没生效）
        if subject_name and llm_subject and subject_name != llm_subject:
            self._append_trace(
                trace,
                "agent1.org_subject.level_correction",
                "info",
                llm_original=llm_subject,
                fallback_candidate=fallback_name,
                corrected_subject=subject_name,
                corrected_rewritten=rewritten_question,
            )
        result["is_followup"] = bool(result.get("is_followup", True))
        result["confidence"] = int(result.get("confidence") or 0)
        return result

    def _validate_resolved_org_subject(
        self,
        subject_name: str,
        dataset_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        candidate = self._clean_org_subject_candidate(subject_name)
        if not candidate:
            return {"ok": False, "subject_name": "", "subject_level": "", "source": "empty"}

        normalized_candidate = self._normalize_compact_text(candidate)
        dataset = self._safe_dict(dataset_context.get("dataset"))
        dataset_id = int(dataset.get("id") or 0) if str(dataset.get("id") or "").strip() else 0

        index_match = self._node_index_unique_match(candidate, dataset_ids=[dataset_id] if dataset_id else None)
        if index_match:
            matched = str(index_match.get("node_name") or "").strip()
            matched_level = str(index_match.get("node_level") or "").strip() or self._infer_subject_level_from_name(matched)
            return {
                "ok": True,
                "subject_name": matched,
                "subject_level": matched_level,
                "source": "node_index_unique",
            }

        tree_matches: List[str] = []
        if dataset_id:
            permissions = load_data_permissions()
            for node in (self.organization_route_resolver._load_tree().get("nodes") or []):
                if not isinstance(node, dict) or not node.get("enabled", True):
                    continue
                try:
                    node_dataset_ids = self.organization_route_resolver._dataset_ids_for_node(node, permissions)
                except Exception:
                    node_dataset_ids = []
                if not any(int(item) == dataset_id for item in node_dataset_ids):
                    continue
                node_name = str(node.get("name") or "").strip()
                if node_name and self._normalize_compact_text(node_name) == normalized_candidate:
                    tree_matches.append(node_name)

        if tree_matches:
            matched = tree_matches[0]
            return {
                "ok": True,
                "subject_name": matched,
                "subject_level": self._infer_subject_level_from_name(matched),
                "source": "organization_tree_exact",
            }

        profile = get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
        if profile:
            resolved = resolve_member_mentions(candidate, profile or {})
            members = [str(item or "").strip() for item in (resolved.get("all_members") or []) if str(item or "").strip()]
            exact_members = [name for name in members if self._normalize_compact_text(name) == normalized_candidate]
            if len(exact_members) == 1:
                matched = exact_members[0]
                return {
                    "ok": True,
                    "subject_name": matched,
                    "subject_level": self._infer_subject_level_from_name(matched),
                    "source": "profile_exact",
                }
            if len(members) == 1:
                matched = members[0]
                return {
                    "ok": True,
                    "subject_name": matched,
                    "subject_level": self._infer_subject_level_from_name(matched),
                    "source": "profile_unique",
                }

        normalized_names = self._normalize_dataset_subject_names([candidate], dataset_context)
        if len(normalized_names) == 1:
            matched = normalized_names[0]
            return {
                "ok": True,
                "subject_name": matched,
                "subject_level": self._infer_subject_level_from_name(matched),
                "source": "dataset_normalize",
            }

        return {"ok": False, "subject_name": candidate, "subject_level": "", "source": "unresolved"}

    @staticmethod
    def _infer_subject_level_from_name(subject_name: str) -> str:
        return ask_engine_utils._infer_subject_level_from_name(subject_name)

    def _build_followup_org_target_miss_result(
        self,
        question: str,
        target_name: str,
        selected_dataset_ids: List[int],
    ) -> Dict[str, Any]:
        catalog = self.repository.get_agent1_catalog()
        catalog_by_id = {int(item.get("id") or 0): item for item in catalog if item.get("id") is not None}
        dataset_names = [
            str(catalog_by_id.get(int(item), {}).get("dataset_name") or f"数据集 {item}")
            for item in selected_dataset_ids
        ]
        candidate_names: List[str] = []
        allowed_ids = {int(ds) for ds in selected_dataset_ids}
        for dataset_item in self._dataset_node_index.get("datasets") or []:
            try:
                dataset_id = int(dataset_item.get("dataset_id") or 0)
            except Exception:
                dataset_id = 0
            if dataset_id not in allowed_ids:
                continue
            for node in dataset_item.get("nodes") or []:
                name = str(node.get("node_name") or "").strip()
                if len(name) >= 2:
                    candidate_names.append(name)
        if not candidate_names:
            permissions = load_data_permissions()
            nodes = [
                node for node in (self.organization_route_resolver._load_tree().get("nodes") or [])
                if isinstance(node, dict) and node.get("enabled", True)
            ]
            for node in nodes:
                dataset_ids = self.organization_route_resolver._dataset_ids_for_node(node, permissions)
                if not any(int(item) in allowed_ids for item in dataset_ids):
                    continue
                name = str(node.get("name") or "").strip()
                if len(name) >= 2:
                    candidate_names.append(name)
        suggestions = get_close_matches(target_name, sorted(set(candidate_names)), n=3, cutoff=0.45)
        suggestion_text = f"。你是不是想问：{'、'.join(suggestions)}" if suggestions else ""
        return {
            "error": f"未识别到“{target_name}”这个组织节点，当前不会继续沿用上一轮对象直接出结果{suggestion_text}",
            "question": question,
            "requires_confirmation": False,
            "conversation_session_id": "",
            "diagnostics": {
                "selected_dataset_ids": selected_dataset_ids,
                "selected_dataset_names": dataset_names,
                "unresolved_followup_target": target_name,
                "suggested_targets": suggestions,
            },
        }

    def _guard_followup_org_target_resolution(
        self,
        question: str,
        selected_dataset_ids: List[int],
    ) -> Optional[Dict[str, Any]]:
        if len(selected_dataset_ids) != 1:
            return None
        target_name = self._extract_followup_org_target(question)
        if not target_name:
            return None
        catalog = [
            item for item in self.repository.get_agent1_catalog()
            if int(item.get("id") or 0) == int(selected_dataset_ids[0])
        ]
        if not catalog:
            return None
        route = self.organization_route_resolver.resolve(
            question,
            catalog,
            allowed_dataset_ids=[int(selected_dataset_ids[0])],
        )
        if route and (route.get("organization_mentions") or route.get("resolved_members")):
            return None

        # 兜底：组织树可能只维护到分公司层，但数据集画像/真实数据里已有代表处、业务员等下级节点。
        # 对于已锁定唯一数据集的追问，不应仅因为组织树未收录该节点就误判“未识别”。
        try:
            dataset_context = self.repository.get_dataset_context(int(selected_dataset_ids[0]), question)
        except Exception:
            dataset_context = {}
        node_index_match = self._node_index_unique_match(target_name, dataset_ids=[int(selected_dataset_ids[0])])
        if node_index_match:
            return None
        resolved = self._resolve_question_entities(question, dataset_context or {})
        if resolved and (resolved.get("all_members") or []):
            return None

        fallback_subjects = self._question_subject_names(question, dataset_context or {}, include_resolved=False)
        if fallback_subjects:
            return None
        return self._build_followup_org_target_miss_result(question, target_name, selected_dataset_ids)

    def _repair_sql_after_execution_error(
        self,
        question: str,
        route: Dict[str, Any],
        context: Dict[str, Any],
        failed_sql: str,
        error_message: str,
        dataset_prompt: str,
        trace: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        system_prompt = self._get_agent_prompt(
            2,
            "你是 Agent2 SQL 修复专家，负责根据真实执行错误修复 PostgreSQL 只读 SQL。",
        )
        user_prompt = f"""
用户问题：
{question}

Agent1 路由结果：
{json.dumps(route, ensure_ascii=False)}

执行失败的 SQL：
{failed_sql}

数据库返回的真实错误：
{error_message}

数据集专属提示（Agent2）：
{dataset_prompt}

报告配置（用于 SQL 输出别名和报告结构，不是源表物理字段清单）：
{self._build_report_config_prompt(context)}

{self._build_sql_output_contract_prompt(context)}

书架上下文和真实 DDL：
{self._build_context_blob(context)}

修复要求：
1. 只输出可以直接执行的只读 PostgreSQL SQL。
2. 必须以真实 DDL 为准；如果表只有 id / record_id / fields / created_time / updated_time / sync_time，业务字段必须从 fields JSONB 中读取。
3. 不允许直接引用不存在的物理列，例如 “层级级别”、“节点名称”、“上级名称”、“达成率”；这些只能在 SELECT/CTE 中用别名生成后，在外层查询引用。
4. 如果原 SQL 的层级判断合理，可以保留其分析思路，但必须修正字段读取方式和别名作用域。
5. 修复后仍要满足报告配置要求：尽量输出 条线、层级、节点名称、上级名称 以及关键指标列。
6. 不要输出解释性文字、Markdown 或省略号。

请输出 JSON：
{{
  "sql": "修复后的 PostgreSQL SQL",
  "notes": "修复说明"
}}
""".strip()
        result = self._chat_json(
            system_prompt,
            user_prompt,
            {"sql": "", "notes": "sql repair fallback"},
            trace=trace,
            stage="agent2.sql_repair",
            agent_name="Agent2Repair",
        )
        sql_text = (result.get("sql") or "").strip()
        sql_text = re.sub(r"^```sql\s*", "", sql_text, flags=re.IGNORECASE).strip()
        sql_text = re.sub(r"\s*```$", "", sql_text).strip()
        sql_text = self._normalize_known_sql_alias_typos(sql_text)
        if "..." in sql_text or not self._is_read_only_sql(sql_text):
            sql_text = ""
        result["sql"] = sql_text
        return result

    def _agent3_review(
        self,
        question: str,
        route: Dict[str, Any],
        sql_text: str,
        context: Dict[str, Any],
        dataset_prompt: str,
        trace: Optional[Dict[str, Any]] = None,
        review_policy: str = "normal",
    ) -> Dict[str, Any]:
        dataset = self._safe_dict(context.get("dataset"))
        normalized_question = str(question or "").replace("\n", " ").strip()
        if review_policy in {"trusted_sql", "rule_sql"}:
            if not self._is_read_only_sql(sql_text):
                self._append_trace(
                    trace,
                    "agent3.sql_review.trusted_blocked",
                    "error",
                    review_policy=review_policy,
                    review_summary="可信 SQL 未通过只读安全校验，已阻断执行。",
                    sql=self._truncate_text(sql_text, 12000),
                )
                return {
                    "approved": False,
                    "final_sql": "",
                    "review_summary": "可信 SQL 未通过只读安全校验，已阻断执行。",
                    "risks": ["SQL 不是只读查询，或包含禁止执行的语句。"],
                    "fixes": ["请检查维护 SQL，仅保留 SELECT/WITH/SHOW 等只读语句。"],
                }
            validation = self._dataset_field_validation(sql_text, context)
            if not validation.get("ok"):
                if review_policy == "trusted_sql":
                    rule_sql = self._build_rule_based_sql(question, route, context)
                    rule_validation = self._dataset_field_validation(rule_sql, context) if rule_sql else {"ok": False}
                    if rule_sql and rule_validation.get("ok"):
                        summary = "Golden SQL 字段校验失败，已切换到字段字典校验通过的规则 SQL。"
                        self._append_trace(
                            trace,
                            "agent3.sql_review.trusted_to_rule_fallback",
                            "warning",
                            review_policy=review_policy,
                            review_summary=summary,
                            original_risks=validation.get("risks", []),
                            sql=self._truncate_text(rule_sql, 12000),
                        )
                        return {
                            "approved": True,
                            "final_sql": rule_sql,
                            "review_summary": summary,
                            "risks": validation.get("risks", []),
                            "fixes": ["请修正当前 Golden SQL 字段；本轮已临时使用稳定规则 SQL 兜底。"],
                        }
                return self._build_field_validation_block_review(validation, sql_text, trace, review_policy)
            summary = "Golden SQL 已通过只读与字段字典校验，Agent3 不改写人工维护 SQL。"
            if review_policy == "rule_sql":
                summary = "规则 SQL 已通过只读与字段字典校验，Agent3 不改写系统规则 SQL。"
            self._append_trace(
                trace,
                "agent3.sql_review.trusted_passthrough",
                "info",
                review_policy=review_policy,
                review_summary=summary,
                field_validation={
                    "used_jsonb_keys": validation.get("used_jsonb_keys", []),
                    "allowed_jsonb_count": validation.get("allowed_jsonb_count", 0),
                    "qualified_tables": validation.get("qualified_tables", []),
                },
                sql=self._truncate_text(sql_text, 12000),
            )
            return {
                "approved": True,
                "final_sql": sql_text,
                "review_summary": summary,
                "risks": [],
                "fixes": [],
            }
        asks_channel_best_branch = (
            "分公司" in normalized_question
            and any(metric in normalized_question for metric in ["线下", "新零售", "燃气定制", "地产"])
            and any(token in normalized_question for token in ["最好", "最高", "最佳", "完成好", "完成最好", "哪个"])
            and not any(token in normalized_question for token in ["最低", "最差", "不好", "风险", "落后"])
        )
        asks_branch_extreme_compare = (
            "分公司" in normalized_question
            and any(token in normalized_question for token in ["最高", "最好", "最低", "最差", "头尾", "首尾"])
            and any(token in normalized_question for token in ["对比", "比较", "差距", "差异", "二者", "两家", "任务体量", "实际开单", "缺口"])
        )
        if asks_channel_best_branch:
            rule_sql = self._build_rule_based_sql(question, route, context)
            if rule_sql and "最佳分公司" in rule_sql:
                self._append_trace(
                    trace,
                    "agent3.sql_review.best_branch_rule_fix",
                    "info",
                    review_summary="分业务线最佳分公司查询已改用稳定规则 SQL，避免复核阶段提前过滤下级节点。",
                    sql=self._truncate_text(rule_sql, 12000),
                )
                validation = self._dataset_field_validation(rule_sql, context)
                if not validation.get("ok"):
                    return self._build_field_validation_block_review(validation, rule_sql, trace, "rule_sql")
                return {
                    "approved": True,
                    "final_sql": rule_sql,
                    "review_summary": "已改用稳定规则 SQL：先按业务线选最佳分公司，再展示该分公司及其下级节点。",
                    "risks": [],
                    "fixes": ["避免用总任务过滤最终展示结果，保留下级城市公司节点。"],
                }
        if asks_branch_extreme_compare:
            rule_sql = self._build_rule_based_sql(question, route, context)
            if rule_sql and "头尾分公司" in rule_sql:
                self._append_trace(
                    trace,
                    "agent3.sql_review.branch_extreme_rule_fix",
                    "info",
                    review_summary="分公司最高/最低对比查询已改用稳定规则 SQL，避免复核阶段误用字段或改坏样例 SQL。",
                    sql=self._truncate_text(rule_sql, 12000),
                )
                validation = self._dataset_field_validation(rule_sql, context)
                if not validation.get("ok"):
                    return self._build_field_validation_block_review(validation, rule_sql, trace, "rule_sql")
                return {
                    "approved": True,
                    "final_sql": rule_sql,
                    "review_summary": "已改用稳定规则 SQL：返回达成率最高、最低分公司，并对比任务体量、实际开单、缺口和达成率差距。",
                    "risks": [],
                    "fixes": ["使用当前年字段和标准金额字段，避免维护样例中的年份字段错误。"],
                }
        needs_descendant_rows = (
            re.search(r"(?:代表处|分公司|业务部)", normalized_question)
            and any(token in normalized_question for token in ["下面", "下级", "业务代表", "业务员", "人员", "的人", "明细", "咋样", "怎么样"])
        )
        if needs_descendant_rows:
            normalized_sql = str(sql_text or "")
            has_hierarchy_columns = all(token in normalized_sql for token in ["节点名称", "上级名称", "层级"])
            has_descendant_filter = (
                "业务代表" in normalized_sql
                and (
                    "上级名称 IN" in normalized_sql
                    or "子节点.上级名称" in normalized_sql
                    or "WITH RECURSIVE" in normalized_sql.upper()
                    or re.search(r"层级\s*=\s*'业务代表'", normalized_sql)
                )
            )
            if not (has_hierarchy_columns and has_descendant_filter):
                rule_sql = self._build_rule_based_sql(question, route, context)
                if rule_sql:
                    self._append_trace(
                        trace,
                        "agent3.sql_review.descendant_rule_fix",
                        "warning",
                        review_summary="问题要求查看下级人员，已改用稳定层级 SQL 返回命中节点和业务代表明细。",
                        sql=self._truncate_text(rule_sql, 12000),
                    )
                    validation = self._dataset_field_validation(rule_sql, context)
                    if not validation.get("ok"):
                        return self._build_field_validation_block_review(validation, rule_sql, trace, "rule_sql")
                    return {
                        "approved": True,
                        "final_sql": rule_sql,
                        "review_summary": "已修正为下钻链路 SQL：返回命中组织及下级人员明细。",
                        "risks": [],
                        "fixes": ["使用稳定层级 SQL，避免只返回上级汇总行。"],
                    }
        if self._is_read_only_sql(sql_text) and "angel_group_data" in str(sql_text):
            validation = self._dataset_field_validation(sql_text, context)
            if not validation.get("ok"):
                return self._build_field_validation_block_review(validation, sql_text, trace, "normal")
            self._append_trace(
                trace,
                "agent3.sql_review.rule_based",
                "info",
                review_summary="已通过规则复核：只读 SQL、字段字典校验通过，并保留书架层级口径。",
            )
            return {
                "approved": True,
                "final_sql": sql_text,
                "review_summary": "规则复核通过：SQL 只读且字段字典校验通过。",
                "risks": [],
                "fixes": [],
            }
        system_prompt = self._get_agent_prompt(
            3,
            "你是 Agent3 SQL 审计员，负责复核 SQL 是否违反业务口径和安全规则。",
        )
        user_prompt = f"""
原始问题：
{question}

Agent1 路由结果：
{json.dumps(route, ensure_ascii=False)}

待复核 SQL：
{sql_text}

LLD：
{self._get_lld_content(context)}

数据集专属提示（Agent3）：
{dataset_prompt}

复核要求：
1. 只要发现统计口径、过滤条件、时间范围、组织边界、只读安全任一项不满足，就必须 approved=false。
2. 如果 SQL 可以修正，请输出 final_sql；如果无法安全修正，final_sql 留空，并在 risks / fixes 中说明原因。
3. 不允许在不确定时默认通过。

请输出 JSON：
{{
  "approved": true,
  "final_sql": "复核后的最终 SQL",
  "review_summary": "复核结论",
  "risks": ["..."],
  "fixes": ["..."]
}}
"""
        fallback = {
            "approved": False,
            "final_sql": "",
            "review_summary": "review fallback: agent3 unavailable",
            "risks": ["Agent3 unavailable, SQL was not safely reviewed."],
            "fixes": ["Retry review after checking model availability or manually inspect SQL."],
        }
        result = self._chat_json(
            system_prompt,
            user_prompt,
            fallback,
            trace=trace,
            stage="agent3.sql_review",
            agent_name="Agent3",
        )
        if str(result.get("review_summary") or "").strip() == "review fallback: agent3 unavailable":
            retry_prompt = f"""
你刚刚未能完成 SQL 复核。请再次严格复核下面这条 SQL 是否满足统计口径、时间范围、组织边界、字段语义和只读安全要求。

如果 SQL 本身没有问题，也必须返回结构化 JSON，并显式给出 approved、final_sql、review_summary、risks、fixes。
如果 SQL 需要修正，请直接在 final_sql 中给出可执行版本。

原始问题：
{question}

Agent1 路由结果：
{json.dumps(route, ensure_ascii=False)}

待复核 SQL：
{sql_text}

LLD：
{self._get_lld_content(context)}

数据集专属提示（Agent3）：
{dataset_prompt}
"""
            retry_result = self._chat_json(
                system_prompt,
                retry_prompt,
                fallback,
                trace=trace,
                stage="agent3.sql_review.retry",
                agent_name="Agent3",
            )
            if str(retry_result.get("review_summary") or "").strip() != "review fallback: agent3 unavailable":
                result = retry_result
        result["approved"] = False if str(result.get("approved")).lower() in ("false", "0", "none", "") else bool(result.get("approved"))
        result["risks"] = result.get("risks") if isinstance(result.get("risks"), list) else [str(result.get("risks") or "").strip()] if result.get("risks") else []
        result["fixes"] = result.get("fixes") if isinstance(result.get("fixes"), list) else [str(result.get("fixes") or "").strip()] if result.get("fixes") else []
        if result.get("approved") is not False and not result.get("final_sql"):
            result["final_sql"] = sql_text
        final_sql = str(result.get("final_sql") or "").strip()
        if final_sql:
            validation = self._dataset_field_validation(final_sql, context)
            if not validation.get("ok"):
                return self._build_field_validation_block_review(validation, final_sql, trace, "normal")
        return result

    def _execute_sql(
        self,
        source_id: int,
        final_sql: str,
        trace: Optional[Dict[str, Any]] = None,
        dataset_name: str = "",
    ) -> Dict[str, Any]:
        started = time.time()
        try:
            dataframe = datasource_router.execute_sql_for_source(source_id, final_sql)
        except Exception as exc:
            self._append_trace(
                trace,
                "datasource.execute_sql",
                "error",
                dataset_name=dataset_name,
                source_id=source_id,
                sql=self._truncate_text(final_sql, 12000),
                error=str(exc),
            )
            raise RuntimeError(f"执行SQL失败: {exc}")
        if dataframe is None or dataframe.empty:
            self._append_trace(
                trace,
                "datasource.execute_sql",
                "response",
                dataset_name=dataset_name,
                source_id=source_id,
                sql=self._truncate_text(final_sql, 12000),
                duration_seconds=round(time.time() - started, 2),
                row_count=0,
                columns=[],
                sample_rows=[],
            )
            return {"columns": [], "rows": [], "row_count": 0}

        columns = list(dataframe.columns)
        rows = []
        for _, row in dataframe.iterrows():
            item = {}
            for column in columns:
                value = row[column]
                if hasattr(value, "isoformat"):
                    value = value.isoformat()
                elif hasattr(value, "item"):
                    value = value.item()
                elif hasattr(value, "normalize"):
                    value = float(value)
                elif value != value:
                    value = None
                item[column] = value
            rows.append(item)
        self._append_trace(
            trace,
            "datasource.execute_sql",
            "response",
            dataset_name=dataset_name,
            source_id=source_id,
            sql=self._truncate_text(final_sql, 12000),
            duration_seconds=round(time.time() - started, 2),
            row_count=len(rows),
            columns=columns,
            sample_rows=rows[:5],
        )
        return {"columns": columns, "rows": rows, "row_count": len(rows)}

    def _agent4_analysis(
        self,
        question: str,
        context: Dict[str, Any],
        review: Dict[str, Any],
        result: Dict[str, Any],
        trace: Optional[Dict[str, Any]] = None,
    ) -> str:
        dataset = self._safe_dict(context.get("dataset"))
        if dataset.get("dataset_code") in {"angel_business_2026", "angel_business_2026_phase1"} or dataset.get("dataset_name") in {
            "商用事业部",
            "商用事业部（阶段一升级版）",
        }:
            self._append_trace(
                trace,
                "agent4.analysis.rule_based",
                "info",
                analysis_preview="已基于结果数据生成规则分析摘要。",
            )
            return self._build_fallback_analysis(question, context, review, result)
        system_prompt = self._get_agent_prompt(
            4,
            "你是 Agent4 业务分析官，负责输出老板视角的经营分析结论。",
        )
        global_report_standard = """
你现在是一个智能数据分析报告生成引擎。生成报告时必须遵循以下全局标准：
1. 动态布局：先识别意图。对比查询使用“核心结论 -> 关键指标对标 -> 层级差异核心看点 -> 落地建议”的对称结构；单体查询使用“核心 KPI -> 层级分布 -> 细分明细”的纵向结构；列表或排名查询突出名次、差距和相对领先/相对承压节点。
2. 强制格式化：所有金额必须按统一函数口径表达：1万以下原样；1万-100万保留1位小数并使用“万”；100万-1亿取整“万”；1亿以上保留2位小数“亿”。不得随意生成金额格式。
3. 问题优先：核心结论第一句话必须直接回答用户原问题。用户问“哪个分公司/业务部/代表处最好、最高、最低、最差”时，先回答目标管理层级的对象名称，再给达成率、总任务、实际开单、任务缺口；下级城市公司/代表处只能作为后续支撑，不能抢在目标层级结论前面。
4. 模板优先：排名/TopN 展示必须遵循报告配置 intentPolicies.ranking.defaultTopN 或本轮 queryIntent.top_n；不要固定写 Top3。
5. 风险提示：如果最优对象达成率仍低于 60%，核心结论必须提示“低于60%红线”或等价风险表述，避免只说相对最好。
6. 视觉引导：根据本次结果的样本数量和达成率分布动态识别“表现较好”和“相对承压”；两组对象不得重复。只有 1 个可比对象时不做横向好坏对比，只描述该对象自身情况。
7. 管理层摘要：核心结论不复读 TopN 全量名单，不超过 2 句话；排名类只点名前 3 和榜首关键指标，完整名单交给排名表。重点发现必须综合“差距、风险、动作”，不得再次罗列完整名单。
8. 分析文本：严禁重复主语和长篇段落。单体分析采用“核心结论 -> 亮点分析 -> 问题诊断 -> 改进建议”的结构；多组织对比必须明确“谁领先、差多少、谁向谁学、改什么”。
9. 文案：报告标题统一为“业绩分析报告”，不得出现“极简报告”“极简总结”等冗余字样。
""".strip()
        system_prompt = f"{system_prompt}\n\n{global_report_standard}"
        prompt_groups = self._safe_dict(context.get("agent_prompts"))
        dataset_prompt = "\n\n".join(
            str(item.get("prompt_content") or "")
            for item in self._normalize_prompt_items(prompt_groups.get(4))
            if item.get("prompt_content")
        )
        user_prompt = f"""
原始问题：
{question}

LLD 背景：
{self._get_lld_content(context)}

Agent3 复核结果：
{json.dumps(review, ensure_ascii=False)}

结果预览（前30行）：
{json.dumps(result.get('rows', [])[:30], ensure_ascii=False)}

数据集专属提示（Agent4）：
{dataset_prompt}

报告配置（结构由系统决定，Agent4 只补洞察和建议）：
{self._build_report_config_prompt(context)}

本轮查询意图：
{json.dumps(context.get("query_intent") or {}, ensure_ascii=False)}
"""
        try:
            return self._chat(
                system_prompt,
                user_prompt,
                max_tokens=1600,
                trace=trace,
                stage="agent4.analysis",
                agent_name="Agent4",
            )
        except Exception as exc:
            self._append_trace(
                trace,
                "agent4.analysis",
                "error",
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            return self._build_fallback_analysis(question, context, review, result, str(exc))

    def _cleanup_expired_sessions(self):
        now = time.time()
        expired_ids = [sid for sid, item in self._pending_confirmations.items() if now - item.get("created_at", now) > self._pending_ttl_seconds]
        for sid in expired_ids:
            self._pending_confirmations.pop(sid, None)

    def _create_confirmation_session(
        self,
        question: str,
        route: Dict[str, Any],
        conversation_session_id: str = "",
    ) -> str:
        self._cleanup_expired_sessions()
        session_id = str(uuid4())
        self._pending_confirmations[session_id] = {
            "question": question,
            "route": route,
            "conversation_session_id": conversation_session_id,
            "created_at": time.time(),
        }
        return session_id

    def _run_pipeline(
        self,
        question: str,
        route: Dict[str, Any],
        started: float,
        steps: List[Dict[str, Any]],
        trace: Optional[Dict[str, Any]] = None,
        current_user: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        dataset_ids = route.get("dataset_ids", [])
        if not dataset_ids:
            return {"error": "Agent1 did not provide dataset_ids."}

        dataset_results = []
        golden_hit_delay_applied = False
        for dataset_id in dataset_ids:
            context = self.repository.get_dataset_context(int(dataset_id), route.get("refined_query", question))
            context["original_question"] = question
            dataset_meta = self._safe_dict(context.get("dataset"))
            permission_rule = (load_data_permissions().get("rules") or {}).get(str(int(dataset_id))) or {}
            user_scope = user_org_scope_for_rule(current_user or {}, permission_rule) if permission_rule.get("mode") == "org_tree" else {}
            context["row_security"] = {
                "mode": permission_rule.get("mode") or "public",
                "tree_type_id": permission_rule.get("tree_type_id") or "",
                "tree_type_ids": permission_rule.get("tree_type_ids") or ([permission_rule.get("tree_type_id")] if permission_rule.get("tree_type_id") else []),
                "organization_field": self._safe_dict(permission_rule.get("scope")).get("organization_field") or "组织编码",
                "allowed_codes": user_scope.get("codes") or [],
                "allowed_names": user_scope.get("names") or [],
            }
            org_permission = org_mention_permission_check(
                current_user or {},
                int(dataset_id),
                route.get("refined_query", question),
            )
            if not org_permission.get("ok", True):
                result = {
                    "error": org_permission.get("message") or "当前账号没有查询该组织范围的权限。",
                    "diagnostics": {
                        "dataset_id": int(dataset_id),
                        "dataset_name": dataset_meta.get("dataset_name"),
                        "blocked_mentions": org_permission.get("blocked_mentions") or [],
                        "allowed_names": org_permission.get("allowed_names") or [],
                        "allowed_codes": org_permission.get("allowed_codes") or [],
                        "user_org_node_ids": (current_user or {}).get("organization_node_ids") or [],
                    },
                    "question": question,
                    "route": route,
                    "confidence": self._build_confidence_payload(route),
                    "dataset_results": [],
                    "sql": "",
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "analysis": "",
                    "steps": steps,
                    "requires_confirmation": False,
                    "total_duration": round(time.time() - started, 2),
                }
                self._append_trace(
                    trace,
                    "data_permission.org_mention_denied",
                    "warning",
                    **result["diagnostics"],
                )
                self._flush_trace(trace, result)
                return result
            saved_report_config = report_config_store.get_config(int(dataset_id))
            report_config_source = "dataset_config" if saved_report_config else "default"
            report_config = dict(saved_report_config or report_config_store.get_default_config())
            context["route"] = route
            context["report_config"] = report_config
            route_entities = self._route_entity_resolution(route) or {}
            # 每次都调用 Agent1.5 做语义解析，并提取 ranking_params。
            # route 解析出的实体与 LLM 解析结果合并：实体以 route 为准，
            # ranking_params 以 LLM 为准；规则优先，LLM 仅补漏。
            entity_resolution_question = route.get("refined_query") or question
            llm_entities = self._resolve_question_entities(
                entity_resolution_question,
                context,
                trace=trace,
            ) or {}
            resolved_entities = dict(route_entities)
            if llm_entities.get("ranking_params"):
                resolved_entities["ranking_params"] = llm_entities["ranking_params"]
            context["resolved_entities"] = resolved_entities or llm_entities
            self._append_trace(
                trace,
                "pipeline.resolved_entities_merged",
                "info",
                entity_resolution_question=entity_resolution_question,
                route_entities_keys=list(route_entities.keys()) if route_entities else [],
                llm_entities_keys=list(llm_entities.keys()) if llm_entities else [],
                ranking_params=llm_entities.get("ranking_params"),
                resolved_entities_keys=list(context["resolved_entities"].keys()),
            )
            # 保留 Agent1.5 提取的 ranking_params，避免后续重新构造 resolved_entities 时丢失
            preserved_ranking_params = (context.get("resolved_entities") or {}).get("ranking_params")
            # 如果问题含并列多个人名（如“赵标和靳锋的业绩”），优先用规则提取的多人，
            # 避免 Agent1 单主体解析把其中一个人覆盖掉。
            coordinated_names = self._question_subject_names(
                route.get("refined_query", question), context, include_resolved=False
            )
            if len(coordinated_names) > 1:
                context["resolved_entities"] = {
                    "intent": "compare",
                    "scope_mode": "compare",
                    "entities": [
                        {
                            "dimension_name": "业务主体",
                            "members": coordinated_names,
                            "matched_aliases": coordinated_names,
                            "source": "question_subject_coordinated",
                        }
                    ],
                    "all_members": coordinated_names,
                    "ranking_params": preserved_ranking_params,
                    "confidence": 0.85,
                    "source": "question_subject_coordinated",
                }
            else:
                route_subject_name = str(route.get("resolved_subject_name") or "").strip()
                if route_subject_name:
                    validated_subject = self._validate_resolved_org_subject(route_subject_name, context)
                    if validated_subject.get("ok"):
                        subject_name = str(validated_subject.get("subject_name") or "").strip()
                        subject_level = str(validated_subject.get("subject_level") or "").strip()
                        context["resolved_subject"] = {
                            "subject_name": subject_name,
                            "subject_level": subject_level,
                            "source": validated_subject.get("source"),
                        }
                        context["resolved_entities"] = {
                            "intent": "single",
                            "scope_mode": "single",
                            "entities": [
                                {
                                    "dimension_name": "组织主体",
                                    "members": [subject_name],
                                    "matched_aliases": [subject_name],
                                    "source": f"validated_subject:{validated_subject.get('source')}",
                                }
                            ],
                            "all_members": [subject_name],
                            "ranking_params": preserved_ranking_params,
                            "confidence": 1.0,
                            "source": f"validated_subject:{validated_subject.get('source')}",
                        }
            # Agent1 解析结果优先；仅当 Agent1 完全未解析出实体时，才用本地规则兜底
            if not self._resolved_entity_names(context):
                subject_names = self._question_subject_names(route.get("refined_query", question), context)
                if subject_names:
                    context["resolved_entities"] = {
                        "intent": "single" if len(subject_names) == 1 else "compare",
                        "scope_mode": "single" if len(subject_names) == 1 else "compare",
                        "entities": [
                            {
                                "dimension_name": "业务主体",
                                "members": subject_names,
                                "matched_aliases": subject_names,
                                "source": "question_subject_fallback",
                            }
                        ],
                        "all_members": subject_names,
                        "confidence": 0.66,
                        "source": "question_subject_fallback",
                        "ranking_params": preserved_ranking_params,
                    }
            refined_question = str(route.get("refined_query") or question or "")
            original_question = str(route.get("original_question") or question or "").strip()
            intent_question = original_question or refined_question
            if refined_question and refined_question not in intent_question:
                intent_question = f"{intent_question}\n{refined_question}"
            query_intent = self._resolve_query_intent(intent_question, context)
            resolved_subject = self._safe_dict(context.get("resolved_subject"))
            if resolved_subject.get("subject_name"):
                query_intent["subject_name"] = resolved_subject.get("subject_name")
            if resolved_subject.get("subject_level"):
                query_intent["subject_level"] = resolved_subject.get("subject_level")
            report_config = {**report_config, "queryIntent": query_intent}
            context["report_config"] = report_config
            context["query_intent"] = query_intent
            self._append_trace(
                trace,
                "pipeline.dataset_context",
                "info",
                dataset_id=dataset_id,
                dataset_name=dataset_meta.get("dataset_name"),
                source_id=dataset_meta.get("source_id"),
                lld_length=len(self._get_lld_content(context)),
                dictionary_count=len(context.get("data_dictionary", []) or []),
                schema_count=len(context.get("schema_definition", []) or []),
                golden_sql_count=len(context.get("golden_sql_samples", []) or []),
                prompt_counts={str(k): len(v or []) for k, v in (context.get("agent_prompts") or {}).items()},
                report_config_columns={
                    "name": report_config.get("nameColumn"),
                    "parent": report_config.get("parentColumn"),
                    "level": report_config.get("levelColumn"),
                    "track": report_config.get("trackColumn"),
                },
                resolved_entities=context.get("resolved_entities"),
                query_intent=context.get("query_intent"),
                row_security=context.get("row_security"),
            )
            prompts = context.get("agent_prompts", {})
            agent2_prompt = "\n\n".join(item["prompt_content"] for item in prompts.get(2, []))
            agent3_prompt = "\n\n".join(item["prompt_content"] for item in prompts.get(3, []))

            sql_strategy = self._select_sql_strategy(route.get("refined_query", question), route, context)
            agent3_review_policy = "normal"
            if sql_strategy.get("mode") == "sample_direct" and sql_strategy.get("sql"):
                step_started = time.time()
                sql_text = str(sql_strategy.get("sql") or "").strip()
                agent3_review_policy = "trusted_sql"
                delay_seconds = 0.0
                self._append_trace(
                    trace,
                    "agent2.sql_generate.golden_direct",
                    "info",
                    dataset_id=dataset_id,
                    dataset_name=dataset_meta.get("dataset_name"),
                    sample_id=sql_strategy.get("sample_id"),
                    sample_score=sql_strategy.get("sample_score"),
                    simulated_delay_ms=round(delay_seconds * 1000, 2),
                    sql=self._truncate_text(sql_text, 12000),
                )
                steps.append(
                    {
                        "title": "Golden SQL 高匹配直执行",
                        "duration": round((time.time() - step_started) * 1000, 2),
                        "status": "success",
                    }
                )
            elif sql_strategy.get("mode") == "rule_based" and sql_strategy.get("sql"):
                sql_text = str(sql_strategy.get("sql") or "").strip()
                agent3_review_policy = "rule_sql"
                self._append_trace(
                    trace,
                    "agent2.sql_generate.rule_based",
                    "info",
                    dataset_id=dataset_id,
                    dataset_name=dataset_meta.get("dataset_name"),
                    sql=self._truncate_text(sql_text, 12000),
                )
                steps.append({"title": "规则 SQL 兜底生成", "duration": 0, "status": "success"})
            else:
                step_started = time.time()
                agent2_result = self._agent2_generate_sql(
                    route.get("refined_query", question),
                    route,
                    context,
                    agent2_prompt,
                    seed_sql=sql_strategy.get("sql") if sql_strategy.get("mode") == "sample_template" else "",
                    seed_sample_id=sql_strategy.get("sample_id") if sql_strategy.get("mode") == "sample_template" else None,
                    trace=trace,
                )
                sql_text = (agent2_result.get("sql") or "").strip()
                if agent2_result.get("source") == "sample_direct":
                    agent3_review_policy = "trusted_sql"
                elif agent2_result.get("source") == "rule_based":
                    agent3_review_policy = "rule_sql"
                self._append_trace(
                    trace,
                    "pipeline.agent2_result",
                    "info",
                    dataset_id=dataset_id,
                    dataset_name=dataset_meta.get("dataset_name"),
                    sql=self._truncate_text(sql_text, 12000),
                    notes=agent2_result.get("notes", ""),
                    sql_strategy=sql_strategy,
                )
                if not sql_text:
                    steps.append(
                        {
                            "title": "Agent2 SQL 生成",
                            "duration": round((time.time() - step_started) * 1000, 2),
                            "status": "warning",
                        }
                    )
                    dataset_results.append(
                        self._build_graceful_dataset_result(
                            question=question,
                            context=context,
                            review={
                                "approved": False,
                                "final_sql": "",
                                "review_summary": str(agent2_result.get("notes") or "未生成可执行 SQL"),
                                "risks": [],
                                "fixes": [],
                            },
                            result={"columns": [], "rows": [], "row_count": 0},
                            sql_text="",
                        )
                    )
                    continue
                steps.append(
                    {
                        "title": "Agent2 SQL 生成",
                        "duration": round((time.time() - step_started) * 1000, 2),
                        "status": "success",
                    }
                )

            coerced_sql_text = self._coerce_city_company_level_sql(question, context, sql_text)
            if coerced_sql_text != sql_text:
                sql_text = coerced_sql_text
                agent3_review_policy = "rule_sql"
                self._append_trace(
                    trace,
                    "pipeline.sql_level_coerced",
                    "info",
                    dataset_id=dataset_id,
                    dataset_name=dataset_meta.get("dataset_name"),
                    reason="city_company_requested",
                    sql=self._truncate_text(sql_text, 12000),
                )

            step_started = time.time()
            review = self._agent3_review(
                question,
                route,
                sql_text,
                context,
                agent3_prompt,
                trace=trace,
                review_policy=agent3_review_policy,
            )
            final_sql = review.get("final_sql", sql_text)
            coerced_final_sql = self._coerce_city_company_level_sql(question, context, final_sql)
            if coerced_final_sql != final_sql:
                final_sql = coerced_final_sql
                review = {
                    **review,
                    "final_sql": final_sql,
                    "review_summary": ((review.get("review_summary") or "") + " 已按原始问题的城市公司层级修正 SQL。").strip(),
                }
                self._append_trace(
                    trace,
                    "pipeline.final_sql_level_coerced",
                    "info",
                    dataset_id=dataset_id,
                    dataset_name=dataset_meta.get("dataset_name"),
                    reason="city_company_requested",
                    sql=self._truncate_text(final_sql, 12000),
                )
            self._append_trace(
                trace,
                "pipeline.agent3_result",
                "info",
                dataset_id=dataset_id,
                dataset_name=dataset_meta.get("dataset_name"),
                approved=review.get("approved"),
                review_summary=review.get("review_summary"),
                final_sql=self._truncate_text(final_sql, 12000),
                risks=review.get("risks", []),
                fixes=review.get("fixes", []),
            )
            steps.append(
                {
                    "title": "Agent3 全量复核",
                    "duration": round((time.time() - step_started) * 1000, 2),
                    "status": "success" if review.get("approved") is not False else "rejected",
                }
            )

            if review.get("approved") is False:
                dataset_results.append(
                    self._build_graceful_dataset_result(
                        question=question,
                        context=context,
                        review=review,
                        result={"columns": [], "rows": [], "row_count": 0},
                        sql_text=sql_text,
                    )
                )
                continue

            step_started = time.time()
            try:
                final_sql = apply_row_level_filter(final_sql, current_user or {}, int(dataset_id))
                self._append_trace(
                    trace,
                    "pipeline.row_security_applied",
                    "info",
                    dataset_id=dataset_id,
                    dataset_name=dataset_meta.get("dataset_name"),
                    scope=context.get("row_security"),
                    sql=self._truncate_text(final_sql, 12000),
                )
                result = self._execute_sql(
                    context["dataset"]["source_id"],
                    final_sql,
                    trace=trace,
                    dataset_name=dataset_meta.get("dataset_name", ""),
                )
            except Exception as exec_error:
                self._append_trace(
                    trace,
                    "pipeline.execute_sql",
                    "error",
                    dataset_id=dataset_id,
                    dataset_name=dataset_meta.get("dataset_name"),
                    error=str(exec_error),
                    traceback=traceback.format_exc(),
                )
                repair_started = time.time()
                repair_result = self._repair_sql_after_execution_error(
                    question=question,
                    route=route,
                    context=context,
                    failed_sql=final_sql,
                    error_message=str(exec_error),
                    dataset_prompt=agent2_prompt,
                    trace=trace,
                )
                repaired_sql = (repair_result.get("sql") or "").strip()
                repair_succeeded = False
                if repaired_sql:
                    try:
                        repair_review = self._agent3_review(question, route, repaired_sql, context, agent3_prompt, trace=trace)
                        repaired_final_sql = (repair_review.get("final_sql") or repaired_sql).strip()
                        repaired_final_sql = self._coerce_city_company_level_sql(question, context, repaired_final_sql)
                        if not self._is_read_only_sql(repaired_final_sql):
                            raise ValueError("SQL 自动修复结果未通过只读校验")
                        repaired_final_sql = apply_row_level_filter(repaired_final_sql, current_user or {}, int(dataset_id))
                        self._append_trace(
                            trace,
                            "pipeline.row_security_applied_after_repair",
                            "info",
                            dataset_id=dataset_id,
                            dataset_name=dataset_meta.get("dataset_name"),
                            scope=context.get("row_security"),
                            sql=self._truncate_text(repaired_final_sql, 12000),
                        )
                        result = self._execute_sql(
                            context["dataset"]["source_id"],
                            repaired_final_sql,
                            trace=trace,
                            dataset_name=dataset_meta.get("dataset_name", ""),
                        )
                        final_sql = repaired_final_sql
                        review = repair_review
                        repair_succeeded = True
                        self._append_trace(
                            trace,
                            "pipeline.execute_sql.repaired",
                            "info",
                            dataset_id=dataset_id,
                            dataset_name=dataset_meta.get("dataset_name"),
                            sql=self._truncate_text(final_sql, 12000),
                            notes=repair_result.get("notes", ""),
                        )
                        steps.append(
                            {
                                "title": "SQL 自动修复",
                                "duration": round((time.time() - repair_started) * 1000, 2),
                                "status": "success",
                            }
                        )
                    except Exception as repair_error:
                        self._append_trace(
                            trace,
                            "pipeline.execute_sql.repair_failed",
                            "error",
                            dataset_id=dataset_id,
                            dataset_name=dataset_meta.get("dataset_name"),
                            error=str(repair_error),
                            traceback=traceback.format_exc(),
                        )
                        steps.append(
                            {
                                "title": "SQL 自动修复",
                                "duration": round((time.time() - repair_started) * 1000, 2),
                                "status": "warning",
                            }
                        )
                if not repair_succeeded:
                    steps.append(
                        {
                            "title": "系统执行 SQL",
                            "duration": round((time.time() - step_started) * 1000, 2),
                            "status": "warning",
                        }
                    )
                    dataset_results.append(
                        self._build_graceful_dataset_result(
                            question=question,
                            context=context,
                            review=review,
                            result={"columns": [], "rows": [], "row_count": 0},
                            sql_text=final_sql,
                        )
                    )
                    continue
            steps.append(
                {
                    "title": "系统执行 SQL",
                    "duration": round((time.time() - step_started) * 1000, 2),
                    "status": "success",
                }
            )

            step_started = time.time()
            analysis_text = self._agent4_analysis(question, context, review, result, trace=trace)
            report_spec = build_report_spec(
                question=question,
                dataset=context["dataset"],
                rows=result.get("rows") or [],
                columns=result.get("columns") or [],
                report_config=report_config,
                sql=final_sql,
                review=review,
                resolved_entities=context.get("resolved_entities"),
            )
            self._append_trace(
                trace,
                "pipeline.agent4_result",
                "info",
                dataset_id=dataset_id,
                dataset_name=dataset_meta.get("dataset_name"),
                analysis_preview=self._truncate_text(analysis_text, 4000),
                report_spec_mode=report_spec.get("analysisMode"),
            )
            steps.append(
                {
                    "title": "Agent4 业务解读",
                    "duration": round((time.time() - step_started) * 1000, 2),
                    "status": "success",
                }
            )

            dataset_results.append(
                {
                    "dataset_id": context["dataset"]["id"],
                    "dataset_code": context["dataset"]["dataset_code"],
                    "dataset_name": context["dataset"]["dataset_name"],
                    "source_id": context["dataset"]["source_id"],
                    "report_config": report_config,
                    "report_config_source": report_config_source,
                    "resolved_entities": context.get("resolved_entities"),
                    "query_intent": context.get("query_intent") or {},
                    "agent3_review": review,
                    "columns": result["columns"],
                    "rows": result["rows"],
                    "row_count": result["row_count"],
                    "report_spec": report_spec,
                    "report_debug": {
                        "dataset_id": context["dataset"]["id"],
                        "dataset_name": context["dataset"]["dataset_name"],
                        "report_config_source": report_config_source,
                        "scene": (report_spec.get("debug") or {}).get("scene"),
                        "contract": (report_spec.get("debug") or {}).get("contract"),
                        "layoutTemplate": report_spec.get("layoutTemplate"),
                        "analysisMode": report_spec.get("analysisMode"),
                    },
                    "analysis": analysis_text,
                    "sql": final_sql,
                }
            )

        primary = dataset_results[0]
        display_title = self._build_display_title(question, primary)
        combined_analysis = "\n\n---\n\n".join(
            [
                f"## {item['dataset_name']}\n\n{item['analysis']}"
                for item in dataset_results
                if item.get("analysis")
            ]
        )
        return {
            "question": question,
            "display_title": display_title,
            "route": route,
            "confidence": self._build_confidence_payload(route, dataset_results),
            "dataset_results": dataset_results,
            "report_configs": {
                str(item.get("dataset_id")): item.get("report_config")
                for item in dataset_results
                if item.get("dataset_id") is not None and item.get("report_config")
            },
            "report_config": primary.get("report_config"),
            "report_spec": primary.get("report_spec"),
            "report_debug": primary.get("report_debug"),
            "data_source": primary["dataset_name"] if len(dataset_results) == 1 else f"跨 {len(dataset_results)} 个数据集",
            "sql": primary["sql"],
            "columns": primary["columns"],
            "rows": primary["rows"],
            "row_count": primary["row_count"],
            "analysis": combined_analysis or primary["analysis"],
            "steps": steps,
            "requires_confirmation": False,
            "total_duration": round(time.time() - started, 2),
        }

    @staticmethod
    def _filter_route_by_allowed_datasets(route: Dict[str, Any], allowed_set: set[int]) -> Dict[str, Any]:
        return ask_engine_utils._filter_route_by_allowed_datasets(route, allowed_set)

    def ask(
        self,
        question: str,
        preferred_dataset_ids: Optional[List[int]] = None,
        allowed_dataset_ids: Optional[List[int]] = None,
        live_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        model_id: Optional[int] = None,
        session_id: str = "",
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        current_user: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        question = (question or "").strip()
        conversation_session_id = str(session_id or "").strip()
        started = time.time()
        steps: List[Dict[str, Any]] = []
        self._preferred_model_id = model_id
        trace = self._new_trace(question, "ask", live_callback=live_callback)
        memory_history = conversation_history or self.short_term_memory.get(conversation_session_id)
        effective_question = self.short_term_memory.resolve_followup(question, memory_history) or question
        org_subject_resolution = None
        if self._looks_like_org_subject_question(question):
            org_subject_resolution = self._agent1_resolve_org_subject(
                question,
                conversation_context=memory_history,
                trace=trace,
            )
            rewritten_question = str((org_subject_resolution or {}).get("rewritten_question") or "").strip()
            if rewritten_question:
                effective_question = rewritten_question
                self._append_trace(
                    trace,
                    "agent1.org_subject_resolved",
                    "info",
                    original_question=question,
                    rewritten_question=rewritten_question,
                    subject_name=(org_subject_resolution or {}).get("subject_name"),
                    subject_level=(org_subject_resolution or {}).get("subject_level"),
                    confidence=(org_subject_resolution or {}).get("confidence"),
                )
        explicit_dataset_ids = self._explicit_dataset_ids_from_question(
            question,
            allowed_dataset_ids=allowed_dataset_ids,
        )
        explicit_dataset_followup_reset = False
        if len(explicit_dataset_ids) == 1 and effective_question != question:
            # 当前追问已明确点名唯一数据集/事业部时，不能把上一轮的事业部文本拼进来。
            # 否则会形成"消费者事业部 + 商用事业部"混合问题，Agent1 会误判为需要确认。
            # 但如果 effective_question 是主体纠正的结果（org_subject_resolution 有 rewritten_question），
            # 说明是"商用事业部丁杰"→"丁杰"这类纠正，不是追问拼接，不应重置。
            org_rewritten = str((org_subject_resolution or {}).get("rewritten_question") or "").strip()
            if org_rewritten and effective_question == org_rewritten:
                # 主体纠正场景，保留 effective_question
                pass
            else:
                effective_question = question
                explicit_dataset_followup_reset = True
        explicit_followup_org_target = self._extract_followup_org_target(question)
        if explicit_followup_org_target and effective_question != question:
            # 追问里已经明确给出了新的组织对象时，不要再把上一轮对象正文一并下传。
            # 否则 SQL 生成阶段容易继续沿用上一轮对象，只把本轮对象当作补充说明。
            effective_question = (
                str((org_subject_resolution or {}).get("rewritten_question") or "").strip()
                or question
            )
        followup_dataset_hint = self._followup_dataset_hint_from_memory(
            question,
            memory_history,
            allowed_dataset_ids=allowed_dataset_ids,
        )
        followup_hint_locked = bool(followup_dataset_hint)
        if followup_dataset_hint and not preferred_dataset_ids:
            preferred_dataset_ids = followup_dataset_hint
        # 去掉题干前缀的序号，例如 "[ 4] xxx"、"4. xxx"、"第4题 xxx"
        effective_question = re.sub(r"^(?:\[\s*\d+\s*\]|\d+[.．、]\s*|第\s*\d+\s*[题问]\s*)", "", effective_question).strip()
        self._append_trace(
            trace,
            "request.received",
            "info",
            question=question,
            effective_question=effective_question,
            session_id=conversation_session_id,
            memory_rounds=len(memory_history),
            explicit_dataset_ids=explicit_dataset_ids,
            explicit_dataset_followup_reset=explicit_dataset_followup_reset,
            followup_dataset_hint=followup_dataset_hint,
            preferred_dataset_ids=preferred_dataset_ids or [],
            allowed_dataset_ids=allowed_dataset_ids or [],
            llm_model=self._llm_model or "",
            llm_base_url=str(getattr(self._llm_client, "base_url", "") or ""),
        )
        if not question:
            result = {"error": "Question cannot be empty."}
            self._flush_trace(trace, result)
            return result
        if not self.repository.is_ready():
            try:
                self.repository.ensure_schema()
            except BookshelfConfigurationError as exc:
                result = {"error": str(exc)}
                self._append_trace(trace, "request.schema_check", "error", error=str(exc))
                self._flush_trace(trace, result)
                return result
            if not self.repository.is_ready():
                result = {
                    "error": (
                        "Bookshelf metadata tables are not ready. "
                        "Please run backend/migrations/20260330_bookshelf_schema.sql first."
                    )
                }
                self._append_trace(trace, "request.schema_check", "error", error=result["error"])
                self._flush_trace(trace, result)
                return result

        try:
            step_started = time.time()
            allowed_set = {int(item) for item in allowed_dataset_ids} if allowed_dataset_ids is not None else None
            if preferred_dataset_ids and self._preferred_dataset_conflicts_with_question(
                question,
                preferred_dataset_ids,
                allowed_dataset_ids,
            ):
                if followup_hint_locked and self._should_keep_followup_dataset_hint(
                    question,
                    preferred_dataset_ids,
                    allowed_dataset_ids=allowed_dataset_ids,
                ):
                    self._append_trace(
                        trace,
                        "agent1.followup_dataset_hint_preserved",
                        "info",
                        reason="followup_target_resolved_inside_previous_dataset",
                        preferred_dataset_ids=preferred_dataset_ids or [],
                    )
                elif followup_hint_locked:
                    self._append_trace(
                        trace,
                        "agent1.followup_dataset_hint_released",
                        "info",
                        reason="current_question_explicitly_matches_another_dataset",
                        preferred_dataset_ids=preferred_dataset_ids or [],
                    )
                    preferred_dataset_ids = []
                else:
                    self._append_trace(
                        trace,
                        "agent1.preferred_dataset_released",
                        "info",
                        reason="current_question_explicitly_matches_another_dataset",
                        preferred_dataset_ids=preferred_dataset_ids or [],
                    )
                    preferred_dataset_ids = []

            if preferred_dataset_ids and not explicit_dataset_ids:
                matched_levels_for_preferred = self._matched_org_level_terms(question)
                if self._is_pure_generic_level_question(question, matched_levels_for_preferred):
                    catalog_for_preferred = self.repository.get_agent1_catalog()
                    if allowed_set is not None:
                        catalog_for_preferred = [
                            item for item in catalog_for_preferred
                            if int(item.get("id") or 0) in allowed_set
                        ]
                    supported_preferred_level_ids = set()
                    for dataset in catalog_for_preferred:
                        profile = get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
                        if any(
                            self._profile_supports_level(profile, term)
                            or self._dataset_node_index_supports_level(dataset, term)
                            or self._dataset_alias_supports_level(dataset, term)
                            for term in matched_levels_for_preferred
                        ):
                            supported_preferred_level_ids.add(int(dataset.get("id") or 0))
                    if len(supported_preferred_level_ids) >= 2:
                        self._append_trace(
                            trace,
                            "agent1.preferred_dataset_released",
                            "info",
                            reason="generic_level_ambiguous",
                            matched_levels=matched_levels_for_preferred,
                            candidate_dataset_ids=sorted(supported_preferred_level_ids),
                            preferred_dataset_ids=preferred_dataset_ids or [],
                        )
                        preferred_dataset_ids = []

            if preferred_dataset_ids and self._looks_like_org_subject_question(question):
                resolved_subject = org_subject_resolution or {}
                subject_name = str(resolved_subject.get("subject_name") or "").strip()
                if subject_name:
                    index_matches = self._node_index_matches(subject_name)
                    distinct_matches = self._dedupe_node_index_matches(index_matches)
                    candidate_dataset_ids = sorted({int(item.get("dataset_id") or 0) for item in distinct_matches if int(item.get("dataset_id") or 0) > 0})
                    if len(distinct_matches) >= 2:
                        self._append_trace(
                            trace,
                            "agent1.preferred_dataset_released",
                            "info",
                            reason="node_index_node_ambiguous",
                            subject_name=subject_name,
                            candidate_dataset_ids=candidate_dataset_ids,
                            preferred_dataset_ids=preferred_dataset_ids or [],
                        )
                        preferred_dataset_ids = []

            if preferred_dataset_ids:
                selected_dataset_ids = [int(item) for item in preferred_dataset_ids]
                if allowed_set is not None:
                    selected_dataset_ids = [item for item in selected_dataset_ids if item in allowed_set]
                if not selected_dataset_ids:
                    result = {
                        "error": "当前账号没有访问所选数据集的权限。请联系超级管理员调整数据权限。",
                        "diagnostics": {
                            "requested_dataset_ids": preferred_dataset_ids or [],
                            "allowed_dataset_ids": allowed_dataset_ids or [],
                            "user_org_codes": (current_user or {}).get("organization_codes") or [],
                            "user_org_node_ids": (current_user or {}).get("organization_node_ids") or [],
                        },
                    }
                    self._append_trace(trace, "data_permission.denied", "warning", preferred_dataset_ids=preferred_dataset_ids)
                    self._flush_trace(trace, result)
                    return result
                followup_target_guard = self._guard_followup_org_target_resolution(question, selected_dataset_ids)
                if followup_target_guard:
                    followup_target_guard["conversation_session_id"] = conversation_session_id
                    self._append_trace(
                        trace,
                        "agent1.followup_target_unresolved",
                        "warning",
                        selected_dataset_ids=selected_dataset_ids,
                        unresolved_target=followup_target_guard.get("diagnostics", {}).get("unresolved_followup_target"),
                        suggestions=followup_target_guard.get("diagnostics", {}).get("suggested_targets", []),
                    )
                route = {
                    "dataset_ids": selected_dataset_ids,
                    "intent": "detail",
                    "refined_query": effective_question,
                    "requires_confirmation": False,
                    "decision": "generate_sql",
                    "match_score": 100,
                    "route_margin": 100,
                    "confirmation_role": "boss",
                    "confirmation_question": "",
                    "confirmation_options": [],
                    "candidate_dataset_ids": selected_dataset_ids,
                    "preferred_dataset_override": True,
                    "matched_sample_id": None,
                    "matched_sample_sql": "",
                    "split_queries": [
                        {"dataset_id": item, "sub_query": effective_question}
                        for item in selected_dataset_ids
                    ],
                }
                self._append_trace(trace, "agent1.preferred_dataset_bypass", "info", route=route)
            else:
                # 主体纠正后 effective_question 已是 "丁杰的业绩"，
                # 路由层应基于纠正后的问题走，避免再用原始 "商用事业部丁杰" 识别出事业部层级
                route_question = effective_question or question
                route = self.route_with_agent1(
                    route_question,
                    trace=trace,
                    conversation_context=memory_history,
                    allowed_dataset_ids=allowed_dataset_ids,
                    current_question=effective_question or question,
                )
                full_catalog = self.repository.get_agent1_catalog()
                self._append_trace(
                    trace,
                    "agent1.route_result",
                    "info",
                    route=route,
                    thought=self._build_route_thought(route, effective_question, full_catalog),
                )
            steps.append(
                {
                    "title": "Agent1 语义路由",
                    "duration": round((time.time() - step_started) * 1000, 2),
                    "status": "success",
                }
            )

            if allowed_set is not None:
                route = self._filter_route_by_allowed_datasets(route, allowed_set)
                # 权限过滤后只剩一个候选选项时，自动命中，不再要求确认
                if route.get("requires_confirmation"):
                    filtered_options = route.get("confirmation_options") or []
                    if len(filtered_options) == 1:
                        only_option = filtered_options[0]
                        route["dataset_ids"] = only_option.get("dataset_ids") or []
                        route["split_queries"] = [
                            {"dataset_id": ds_id, "sub_query": route.get("refined_query") or effective_question}
                            for ds_id in (only_option.get("dataset_ids") or [])
                        ]
                        route["requires_confirmation"] = False
                        route["decision"] = "generate_sql"
                        route["arbiter_reason"] = (route.get("arbiter_reason") or "") + ";single_allowed_option_after_filter"
                if not route.get("dataset_ids"):
                    result = {
                        "error": "当前账号没有可访问的数据集。请联系超级管理员调整数据权限。",
                        "diagnostics": {
                            "allowed_dataset_ids": allowed_dataset_ids or [],
                            "user_org_codes": (current_user or {}).get("organization_codes") or [],
                            "user_org_node_ids": (current_user or {}).get("organization_node_ids") or [],
                            "route_before_filter": route,
                        },
                    }
                    self._append_trace(trace, "data_permission.no_allowed_dataset", "warning", allowed_dataset_ids=allowed_dataset_ids or [])
                    self._flush_trace(trace, result)
                    return result

            if route.get("preferred_dataset_override") and route.get("requires_confirmation"):
                route["requires_confirmation"] = False
                route["decision"] = "generate_sql"
                route["confirmation_question"] = ""
                route["confirmation_options"] = []
                route["arbiter_reason"] = (route.get("arbiter_reason") or "") + ";preferred_dataset_override"
                self._append_trace(trace, "agent1.preferred_dataset_confirmation_bypassed", "info", route=route)

            if route.get("requires_confirmation"):
                confirmation_session_id = self._create_confirmation_session(
                    question=effective_question,
                    route=route,
                    conversation_session_id=conversation_session_id,
                )
                result = {
                    "question": question,
                    "effective_question": effective_question,
                    "requires_confirmation": True,
                    "confirmation_role": route.get("confirmation_role", "boss"),
                    "confirmation_question": route.get("confirmation_question"),
                    "confirmation_options": route.get("confirmation_options", []),
                    "session_id": confirmation_session_id,
                    "conversation_session_id": conversation_session_id,
                    "handoff_to": "boss",
                    "route": route,
                    "confidence": self._build_confidence_payload(route),
                    "steps": steps,
                    "sql": "",
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "analysis": "等待老板确认后继续执行。",
                    "total_duration": round(time.time() - started, 2),
                }
                self._append_trace(
                    trace,
                    "confirmation.created",
                    "info",
                    session_id=confirmation_session_id,
                    conversation_session_id=conversation_session_id,
                    confirmation_question=result["confirmation_question"],
                    confirmation_options=result["confirmation_options"],
                )
                self._flush_trace(trace, result)
                return result

            result = self._run_pipeline(effective_question, route, started, steps, trace=trace, current_user=current_user)
            result["question"] = question
            result["effective_question"] = effective_question
            result["conversation_session_id"] = conversation_session_id
            if conversation_session_id and not result.get("error"):
                self.short_term_memory.remember_result(conversation_session_id, question, route, result)
            self._flush_trace(trace, result)
            return result
        except (BookshelfConfigurationError, ValueError) as exc:
            result = {"error": str(exc)}
            self._append_trace(trace, "request.error", "error", error=str(exc), traceback=traceback.format_exc())
            self._flush_trace(trace, result)
            return result
        except Exception as exc:
            result = {"error": f"Four-agent ask failed: {exc}"}
            self._append_trace(trace, "request.error", "error", error=str(exc), traceback=traceback.format_exc())
            self._flush_trace(trace, result)
            return result

    def confirm_by_boss(
        self,
        session_id: str,
        selected_option: str,
        selected_dataset_ids: Optional[List[int]] = None,
        allowed_dataset_ids: Optional[List[int]] = None,
        option_id: str = "",
        live_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        current_user: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        started = time.time()
        steps: List[Dict[str, Any]] = []
        trace = self._new_trace(selected_option or session_id, "confirm_by_boss", live_callback=live_callback)
        self._append_trace(
            trace,
            "confirmation.received",
            "info",
            session_id=session_id,
            selected_option=selected_option,
            option_id=option_id,
            selected_dataset_ids=selected_dataset_ids or [],
            allowed_dataset_ids=allowed_dataset_ids or [],
        )
        self._cleanup_expired_sessions()

        if not session_id:
            result = {"error": "session_id is required."}
            self._flush_trace(trace, result)
            return result

        pending = self._pending_confirmations.get(session_id)
        if not pending:
            result = {"error": "Confirmation session not found or expired."}
            self._append_trace(trace, "confirmation.lookup", "error", error=result["error"])
            self._flush_trace(trace, result)
            return result

        question = pending["question"]
        route = dict(pending["route"])
        route["original_question"] = question
        allowed_set = {int(item) for item in allowed_dataset_ids} if allowed_dataset_ids is not None else None
        if allowed_set is not None:
            route = self._filter_route_by_allowed_datasets(route, allowed_set)
            if not route.get("dataset_ids") and not route.get("confirmation_options"):
                result = {"error": "当前账号没有访问该确认口径数据集的权限。请联系超级管理员调整数据权限。"}
                self._append_trace(trace, "data_permission.confirm_denied", "warning", allowed_dataset_ids=allowed_dataset_ids or [])
                self._flush_trace(trace, result)
                return result
        conversation_session_id = str(pending.get("conversation_session_id") or "").strip()
        confirmation_options = self._normalize_confirmation_options(
            route.get("confirmation_options"),
            route.get("candidate_dataset_ids", []) or route.get("dataset_ids", []),
        )
        selected_option_item = None
        if option_id:
            selected_option_item = next((item for item in confirmation_options if item.get("id") == option_id), None)

        if selected_dataset_ids:
            route["dataset_ids"] = [int(item) for item in selected_dataset_ids]
            if allowed_set is not None:
                route["dataset_ids"] = [item for item in route["dataset_ids"] if item in allowed_set]
                if not route["dataset_ids"]:
                    result = {"error": "当前账号没有访问所选数据集的权限。请联系超级管理员调整数据权限。"}
                    self._append_trace(trace, "data_permission.confirm_selected_denied", "warning", selected_dataset_ids=selected_dataset_ids)
                    self._flush_trace(trace, result)
                    return result
            # 通过 dataset_ids 确认时，也要找到对应的 option 以获取 resolved_subject_name
            if len(route["dataset_ids"]) == 1 and not selected_option_item:
                selected_dataset_id = route["dataset_ids"][0]
                selected_option_item = next(
                    (item for item in confirmation_options
                     if item.get("dataset_ids") and int(item["dataset_ids"][0]) == selected_dataset_id),
                    None,
                )
        else:
            option_text = (selected_option_item or {}).get("label") or (selected_option or "").strip()
            if selected_option_item and selected_option_item.get("dataset_ids"):
                route["dataset_ids"] = [int(item) for item in selected_option_item.get("dataset_ids", [])]
            if not option_text:
                result = {"error": "selected_option or option_id is required when selected_dataset_ids is empty."}
                self._append_trace(trace, "confirmation.validation", "error", error=result["error"])
                self._flush_trace(trace, result)
                return result
            candidate_ids = route.get("candidate_dataset_ids", []) or route.get("dataset_ids", [])
            if "跨数据集" in option_text and len(candidate_ids) >= 2:
                route["dataset_ids"] = candidate_ids[:2]
            else:
                route["dataset_ids"] = route.get("dataset_ids", []) or ([candidate_ids[0]] if candidate_ids else route.get("dataset_ids", []))

        # 单数据集确认时，将问题中其他数据集的维度别名映射到当前数据集
        if len(route.get("dataset_ids") or []) == 1:
            selected_dataset_id = int(route["dataset_ids"][0])
            selected_dataset = next(
                (ds for ds in self.repository.get_agent1_catalog() if int(ds.get("id") or 0) == selected_dataset_id),
                None,
            )
            if selected_dataset:
                base_query = str(route.get("refined_query") or question or "").strip()
                rewritten = self._map_dimension_aliases_for_dataset(base_query, selected_dataset)
                if rewritten != base_query:
                    route["refined_query"] = rewritten
                    route["dimension_alias_rewritten"] = True

        confirmation_notes = []
        if selected_option_item:
            resolved_subject_name = str(selected_option_item.get("resolved_subject_name") or "").strip()
            resolved_subject_level = str(selected_option_item.get("resolved_subject_level") or "").strip()
            if not resolved_subject_name:
                label_subject_name = self._extract_subject_from_confirmation_label(
                    (selected_option_item or {}).get("label") or selected_option or ""
                )
                selected_dataset_id = 0
                if len(route.get("dataset_ids") or []) == 1:
                    try:
                        selected_dataset_id = int((route.get("dataset_ids") or [0])[0] or 0)
                    except Exception:
                        selected_dataset_id = 0
                index_match = self._node_index_unique_match(
                    label_subject_name,
                    dataset_ids=[selected_dataset_id] if selected_dataset_id else None,
                ) if label_subject_name else None
                if index_match:
                    resolved_subject_name = str(index_match.get("node_name") or "").strip()
                    resolved_subject_level = str(index_match.get("node_level") or "").strip()
                elif label_subject_name:
                    resolved_subject_name = label_subject_name
            if resolved_subject_name:
                route["resolved_subject_name"] = resolved_subject_name
                if resolved_subject_level:
                    route["resolved_subject_level"] = resolved_subject_level
                base_query = str(route.get("refined_query") or question or "").strip()
                original_subject_name = str(route.get("route_subject_name") or route.get("matched_alias") or "").strip()
                if not original_subject_name:
                    org_subject_resolution = self._agent1_resolve_org_subject(
                        question,
                        conversation_context=[],
                    ) or {}
                    original_subject_name = str(org_subject_resolution.get("subject_name") or "").strip()
                if base_query:
                    if original_subject_name and original_subject_name in base_query:
                        route["refined_query"] = base_query.replace(original_subject_name, resolved_subject_name)
                    elif resolved_subject_name not in base_query:
                        route["refined_query"] = f"{resolved_subject_name}的业绩"
                route["refined_query"] = re.sub(
                    r"(城市分公司)分公司|(代表处)代表处|(业务部)业务部|(分公司)分公司",
                    lambda m: next(group for group in m.groups() if group),
                    str(route.get("refined_query") or "").strip(),
                )
                # 清理确认后 refined_query 中残留的口语词，避免 SQL 生成被干扰
                route["refined_query"] = self._clean_org_subject_candidate(
                    str(route.get("refined_query") or "").strip()
                )
                route["refined_query"] = re.sub(
                    r"(城市分公司)分公司|(代表处)代表处|(业务部)业务部|(分公司)分公司",
                    lambda m: next(group for group in m.groups() if group),
                    str(route.get("refined_query") or "").strip(),
                )
                confirmation_notes.append(f"确认组织节点：{resolved_subject_name}")
            resolved_members = [str(item).strip() for item in (selected_option_item.get("resolved_members") or []) if str(item).strip()]
            if resolved_members:
                route["resolved_members"] = resolved_members
                confirmation_notes.append(f"确认成员集合：{'、'.join(resolved_members)}")
            if selected_option_item.get("resolved_dimension"):
                route["resolved_dimension"] = str(selected_option_item.get("resolved_dimension") or "").strip()
            if selected_option_item.get("matched_alias"):
                route["matched_alias"] = str(selected_option_item.get("matched_alias") or "").strip()
            if selected_option_item.get("scope_mode"):
                route["scope_mode"] = str(selected_option_item.get("scope_mode") or "aggregate")
                confirmation_notes.append(
                    "输出方式：成员分别对比" if route["scope_mode"] == "compare" else "输出方式：先汇总后分析"
                )
            if selected_option_item.get("confirmation_type"):
                route["confirmation_type"] = str(selected_option_item.get("confirmation_type") or "").strip()

        if confirmation_notes:
            base_query = str(route.get("refined_query") or question or "").strip()
            route["refined_query"] = (base_query + "\n补充确认：" + "；".join(confirmation_notes)).strip()

        if conversation_session_id and selected_option_item:
            self.short_term_memory.remember_confirmation(
                conversation_session_id,
                question,
                route,
                selected_option_item,
            )

        route["requires_confirmation"] = False
        route["decision"] = "generate_sql"
        route["boss_confirmation"] = {
            "selected_option": (selected_option_item or {}).get("label") or selected_option or "",
            "selected_option_id": (selected_option_item or {}).get("id") or option_id or "",
            "selected_dataset_ids": route.get("dataset_ids", []),
            "confirmed_at": int(time.time()),
        }
        self._append_trace(trace, "confirmation.resolved", "info", route=route)

        steps.append(
            {
                "title": "老板确认口径",
                "duration": 0,
                "status": "success",
                "message": selected_option or "",
            }
        )

        result = self._run_pipeline(question, route, started, steps, trace=trace, current_user=current_user)
        result["session_id"] = session_id
        result["conversation_session_id"] = conversation_session_id
        if conversation_session_id and not result.get("error"):
            self.short_term_memory.remember_result(conversation_session_id, question, route, result)
        self._pending_confirmations.pop(session_id, None)
        self._flush_trace(trace, result)
        return result


four_agent_ask_service = FourAgentAskService()
