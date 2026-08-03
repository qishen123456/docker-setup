from __future__ import annotations

import json
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple

from llm_stream_parser import extract_stream_delta, stream_delta_value_to_text


class LLMClient:
    def __init__(
        self,
        *,
        openai_factory: Callable[..., Any],
        get_default_config: Callable[[], Optional[Dict[str, Any]]],
        get_configs: Callable[[], List[Dict[str, Any]]],
        decode_secret: Callable[[str], str],
        should_retry: Callable[[Exception], bool],
        append_trace: Callable[..., None],
        append_llm_delta: Callable[..., None],
        extract_json_block: Callable[[str], str],
        truncate_text: Callable[[Any, int], str],
    ):
        self._openai_factory = openai_factory
        self._get_default_config = get_default_config
        self._get_configs = get_configs
        self._decode_secret = decode_secret
        self._should_retry = should_retry
        self._append_trace = append_trace
        self._append_llm_delta = append_llm_delta
        self._extract_json_block = extract_json_block
        self._truncate_text = truncate_text
        self._llm_client: Any = None
        self._llm_model: Optional[str] = None
        self._preferred_model_id: Optional[int] = None

    def _load_llm(self):
        config = self._get_default_config()
        if not config:
            self._llm_client = None
            self._llm_model = None
            return
        self._activate_llm(config)

    def _activate_llm(self, config: Dict[str, Any]) -> None:
        self._llm_model = config.get("model")
        self._llm_client = self._openai_factory(
            api_key=config.get("api_key", ""),
            base_url=config.get("base_url", "https://api.openai.com/v1"),
        )

    def _candidate_llm_configs(self, preferred_model_id: Optional[int] = None) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        seen = set()

        if preferred_model_id is not None:
            for item in self._get_configs():
                if item.get("id") == preferred_model_id and item.get("is_active"):
                    config = dict(item)
                    config["api_key"] = self._decode_secret(config.pop("api_key_b64", ""))
                    signature = self._config_signature(config)
                    seen.add(signature)
                    candidates.append(config)
                    break

        default_config = self._get_default_config()
        if default_config:
            signature = self._config_signature(default_config)
            if signature not in seen:
                seen.add(signature)
                candidates.append(default_config)

        for item in self._get_configs():
            if not item.get("is_active"):
                continue
            config = dict(item)
            config["api_key"] = self._decode_secret(config.pop("api_key_b64", ""))
            signature = self._config_signature(config)
            if signature in seen:
                continue
            seen.add(signature)
            candidates.append(config)

        return candidates

    @staticmethod
    def _config_signature(config: Dict[str, Any]) -> Tuple[str, str, str]:
        return (
            str(config.get("model") or ""),
            str(config.get("base_url") or ""),
            str(config.get("api_key") or ""),
        )

    @staticmethod
    def _stream_delta_value_to_text(value: Any) -> str:
        return stream_delta_value_to_text(value)

    @staticmethod
    def _extract_stream_delta(delta_obj: Any) -> Tuple[str, str]:
        return extract_stream_delta(delta_obj)

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
                content = self._consume_stream(stream, trace, stage, agent_name, started)
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
                retryable = index < len(candidate_configs) and self._should_retry(exc)
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

    def _consume_stream(self, stream, trace, stage, agent_name, started) -> str:
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
                self._append_llm_delta(trace, stage or "llm.call", agent_name, pending_delta, "".join(chunks), started)
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
            self._append_llm_delta(trace, stage or "llm.call", agent_name, pending_delta, content, started)
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
        return content

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
            parsed = json.loads(self._extract_json_block(raw))
            self._append_trace(trace, stage or "llm.call", "parsed", agent=agent_name, parsed_json=parsed)
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
