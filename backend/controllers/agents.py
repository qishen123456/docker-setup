"""
Agent management controller.
"""

from flask import Blueprint, jsonify, request
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_registry import get_agent, load_agents, update_agent
from security import require_feature


agents_bp = Blueprint("agents", __name__)


@agents_bp.route("/api/agents", methods=["GET"])
def list_agents():
    _, denied = require_feature("agent_management", "当前账号没有查看智能体配置权限")
    if denied:
        return denied
    try:
        return jsonify({"agents": load_agents()})
    except Exception as exc:
        return jsonify({"error": f"list agents failed: {exc}"}), 500


@agents_bp.route("/api/agents/<int:agent_no>", methods=["GET"])
def get_agent_detail(agent_no: int):
    _, denied = require_feature("agent_management", "当前账号没有查看智能体配置权限")
    if denied:
        return denied
    try:
        item = get_agent(agent_no)
        if not item:
            return jsonify({"error": f"agent not found: {agent_no}"}), 404
        return jsonify({"agent": item})
    except Exception as exc:
        return jsonify({"error": f"get agent failed: {exc}"}), 500


@agents_bp.route("/api/agents/<int:agent_no>", methods=["PUT"])
def update_agent_detail(agent_no: int):
    _, denied = require_feature("agent_config_edit", "当前账号没有保存智能体配置权限")
    if denied:
        return denied
    try:
        payload = request.get_json() or {}
        updated = update_agent(agent_no, payload)
        return jsonify({"agent": updated, "message": "agent updated"})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": f"update agent failed: {exc}"}), 500
