import json
import logging
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
        self._llm_client: Optional[OpenAI] = None
        self._llm_model: Optional[str] = None
        self._preferred_model_id: Optional[int] = None
        self._pending_confirmations: Dict[str, Dict[str, Any]] = {}
        self._pending_ttl_seconds = 30 * 60
        self.short_term_memory = ShortTermMemoryStore(max_rounds=8)
        self.disambiguation_arbiter = DisambiguationArbiter()
        self.organization_route_resolver = OrganizationRouteResolver()
        self._trace_file_path = os.path.join(CURRENT_DIR, "logs", "smartask_trace.jsonl")
        self._trace_logger = self._build_trace_logger()
        self._load_llm()

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
        text = str(value or "")
        if len(text) <= 8:
            return "***" if text else ""
        return f"{text[:4]}***{text[-4:]}"

    @staticmethod
    def _truncate_text(value: Any, limit: int = 4000) -> str:
        text = str(value or "")
        if len(text) <= limit:
            return text
        return text[:limit] + f"\n...[truncated {len(text) - limit} chars]"

    @staticmethod
    def _stream_preview(value: Any, limit: int = 1400) -> str:
        text = str(value or "").strip()
        if len(text) <= limit:
            return text
        return "..." + text[-limit:]

    def _new_trace(
        self,
        question: str,
        entry: str,
        live_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        return {
            "trace_id": str(uuid4()),
            "entry": entry,
            "question": question,
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "model": self._llm_model or "",
            "base_url": getattr(self._llm_client, "base_url", "") if self._llm_client else "",
            "events": [],
            "_live_callback": live_callback,
        }

    def _write_trace_line(self, payload: Dict[str, Any]) -> None:
        try:
            os.makedirs(os.path.dirname(self._trace_file_path), exist_ok=True)
            with open(self._trace_file_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            pass

    @staticmethod
    def _build_trace_snapshot(trace: Dict[str, Any], include_result: bool = False) -> Dict[str, Any]:
        snapshot = {
            key: value
            for key, value in trace.items()
            if not str(key).startswith("_") and (include_result or key != "result")
        }
        if not include_result:
            snapshot.pop("result", None)
        return snapshot

    def _emit_live_trace(self, trace: Optional[Dict[str, Any]], payload: Dict[str, Any]) -> None:
        if not trace:
            return
        callback = trace.get("_live_callback")
        if not callback:
            return
        try:
            callback(payload)
        except Exception:
            pass

    def _append_trace(self, trace: Optional[Dict[str, Any]], stage: str, status: str = "info", **payload: Any) -> None:
        if not trace:
            return
        event = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "stage": stage,
            "status": status,
        }
        event.update(payload)
        trace.setdefault("events", []).append(event)
        self._write_trace_line(
            {
                "type": "event",
                "trace_id": trace.get("trace_id"),
                "entry": trace.get("entry"),
                "question": trace.get("question"),
                "model": trace.get("model"),
                "base_url": trace.get("base_url"),
                "event": event,
            }
        )
        self._emit_live_trace(
            trace,
            {
                "type": "trace",
                "trace_id": trace.get("trace_id"),
                "entry": trace.get("entry"),
                "question": trace.get("question"),
                "model": trace.get("model"),
                "base_url": trace.get("base_url"),
                "event": event,
            },
        )

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
        if not trace or (not delta_text and not reasoning_delta):
            return
        event = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "stage": stage or "llm.call",
            "status": "delta",
            "agent": agent_name,
            "duration_seconds": round(time.time() - started, 2),
            "delta_kind": delta_kind or "content",
        }
        if delta_text:
            event["delta_text"] = self._truncate_text(delta_text, 800)
            event["stream_text"] = self._stream_preview(stream_text or delta_text)
        if reasoning_delta:
            event["reasoning_delta"] = self._truncate_text(reasoning_delta, 800)
            event["reasoning_text"] = self._stream_preview(reasoning_text or reasoning_delta)
        trace.setdefault("events", []).append(event)
        self._emit_live_trace(
            trace,
            {
                "type": "trace",
                "trace_id": trace.get("trace_id"),
                "entry": trace.get("entry"),
                "question": trace.get("question"),
                "model": trace.get("model"),
                "base_url": trace.get("base_url"),
                "event": event,
            },
        )

    def _stream_delta_value_to_text(self, value: Any) -> str:
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

    def _extract_stream_delta(self, delta_obj: Any) -> Tuple[str, str]:
        content_delta = self._stream_delta_value_to_text(getattr(delta_obj, "content", ""))
        reasoning_delta = ""
        reasoning_keys = ("reasoning_content", "reasoning", "reasoning_text")

        for key in reasoning_keys:
            reasoning_delta = self._stream_delta_value_to_text(getattr(delta_obj, key, ""))
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
                    reasoning_delta = self._stream_delta_value_to_text(source.get(key))
                    if reasoning_delta:
                        break
                if reasoning_delta:
                    break

        return content_delta, reasoning_delta

    def _flush_trace(self, trace: Optional[Dict[str, Any]], result: Optional[Dict[str, Any]] = None) -> None:
        if not trace:
            return
        if result is not None:
            trace["result"] = result
        summary_payload = {"type": "summary", **self._build_trace_snapshot(trace, include_result=True)}
        self._write_trace_line(summary_payload)
        self._emit_live_trace(trace, summary_payload)

    def _load_llm(self):
        config = get_default_ai_model()
        if not config:
            self._llm_client = None
            self._llm_model = None
            return
        self._activate_llm(config)

    def _activate_llm(self, config: Dict[str, Any]) -> None:
        self._llm_model = config.get("model")
        self._llm_client = OpenAI(
            api_key=config.get("api_key", ""),
            base_url=config.get("base_url", "https://api.openai.com/v1"),
        )

    def _candidate_llm_configs(self, preferred_model_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Build ordered candidate list. If preferred_model_id is given, put that model first."""
        candidates: List[Dict[str, Any]] = []
        seen = set()

        # If a specific model is requested, put it first
        if preferred_model_id is not None:
            for item in get_ai_models():
                if item.get("id") == preferred_model_id and item.get("is_active"):
                    config = dict(item)
                    config["api_key"] = decode_secret(config.pop("api_key_b64", ""))
                    signature = (
                        str(config.get("model") or ""),
                        str(config.get("base_url") or ""),
                        str(config.get("api_key") or ""),
                    )
                    seen.add(signature)
                    candidates.append(config)
                    break

        # Then add default model
        default_config = get_default_ai_model()
        if default_config:
            signature = (
                str(default_config.get("model") or ""),
                str(default_config.get("base_url") or ""),
                str(default_config.get("api_key") or ""),
            )
            if signature not in seen:
                seen.add(signature)
                candidates.append(default_config)

        # Then add remaining active models
        for item in get_ai_models():
            if not item.get("is_active"):
                continue
            config = dict(item)
            config["api_key"] = decode_secret(config.pop("api_key_b64", ""))
            signature = (
                str(config.get("model") or ""),
                str(config.get("base_url") or ""),
                str(config.get("api_key") or ""),
            )
            if signature in seen:
                continue
            seen.add(signature)
            candidates.append(config)

        return candidates

    @staticmethod
    def _should_retry_with_another_model(exc: Exception) -> bool:
        return exc.__class__.__name__ in {
            "AuthenticationError",
            "PermissionDeniedError",
            "APITimeoutError",
            "APIConnectionError",
            "InternalServerError",
            "RateLimitError",
        }

    @staticmethod
    def _safe_dict(value: Any) -> Dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _get_lld_content(self, context: Dict[str, Any]) -> str:
        lld_document = self._safe_dict(context.get("lld_document"))
        return str(lld_document.get("content") or "")

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _parse_cn_int(value: Any, default: int = 0) -> int:
        text = str(value or "").strip()
        if not text:
            return default
        if text.isdigit():
            return int(text)
        digits = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
        if text == "十":
            return 10
        if "十" in text:
            left, _, right = text.partition("十")
            tens = digits.get(left, 1 if not left else 0)
            ones = digits.get(right, 0)
            return tens * 10 + ones if tens else default
        return digits.get(text, default)

    def _resolve_query_intent(self, question: str, context: Dict[str, Any]) -> Dict[str, Any]:
        config = self._safe_dict(context.get("report_config")) or report_config_store.get_default_config()
        policies = self._safe_dict(config.get("intentPolicies"))
        ranking_policy = self._safe_dict(policies.get("ranking"))
        text = str(question or "").replace("\n", " ").strip()
        intent = {
            "intent": "unknown",
            "source": "report_config.intentPolicies",
            "target_level": "",
            "top_n": None,
            "sort_metric_key": "",
            "sort_metric_column": "",
            "direction": "",
            "output_mode": "",
            "matched_triggers": [],
        }
        if not text or ranking_policy.get("enabled") is False:
            return intent

        triggers = [str(item) for item in (ranking_policy.get("triggers") or []) if str(item).strip()]

        def trigger_matched(item: str) -> bool:
            if item in {"前", "后"}:
                return bool(re.search(rf"{re.escape(item)}\s*(?:\d+|[一二两三四五六七八九十]+)", text))
            if item.lower() == "top":
                return bool(re.search(r"\btop\s*(?:\d+|[一二两三四五六七八九十]+)?", text, flags=re.I))
            return item.lower() in text.lower()

        matched_triggers = [item for item in triggers if item and trigger_matched(item)]
        if not matched_triggers:
            return intent

        max_top_n = self._safe_int(ranking_policy.get("maxTopN"), 20)
        default_top_n = self._safe_int(ranking_policy.get("defaultTopN"), 3)
        rank_match = re.search(r"(?:Top|TOP|top|前|后|倒数)\s*(\d+|[一二两三四五六七八九十]+)", text)
        top_n = self._parse_cn_int(rank_match.group(1) if rank_match else "", default_top_n)
        top_n = max(1, min(max_top_n, top_n))

        negative_triggers = [str(item) for item in (ranking_policy.get("negativeTriggers") or []) if str(item).strip()]
        direction = "asc" if any(item in text for item in negative_triggers) else str(ranking_policy.get("defaultDirection") or "desc")
        if direction not in {"asc", "desc"}:
            direction = "desc"

        target_level = ""
        aliases = self._safe_dict(ranking_policy.get("targetLevelAliases"))
        level_candidates = []
        for level, level_aliases in aliases.items():
            candidates = [str(level)] + [str(item) for item in (level_aliases or [])]
            if str(level) == "城市公司":
                candidates.append("城市分公司")
            for candidate in candidates:
                if candidate:
                    level_candidates.append((candidate, str(level)))
        for candidate, level in sorted(level_candidates, key=lambda item: len(item[0]), reverse=True):
            if candidate in text:
                target_level = level
                break
        if not target_level:
            if "城市分公司" in text or "城市公司" in text:
                target_level = "城市公司"
            for dimension in config.get("analysisDimensions") or []:
                for level in dimension.get("path") or []:
                    if target_level:
                        break
                    if level and str(level) in text:
                        target_level = str(level)
                        break
                if target_level:
                    break

        metrics = [item for item in (config.get("metrics") or []) if isinstance(item, dict)]
        metric = next(
            (
                item for item in metrics
                if any(str(item.get(key) or "") and str(item.get(key) or "") in text for key in ("key", "label", "column"))
            ),
            None,
        )
        if not metric:
            default_metric_key = str(ranking_policy.get("defaultMetricKey") or "")
            metric = next((item for item in metrics if str(item.get("key") or "") == default_metric_key), None)
        metric = metric or {}

        intent.update({
            "intent": "ranking",
            "target_level": target_level,
            "top_n": top_n,
            "sort_metric_key": metric.get("key") or "",
            "sort_metric_column": metric.get("column") or metric.get("label") or "",
            "direction": direction,
            "output_mode": ranking_policy.get("outputMode") or "topn_only",
            "matched_triggers": matched_triggers,
        })
        return intent

    @staticmethod
    def _normalize_prompt_items(items: Any) -> List[Dict[str, Any]]:
        return [item for item in (items or []) if isinstance(item, dict)]

    @staticmethod
    def _is_read_only_sql(sql_text: str) -> bool:
        normalized = re.sub(r"/\*.*?\*/", " ", str(sql_text or ""), flags=re.S)
        normalized = re.sub(r"--.*?$", " ", normalized, flags=re.M).strip().lower()
        if not normalized:
          return False
        if not (normalized.startswith("select") or normalized.startswith("with")):
          return False
        blocked = [
            " insert ", " update ", " delete ", " drop ", " truncate ", " alter ",
            " create ", " replace ", " grant ", " revoke ", " merge ", " call ",
        ]
        padded = f" {normalized} "
        return not any(token in padded for token in blocked)

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
        option = {
            "id": option_id,
            "label": label,
            "description": description,
            "dataset_ids": [int(item) for item in (dataset_ids or []) if item is not None],
            "option_type": option_type,
        }
        if isinstance(extra, dict):
            for key, value in extra.items():
                if key in option or value is None:
                    continue
                option[key] = value
        return option

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
        if value is None:
            return None
        if isinstance(value, (int, float)):
            if value != value:
                return None
            return float(value)
        text = str(value).strip()
        if not text:
            return None
        cleaned = re.sub(r"[^0-9.\-]", "", text)
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None

    @staticmethod
    def _format_metric(value: Optional[float], suffix: str = "") -> str:
        if value is None:
            return "-"
        if not suffix:
            abs_value = abs(value)
            if abs_value < 10000:
                if value == int(value):
                    return str(int(value))
                return f"{value:.2f}".rstrip("0").rstrip(".")
            if abs_value < 1000000:
                return f"{value / 10000:.1f}万"
            if abs_value < 100000000:
                return f"{round(value / 10000)}万"
            return f"{value / 100000000:.2f}亿"
        if value == int(value):
            return f"{int(value):,}{suffix}"
        return f"{value:.2f}{suffix}"

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
    ) -> str:
        if not isinstance(rows, list) or not rows:
            return ""
        if not isinstance(columns, list):
            columns = []

        config = report_config or report_config_store.get_default_config()
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
        is_comparison = len(resolved_names) > 1 or bool(re.search(r"对比|比较|哪个|谁更|差异|分别|各自|和.+比|跟.+比|与.+比|\bvs\b", question or "", re.I))
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
        try:
            score = int(route.get("match_score") or (78 if candidate_count <= 1 else 64))
        except Exception:
            score = 78 if candidate_count <= 1 else 64

        if candidate_count > 1:
            score -= min(12, (candidate_count - 1) * 6)
        route_margin = int(route.get("route_margin") or 0)
        if route_margin >= 20:
            score += 4
        elif candidate_count > 1 and route_margin <= 8:
            score -= 6
        if route.get("requires_confirmation"):
            score = min(score, 60)
        if route.get("preferred_dataset_override"):
            score = max(score, 72)

        score = max(0, min(100, score))
        level = "high" if score >= 82 else "medium" if score >= 65 else "low"
        label = "高" if score >= 82 else "中" if score >= 65 else "待确认"

        if route.get("requires_confirmation"):
            summary = "当前命中仍存在不确定性，已暂停并等待确认统计口径。"
        elif route.get("arbiter_reason") == "profile_scope_resolved":
            summary = "当前问题中的组织简称或合称已命中数据集画像，系统按画像映射的数据集执行。"
        elif route.get("arbiter_reason") == "explicit_dataset_alias":
            summary = "当前问题直接命中了数据集名称、业务域或已维护同义词。"
        elif route.get("arbiter_reason") == "organization_tree_name_resolved":
            summary = "当前问题命中了组织树节点，系统按该节点绑定的数据集执行。"
        elif score < 70:
            summary = "当前更像相似命中，系统不会把它当作确定命中直接下结论。"
        elif candidate_count > 1:
            summary = f"当前存在 {candidate_count} 个候选口径，后续执行会继续标注采用的数据范围。"
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
            "match_score": int(route.get("match_score") or 0),
            "route_margin": route_margin,
            "reason": route.get("arbiter_reason") or "",
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
        rule_based_sql = self._build_rule_based_sql(question, route, context)
        route_sample_sql = str(route.get("matched_sample_sql") or "").strip()
        route_sample_id = route.get("matched_sample_id")
        query_intent = self._safe_dict(context.get("query_intent"))
        original_question = str(context.get("original_question") or "")
        level_hint_text = "\n".join(item for item in [str(question or ""), original_question] if item)
        requested_city_level = (
            str(query_intent.get("target_level") or "") == "城市公司"
            or "城市公司" in level_hint_text
            or "城市分公司" in level_hint_text
        )

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
            asks_city_level = "层级='城市公司'" in compact_sql or '层级="城市公司"' in compact_sql
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
        return re.sub(r"[\s,，、/\\|()（）【】\[\]{}<>《》“”\"'：:；;.!！?？-]+", "", str(value or "")).lower()

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

    def _question_subject_names(self, question: str, context: Dict[str, Any]) -> List[str]:
        names = self._resolved_entity_names(context)
        dataset = self._safe_dict(context.get("dataset"))
        profile = get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
        if profile:
            semantic = resolve_member_mentions(question, profile)
            for name in semantic.get("all_members") or []:
                value = str(name or "").strip()
                if value and value not in names:
                    names.append(value)

        text = str(question or "").replace("\n", " ").strip()
        for match in re.findall(r"[\u4e00-\u9fa5A-Za-z0-9（）()]+?(?:代表处|分公司|业务部|事业部)", text):
            cleaned = match.strip("，,、 和与及的业绩情况表现整体")
            if re.search(r"^(?:三|四|五|六|七|八|九|十|两|\d+)(?:个|大)?", cleaned):
                continue
            if any(token in cleaned for token in ["哪些", "所有", "各", "每个", "业务线", "任务完成", "最好", "最高", "最低", "哪个"]):
                continue
            if cleaned and cleaned not in names:
                names.append(cleaned)

        person_patterns = [
            r"(?:帮我)?(?:看下|看一下|查一下|查询|分析一下|分析|看看|了解一下|了解|问下|问一下)\s*([\u4e00-\u9fa5]{2,4})(?:的)?(?:业绩|绩效|达成率|达成|开单|完成情况|完成|情况|表现)",
            r"(?:问的是|查询的是|看的是|主体是|节点是|人员是|业务员是|业务代表是)\s*([\u4e00-\u9fa5]{2,6})",
            r"([\u4e00-\u9fa5]{2,4})(?:的)?(?:业绩|绩效|达成率|开单|完成情况|表现)",
        ]
        for pattern in person_patterns:
            for match in re.findall(pattern, text):
                candidate = str(match or "").strip("，,、 的呢吗么吧")
                candidate = re.sub(r"^(看下|看一下|查一下|查询|分析一下|分析|看看|了解一下|了解|问下|问一下)", "", candidate).strip()
                if self._looks_like_noise_subject(candidate):
                    continue
                if candidate not in names:
                    names.append(candidate)
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
        self._load_llm()
        candidate_configs = self._candidate_llm_configs(preferred_model_id=self._preferred_model_id)
        if not candidate_configs:
            raise RuntimeError("Default AI model is not configured.")
        last_error: Optional[Exception] = None

        for index, config in enumerate(candidate_configs, start=1):
            self._activate_llm(config)
            started = time.time()
            self._append_trace(
                trace,
                stage or "llm.call",
                "request",
                agent=agent_name,
                provider="openai-compatible",
                model=self._llm_model,
                endpoint=f"{getattr(self._llm_client, 'base_url', '')}chat.completions.create",
                candidate_index=index,
                candidate_count=len(candidate_configs),
                max_tokens=max_tokens,
                system_prompt=self._truncate_text(system_prompt, 12000),
                user_prompt=self._truncate_text(user_prompt, 16000),
            )
            try:
                stream = self._llm_client.chat.completions.create(
                    model=self._llm_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                    max_tokens=max_tokens,
                    stream=True,
                    timeout=180,
                )
                chunks: List[str] = []
                reasoning_chunks: List[str] = []
                pending_delta = ""
                pending_reasoning = ""
                last_emit_at = time.time()
                last_reasoning_emit_at = time.time()
                for chunk in stream:
                    try:
                        delta_obj = chunk.choices[0].delta
                        delta, reasoning_delta = self._extract_stream_delta(delta_obj)
                    except Exception:
                        delta = ""
                        reasoning_delta = ""
                    if not delta and not reasoning_delta:
                        continue
                    now = time.time()
                    if delta:
                        chunks.append(delta)
                        pending_delta += delta
                    if reasoning_delta:
                        reasoning_chunks.append(reasoning_delta)
                        pending_reasoning += reasoning_delta
                    if pending_delta and (len(pending_delta) >= 24 or now - last_emit_at >= 0.35):
                        self._append_llm_delta(
                            trace,
                            stage or "llm.call",
                            agent_name,
                            pending_delta,
                            "".join(chunks),
                            started,
                        )
                        pending_delta = ""
                        last_emit_at = now
                    if pending_reasoning and (len(pending_reasoning) >= 24 or now - last_reasoning_emit_at >= 0.35):
                        self._append_llm_delta(
                            trace,
                            stage or "llm.call",
                            agent_name,
                            "",
                            "",
                            started,
                            reasoning_delta=pending_reasoning,
                            reasoning_text="".join(reasoning_chunks),
                            delta_kind="reasoning",
                        )
                        pending_reasoning = ""
                        last_reasoning_emit_at = now

                content = "".join(chunks).strip()
                if pending_delta:
                    self._append_llm_delta(
                        trace,
                        stage or "llm.call",
                        agent_name,
                        pending_delta,
                        content,
                        started,
                    )
                if pending_reasoning:
                    self._append_llm_delta(
                        trace,
                        stage or "llm.call",
                        agent_name,
                        "",
                        "",
                        started,
                        reasoning_delta=pending_reasoning,
                        reasoning_text="".join(reasoning_chunks),
                        delta_kind="reasoning",
                    )
                self._append_trace(
                    trace,
                    stage or "llm.call",
                    "response",
                    agent=agent_name,
                    duration_seconds=round(time.time() - started, 2),
                    response_text=self._truncate_text(content, 16000),
                )
                return content
            except Exception as exc:
                last_error = exc
                retryable = index < len(candidate_configs) and self._should_retry_with_another_model(exc)
                self._append_trace(
                    trace,
                    stage or "llm.call",
                    "retry" if retryable else "error",
                    agent=agent_name,
                    duration_seconds=round(time.time() - started, 2),
                    error=str(exc),
                    candidate_index=index,
                    candidate_count=len(candidate_configs),
                    retry_with_next_model=retryable,
                )
                if not retryable:
                    raise

        if last_error:
            raise last_error
        raise RuntimeError("No active AI model is available.")

    def _chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        fallback: Dict[str, Any],
        trace: Optional[Dict[str, Any]] = None,
        stage: str = "",
        agent_name: str = "",
    ) -> Dict[str, Any]:
        try:
            raw = self._chat(system_prompt, user_prompt, trace=trace, stage=stage, agent_name=agent_name)
            parsed = json.loads(_extract_json_block(raw))
            self._append_trace(
                trace,
                stage or "llm.call",
                "parsed",
                agent=agent_name,
                parsed_json=parsed,
            )
            return parsed
        except Exception as exc:
            self._append_trace(
                trace,
                stage or "llm.call",
                "fallback",
                agent=agent_name,
                error=str(exc),
                traceback=traceback.format_exc(),
                fallback=fallback,
            )
            return fallback

    def _get_agent_prompt(self, agent_no: int, fallback: str) -> str:
        agent = get_agent(agent_no)
        prompt = (agent or {}).get("system_prompt") or fallback
        knowledge = "\n".join(f"- {item}" for item in (agent or {}).get("knowledge_base", []))
        return f"{prompt}\n\n补充知识：\n{knowledge}".strip()

    def _build_report_config_prompt(self, context: Dict[str, Any]) -> str:
        config = self._safe_dict(context.get("report_config")) or report_config_store.get_default_config()
        if not config:
            return ""
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
            "dynamicPerformanceRule": "报告中的好/差节点必须基于本次结果动态分组；不要按固定阈值或固定 TopN 硬切。好/差两组不得重复；可比对象少于 2 个时不做横向对比。",
            "agentReportGuidance": config.get("agentReportGuidance", ""),
            "resolvedQuestionScope": context.get("resolved_entities") or {},
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    @staticmethod
    def _profile_catalog(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        catalog = []
        for level in profile.get("levels") or []:
            if not isinstance(level, dict):
                continue
            members = [str(item).strip() for item in (level.get("members") or []) if str(item).strip()]
            groups = []
            for group in level.get("groups") or []:
                if isinstance(group, dict):
                    groups.append(
                        {
                            "group_name": group.get("group_name"),
                            "aliases": group.get("aliases") or [],
                            "members": group.get("members") or [],
                        }
                    )
            catalog.append(
                {
                    "dimension_name": level.get("dimension_name"),
                    "aliases": level.get("aliases") or [],
                    "members": members[:80],
                    "groups": groups[:20],
                }
            )
        return catalog

    @staticmethod
    def _profile_member_map(profile: Dict[str, Any]) -> Dict[str, str]:
        member_map: Dict[str, str] = {}
        for level in profile.get("levels") or []:
            if not isinstance(level, dict):
                continue
            for member in level.get("members") or []:
                value = str(member or "").strip()
                if value:
                    member_map[value] = str(level.get("dimension_name") or "").strip()
        return member_map

    @staticmethod
    def _normalize_entity_resolution(
        raw: Dict[str, Any],
        fallback: Dict[str, Any],
        profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        member_map = FourAgentAskService._profile_member_map(profile)
        ordered_members: List[str] = []
        entities_by_dimension: Dict[str, Dict[str, Any]] = {}

        for entity in raw.get("entities") or []:
            if not isinstance(entity, dict):
                continue
            dimension_name = str(entity.get("dimension_name") or "").strip()
            for member in entity.get("members") or []:
                member_name = str(member or "").strip()
                if not member_name or member_name not in member_map:
                    continue
                resolved_dimension = dimension_name or member_map.get(member_name) or ""
                if member_name not in ordered_members:
                    ordered_members.append(member_name)
                bucket = entities_by_dimension.setdefault(
                    resolved_dimension,
                    {
                        "dimension_name": resolved_dimension,
                        "members": [],
                        "matched_phrase": str(entity.get("matched_phrase") or entity.get("matched_alias") or "").strip(),
                        "source": str(raw.get("source") or entity.get("source") or "llm_semantic"),
                    },
                )
                if member_name not in bucket["members"]:
                    bucket["members"].append(member_name)

        if not ordered_members:
            for member in fallback.get("all_members") or []:
                member_name = str(member or "").strip()
                if not member_name or member_name not in member_map or member_name in ordered_members:
                    continue
                ordered_members.append(member_name)
                dimension_name = member_map.get(member_name) or ""
                bucket = entities_by_dimension.setdefault(
                    dimension_name,
                    {
                        "dimension_name": dimension_name,
                        "members": [],
                        "matched_phrase": "",
                        "source": "profile_semantic",
                    },
                )
                bucket["members"].append(member_name)
        else:
            for member in fallback.get("all_members") or []:
                member_name = str(member or "").strip()
                if not member_name or member_name not in member_map or member_name in ordered_members:
                    continue
                ordered_members.append(member_name)
                dimension_name = member_map.get(member_name) or ""
                bucket = entities_by_dimension.setdefault(
                    dimension_name,
                    {
                        "dimension_name": dimension_name,
                        "members": [],
                        "matched_phrase": "",
                        "source": "profile_semantic",
                    },
                )
                bucket["members"].append(member_name)

        scope_mode = str(raw.get("scope_mode") or raw.get("intent") or fallback.get("scope_mode") or "").lower()
        if len(ordered_members) > 1:
            scope_mode = "compare"
        elif len(ordered_members) == 1 and scope_mode not in {"aggregate", "ranking"}:
            scope_mode = "single"
        elif not ordered_members:
            scope_mode = "unknown"

        confidence = raw.get("confidence", fallback.get("confidence", 0))
        try:
            confidence_value = float(confidence)
        except Exception:
            confidence_value = 0

        return {
            "intent": "compare" if scope_mode == "compare" else ("single" if scope_mode == "single" else str(raw.get("intent") or fallback.get("intent") or "unknown")),
            "scope_mode": scope_mode,
            "entities": list(entities_by_dimension.values()),
            "all_members": ordered_members,
            "confidence": confidence_value,
            "source": str(raw.get("source") or ("llm_semantic" if ordered_members else fallback.get("source") or "unknown")),
        }

    @staticmethod
    def _profile_scope_hint(question: str, profile: Dict[str, Any], fallback: Dict[str, Any]) -> bool:
        if fallback.get("all_members"):
            return True
        normalized_question = re.sub(r"\s+", "", str(question or ""))
        for level in profile.get("levels") or []:
            if not isinstance(level, dict):
                continue
            terms = [level.get("dimension_name"), *(level.get("aliases") or [])]
            for term in terms:
                if term and str(term) in normalized_question:
                    return True
        return False

    def _resolve_question_entities(
        self,
        question: str,
        context: Dict[str, Any],
        trace: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        dataset = self._safe_dict(context.get("dataset"))
        profile = get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
        if not profile:
            return {
                "intent": "unknown",
                "scope_mode": "unknown",
                "entities": [],
                "all_members": [],
                "confidence": 0,
                "source": "no_profile",
            }

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
5. 不确定时 entities 留空，不要硬猜。

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
  "confidence": 0.0
}}
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
        resolved = context.get("resolved_entities") if isinstance(context, dict) else {}
        if not isinstance(resolved, dict):
            return []
        names: List[str] = []
        for name in resolved.get("all_members") or []:
            value = str(name or "").strip()
            if value and value not in names:
                names.append(value)
        for entity in resolved.get("entities") or []:
            if not isinstance(entity, dict):
                continue
            for name in entity.get("members") or []:
                value = str(name or "").strip()
                if value and value not in names:
                    names.append(value)
        return names

    @staticmethod
    def _route_entity_resolution(route: Dict[str, Any]) -> Dict[str, Any]:
        members = []
        for name in route.get("resolved_members") or route.get("resolved_entities_preview") or []:
            value = str(name or "").strip()
            if value and value not in members:
                members.append(value)
        for mention in route.get("organization_mentions") or []:
            if not isinstance(mention, dict):
                continue
            value = str(mention.get("node_name") or "").strip()
            if value and value not in members:
                members.append(value)
        if not members:
            return {}
        scope_mode = str(route.get("scope_mode") or "").strip().lower()
        if scope_mode not in {"single", "compare", "aggregate", "ranking"}:
            scope_mode = "compare" if len(members) > 1 else "single"
        return {
            "intent": "compare" if scope_mode == "compare" else ("single" if scope_mode == "single" else scope_mode),
            "scope_mode": scope_mode,
            "entities": [
                {
                    "dimension_name": "组织树节点",
                    "members": members,
                    "matched_phrase": "、".join(members),
                    "source": "organization_tree_route",
                }
            ],
            "all_members": members,
            "confidence": 1.0,
            "source": "organization_tree_route",
        }

    @staticmethod
    def _tokenize(text: str) -> set:
        parts = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{1,4}", (text or "").lower())
        return {item for item in parts if item.strip()}

    @staticmethod
    def _normalize_compact_text(text: Any) -> str:
        return re.sub(r"\s+", "", str(text or "")).lower()

    @staticmethod
    def _normalize_known_sql_alias_typos(sql_text: str) -> str:
        sql = str(sql_text or "")
        sql = re.sub(r"条线[\s_-]*type\b", "条线类型", sql, flags=re.IGNORECASE)
        return sql

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
            "业务部",
            "行业业务部",
            "城市公司",
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
            "业务部",
            "行业业务部",
            "城市公司",
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

    def _dataset_alias_match_score(self, question: str, dataset: Dict[str, Any]) -> int:
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
        generic_aliases = {"业绩", "分析", "数据", "指标", "结果", "结果指标", "销售业绩"}
        score = 0
        for alias in alias_candidates:
            normalized_alias = self._normalize_compact_text(alias)
            if len(normalized_alias) < 2:
                continue
            if normalized_alias in generic_aliases:
                continue
            if normalized_alias in normalized_question:
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
                if term and term in normalized_question:
                    score = max(score, 90)
        profile = get_dataset_profile(dataset.get("dataset_code"), dataset.get("dataset_name"))
        profile_level_score = self._profile_level_alias_score(question, profile)
        if profile_level_score:
            score = max(score, profile_level_score)
        if profile:
            resolved_scope = resolve_member_mentions(question, profile)
            if resolved_scope.get("all_members"):
                score = max(score, 96 if len(resolved_scope.get("all_members") or []) > 1 else 92)
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
        schema_hit = 1 if any(token in dataset_tokens for token in ("日期", "时间", "金额", "分公司", "事业部", "代表处", "业务代表", "业务部", "城市公司", "区域")) else 0
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
        samples = context.get("golden_sql_samples", []) or []
        common_questions = context.get("common_questions", []) or []
        return {
            "golden_sql_count": len(samples),
            "top_sample_questions": [item.get("question", "") for item in samples[:3] if item.get("question")],
            "common_question_examples": [item.get("question_text", "") for item in common_questions[:3] if item.get("question_text")],
            "has_lld": bool(str((context.get("lld_document") or {}).get("content") or "").strip()),
            "schema_table_count": len(context.get("schema_definition", []) or []),
            "dictionary_count": len(context.get("data_dictionary", []) or []),
        }

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
        if len(members) <= 1:
            return False
        text = re.sub(r"\s+", "", str(question or ""))
        alias = re.sub(r"\s+", "", str(matched_alias or ""))
        if not alias:
            return False
        explicit_group_markers = ("三大", "3大", "三个", "各", "所有", "全部", "每个", "分别", "对比", "比较", "排名", "排行")
        intent_markers = ("业绩", "表现", "情况", "如何", "怎么样", "达成", "开单", "任务", "缺口", "对比", "比较", "排名", "排行")
        return any(marker in alias or marker in text for marker in explicit_group_markers) and any(
            marker in text for marker in intent_markers
        )

    def _detect_ambiguity(self, question: str, ranked_candidates: List[Tuple[Dict[str, Any], int]]) -> Optional[Dict[str, Any]]:
        if not ranked_candidates:
            return None

        candidate_ids = [item[0]["id"] for item in ranked_candidates[:3]]
        candidate_names = [item[0].get("dataset_name") or f"数据集 {item[0]['id']}" for item in ranked_candidates[:3]]
        ambiguous_terms = ["分公司", "组织", "代表处", "条线", "事业部", "区域", "部门", "团队"]
        if len(ranked_candidates) >= 2:
            top1_score = ranked_candidates[0][1]
            top2_score = ranked_candidates[1][1]
            if abs(top1_score - top2_score) <= 12 and top2_score >= 60:
                return {
                    "requires_confirmation": True,
                    "confirmation_role": "boss",
                    "confirmation_question": "请老板确认本次问数优先使用哪个数据集口径？",
                    "confirmation_options": [
                        f"{ranked_candidates[0][0]['dataset_name']}（优先）",
                        f"{ranked_candidates[1][0]['dataset_name']}",
                        "跨数据集汇总（拆分子任务）",
                    ],
                    "candidate_dataset_ids": candidate_ids,
                }

        if len(ranked_candidates) >= 2 and any(term in question for term in ambiguous_terms):
            return {
                "requires_confirmation": True,
                "confirmation_role": "boss",
                "confirmation_question": "请老板确认组织统计口径：",
                "confirmation_options": [
                    "仅按分公司字段统计（推荐）",
                    "按所有名称包含分公司的组织节点统计",
                    "两种口径同时输出对比",
                ],
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
            candidate_blocks.append(
                {
                    "dataset_id": dataset["id"],
                    "dataset_name": dataset.get("dataset_name"),
                    "business_domain": dataset.get("business_domain"),
                    "synonyms": dataset.get("synonyms", []),
                    "score_hint": score,
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
2. 如果多个数据集都能回答问题，但统计口径不同，必须 requires_confirmation=true。
3. refined_query 需要补齐时间范围、组织口径、统计对象，但不能虚构用户没有表达的事实。
4. 只有在数据集明显唯一且口径无歧义时，才能给出 direct_execute 或 generate_sql。

请输出 JSON：
{{
  "dataset_ids": [1],
  "intent": "summary|detail|confirm",
  "refined_query": "重写后的查询",
  "decision": "direct_execute|generate_sql|wait_boss_confirm",
  "match_score": 0,
  "requires_confirmation": false,
  "confirmation_role": "boss",
  "confirmation_question": "",
  "confirmation_options": [],
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
        full_catalog = self.repository.get_agent1_catalog()
        catalog = full_catalog
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
            )
            return org_route

        candidate_contexts: List[Tuple[Dict[str, Any], Dict[str, Any], int]] = []
        for dataset in catalog:
            context = self.repository.get_dataset_context(dataset["id"], question, top_k_samples=5)
            score = self._compute_dataset_match(question, dataset, context)
            candidate_contexts.append((dataset, context, score))

        candidate_contexts.sort(key=lambda item: item[2], reverse=True)
        ranked = [(item[0], item[2]) for item in candidate_contexts]
        best_dataset, best_context, best_score = candidate_contexts[0]
        runner_up_score = candidate_contexts[1][2] if len(candidate_contexts) > 1 else 0
        route_margin = best_score - runner_up_score
        best_alias_score = self._dataset_alias_match_score(question, best_dataset)
        runner_alias_score = (
            self._dataset_alias_match_score(question, candidate_contexts[1][0])
            if len(candidate_contexts) > 1
            else 0
        )
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
        direct_execute = (
            best_score >= 92
            and best_sample_score >= (70 if len(candidate_contexts) == 1 else 95)
            and route_margin >= 18
            and bool(best_sample.get("sql_text"))
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
        dataset_code = str(dataset.get("dataset_code") or dataset.get("code") or "")
        dataset_name = str(dataset.get("dataset_name") or dataset.get("name") or "")
        normalized_question = str(question or "").replace("\n", " ").strip()
        original_question = str(context.get("original_question") or "").replace("\n", " ").strip()
        if original_question and original_question not in normalized_question:
            normalized_question = f"{normalized_question} {original_question}".strip()
        is_consumer_dataset = (
            dataset_code in {"consumer_business_standard_v1", "public_feishu_tbl_xioafeizhe_609826"}
            or "消费者" in dataset_name
        )
        is_syyb_dataset = dataset_code in {"angel_business_2026", "angel_business_2026_phase1"} or dataset_name in {
            "商用事业部",
            "商用事业部（阶段一升级版）",
        }
        is_phase1_dataset = dataset_code == "angel_business_2026_phase1" or dataset_name == "商用事业部（阶段一升级版）"

        if is_consumer_dataset:
            return self._build_consumer_business_sql(normalized_question, context)

        if not is_syyb_dataset:
            return ""

        syyb_base_sql = self._build_syyb_base_sql(context)
        ranking_tokens = ["排名", "最低", "最高", "最好", "最差", "Top", "top", "前", "后"]
        has_ranking_intent = any(token in normalized_question for token in ranking_tokens)
        if is_phase1_dataset and has_ranking_intent:
            rank_match = re.search(r"(?:Top|TOP|top|前|后|倒数)\s*(\d+|[一二两三四五六七八九十]+)", normalized_question)
            configured_limit = self._parse_cn_int(rank_match.group(1) if rank_match else "", 0)
            default_rank_limit = 3 if any(token in normalized_question for token in ["Top", "top", "前", "后", "排名", "排行"]) else 1
            rank_limit = max(1, min(20, configured_limit or default_rank_limit))
            is_top_rank = any(token in normalized_question for token in ["最高", "最好", "Top", "top", "前"])
            order_direction = "DESC" if is_top_rank else "ASC"
            asks_grouped_rank = any(token in normalized_question for token in ["各", "每个", "分别", "各自", "按上级", "按代表处", "分组"])

            if "业务代表" in normalized_question or "业务员" in normalized_question:
                metric_column = "年度开单金额" if ("开单" in normalized_question or "金额" in normalized_question) else "达成率"
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
            if "代表处" in normalized_question:
                return f"""
WITH 汇总结果 AS (
{syyb_base_sql}
),
代表处分公司内排序 AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY 上级名称
            ORDER BY 达成率 {order_direction}, 剩余任务金额 DESC, 节点名称
        ) AS 分公司内排名
    FROM 汇总结果
    WHERE 层级 = '代表处'
)
SELECT *
FROM 代表处分公司内排序
WHERE 分公司内排名 <= {rank_limit}
ORDER BY 上级名称, 分公司内排名, 达成率 {order_direction}, 剩余任务金额 DESC, 节点名称
LIMIT 50
""".strip()
            if "分公司" in normalized_question:
                return f"""
