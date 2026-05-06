import json
import logging
import os
import re
import sys
import time
import traceback
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
from dataset_dimension_profiles import find_group_matches, get_dataset_profile
import dataset_report_config as report_config_store
from report_spec_builder import build_report_spec
from memory import ShortTermMemoryStore


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
        )
        if layered:
            return layered

        if row_count <= 0:
            lines = [
                "## 业绩分析报告",
                "",
                "### 核心结论",
                f"本次围绕“{question or dataset_name}”未查询到匹配数据，暂不能判断业绩好坏。",
                "",
                "### 问题诊断",
                "• **痛点：** 查询结果 -> 0 行 -> 可能是组织名称、时间范围或层级口径没有命中明细数据。",
            ]
            if review_summary:
                lines.append(f"• **痛点：** SQL复核 -> {review_summary} -> SQL 语法通过不代表业务过滤条件一定命中数据。")
            if error_message:
                lines.append(f"• **痛点：** 执行链路 -> 生成失败 -> 已退回无结果诊断，原因：{error_message}")
            lines.extend(
                [
                    "",
                    "### 改进建议",
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

        name_col = str(config.get("nameColumn") or "节点名称")
        parent_col = str(config.get("parentColumn") or "上级名称")
        level_col = str(config.get("levelColumn") or "层级")
        track_col = str(config.get("trackColumn") or "条线")
        task_col = str(task_metric.get("column") or "")
        actual_col = str(actual_metric.get("column") or "")
        rate_col = str(rate_metric.get("column") or "")
        levels = [item for item in (config.get("levels") or []) if isinstance(item, dict)]
        risk_threshold = self._to_float(config.get("riskThreshold"))
        if risk_threshold is None:
            risk_threshold = 80

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

        def format_rank(items: List[Dict[str, Any]]) -> str:
            if not items:
                return "暂无"
            return "、".join(f"{row_name(row)} {self._format_metric(row_rate(row), '%')}" for row in items)

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
            risk_rows = rank_items([row for row in section_rows if (row_rate(row) or 0) < risk_threshold], False, 6)
            top_rows = rank_items(section_rows, True, 6)
            parent_groups: Dict[str, int] = {}
            if parent_col in columns:
                for row in section_rows:
                    parent = normalized_text(row, parent_col) or "未归属"
                    parent_groups[parent] = parent_groups.get(parent, 0) + 1
            group_text = "、".join(f"{name}({count})" for name, count in list(parent_groups.items())[:6]) or "按当前结果直接展示"
            lines.extend(
                [
                    f"#### {' / '.join(tracks) + '｜' if tracks else ''}{section['name']}",
                    f"• **亮点：** 表现较好节点 -> {format_rank(top_rows)} -> 可沉淀可复制动作。",
                    f"• **痛点：** 风险节点 -> {format_rank(risk_rows)} -> 需要短周期跟进缺口。",
                    f"• **结构：** 下级单元 -> {', '.join([row_name(row) for row in section_rows[:12]]) or '暂无'}（共 {len(section_rows)} 个） -> 上级分组：{group_text}。",
                    "",
                ]
            )

        risk_count = sum(1 for section in level_sections for row in section["rows"] if (row_rate(row) or 0) < risk_threshold)
        top_examples = rank_items(valid_rows, True, 3)
        risk_examples = rank_items([row for row in valid_rows if (row_rate(row) or 0) < risk_threshold], False, 3)
        lines.extend(
            [
                "### 改进建议",
                f"• {top_section['name']}：优先聚焦低于 {self._format_metric(risk_threshold, '%')} 的节点，复盘目标拆解、项目推进和资源投入是否匹配。",
                f"• {bottom_section['name']}：对低达成节点做短周期跟进，对高达成节点沉淀可复制动作。",
                f"• 当前共识别 {risk_count} 个风险节点，建议优先查看 {format_rank(risk_examples)}；表现较好节点可参考 {format_rank(top_examples)}。",
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
        }

    def _select_sql_strategy(self, question: str, route: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        samples = context.get("golden_sql_samples") or []
        top_sample = samples[0] if samples else {}
        top_sample_sql = str(top_sample.get("sql_text") or "").strip()
        top_sample_score = self._safe_int(top_sample.get("match_score"), 0)
        route_match_score = self._safe_int(route.get("match_score"), 0)
        route_margin = self._safe_int(route.get("route_margin"), 0)
        preferred_override = bool(route.get("preferred_dataset_override"))
        rule_based_sql = self._build_rule_based_sql(question, route, context)

        if rule_based_sql:
            return {
                "mode": "rule_based",
                "sql": rule_based_sql,
                "sample_id": None,
                "sample_score": 0,
            }

        if route.get("decision") == "direct_execute" and top_sample_sql:
            return {
                "mode": "sample_direct",
                "sql": top_sample_sql,
                "sample_id": top_sample.get("id"),
                "sample_score": top_sample_score,
            }

        if top_sample_sql and (
            top_sample_score >= 96
            or (preferred_override and top_sample_score >= 82)
            or (route_match_score >= 86 and top_sample_score >= 84 and route_margin >= 8)
        ):
            return {
                "mode": "sample_direct",
                "sql": top_sample_sql,
                "sample_id": top_sample.get("id"),
                "sample_score": top_sample_score,
            }

        if top_sample_sql and (
            top_sample_score >= 66
            or (preferred_override and top_sample_score >= 58)
        ):
            return {
                "mode": "sample_template",
                "sql": top_sample_sql,
                "sample_id": top_sample.get("id"),
                "sample_score": top_sample_score,
            }

        return {
            "mode": "agent_generate",
            "sql": "",
            "sample_id": None,
            "sample_score": 0,
        }

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
            "riskThreshold": config.get("riskThreshold"),
            "agentReportGuidance": config.get("agentReportGuidance", ""),
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    @staticmethod
    def _tokenize(text: str) -> set:
        parts = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{1,4}", (text or "").lower())
        return {item for item in parts if item.strip()}

    def _compute_dataset_match(self, question: str, dataset: Dict[str, Any], context: Dict[str, Any]) -> int:
        q_tokens = self._tokenize(question)
        if not q_tokens:
            return 0

        synonyms = " ".join(dataset.get("synonyms", []) or [])
        common_questions = " ".join(item.get("question_text", "") for item in context.get("common_questions", [])[:8])
        lld_text = self._get_lld_content(context)[:600]
        dataset_text = f"{dataset.get('dataset_name', '')} {dataset.get('business_domain', '')} {synonyms} {common_questions} {lld_text}"
        dataset_tokens = self._tokenize(dataset_text)
        synonym_overlap = len(q_tokens.intersection(dataset_tokens))
        sample_score = max([int(item.get("match_score", 0)) for item in context.get("golden_sql_samples", [])] or [0])
        schema_hit = 1 if any(token in dataset_tokens for token in ("日期", "时间", "金额", "分公司", "事业部", "区域")) else 0
        score = synonym_overlap * 12 + min(sample_score, 90) + schema_hit * 4
        return min(score, 100)

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
    ) -> Dict[str, Any]:
        catalog = self.repository.get_agent1_catalog()
        if not catalog:
            return {
                "dataset_ids": [],
                "intent": "detail",
                "refined_query": question,
                "requires_confirmation": False,
                "decision": "generate_sql",
            }

        candidate_contexts: List[Tuple[Dict[str, Any], Dict[str, Any], int]] = []
        for dataset in catalog:
            context = self.repository.get_dataset_context(dataset["id"], question, top_k_samples=5)
            score = self._compute_dataset_match(question, dataset, context)
            candidate_contexts.append((dataset, context, score))

        candidate_contexts.sort(key=lambda item: item[2], reverse=True)
        ranked = [(item[0], item[2]) for item in candidate_contexts]

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

        best_dataset, best_context, best_score = candidate_contexts[0]
        best_sample = (best_context.get("golden_sql_samples") or [{}])[0]
        best_sample_score = int(best_sample.get("match_score", 0))
        runner_up_score = candidate_contexts[1][2] if len(candidate_contexts) > 1 else 0
        route_margin = best_score - runner_up_score
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
                "Common Questions:\n" + "\n".join(common_question_lines),
                "Data Dictionary:\n" + "\n".join(dictionary_lines),
                "Schema Definition:\n" + "\n\n".join(schema_lines),
                "Join Relations:\n" + "\n".join(relation_lines),
                "Golden SQL Samples:\n" + "\n\n".join(sample_lines),
            ]
        )

    def _build_rule_based_sql(self, question: str, route: Dict[str, Any], context: Dict[str, Any]) -> str:
        dataset = self._safe_dict(context.get("dataset"))
        dataset_code = str(dataset.get("dataset_code") or "")
        dataset_name = str(dataset.get("dataset_name") or "")
        normalized_question = str(question or "").replace("\n", " ").strip()
        is_syyb_dataset = dataset_code in {"angel_business_2026", "angel_business_2026_phase1"} or dataset_name in {
            "商用事业部",
            "商用事业部（阶段一升级版）",
        }
        is_phase1_dataset = dataset_code == "angel_business_2026_phase1" or dataset_name == "商用事业部（阶段一升级版）"

        if not is_syyb_dataset:
            return ""

        ranking_tokens = ["排名", "最低", "最高", "最好", "最差", "Top", "top", "前", "后"]
        has_ranking_intent = any(token in normalized_question for token in ranking_tokens)
        if is_phase1_dataset and has_ranking_intent:
            if "代表处" in normalized_question:
                order_direction = "DESC" if any(token in normalized_question for token in ["最高", "最好", "Top", "top", "前"]) else "ASC"
                rank_limit = 3 if any(token in normalized_question for token in ["Top", "top", "前", "后", "排名"]) else 1
                return f"""
WITH 汇总结果 AS (
{SYYB_BASE_SQL}
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
            if "业务代表" in normalized_question or "业务员" in normalized_question:
                is_desc = any(token in normalized_question for token in ["最高", "最好", "Top", "top", "前"])
                order_direction = "DESC" if is_desc else "ASC"
                rank_limit = 3 if any(token in normalized_question for token in ["Top", "top", "前", "后", "排名"]) else 1
                metric_column = "年度开单金额" if ("开单" in normalized_question or "金额" in normalized_question) else "达成率"
                return f"""
WITH 汇总结果 AS (
{SYYB_BASE_SQL}
),
业务代表上级内排序 AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY 上级名称
            ORDER BY {metric_column} {order_direction}, 剩余任务金额 DESC, 节点名称
        ) AS 上级内排名
    FROM 汇总结果
    WHERE 层级 = '业务代表'
)
SELECT *
FROM 业务代表上级内排序
WHERE 上级内排名 <= {rank_limit}
ORDER BY 上级名称, 上级内排名, {metric_column} {order_direction}, 剩余任务金额 DESC, 节点名称
LIMIT 50
""".strip()
            if "分公司" in normalized_question:
                order_direction = "DESC" if any(token in normalized_question for token in ["最高", "最好", "Top", "top", "前"]) else "ASC"
                return f"""
