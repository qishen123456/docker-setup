"""
Chat controller (primary endpoint) powered by four-agent ask service.
"""

from flask import Blueprint, jsonify, request
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_manager import add_query_history, get_query_history
from four_agent_ask import four_agent_ask_service


chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/api/chat", methods=["POST"])
def chat():
    try:
        payload = request.get_json() or {}
        question = (payload.get("question") or "").strip()
        if not question:
            return jsonify({"error": "Question cannot be empty."}), 400

        result = four_agent_ask_service.ask(question)
        if result.get("error"):
            add_query_history(question, "", "error", result.get("error", "unknown error"))
            return jsonify(result), 400

        add_query_history(question, result.get("sql", ""), "success")
        return jsonify(result)
    except Exception as exc:
        add_query_history(
            (request.get_json() or {}).get("question", ""),
            "",
            "error",
            str(exc),
        )
        return jsonify({"error": f"chat failed: {exc}"}), 500


@chat_bp.route("/api/chat/generate-sql", methods=["POST"])
def generate_sql_only():
    try:
        payload = request.get_json() or {}
        question = (payload.get("question") or "").strip()
        if not question:
            return jsonify({"error": "Question cannot be empty."}), 400

        result = four_agent_ask_service.ask(question)
        if result.get("error"):
            return jsonify(result), 400

        return jsonify(
            {
                "question": question,
                "sql": result.get("sql", ""),
                "route": result.get("route", {}),
            }
        )
    except Exception as exc:
        return jsonify({"error": f"generate-sql failed: {exc}"}), 500


@chat_bp.route("/api/chat/history", methods=["GET"])
def get_history():
    try:
        limit = int(request.args.get("limit", 20))
        return jsonify({"history": get_query_history(limit=limit)})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@chat_bp.route("/api/chat/vanna-status", methods=["GET"])
def vanna_status():
    try:
        ready = four_agent_ask_service.repository.is_ready()
        if not ready:
            return (
                jsonify(
                    {
                        "ready": False,
                        "message": (
                            "Bookshelf metadata not initialized. "
                            "Run backend/migrations/20260330_bookshelf_schema.sql first."
                        ),
                    }
                ),
                503,
            )
        return jsonify({"ready": True, "message": "Four-agent pipeline is ready"})
    except Exception as exc:
        return jsonify({"ready": False, "message": str(exc)}), 500
