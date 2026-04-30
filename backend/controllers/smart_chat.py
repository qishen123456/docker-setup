"""
Smart chat controller for dataset-isolated four-agent orchestration.
"""

from flask import Blueprint, Response, jsonify, request, stream_with_context
import json
import inspect
import os
import queue
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datasource_router import router as legacy_router
from four_agent_ask import four_agent_ask_service
import dataset_report_config as drc


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


def _json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


def _sse_frame(event_name: str, payload: dict) -> str:
    return f"event: {event_name}\ndata: {json.dumps(_json_safe(payload), ensure_ascii=False)}\n\n"


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
        session_id = (payload.get("session_id") or "").strip()
        conversation_history = payload.get("conversation_history")
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
        result = four_agent_ask_service.ask(
            question,
            preferred_dataset_ids=selected_dataset_ids,
            session_id=session_id,
            conversation_history=conversation_history if isinstance(conversation_history, list) else None,
        )
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


@smart_chat_bp.route("/api/smart-chat/stream", methods=["POST"])
def smart_chat_stream():
    started = time.time()
    payload = request.get_json() or {}
    question = (payload.get("question") or "").strip()
    session_id = (payload.get("session_id") or "").strip()
    conversation_history = payload.get("conversation_history")
    selected_dataset_ids = payload.get("selected_dataset_ids")
    model_id = payload.get("model_id")  # None = AUTO (use default)

    if not question:
        return jsonify({"error": "Question cannot be empty."}), 400
    if selected_dataset_ids is not None and not isinstance(selected_dataset_ids, list):
        return jsonify({"error": "selected_dataset_ids must be a list when provided."}), 400

    # Normalize model_id
    if model_id is not None:
        try:
            model_id = int(model_id)
        except (ValueError, TypeError):
            model_id = None

    def event_stream():
        event_queue: "queue.Queue[dict]" = queue.Queue()
        completed = threading.Event()

        def emit(payload: dict) -> None:
            event_queue.put(payload)

        def run_ask() -> None:
            try:
                result = four_agent_ask_service.ask(
                    question,
                    preferred_dataset_ids=selected_dataset_ids,
                    live_callback=emit,
                    model_id=model_id,
                    session_id=session_id,
                    conversation_history=conversation_history if isinstance(conversation_history, list) else None,
                )
                result["total_duration"] = round(time.time() - started, 2)
                # Attach report_config if dataset was identified
                ds_id = result.get("dataset_id")
                if ds_id:
                    rc = drc.get_config(int(ds_id))
                    if rc:
                        result["report_config"] = rc
                event_queue.put({"type": "result", "result": result})
            except Exception as exc:
                event_queue.put(
                    {
                        "type": "result",
                        "result": {
                            "error": f"smart-chat failed: {exc}",
                            "total_duration": round(time.time() - started, 2),
                        },
                    }
                )
            finally:
                completed.set()

        worker = threading.Thread(target=run_ask, daemon=True)
        worker.start()
        yield _sse_frame("ready", {"ok": True, "question": question})

        while not completed.is_set() or not event_queue.empty():
            try:
                item = event_queue.get(timeout=1.0)
            except queue.Empty:
                yield _sse_frame("heartbeat", {"time": time.time()})
                continue

            item_type = str(item.get("type") or "")
            if item_type == "trace":
                yield _sse_frame("trace", item)
                continue
            if item_type == "summary":
                yield _sse_frame("summary", item)
                continue
            if item_type == "result":
                yield _sse_frame("result", item.get("result") or {})
                break

        yield _sse_frame("done", {"ok": True})

    response = Response(stream_with_context(event_stream()), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


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
