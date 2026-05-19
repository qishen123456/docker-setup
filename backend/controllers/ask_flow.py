from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from flask import Blueprint, jsonify, request

from ask_flow.controller import DEFAULT_ASK_FLOW_CONFIG, ask_flow_controller
from auth_store import get_current_user
from config_manager import write_json


ask_flow_bp = Blueprint("ask_flow", __name__, url_prefix="/api/admin/ask-flow")


def _require_super_admin():
    user = get_current_user()
    if user.get("role") != "super_admin":
        return None, (jsonify({"success": False, "error": "只有超级管理员可以维护问数流程控制器"}), 403)
    return user, None


def _normalize_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("1", "true", "yes", "on"):
            return True
        if normalized in ("0", "false", "no", "off"):
            return False
    return fallback


def _normalize_flow(value: Any, fallback: str = "basic") -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in ("basic", "advanced") else fallback


def _normalize_roles(value: Any) -> list[str]:
    allowed = {"super_admin", "admin", "business_admin", "user"}
    if not isinstance(value, list):
        return ["super_admin"]
    result = []
    for item in value:
        role = str(item or "").strip()
        if role in allowed and role not in result:
            result.append(role)
    return result or ["super_admin"]


def _normalize_dataset_policies(value: Any) -> Dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result: Dict[str, str] = {}
    for key, flow in value.items():
        try:
            dataset_id = str(int(key))
        except Exception:
            continue
        normalized_flow = _normalize_flow(flow, "")
        if normalized_flow:
            result[dataset_id] = normalized_flow
    return result


def _normalize_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    current = ask_flow_controller.load_config()
    config = deepcopy(DEFAULT_ASK_FLOW_CONFIG)
    config.update({key: current.get(key, value) for key, value in DEFAULT_ASK_FLOW_CONFIG.items()})
    config["defaultFlow"] = _normalize_flow(payload.get("defaultFlow", config.get("defaultFlow")), "basic")
    config["advancedEnabled"] = _normalize_bool(payload.get("advancedEnabled"), bool(config.get("advancedEnabled")))
    config["advancedRoles"] = _normalize_roles(payload.get("advancedRoles", config.get("advancedRoles")))
    config["datasetPolicies"] = _normalize_dataset_policies(payload.get("datasetPolicies", config.get("datasetPolicies")))
    config["fallbackToBasicOnError"] = _normalize_bool(
        payload.get("fallbackToBasicOnError"),
        bool(config.get("fallbackToBasicOnError")),
    )
    config["attachMetadata"] = _normalize_bool(payload.get("attachMetadata"), bool(config.get("attachMetadata")))
    return config


@ask_flow_bp.route("", methods=["GET"])
def get_ask_flow_config():
    _, error = _require_super_admin()
    if error:
        return error
    config = ask_flow_controller.load_config()
    return jsonify(
        {
            "success": True,
            "data": {
                "config": config,
                "effectiveDecision": ask_flow_controller.decide(user={"role": "super_admin"}).to_dict(),
            },
        }
    )


@ask_flow_bp.route("", methods=["PUT"])
def update_ask_flow_config():
    user, error = _require_super_admin()
    if error:
        return error
    payload = request.get_json(silent=True) or {}
    raw_config = payload.get("config") if isinstance(payload.get("config"), dict) else payload
    config = _normalize_config(raw_config if isinstance(raw_config, dict) else {})
    write_json("ask_flow.json", config)
    return jsonify(
        {
            "success": True,
            "data": {
                "config": ask_flow_controller.load_config(),
                "effectiveDecision": ask_flow_controller.decide(user={"role": "super_admin"}).to_dict(),
                "operator": user.get("username") or user.get("name") or "",
            },
        }
    )


@ask_flow_bp.route("/reset", methods=["POST"])
def reset_ask_flow_config():
    _, error = _require_super_admin()
    if error:
        return error
    write_json("ask_flow.json", deepcopy(DEFAULT_ASK_FLOW_CONFIG))
    return jsonify(
        {
            "success": True,
            "data": {
                "config": ask_flow_controller.load_config(),
                "effectiveDecision": ask_flow_controller.decide(user={"role": "super_admin"}).to_dict(),
            },
        }
    )