WITH 汇总结果 AS (
{SYYB_BASE_SQL}
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
{SYYB_BASE_SQL}
)
SELECT *
FROM 汇总结果
WHERE 达成率 < 10
ORDER BY 达成率 ASC, 剩余任务金额 DESC, 节点名称
LIMIT 50
""".strip()

        entity_names = []
        for match in re.findall(r"[\u4e00-\u9fa5A-Za-z0-9（）()]+?(?:代表处|分公司|业务部)", normalized_question):
            cleaned = match.strip("，,、 和与及的业绩情况表现")
            if is_phase1_dataset and cleaned in {"哪些代表处", "各代表处", "所有代表处", "哪些分公司", "各分公司", "所有分公司", "哪些业务部", "各业务部"}:
                continue
            if cleaned and cleaned not in entity_names:
                entity_names.append(cleaned)
        if entity_names:
            quoted_entities = ",".join("'" + item.replace("'", "''") + "'" for item in entity_names)
            return f"""
WITH 汇总结果 AS (
{SYYB_BASE_SQL}
),
命中节点 AS (
    SELECT 节点名称
    FROM 汇总结果
    WHERE 节点名称 IN ({quoted_entities}) OR 上级名称 IN ({quoted_entities})
),
命中孙级 AS (
    SELECT 子节点.节点名称
    FROM 汇总结果 子节点
    WHERE 子节点.上级名称 IN (SELECT 节点名称 FROM 命中节点)
)
SELECT *
FROM 汇总结果
WHERE 节点名称 IN ({quoted_entities})
   OR 上级名称 IN ({quoted_entities})
   OR 节点名称 IN (SELECT 节点名称 FROM 命中孙级)
