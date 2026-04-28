"""
Smart chat controller for dataset-isolated four-agent orchestration.
"""

from flask import Blueprint, jsonify, request
import json
import inspect
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datasource_router import router as legacy_router
from four_agent_ask import four_agent_ask_service


smart_chat_bp = Blueprint("smart_chat", __name__)


def _append_controller_debug(event: str, **payload):
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(log_dir, exist_ok=True)
    line = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "event": event,
    }
    line.update(payload)
    with open(os.path.join(log_dir, "smart_chat_controller.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + "\n")


@smart_chat_bp.route("/api/smart-chat", methods=["POST"])
def smart_chat():
    started = time.time()
    try:
        _append_controller_debug("smart_chat.request.enter")
        payload = request.get_json() or {}
        _append_controller_debug("smart_chat.request.payload", payload=payload)
        _append_controller_debug(
            "smart_chat.service.meta",
            service_module=four_agent_ask_service.__class__.__module__,
            service_file=inspect.getsourcefile(four_agent_ask_service.__class__),
        )
        if hasattr(four_agent_ask_service, "_write_trace_line"):
            four_agent_ask_service._write_trace_line(
                {
                    "type": "controller_probe",
                    "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    "question": payload.get("question", ""),
                }
            )
        question = (payload.get("question") or "").strip()
        selected_dataset_ids = payload.get("selected_dataset_ids")
        if not question:
            _append_controller_debug("smart_chat.request.reject", reason="empty_question")
            return jsonify({"error": "Question cannot be empty."}), 400
        if selected_dataset_ids is not None and not isinstance(selected_dataset_ids, list):
            _append_controller_debug("smart_chat.request.reject", reason="selected_dataset_ids_not_list")
            return jsonify({"error": "selected_dataset_ids must be a list when provided."}), 400

        _append_controller_debug(
            "smart_chat.service.ask.start",
            question=question,
            selected_dataset_ids=selected_dataset_ids,
        )
        result = four_agent_ask_service.ask(question, preferred_dataset_ids=selected_dataset_ids)
        _append_controller_debug(
            "smart_chat.service.ask.done",
            has_error=bool(result.get("error")),
            keys=sorted(result.keys()),
        )
        result["total_duration"] = round(time.time() - started, 2)

        if result.get("error"):
            _append_controller_debug("smart_chat.response.error", error=result.get("error"))
            return jsonify(result), 400
        _append_controller_debug("smart_chat.response.success", total_duration=result["total_duration"])
        return jsonify(result)
    except Exception as exc:
        _append_controller_debug("smart_chat.response.exception", error=str(exc))
        return jsonify(
            {
                "error": f"smart-chat failed: {exc}",
                "total_duration": round(time.time() - started, 2),
            }
        ), 500


@smart_chat_bp.route("/api/smart-chat/confirm-by-boss", methods=["POST"])
def confirm_by_boss():
    started = time.time()
    try:
        payload = request.get_json() or {}
        session_id = (payload.get("session_id") or "").strip()
        selected_option = (payload.get("selected_option") or "").strip()
        option_id = (payload.get("option_id") or "").strip()
        selected_dataset_ids = payload.get("selected_dataset_ids")

        if not session_id:
            return jsonify({"error": "session_id is required."}), 400

        if selected_dataset_ids is not None and not isinstance(selected_dataset_ids, list):
            return jsonify({"error": "selected_dataset_ids must be a list when provided."}), 400

        result = four_agent_ask_service.confirm_by_boss(
            session_id=session_id,
            selected_option=selected_option,
            selected_dataset_ids=selected_dataset_ids,
            option_id=option_id,
        )
        result["total_duration"] = round(time.time() - started, 2)

        if result.get("error"):
            return jsonify(result), 400
        return jsonify(result)
    except Exception as exc:
        return jsonify(
            {
                "error": f"confirm-by-boss failed: {exc}",
                "total_duration": round(time.time() - started, 2),
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