WITH 汇总结果 AS (
{syyb_base_sql}
)
SELECT *
FROM 汇总结果
WHERE 层级 = '分公司'
ORDER BY 达成率 {order_direction}, 剩余任务金额 DESC, 节点名称
LIMIT 20
""".strip()

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

        entity_names = self._resolved_entity_names(context)
        if not entity_names:
            profile = get_dataset_profile(dataset_code, dataset_name)
            if profile:
                semantic_fallback = resolve_member_mentions(normalized_question, profile)
                entity_names = [str(item).strip() for item in (semantic_fallback.get("all_members") or []) if str(item).strip()]
        if not entity_names:
            for match in re.findall(r"[\u4e00-\u9fa5A-Za-z0-9（）()]+?(?:代表处|分公司|业务部)", normalized_question):
                cleaned = match.strip("，,、 和与及的业绩情况表现")
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
        if entity_names:
            quoted_entities = ",".join("'" + item.replace("'", "''") + "'" for item in entity_names)
            return f"""
WITH RECURSIVE 汇总结果 AS (
{syyb_base_sql}
),
命中链路 AS (
    SELECT *
    FROM 汇总结果
    WHERE 节点名称 IN ({quoted_entities})
    UNION ALL
    SELECT 子节点.*
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
)
SELECT *
FROM 命中链路
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

        if all(token in normalized_question for token in ["东部分公司", "南部分公司"]):
            return f"""
{syyb_base_sql}
HAVING 节点名称 IN ('东部分公司','南部分公司') OR 上级名称 IN ('东部分公司','南部分公司')
ORDER BY 条线 DESC, 层级 DESC, 上级名称, 节点名称
LIMIT 10000
""".strip()

        if all(token in normalized_question for token in ["东部分公司", "达成率", "剩余任务"]):
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

        return ""

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

        city_field_key = consumer_key("城市公司", "城市分公司")
        query_intent = self._safe_dict(context.get("query_intent"))
        intent_is_ranking = query_intent.get("intent") == "ranking"
        intent_target_level = str(query_intent.get("target_level") or "")
        asks_branch_extremes = (
            "分公司" in normalized_question
            and any(token in normalized_question for token in ["最高", "最好", "最低", "最差", "头尾", "首尾"])
            and any(token in normalized_question for token in ["对比", "比较", "差距", "差异", "二者", "两家", "任务体量", "实际开单", "缺口"])
        )
        entity_names = self._resolved_entity_names(context)
        if not entity_names and not asks_branch_extremes:
            for match in re.findall(r"[\u4e00-\u9fa5A-Za-z0-9（）()]+?(?:分公司|城市公司|城市分公司|事业部)", normalized_question):
                cleaned = match.strip("，,、 和与及的业绩情况表现整体")
                if cleaned and cleaned not in {"哪些分公司", "各分公司", "所有分公司", "哪些城市公司", "各城市公司", "所有城市公司"}:
                    entity_names.append(cleaned)

        scope_filter = ""
        if entity_names:
            quoted_entities = ",".join("'" + item.replace("'", "''") + "'" for item in entity_names)
            scope_filter = f"""
WHERE 节点名称 = '消费者事业部'
   OR 节点名称 IN ({quoted_entities})
   OR 上级名称 IN ({quoted_entities})
   OR 上级名称 IN (
       SELECT 节点名称
       FROM 汇总结果
       WHERE 节点名称 IN ({quoted_entities}) OR 上级名称 IN ({quoted_entities})
   )
"""

        channel_metric = ""
        for candidate in ["燃气定制", "新零售", "线下", "地产"]:
            if candidate in normalized_question:
                channel_metric = candidate
                break
        if channel_metric:
            task_metric_expr = f"COALESCE({channel_metric}任务_万元, 0) * 10000"
            actual_metric_expr = f"COALESCE({channel_metric}实际_万元, 0) * 10000"
            metric_scope_expr = f"'{channel_metric}'"
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
        COALESCE(NULLIF(TRIM(fields->>'{city_field_key}'), ''), '') AS 城市公司,
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
            WHEN 城市公司 <> '' THEN '城市公司'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '消费者事业部总体'
        END AS 层级,
        CASE
            WHEN 城市公司 <> '' THEN 城市公司
            WHEN 分公司 <> '' THEN 分公司
            ELSE 事业部
        END AS 节点名称,
        CASE
            WHEN 城市公司 <> '' THEN 分公司
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
      AND (事业部 = '消费者事业部' OR 分公司 <> '' OR 城市公司 <> '')
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
            city_field_key=city_field_key,
        ).strip()

        city_level_requested = (
            intent_target_level == "城市公司"
            or "城市公司" in normalized_question
            or "城市分公司" in normalized_question
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
        if asks_city_ranking:
            rank_match = re.search(r"(?:Top|top|前|后|倒数)\s*(\d+|[一二两三四五六七八九十]+)", normalized_question)
            rank_text = rank_match.group(1) if rank_match else ""
            chinese_digits = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}

            def parse_city_rank_limit(value: str) -> int:
                if not value:
                    return 3 if any(token in normalized_question for token in ["Top", "top", "前", "后", "排名", "排行"]) else 1
                if value.isdigit():
                    return max(1, min(20, int(value)))
                if value == "十":
                    return 10
                if "十" in value:
                    left, _, right = value.partition("十")
                    tens = chinese_digits.get(left, 1 if left == "" else 0)
                    ones = chinese_digits.get(right, 0)
                    return max(1, min(20, tens * 10 + ones))
                return max(1, min(20, chinese_digits.get(value, 3)))

            rank_limit = self._safe_int(query_intent.get("top_n"), 0) if intent_is_ranking else 0
            if rank_limit <= 0:
                rank_limit = parse_city_rank_limit(rank_text)
            rank_limit = max(1, min(20, rank_limit))
            order_direction = str(query_intent.get("direction") or "").upper() if intent_is_ranking else ""
            if order_direction not in {"ASC", "DESC"}:
                order_direction = "ASC" if any(token in normalized_question for token in ["最低", "最差", "后", "倒数", "落后"]) else "DESC"
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
            sort_column = configured_sort_column if configured_sort_column in allowed_sort_columns else "达成率"
            return f"""
{base_sql}
SELECT *
FROM 汇总结果
WHERE 层级 = '城市公司'
ORDER BY {sort_column} {order_direction}, 年度开单金额 DESC, 剩余任务金额 DESC, 节点名称
LIMIT {rank_limit}
""".strip()
        if asks_branch_ranking and not asks_branch_extremes and not (channel_metric and asks_best_branch):
            rank_match = re.search(r"(?:Top|top|前|后|倒数)\s*(\d+|[一二两三四五六七八九十]+)", normalized_question)
            rank_text = rank_match.group(1) if rank_match else ""
            chinese_digits = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}

            def parse_rank_limit(value: str) -> int:
                if not value:
                    return 3 if any(token in normalized_question for token in ["Top", "top", "前", "后", "排名", "排行"]) else 1
                if value.isdigit():
                    return max(1, min(20, int(value)))
                if value == "十":
                    return 10
                if "十" in value:
                    left, _, right = value.partition("十")
                    tens = chinese_digits.get(left, 1 if left == "" else 0)
                    ones = chinese_digits.get(right, 0)
                    return max(1, min(20, tens * 10 + ones))
                return max(1, min(20, chinese_digits.get(value, 3)))

            rank_limit = self._safe_int(query_intent.get("top_n"), 0) if intent_is_ranking else 0
            if rank_limit <= 0:
                rank_limit = parse_rank_limit(rank_text)
            rank_limit = max(1, min(20, rank_limit))
            order_direction = str(query_intent.get("direction") or "").upper() if intent_is_ranking else ""
            if order_direction not in {"ASC", "DESC"}:
                order_direction = "ASC" if any(token in normalized_question for token in ["最低", "最差", "后", "倒数", "落后"]) else "DESC"
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
            sort_column = configured_sort_column if configured_sort_column in allowed_sort_columns else "达成率"
            return f"""
{base_sql}
SELECT *
FROM 汇总结果
WHERE 层级 = '分公司'
ORDER BY {sort_column} {order_direction}, 年度开单金额 DESC, 剩余任务金额 DESC, 节点名称
LIMIT {rank_limit}
""".strip()
        if channel_metric and asks_best_branch:
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
      AND 总任务金额 > 0
    ORDER BY 达成率 DESC, 年度开单金额 DESC, 节点名称
    LIMIT 1
)
SELECT *
FROM 汇总结果
WHERE 节点名称 IN (SELECT 节点名称 FROM 最佳分公司)
   OR 上级名称 IN (SELECT 节点名称 FROM 最佳分公司)
