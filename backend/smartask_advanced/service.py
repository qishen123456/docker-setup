from __future__ import annotations

from typing import Any, Dict

from smartask_basic.service import basic_ask_service


class AdvancedAskService:
    """
    Placeholder for the future advanced ask engine.

    For the first controller rollout this intentionally mirrors the basic
    engine so enabling the shell cannot change ask behavior. New skills and
    planners should be added here, not inside four_agent_ask.py.
    """

    name = "advanced"

    def __init__(self, fallback_service=None):
        self.fallback_service = fallback_service or basic_ask_service

    @property
    def repository(self):
        return self.fallback_service.repository

    def ask(self, **kwargs) -> Dict[str, Any]:
        return self.fallback_service.ask(**kwargs)

    def confirm_by_boss(self, **kwargs) -> Dict[str, Any]:
        return self.fallback_service.confirm_by_boss(**kwargs)

    def route_with_agent1(self, *args, **kwargs) -> Dict[str, Any]:
        return self.fallback_service.route_with_agent1(*args, **kwargs)

    def write_controller_probe(self, payload: Dict[str, Any]) -> None:
        self.fallback_service.write_controller_probe(payload)


advanced_ask_service = AdvancedAskService()
