"""
Smart chat controller for dataset-isolated four-agent orchestration.
"""

from flask import Blueprint, jsonify, request
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datasource_router import router as legacy_router
from four_agent_ask import four_agent_ask_service


smart_chat_bp = Blueprint("smart_chat", __name__)


@smart_chat_bp.route("/api/smart-chat", methods=["POST"])
def smart_chat():
    started = time.time()
    try:
        payload = request.get_json() or {}
        question = (payload.get("question") or "").strip()
        selected_dataset_ids = payload.get("selected_dataset_ids")
        if not question:
            return jsonify({"error": "Question cannot be empty."}), 400
        if selected_dataset_ids is not None and not isinstance(selected_dataset_ids, list):
            return jsonify({"error": "selected_dataset_ids must be a list when provided."}), 400

        result = four_agent_ask_service.ask(question, preferred_dataset_ids=selected_dataset_ids)
        result["total_duration"] = round((time.time() - started) * 1000, 2)

        if result.get("error"):
            return jsonify(result), 400
        return jsonify(result)
    except Exception as exc:
        return jsonify(
            {
                "error": f"smart-chat failed: {exc}",
                "total_duration": round((time.time() - started) * 1000, 2),
            }
        ), 500


@smart_chat_bp.route("/api/smart-chat/confirm-by-boss", methods=["POST"])
def confirm_by_boss():
    started = time.time()
    try:
        payload = request.get_json() or {}
        session_id = (payload.get("session_id") or "").strip()
        selected_option = (payload.get("selected_option") or "").strip()
        selected_dataset_ids = payload.get("selected_dataset_ids")

        if not session_id:
            return jsonify({"error": "session_id is required."}), 400

        if selected_dataset_ids is not None and not isinstance(selected_dataset_ids, list):
            return jsonify({"error": "selected_dataset_ids must be a list when provided."}), 400

        result = four_agent_ask_service.confirm_by_boss(
            session_id=session_id,
            selected_option=selected_option,
            selected_dataset_ids=selected_dataset_ids,
        )
        result["total_duration"] = round((time.time() - started) * 1000, 2)

        if result.get("error"):
            return jsonify(result), 400
        return jsonify(result)
    except Exception as exc:
        return jsonify(
            {
                "error": f"confirm-by-boss failed: {exc}",
                "total_duration": round((time.time() - started) * 1000, 2),
            }
        ), 500


@smart_chat_bp.route("/api/data-sources", methods=["GET"])
def list_data_sources():
    try:
        sources = []
        for ds_id, config in legacy_router.data_sources.items():
            sources.append(
                {
                    "id": ds_id,
                    "name": config["name"],
                    "type": config["type"],
                    "keywords": legacy_router.keywords.get(ds_id, []),
                }
            )
        return jsonify({"data_sources": sources, "total": len(sources)})
    except Exception as exc:
        return jsonify({"error": f"list data sources failed: {exc}"}), 500


@smart_chat_bp.route("/api/test-source-identification", methods=["POST"])
def test_source_identification():
    try:
        payload = request.get_json() or {}
        question = (payload.get("question") or "").strip()
        if not question:
            return jsonify({"error": "Question cannot be empty."}), 400

        route = four_agent_ask_service.route_with_agent1(question)
        return jsonify({"question": question, "route": route})
    except Exception as exc:
        return jsonify({"error": f"route test failed: {exc}"}), 500
