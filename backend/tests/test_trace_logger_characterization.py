import inspect
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from four_agent_ask import FourAgentAskService
from smartask_basic.service import BasicAskService
from trace_logger import TraceLogger


class TraceLoggerCharacterizationTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.trace_path = Path(self.temp_dir.name) / "nested" / "trace.jsonl"
        self.logger = TraceLogger(str(self.trace_path))

    def tearDown(self):
        self.temp_dir.cleanup()

    def _read_lines(self):
        if not self.trace_path.exists():
            return []
        return [json.loads(line) for line in self.trace_path.read_text(encoding="utf-8").splitlines()]

    def test_event_and_summary_jsonl_fields_order_and_result_rules(self):
        live_payloads = []
        trace = self.logger._new_trace(
            "查看业绩",
            "ask",
            live_callback=live_payloads.append,
            model="model-a",
            base_url="https://llm.example/v1",
        )

        with patch("trace_logger.time.strftime", return_value="2026-08-02 12:00:00"):
            self.logger._append_trace(trace, "route", "ok", dataset_id=3)
        self.logger._flush_trace(trace, {"answer": "完成"})

        event_line, summary_line = self._read_lines()
        self.assertEqual(
            list(event_line),
            ["type", "trace_id", "entry", "question", "model", "base_url", "event"],
        )
        self.assertEqual(
            list(summary_line),
            ["type", "trace_id", "entry", "question", "started_at", "model", "base_url", "events", "result"],
        )
        self.assertEqual(
            list(event_line["event"]),
            ["time", "stage", "status", "dataset_id"],
        )
        self.assertNotIn("_live_callback", event_line)
        self.assertNotIn("_live_callback", summary_line)
        self.assertEqual(summary_line["result"], {"answer": "完成"})
        self.assertEqual([item["type"] for item in live_payloads], ["trace", "summary"])

        trace_without_result = self.logger._new_trace("问题", "ask", model="", base_url="")
        self.logger._flush_trace(trace_without_result)
        self.assertNotIn("result", self._read_lines()[-1])

        trace_with_existing_result = self.logger._new_trace("问题", "ask", model="", base_url="")
        trace_with_existing_result["result"] = {"answer": "已有结果"}
        self.logger._flush_trace(trace_with_existing_result)
        self.assertEqual(self._read_lines()[-1]["result"], {"answer": "已有结果"})

    def test_content_and_reasoning_delta_are_live_only(self):
        live_payloads = []
        trace = self.logger._new_trace("问题", "ask", live_callback=live_payloads.append, model="m", base_url="u")

        with patch("trace_logger.time.strftime", return_value="2026-08-02 12:00:00"), patch(
            "trace_logger.time.time", return_value=15.126
        ):
            self.logger._append_llm_delta(
                trace,
                "agent2",
                "Agent2",
                "content delta",
                "content stream",
                10.0,
                reasoning_delta="reason delta",
                reasoning_text="reason stream",
                delta_kind="reasoning",
            )

        self.assertEqual(self._read_lines(), [])
        event = trace["events"][0]
        self.assertEqual(
            list(event),
            [
                "time", "stage", "status", "agent", "duration_seconds", "delta_kind",
                "delta_text", "stream_text", "reasoning_delta", "reasoning_text",
            ],
        )
        self.assertEqual(event["duration_seconds"], 5.13)
        self.assertEqual(event["delta_text"], "content delta")
        self.assertEqual(event["reasoning_delta"], "reason delta")
        self.assertEqual(live_payloads[0]["event"], event)

    def test_empty_trace_and_empty_delta_are_no_ops(self):
        self.logger._append_trace(None, "route")
        self.logger._append_llm_delta(None, "agent", "Agent", "x", "x", time.time())
        self.logger._flush_trace(None, {"answer": "x"})
        trace = self.logger._new_trace("问题", "ask", model="", base_url="")
        self.logger._append_llm_delta(trace, "agent", "Agent", "", "", time.time())

        self.assertEqual(trace["events"], [])
        self.assertEqual(self._read_lines(), [])

    def test_callback_and_file_errors_are_swallowed(self):
        def failing_callback(_payload):
            raise RuntimeError("callback failed")

        trace = self.logger._new_trace("问题", "ask", live_callback=failing_callback, model="", base_url="")
        self.logger._append_trace(trace, "route")
        self.logger._flush_trace(trace, {"answer": "x"})

        with patch("builtins.open", side_effect=OSError("disk failed")):
            self.logger._write_trace_line({"type": "probe"})

        self.assertEqual(len(trace["events"]), 1)
        self.assertEqual(len(self._read_lines()), 2)

    def test_facade_signatures_remain_compatible(self):
        class SignatureBaseline:
            def _new_trace(
                self,
                question: str,
                entry: str,
                live_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
            ) -> Dict[str, Any]:
                raise NotImplementedError

            def _write_trace_line(self, payload: Dict[str, Any]) -> None:
                raise NotImplementedError

            def _emit_live_trace(self, trace: Optional[Dict[str, Any]], payload: Dict[str, Any]) -> None:
                raise NotImplementedError

            def _append_trace(
                self,
                trace: Optional[Dict[str, Any]],
                stage: str,
                status: str = "info",
                **payload: Any,
            ) -> None:
                raise NotImplementedError

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
                raise NotImplementedError

            def _flush_trace(
                self,
                trace: Optional[Dict[str, Any]],
                result: Optional[Dict[str, Any]] = None,
            ) -> None:
                raise NotImplementedError

        names = (
            "_new_trace",
            "_write_trace_line",
            "_emit_live_trace",
            "_append_trace",
            "_append_llm_delta",
            "_flush_trace",
        )
        actual = {name: inspect.signature(getattr(FourAgentAskService, name)) for name in names}
        expected = {name: inspect.signature(getattr(SignatureBaseline, name)) for name in names}
        self.assertEqual(actual, expected)

    def test_facade_values_and_basic_service_probe_remain_compatible(self):
        service = object.__new__(FourAgentAskService)
        service._llm_model = "facade-model"
        service._llm_client = type("Client", (), {"base_url": "https://facade.example/v1"})()
        service._trace_file_path = str(self.trace_path)
        service.trace_logger = TraceLogger(service._trace_file_path)

        trace = service._new_trace("问题", "basic")
        self.assertEqual(trace["model"], "facade-model")
        self.assertEqual(trace["base_url"], "https://facade.example/v1")

        BasicAskService(delegate=service).write_controller_probe({"type": "controller_probe", "ok": True})
        self.assertEqual(self._read_lines(), [{"type": "controller_probe", "ok": True}])


if __name__ == "__main__":
    unittest.main()
