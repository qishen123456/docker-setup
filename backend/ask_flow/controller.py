from __future__ import annotations

import os
import time
from copy import deepcopy
from typing import Any, Dict, Iterable, Optional

from config_manager import read_json
from smartask_basic.service import basic_ask_service
from smartask_advanced.service import advanced_ask_service

from .contracts import AskRequest, ConfirmRequest, FlowDecision


DEFAULT_ASK_FLOW_CONFIG: Dict[str, Any] = {
    "defaultFlow": "basic",
    "advancedEnabled": False,
    "advancedRoles": ["super_admin"],
    "datasetPolicies": {},
    "fallbackToBasicOnError": True,
    "attachMetadata": True,
}
ADVANCED_ASK_FLOW_FEATURE_KEY = "advanced_ask_flow"


class AskFlowController:
    """Selects the ask engine while keeping the old basic flow untouched."""

    def __init__(self, basic_service=None, advanced_service=None):
        self.basic_service = basic_service or basic_ask_service
        self.advanced_service = advanced_service or advanced_ask_service

    def load_config(self) -> Dict[str, Any]:
        config = deepcopy(DEFAULT_ASK_FLOW_CONFIG)
        stored = read_json("ask_flow.json")
        if isinstance(stored, dict):
            for key, value in stored.items():
                if key == "datasetPolicies" and isinstance(value, dict):
                    config[key].update(value)
                elif key in config:
                    config[key] = value

        env_default = (os.getenv("SMARTASK_DEFAULT_FLOW") or "").strip().lower()
        if env_default in ("basic", "advanced"):
            config["defaultFlow"] = env_default

        env_advanced = (os.getenv("SMARTASK_ADVANCED_FLOW_ENABLED") or "").strip().lower()
        if env_advanced in ("1", "true", "yes", "on"):
            config["advancedEnabled"] = True
        elif env_advanced in ("0", "false", "no", "off"):
            config["advancedEnabled"] = False
        return config

    def active_service(self):
        return self.basic_service

    def route_with_agent1(self, *args, **kwargs) -> Dict[str, Any]:
        return self.basic_service.route_with_agent1(*args, **kwargs)

    def _role_allowed(self, user: Optional[Dict[str, Any]], config: Dict[str, Any]) -> bool:
        roles = config.get("advancedRoles") or []
        if not roles:
            return True
        allowed_roles = {str(item).strip() for item in roles if str(item).strip()}
        user_roles = set()
        role = str((user or {}).get("role") or "").strip()
        if role:
            user_roles.add(role)
        role_ids = (user or {}).get("role_ids")
        if isinstance(role_ids, list):
            user_roles.update(str(item).strip() for item in role_ids if str(item).strip())
        if allowed_roles.intersection(user_roles):
            return True
        try:
            from feature_flags import feature_available
            return feature_available(ADVANCED_ASK_FLOW_FEATURE_KEY, user or {})
        except Exception:
            return False

    @staticmethod
    def _first_dataset_id(dataset_ids: Optional[Iterable[Any]]) -> str:
        for item in dataset_ids or []:
            try:
                return str(int(item))
            except Exception:
                continue
        return ""

    def decide(self, *, user: Optional[Dict[str, Any]], requested_flow: str = "", dataset_ids=None) -> FlowDecision:
        config = self.load_config()
        requested = str(requested_flow or "").strip().lower()
        dataset_policy = ""
        dataset_id = self._first_dataset_id(dataset_ids)
        policies = config.get("datasetPolicies") if isinstance(config.get("datasetPolicies"), dict) else {}
        if dataset_id:
            dataset_policy = str(policies.get(dataset_id) or "").strip().lower()

        candidate = requested if requested in ("basic", "advanced") else ""
        if not candidate and dataset_policy in ("basic", "advanced"):
            candidate = dataset_policy
        if not candidate:
            candidate = str(config.get("defaultFlow") or "basic").strip().lower()
        if candidate not in ("basic", "advanced"):
            candidate = "basic"

        if candidate != "advanced":
            return FlowDecision("basic", "basic_selected", requested, config)
        if not bool(config.get("advancedEnabled")):
            return FlowDecision("basic", "advanced_disabled", requested, config)
        if not self._role_allowed(user, config):
            return FlowDecision("basic", "advanced_role_denied", requested, config)
        return FlowDecision("advanced", "advanced_selected", requested, config)

    def _service_for(self, decision: FlowDecision):
        if decision.flow == "advanced":
            return self.advanced_service
        return self.basic_service

    @staticmethod
    def _attach_metadata(result: Dict[str, Any], decision: FlowDecision, started: float) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return result
        if decision.config.get("attachMetadata") is False:
            result.pop("ask_flow", None)
            diagnostics = result.get("diagnostics")
            if isinstance(diagnostics, dict):
                diagnostics.pop("ask_flow", None)
            return result
        metadata = {
            "flow": decision.flow,
            "reason": decision.reason,
            "requested_flow": decision.requested_flow,
            "controller": "AskFlowController",
            "duration_seconds": round(time.time() - started, 3),
        }
        result.setdefault("ask_flow", metadata)
        diagnostics = result.get("diagnostics")
        if isinstance(diagnostics, dict):
            diagnostics.setdefault("ask_flow", metadata)
        return result

    def ask(self, request: AskRequest) -> Dict[str, Any]:
        started = time.time()
        decision = self.decide(
            user=request.current_user,
            requested_flow=request.requested_flow,
            dataset_ids=request.preferred_dataset_ids,
        )
        service = self._service_for(decision)
        try:
            result = service.ask(
                question=request.question,
                preferred_dataset_ids=request.preferred_dataset_ids,
                allowed_dataset_ids=request.allowed_dataset_ids,
                live_callback=request.live_callback,
                model_id=request.model_id,
                session_id=request.session_id,
                conversation_history=request.conversation_history,
                current_user=request.current_user,
            )
        except Exception:
            if decision.flow != "advanced" or not bool(decision.config.get("fallbackToBasicOnError", True)):
                raise
            fallback_decision = FlowDecision(
                "basic",
                "advanced_error_fallback",
                decision.requested_flow,
                decision.config,
            )
            result = self.basic_service.ask(
                question=request.question,
                preferred_dataset_ids=request.preferred_dataset_ids,
                allowed_dataset_ids=request.allowed_dataset_ids,
                live_callback=request.live_callback,
                model_id=request.model_id,
                session_id=request.session_id,
                conversation_history=request.conversation_history,
                current_user=request.current_user,
            )
            decision = fallback_decision
        return self._attach_metadata(result, decision, started)

    def confirm_by_boss(self, request: ConfirmRequest) -> Dict[str, Any]:
        started = time.time()
        decision = self.decide(
            user=request.current_user,
            requested_flow=request.requested_flow,
            dataset_ids=request.selected_dataset_ids,
        )
        service = self._service_for(decision)
        try:
            result = service.confirm_by_boss(
                session_id=request.session_id,
                selected_option=request.selected_option,
                selected_dataset_ids=request.selected_dataset_ids,
                allowed_dataset_ids=request.allowed_dataset_ids,
                option_id=request.option_id,
                live_callback=request.live_callback,
                current_user=request.current_user,
            )
        except Exception:
            if decision.flow != "advanced" or not bool(decision.config.get("fallbackToBasicOnError", True)):
                raise
            fallback_decision = FlowDecision(
                "basic",
                "advanced_error_fallback",
                decision.requested_flow,
                decision.config,
            )
            result = self.basic_service.confirm_by_boss(
                session_id=request.session_id,
                selected_option=request.selected_option,
                selected_dataset_ids=request.selected_dataset_ids,
                allowed_dataset_ids=request.allowed_dataset_ids,
                option_id=request.option_id,
                live_callback=request.live_callback,
                current_user=request.current_user,
            )
            decision = fallback_decision
        return self._attach_metadata(result, decision, started)

    def write_controller_probe(self, payload: Dict[str, Any]) -> None:
        self.basic_service.write_controller_probe(payload)


ask_flow_controller = AskFlowController()
