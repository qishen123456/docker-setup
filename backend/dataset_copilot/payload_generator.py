"""DatasetCopilot — single-shot LLM payload generator.

Usage:
    copilot = DatasetCopilot()
    payload = copilot.generate(dataset_meta, doc_text)
    copilot.save_local(payload, dataset_id=1)
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

try:
    from .copilot_prompts import SYSTEM_PROMPT, build_user_prompt
except ImportError:  # pragma: no cover - fallback for direct script use
    from copilot_prompts import SYSTEM_PROMPT, build_user_prompt  # type: ignore

try:
    from openai import OpenAI
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "openai SDK is required for Dataset Copilot. Install with `pip install openai`."
    ) from exc


class CopilotError(Exception):
    pass


_REQUIRED_TOP_KEYS = (
    "lld_documents",
    "schema_definition",
    "data_dictionary",
    "golden_sql_samples",
    "agent_prompts",
)


class DatasetCopilot:
    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        output_dir: Optional[str] = None,
        request_timeout: float = 240.0,
        use_json_mode: bool = False,
    ) -> None:
        cfg = self._resolve_llm_config(model, base_url, api_key)
        self._model = cfg["model"]
        self._client = OpenAI(
            api_key=cfg["api_key"],
            base_url=cfg["base_url"],
            timeout=request_timeout,
        )
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._use_json_mode = use_json_mode
        self._output_dir = output_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "output"
        )
        os.makedirs(self._output_dir, exist_ok=True)

    # ------------------------------------------------------------------ LLM config
    @staticmethod
    def _resolve_llm_config(
        model: Optional[str], base_url: Optional[str], api_key: Optional[str]
    ) -> Dict[str, str]:
        if model and base_url and api_key:
            return {"model": model, "base_url": base_url, "api_key": api_key}
        try:
            from config_manager import get_default_ai_model  # type: ignore
        except ImportError as exc:
            raise CopilotError(
                "Cannot resolve default AI model. Run from backend/ or supply model/base_url/api_key explicitly."
            ) from exc
        cfg = get_default_ai_model() or {}
        if not cfg.get("model") or not cfg.get("api_key"):
            raise CopilotError(
                "No default AI model configured. Configure one in 模型管理 or pass --model/--base-url/--api-key."
            )
        return {
            "model": model or cfg["model"],
            "base_url": base_url or cfg.get("base_url") or "https://api.openai.com/v1",
            "api_key": api_key or cfg["api_key"],
        }

    # ------------------------------------------------------------------ public API
    def generate(
        self,
        dataset_meta: Dict[str, Any],
        doc_text: str,
        sample_rows_text: str = "",
        retries: int = 2,
        doc_max_chars: int = 7000,
    ) -> Dict[str, Any]:
        if len(doc_text) > doc_max_chars:
            print(
                f"[copilot] doc trimmed from {len(doc_text)} -> {doc_max_chars} chars",
                flush=True,
            )
            doc_text = doc_text[:doc_max_chars]
        user_prompt = build_user_prompt(doc_text, dataset_meta, sample_rows_text)
        base_prompt = user_prompt
        last_err: Optional[Exception] = None
        for attempt in range(retries + 1):
            raw = ""
            try:
                raw = self._invoke_llm(user_prompt)
                payload = self._parse_json(raw)
                self._validate(payload)
                return self._normalize(payload)
            except Exception as exc:
                last_err = exc
                print(f"[copilot] attempt {attempt + 1} failed: {exc}", flush=True)
                if raw and "json parse failed" in str(exc):
                    user_prompt = self._build_json_repair_prompt(raw, exc)
                else:
                    user_prompt = self._build_retry_prompt(base_prompt, exc)
        raise CopilotError(f"copilot generate failed after {retries + 1} attempts: {last_err}")

    def save_local(self, payload: Dict[str, Any], dataset_id: int) -> str:
        path = os.path.join(self._output_dir, f"dataset_{dataset_id}_payload.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        backup = os.path.join(self._output_dir, f"dataset_{dataset_id}_payload.{ts}.json")
        with open(backup, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        return path

    # ------------------------------------------------------------------ internal
    @staticmethod
    def _build_retry_prompt(previous_prompt: str, exc: Exception) -> str:
        return (
            previous_prompt
            + "\n\n## Previous output failed validation\n"
            + f"Error: {exc}\n"
            + "Return ONE complete, valid JSON object only. No markdown, no comments.\n"
            + "Make the JSON smaller so it cannot be truncated: exactly 3 golden_sql_samples, "
            + "4 agent_prompts, 6 common_questions, 4 regression_cases, and concise text fields.\n"
            + "Every string must be properly escaped. Do not omit commas between fields or array items.\n"
            + "If a SQL sample is long, keep the SQL correct but reduce explanatory text.\n"
        )

    @staticmethod
    def _build_json_repair_prompt(raw_json: str, exc: Exception) -> str:
        raw = raw_json.strip()
        if len(raw) > 50000:
            raw = raw[:50000]
        return (
            "The following JSON-like payload is invalid. Repair it into ONE complete, valid JSON object.\n"
            f"Parser error: {exc}\n"
            "Rules:\n"
            "1. Output only JSON. No markdown and no explanation.\n"
            "2. Preserve the same top-level keys: synonyms, lld_documents, schema_definition, "
            "data_dictionary, table_relations, golden_sql_samples, agent_prompts, common_questions, "
            "regression_cases, external_configs, report_config.\n"
            "3. If the payload is too long, keep exactly 3 golden_sql_samples, 4 agent_prompts, "
            "6 common_questions and 4 regression_cases.\n"
            "4. Fix missing commas, broken quotes, unescaped newlines, and trailing fragments.\n"
            "5. Make sure the JSON can be parsed by Python json.loads.\n\n"
            "Invalid payload:\n"
            f"{raw}"
        )

    def _invoke_llm(self, user_prompt: str) -> str:
        kwargs = dict(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            stream=True,
        )
        if self._use_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        print(
            f"[copilot] calling model={self._model} max_tokens={self._max_tokens} "
            f"json_mode={self._use_json_mode} stream=True",
            flush=True,
        )
        try:
            return self._stream_completion(kwargs)
        except Exception as exc:
            message = str(exc)
            if self._use_json_mode and ("response_format" in message or "json_object" in message):
                print("[copilot] json_mode unsupported by provider, retrying without json_mode", flush=True)
                kwargs.pop("response_format", None)
                return self._stream_completion(kwargs)
            raise

    def _stream_completion(self, kwargs: Dict[str, Any]) -> str:
        chunks: List[str] = []
        bytes_seen = 0
        last_print = time.time()
        finish_reason = None
        stream = self._client.chat.completions.create(**kwargs)
        for event in stream:
            try:
                finish_reason = event.choices[0].finish_reason or finish_reason
            except Exception:
                pass
            try:
                delta = event.choices[0].delta.content or ""
            except Exception:
                delta = ""
            if not delta:
                continue
            chunks.append(delta)
            bytes_seen += len(delta)
            now = time.time()
            if now - last_print >= 5:
                print(f"[copilot] streamed {bytes_seen} chars ...", flush=True)
                last_print = now
        content = "".join(chunks).strip()
        if not content:
            raise CopilotError("LLM returned empty content")
        if finish_reason == "length":
            raise CopilotError(
                "model output was truncated by max_tokens before completing JSON; "
                "increase max_tokens or reduce prompt/output size"
            )
        print(f"[copilot] received {len(content)} chars total", flush=True)
        return content

    @staticmethod
    def _parse_json(raw: str) -> Dict[str, Any]:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        # Sometimes models still wrap with prose; try to slice the outermost {}
        first = text.find("{")
        last = text.rfind("}")
        if first == -1 or last == -1 or last <= first:
            raise CopilotError("LLM output is not valid JSON")
        text = text[first : last + 1]
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            start = max(0, exc.pos - 160)
            end = min(len(text), exc.pos + 160)
            near = text[start:end].replace("\n", "\\n")
            raise CopilotError(f"json parse failed: {exc}; near={near}") from exc

    @staticmethod
    def _validate(payload: Dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise CopilotError("payload must be a JSON object")
        missing = [k for k in _REQUIRED_TOP_KEYS if k not in payload]
        if missing:
            raise CopilotError(f"payload missing top-level keys: {missing}")

        lld = [x for x in (payload.get("lld_documents") or []) if (x.get("content") or "").strip()]
        schema = [
            x for x in (payload.get("schema_definition") or [])
            if (x.get("table_name") or "").strip() and (x.get("ddl_sql") or "").strip()
        ]
        dictionary = [
            x for x in (payload.get("data_dictionary") or [])
            if (x.get("table_name") or "").strip()
            and (x.get("column_name") or "").strip()
            and (x.get("semantic_name") or "").strip()
        ]
        golden = [
            x for x in (payload.get("golden_sql_samples") or [])
            if (x.get("question") or "").strip() and (x.get("sql_text") or "").strip()
        ]
        prompt_agents = {
            int(x.get("agent_no") or 0)
            for x in (payload.get("agent_prompts") or [])
            if int(x.get("agent_no") or 0) in (1, 2, 3, 4)
            and (x.get("prompt_content") or "").strip()
        }

        problems: List[str] = []
        if not lld:
            problems.append("lld_documents 至少 1 份且 content 非空")
        if not schema:
            problems.append("schema_definition 至少 1 张且 ddl_sql 非空")
        if not dictionary:
            problems.append("data_dictionary 至少 1 条字段语义")
        if len(golden) < 3:
            problems.append(f"golden_sql_samples 至少 3 条（当前 {len(golden)} 条）")
        missing_agents = sorted(set([1, 2, 3, 4]) - prompt_agents)
        if missing_agents:
            problems.append(f"agent_prompts 缺失 Agent {missing_agents}")
        if problems:
            raise CopilotError("; ".join(problems))

    @staticmethod
    def _normalize(payload: Dict[str, Any]) -> Dict[str, Any]:
        # Fill optional collections with empty lists so PUT endpoint never KeyErrors.
        for key in (
            "synonyms",
            "table_relations",
            "common_questions",
            "regression_cases",
            "external_configs",
        ):
            payload.setdefault(key, [])
        # Ensure golden_sql_samples have quality_score and tags
        for item in payload.get("golden_sql_samples", []):
            item.setdefault("intent_type", "general")
            item.setdefault("tags", [])
            try:
                item["quality_score"] = int(item.get("quality_score") or 90)
            except (TypeError, ValueError):
                item["quality_score"] = 90
        # Ensure LLD has version/title
        for idx, item in enumerate(payload.get("lld_documents", []), start=1):
            item.setdefault("version", idx)
            item.setdefault("title", f"LLD v{item['version']}")
            item.setdefault("redline_rules", [])
            item.setdefault("is_active", True)
        return payload
