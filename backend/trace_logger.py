from __future__ import annotations

import json
import os
import time
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from ask_engine_utils import _build_trace_snapshot, _stream_preview, _truncate_text


class TraceLogger:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def _new_trace(
        self,
        question: str,
        entry: str,
        live_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        model: Any = "",
        base_url: Any = "",
    ) -> Dict[str, Any]:
        return {
            "trace_id": str(uuid4()),
            "entry": entry,
            "question": question,
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "model": model or "",
            "base_url": base_url or "",
            "events": [],
            "_live_callback": live_callback,
        }

    def _write_trace_line(self, payload: Dict[str, Any]) -> None:
        try:
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            pass

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

    def _append_trace(
        self,
        trace: Optional[Dict[str, Any]],
        stage: str,
        status: str = "info",
        **payload: Any,
    ) -> None:
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
            event["delta_text"] = _truncate_text(delta_text, 800)
            event["stream_text"] = _stream_preview(stream_text or delta_text)
        if reasoning_delta:
            event["reasoning_delta"] = _truncate_text(reasoning_delta, 800)
            event["reasoning_text"] = _stream_preview(reasoning_text or reasoning_delta)
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

    def _flush_trace(
        self,
        trace: Optional[Dict[str, Any]],
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not trace:
            return
        if result is not None:
            trace["result"] = result
        summary_payload = {"type": "summary", **_build_trace_snapshot(trace, include_result=True)}
        self._write_trace_line(summary_payload)
        self._emit_live_trace(trace, summary_payload)