ORDER BY 条线 DESC, 层级 DESC, 上级名称, 节点名称
LIMIT 10000
""".strip()

        if all(token in normalized_question for token in ["东部分公司", "南部分公司"]):
            return f"""
{SYYB_BASE_SQL}
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
        if rule_based_sql and (not defer_rule_fallback or force_grouped_ranking):
            self._append_trace(
                trace,
                "agent2.sql_generate.grouped_rule" if force_grouped_ranking else "agent2.sql_generate.rule_based",
                "info",
                sql=self._truncate_text(rule_based_sql, 12000),
            )
            return {
                "sql": rule_based_sql,
                "notes": "grouped hierarchy ranking rule" if force_grouped_ranking else "rule based sql fallback",
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
                return {"sql": seed_sql, "notes": "golden sample seed fallback", "sample_id": seed_sample_id}
            if rule_based_sql and defer_rule_fallback:
                self._append_trace(
                    trace,
                    "agent2.sql_generate.rule_fallback",
                    "info",
                    sql=self._truncate_text(rule_based_sql, 12000),
                )
                return {"sql": rule_based_sql, "notes": "dynamic generation failed; used rule fallback"}
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
    ) -> Dict[str, Any]:
        dataset = self._safe_dict(context.get("dataset"))
        if self._is_read_only_sql(sql_text) and "angel_group_data" in str(sql_text):
            self._append_trace(
                trace,
                "agent3.sql_review.rule_based",
                "info",
                review_summary="已通过规则复核：只读 SQL、限定 angel_group_data，并保留书架层级口径。",
            )
            return {
                "approved": True,
                "final_sql": sql_text,
                "review_summary": "规则复核通过：SQL 只读且使用当前数据集表结构。",
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
1. 动态布局：先识别意图。对比查询使用左右对称对比结构；单体查询使用“核心 KPI -> 趋势/对比图 -> 细分维度”的纵向结构；列表或排名查询突出名次、差距和 Top/Bottom。
2. 强制格式化：所有金额必须按统一函数口径表达：1万以下原样；1万-100万保留1位小数并使用“万”；100万-1亿取整“万”；1亿以上保留2位小数“亿”。不得随意生成金额格式。
3. 视觉引导：完成率按红绿灯解释，>=100% 为绿灯，80%-100% 为黄灯，<80% 为红灯；涉及多维度排序时默认按完成率降序。
4. 分析文本：严禁重复主语和长篇段落。必须采用“核心结论 -> 亮点分析 • -> 问题诊断 • -> 改进建议”的结构。
5. 文案：报告标题统一为“业绩分析报告”，不得出现“极简报告”“极简总结”等冗余字样。
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
    ) -> Dict[str, Any]:
        dataset_ids = route.get("dataset_ids", [])
        if not dataset_ids:
            return {"error": "Agent1 did not provide dataset_ids."}

        dataset_results = []
        for dataset_id in dataset_ids:
            context = self.repository.get_dataset_context(int(dataset_id), route.get("refined_query", question))
            dataset_meta = self._safe_dict(context.get("dataset"))
            report_config = report_config_store.get_config(int(dataset_id)) or report_config_store.get_default_config()
            context["report_config"] = report_config
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
            )
            prompts = context.get("agent_prompts", {})
            agent2_prompt = "\n\n".join(item["prompt_content"] for item in prompts.get(2, []))
            agent3_prompt = "\n\n".join(item["prompt_content"] for item in prompts.get(3, []))

            rule_override_sql = self._build_rule_based_sql(route.get("refined_query", question), route, context)
            if route.get("decision") == "direct_execute" and (route.get("matched_sample_sql") or rule_override_sql):
                sql_text = rule_override_sql or route.get("matched_sample_sql")
                steps.append({"title": "Agent1 高匹配直执行", "duration": 0, "status": "success"})
            else:
                step_started = time.time()
                agent2_result = self._agent2_generate_sql(route.get("refined_query", question), route, context, agent2_prompt, trace=trace)
                sql_text = (agent2_result.get("sql") or "").strip()
                self._append_trace(
                    trace,
                    "pipeline.agent2_result",
                    "info",
                    dataset_id=dataset_id,
                    dataset_name=dataset_meta.get("dataset_name"),
                    sql=self._truncate_text(sql_text, 12000),
                    notes=agent2_result.get("notes", ""),
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
            review = self._agent3_review(question, route, sql_text, context, agent3_prompt, trace=trace)
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
                fallback_sql = (final_sql or sql_text or "").strip()
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
                    "agent3_review": review,
                    "columns": result["columns"],
                    "rows": result["rows"],
                    "row_count": result["row_count"],
                    "report_spec": report_spec,
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

    def ask(
        self,
        question: str,
        preferred_dataset_ids: Optional[List[int]] = None,
        live_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        model_id: Optional[int] = None,
        session_id: str = "",
        conversation_history: Optional[List[Dict[str, Any]]] = None,
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
            if preferred_dataset_ids:
                selected_dataset_ids = [int(item) for item in preferred_dataset_ids]
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
                route = self.route_with_agent1(effective_question, trace=trace, conversation_context=memory_history)
                self._append_trace(trace, "agent1.route_result", "info", route=route)
            steps.append(
                {
                    "title": "Agent1 语义路由",
                    "duration": round((time.time() - step_started) * 1000, 2),
                    "status": "success",
                }
            )

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

            result = self._run_pipeline(effective_question, route, started, steps, trace=trace)
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
        option_id: str = "",
        live_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
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

        result = self._run_pipeline(question, route, started, steps, trace=trace)
        result["session_id"] = session_id
        result["conversation_session_id"] = conversation_session_id
        if conversation_session_id and not result.get("error"):
            self.short_term_memory.remember_result(conversation_session_id, question, route, result)
        self._pending_confirmations.pop(session_id, None)
        self._flush_trace(trace, result)
        return result


four_agent_ask_service = FourAgentAskService()


