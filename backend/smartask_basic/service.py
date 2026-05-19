from __future__ import annotations

from typing import Any, Dict

from four_agent_ask import four_agent_ask_service


class BasicAskService:
    """Thin wrapper around the existing four-agent pipeline."""

    name = "basic"

    def __init__(self, delegate=None):
        self.delegate = delegate or four_agent_ask_service

    @property
    def repository(self):
        return self.delegate.repository

    def ask(self, **kwargs) -> Dict[str, Any]:
        return self.delegate.ask(**kwargs)

    def confirm_by_boss(self, **kwargs) -> Dict[str, Any]:
        return self.delegate.confirm_by_boss(**kwargs)

    def route_with_agent1(self, *args, **kwargs) -> Dict[str, Any]:
        return self.delegate.route_with_agent1(*args, **kwargs)

    def write_controller_probe(self, payload: Dict[str, Any]) -> None:
        if hasattr(self.delegate, "_write_trace_line"):
            self.delegate._write_trace_line(payload)


basic_ask_service = BasicAskService()
