import ast
import inspect
import os
import sys
import textwrap
import unittest
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from four_agent_ask import FourAgentAskService
from llm_client import LLMClient


class FakeCompletions:
    def __init__(self, outcome, calls):
        self.outcome = outcome
        self.calls = calls

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class FakeOpenAIFactory:
    def __init__(self, outcomes):
        self.outcomes = outcomes
        self.created = []
        self.calls = []

    def __call__(self, api_key, base_url):
        self.created.append((api_key, base_url))
        completions = FakeCompletions(self.outcomes[base_url], self.calls)
        return SimpleNamespace(
            base_url=base_url,
            chat=SimpleNamespace(completions=completions),
        )


def chunk(content="", reasoning="", **extra):
    delta = SimpleNamespace(
        content=content,
        reasoning_content=reasoning,
        model_extra=extra or None,
        additional_kwargs=None,
        model_dump=lambda: {},
    )
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


class LLMClientCharacterizationTest(unittest.TestCase):
    def _client(self, *, models=None, default=None, outcomes=None):
        traces = []
        deltas = []
        factory = FakeOpenAIFactory(outcomes or {})
        client = LLMClient(
            openai_factory=factory,
            get_default_config=lambda: default,
            get_configs=lambda: list(models or []),
            decode_secret=lambda value: f"decoded:{value}",
            should_retry=lambda exc: exc.__class__.__name__ in {
                "APITimeoutError",
                "RateLimitError",
            },
            append_trace=lambda trace, stage, status="info", **payload: traces.append(
                {"stage": stage, "status": status, **payload}
            ),
            append_llm_delta=lambda trace, stage, agent, delta, stream, started, **payload: deltas.append(
                {
                    "stage": stage,
                    "agent": agent,
                    "delta": delta,
                    "stream": stream,
                    **payload,
                }
            ),
            extract_json_block=lambda text: text[text.find("{") : text.rfind("}") + 1],
            truncate_text=lambda value, limit: str(value)[:limit],
        )
        return client, factory, traces, deltas

    def test_candidates_preferred_default_active_dedupe_and_secret_decode(self):
        models = [
            {"id": 1, "model": "default", "base_url": "u1", "api_key_b64": "k1", "is_active": True},
            {"id": 2, "model": "preferred", "base_url": "u2", "api_key_b64": "k2", "is_active": True},
            {"id": 3, "model": "default", "base_url": "u1", "api_key_b64": "k1", "is_active": True},
            {"id": 4, "model": "other", "base_url": "u4", "api_key_b64": "k4", "is_active": True},
            {"id": 5, "model": "inactive", "base_url": "u5", "api_key_b64": "k5", "is_active": False},
        ]
        default = {"id": 1, "model": "default", "base_url": "u1", "api_key": "decoded:k1", "is_active": True}
        client, _, _, _ = self._client(models=models, default=default)

        candidates = client._candidate_llm_configs(preferred_model_id=2)

        self.assertEqual([item["id"] for item in candidates], [2, 1, 4])
        self.assertEqual(candidates[0]["api_key"], "decoded:k2")
        self.assertNotIn("api_key_b64", candidates[0])
        self.assertNotIn(5, [item["id"] for item in candidates])
        self.assertNotEqual(client._candidate_llm_configs(preferred_model_id=5)[0]["id"], 5)

    def test_load_activate_state_and_no_model_error(self):
        default = {"model": "m", "base_url": "u", "api_key": "key"}
        client, factory, _, _ = self._client(default=default, models=[{**default, "is_active": True}], outcomes={"u": []})
        client._load_llm()
        self.assertEqual(client._llm_model, "m")
        self.assertEqual(factory.created[-1], ("key", "u"))
        self.assertIsNotNone(client._llm_client)

        empty, _, _, _ = self._client()
        with self.assertRaisesRegex(RuntimeError, "Default AI model is not configured"):
            empty._chat("system", "user")

    def test_stream_parser_content_reasoning_and_pending_flush(self):
        stream = [
            chunk(content=[{"text": "hello"}, {"content": " world"}]),
            chunk(reasoning="because"),
            chunk(reasoning_text=" fallback-reason"),
        ]
        config = {"id": 1, "model": "m", "base_url": "u", "api_key": "k", "is_active": True}
        client, factory, traces, deltas = self._client(models=[config], default=config, outcomes={"u": stream})

        with patch("llm_client.time.time", return_value=10.0):
            result = client._chat("system", "user", trace={}, stage="agent2", agent_name="Agent2")

        self.assertEqual(result, "hello world")
        self.assertEqual([item["status"] for item in traces], ["request", "response"])
        self.assertEqual(len(deltas), 2)
        self.assertEqual(deltas[0]["delta"], "hello world")
        self.assertEqual(deltas[0]["stream"], "hello world")
        self.assertEqual(deltas[1]["reasoning_delta"], "because fallback-reason")
        self.assertEqual(deltas[1]["delta_kind"], "reasoning")
        call = factory.calls[0]
        self.assertEqual(call["temperature"], 0.1)
        self.assertEqual(call["timeout"], 180)
        self.assertTrue(call["stream"])

    def test_retry_switches_model_and_non_retryable_raises(self):
        Retryable = type("APITimeoutError", (Exception,), {})
        configs = [
            {"id": 1, "model": "m1", "base_url": "u1", "api_key_b64": "k1", "is_active": True},
            {"id": 2, "model": "m2", "base_url": "u2", "api_key_b64": "k2", "is_active": True},
        ]
        default = {"id": 1, "model": "m1", "base_url": "u1", "api_key": "decoded:k1", "is_active": True}
        client, factory, traces, _ = self._client(
            models=configs,
            default=default,
            outcomes={"u1": Retryable("timeout"), "u2": [chunk(content="ok")]},
        )
        self.assertEqual(client._chat("s", "u", trace={}, stage="agent1"), "ok")
        self.assertEqual([item["status"] for item in traces], ["request", "retry", "request", "response"])
        self.assertEqual(factory.created[-1], ("decoded:k2", "u2"))
        self.assertTrue(traces[1]["retry_with_next_model"])

        client, _, traces, _ = self._client(
            models=configs,
            default=default,
            outcomes={"u1": ValueError("bad request"), "u2": [chunk(content="unused")]},
        )
        with self.assertRaisesRegex(ValueError, "bad request"):
            client._chat("s", "u", trace={}, stage="agent1")
        self.assertEqual([item["status"] for item in traces], ["request", "error"])
        self.assertFalse(traces[-1]["retry_with_next_model"])

    def test_chat_json_success_fallback_trace_and_monkeypatch_contract(self):
        client, _, traces, _ = self._client()
        client._chat = lambda *args, **kwargs: "prefix {\"ok\": true} suffix"
        self.assertEqual(client._chat_json("s", "u", {"ok": False}, trace={}, stage="agent3"), {"ok": True})
        self.assertEqual(traces[-1], {"stage": "agent3", "status": "parsed", "agent": "", "parsed_json": {"ok": True}})

        client._chat = lambda *args, **kwargs: "not json"
        fallback = {"ok": False}
        self.assertIs(client._chat_json("s", "u", fallback, trace={}, stage="agent3"), fallback)
        self.assertEqual(traces[-1]["status"], "fallback")
        self.assertEqual(traces[-1]["fallback"], fallback)
        self.assertIn("traceback", traces[-1])

        service = object.__new__(FourAgentAskService)
        fake = lambda *args, **kwargs: {"patched": True}
        service._chat_json = fake
        self.assertIs(service._chat_json, fake)

    def test_facade_signatures_match_locked_baseline(self):
        class SignatureBaseline:
            def _load_llm(self):
                raise NotImplementedError

            def _activate_llm(self, config: Dict[str, Any]) -> None:
                raise NotImplementedError

            def _candidate_llm_configs(
                self, preferred_model_id: Optional[int] = None
            ) -> List[Dict[str, Any]]:
                raise NotImplementedError

            def _chat(
                self,
                system_prompt: str,
                user_prompt: str,
                max_tokens: int = 2400,
                trace: Optional[Dict[str, Any]] = None,
                stage: str = "",
                agent_name: str = "",
            ) -> str:
                raise NotImplementedError

            def _chat_json(
                self,
                system_prompt: str,
                user_prompt: str,
                fallback: Dict[str, Any],
                trace: Optional[Dict[str, Any]] = None,
                stage: str = "",
                agent_name: str = "",
            ) -> Dict[str, Any]:
                raise NotImplementedError

        names = (
            "_load_llm",
            "_activate_llm",
            "_candidate_llm_configs",
            "_chat",
            "_chat_json",
        )
        actual = {name: inspect.signature(getattr(FourAgentAskService, name)) for name in names}
        expected = {name: inspect.signature(getattr(SignatureBaseline, name)) for name in names}
        self.assertEqual(actual, expected)

    def test_facade_properties_are_bidirectional_without_state_copies(self):
        service = object.__new__(FourAgentAskService)
        component = service._llm_component()
        fake_client = object()

        service._llm_client = fake_client
        service._llm_model = "model-a"
        service._preferred_model_id = 17
        self.assertIs(component._llm_client, fake_client)
        self.assertEqual(component._llm_model, "model-a")
        self.assertEqual(component._preferred_model_id, 17)

        component._llm_client = None
        component._llm_model = "model-b"
        component._preferred_model_id = 23
        self.assertIsNone(service._llm_client)
        self.assertEqual(service._llm_model, "model-b")
        self.assertEqual(service._preferred_model_id, 23)
        self.assertFalse(
            {"_llm_client", "_llm_model", "_preferred_model_id"} & service.__dict__.keys()
        )

    def test_ask_sets_preferred_model_before_new_trace(self):
        source = textwrap.dedent(inspect.getsource(FourAgentAskService.ask))
        tree = ast.parse(source)
        assignments = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
                and target.attr == "_preferred_model_id"
                for target in node.targets
            )
        ]
        new_trace_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_new_trace"
        ]
        self.assertEqual(len(assignments), 1)
        self.assertEqual(len(new_trace_calls), 1)
        self.assertLess(assignments[0].lineno, new_trace_calls[0].lineno)

        service = object.__new__(FourAgentAskService)
        service._preferred_model_id = 31
        self.assertEqual(service._llm_component()._preferred_model_id, 31)


if __name__ == "__main__":
    unittest.main()