ORDER BY
    CASE 层级 WHEN '分公司' THEN 1 WHEN '城市公司' THEN 2 ELSE 9 END,
    达成率 DESC,
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
    CASE 层级 WHEN '消费者事业部总体' THEN 0 WHEN '分公司' THEN 1 WHEN '城市公司' THEN 2 ELSE 9 END,
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
9. 如果用户问某个组织节点“业绩怎么样/情况/表现/分析”，这是单体分析场景，不要只返回该节点下一层；必须按报告配置 analysisDimensions 的父子链路返回“命中节点 + 下级节点 + 下下级明细节点”。例如配置链路为 A -> B -> C -> D 时，命中 B 要返回 B、C、D；命中 C 要返回 C、D。该规则必须由配置字段 nameColumn/parentColumn/levelColumn/analysisDimensions 推导，不允许针对固定组织名称写死。

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
            context["resolved_entities"] = self._route_entity_resolution(route) or self._resolve_question_entities(
                route.get("refined_query", question),
                context,
                trace=trace,
            )
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
                    }
            refined_question = str(route.get("refined_query") or question or "")
            intent_question = refined_question
            if question and question not in intent_question:
                intent_question = f"{intent_question}\n{question}"
            query_intent = self._resolve_query_intent(intent_question, context)
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
                if not golden_hit_delay_applied:
                    delay_seconds = random.uniform(2.0, 3.0)
                    time.sleep(delay_seconds)
                    golden_hit_delay_applied = True
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
                    "status": "success",
                }
            )

            if review.get("approved") is False:
                fallback_sql = (final_sql or "").strip()
                if not fallback_sql:
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
                if not self._is_read_only_sql(fallback_sql):
                    dataset_results.append(
                        self._build_graceful_dataset_result(
                            question=question,
                            context=context,
                            review=review,
                            result={"columns": [], "rows": [], "row_count": 0},
                            sql_text="",
                        )
                    )
                    continue
                final_sql = fallback_sql

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
        combined_analysis = "\n\n---\n\n".join(
            [
                f"## {item['dataset_name']}\n\n{item['analysis']}"
                for item in dataset_results
                if item.get("analysis")
            ]
        )
        return {
            "question": question,
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
        route = dict(route or {})

        def allowed_ids(values: Any) -> List[int]:
            result: List[int] = []
            for item in values or []:
                try:
                    dataset_id = int(item)
                except (TypeError, ValueError):
                    continue
                if dataset_id in allowed_set and dataset_id not in result:
                    result.append(dataset_id)
            return result

        route["dataset_ids"] = allowed_ids(route.get("dataset_ids"))
        route["candidate_dataset_ids"] = allowed_ids(route.get("candidate_dataset_ids"))
        route["split_queries"] = [
            item for item in (route.get("split_queries") or [])
            if isinstance(item, dict) and allowed_ids([item.get("dataset_id")])
        ]
        filtered_options = []
        for option in route.get("confirmation_options") or []:
            if not isinstance(option, dict):
                continue
            next_option = dict(option)
            next_option["dataset_ids"] = allowed_ids(next_option.get("dataset_ids"))
            if next_option["dataset_ids"]:
                filtered_options.append(next_option)
        route["confirmation_options"] = filtered_options
        if route.get("requires_confirmation") and not filtered_options:
            route["requires_confirmation"] = False
            route["decision"] = "generate_sql"
        return route

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
        self._append_trace(
            trace,
            "request.received",
            "info",
            question=question,
            effective_question=effective_question,
            session_id=conversation_session_id,
            memory_rounds=len(memory_history),
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
                self._append_trace(
                    trace,
                    "agent1.preferred_dataset_released",
                    "info",
                    reason="current_question_explicitly_matches_another_dataset",
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
                route = self.route_with_agent1(
                    effective_question,
                    trace=trace,
                    conversation_context=memory_history,
                    allowed_dataset_ids=allowed_dataset_ids,
                    current_question=question,
                )
                self._append_trace(trace, "agent1.route_result", "info", route=route)
            steps.append(
                {
                    "title": "Agent1 语义路由",
                    "duration": round((time.time() - step_started) * 1000, 2),
                    "status": "success",
                }
            )

            if allowed_set is not None:
                route = self._filter_route_by_allowed_datasets(route, allowed_set)
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

        confirmation_notes = []
        if selected_option_item:
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


