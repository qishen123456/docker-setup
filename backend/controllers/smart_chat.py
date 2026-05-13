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
from auth_store import get_current_user
from data_permission_store import allowed_dataset_ids_for_user
from system_log_store import log_event, request_snapshot


smart_chat_bp = Blueprint("smart_chat", __name__)


def _active_dataset_ids() -> list[int]:
    try:
        return [int(item.get("id")) for item in four_agent_ask_service.repository.get_agent1_catalog() if item.get("id") is not None]
    except Exception:
        return []


def _allowed_dataset_ids(user: dict) -> list[int]:
    return allowed_dataset_ids_for_user(user or {}, _active_dataset_ids())


def _filter_requested_dataset_ids(user: dict, selected_dataset_ids):
    if selected_dataset_ids is None:
        return None
    allowed = set(_allowed_dataset_ids(user))
    filtered = []
    for item in selected_dataset_ids:
        try:
            dataset_id = int(item)
        except (TypeError, ValueError):
            continue
        if dataset_id in allowed and dataset_id not in filtered:
            filtered.append(dataset_id)
    return filtered


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


def _safe_int(value, fallback=0) -> int:
    try:
        return int(value)
    except Exception:
        return fallback


def _is_low_confidence(result: dict) -> bool:
    if not isinstance(result, dict) or result.get("error"):
        return False
    if result.get("requires_confirmation"):
        return True
    confidence = result.get("confidence") if isinstance(result.get("confidence"), dict) else {}
    route = confidence.get("route") if isinstance(confidence.get("route"), dict) else {}
    output = confidence.get("result") if isinstance(confidence.get("result"), dict) else {}
    route_score = _safe_int(route.get("score"), 100)
    output_score = _safe_int(output.get("score"), 100) if output else 100
    return route.get("level") == "low" or output.get("level") == "low" or route_score < 65 or output_score < 62


def _compact_trace_events(trace_events: list) -> list:
    rows = []
    for payload in trace_events or []:
        if not isinstance(payload, dict):
            continue
        if payload.get("type") == "trace" and isinstance(payload.get("event"), dict):
            events = [payload.get("event")]
        elif payload.get("type") == "summary" and isinstance(payload.get("events"), list):
            events = payload.get("events")
        else:
            events = []
        for event in events:
            if not isinstance(event, dict):
                continue
            rows.append(
                {
                    "time": event.get("time"),
                    "stage": event.get("stage"),
                    "status": event.get("status"),
                    "agent": event.get("agent"),
                    "duration_seconds": event.get("duration_seconds"),
                    "detail": event.get("detail") or event.get("message") or event.get("summary") or event.get("error") or "",
                    "reasoning": event.get("reasoning_text") or event.get("reasoning_delta") or "",
                    "stream": event.get("stream_text") or event.get("delta_text") or "",
                    "sql": event.get("sql") or event.get("final_sql") or "",
                    "risk": event.get("risks") or event.get("risk") or "",
                }
            )
    return rows[-180:]


def _compact_dataset_results(result: dict) -> list:
    compact = []
    for item in result.get("dataset_results") or []:
        if not isinstance(item, dict):
            continue
        compact.append(
            {
                "dataset_id": item.get("dataset_id"),
                "dataset_name": item.get("dataset_name"),
                "sql": item.get("sql") or "",
                "row_count": item.get("row_count"),
                "columns": item.get("columns") or [],
                "rows_preview": (item.get("rows") or [])[:20],
                "analysis": item.get("analysis") or "",
                "agent3_review": item.get("agent3_review") or {},
            }
        )
    return compact


def _log_smart_chat_result(
    *,
    result: dict,
    question: str,
    started: float,
    user: dict,
    request_info: dict,
    trace_events: list | None = None,
    event_prefix: str = "smart_chat",
) -> None:
    result = result or {}
    duration_ms = int((time.time() - started) * 1000)
    has_error = bool(result.get("error"))
    low_confidence = _is_low_confidence(result)
    if has_error:
        category = "error"
        level = "error"
        event_type = f"{event_prefix}_error"
        title = "智能问数执行失败"
    elif low_confidence:
        category = "low_confidence"
        level = "warning"
        event_type = f"{event_prefix}_low_confidence"
        title = "低置信度智能问数结果"
    else:
        category = "qa"
        level = "info"
        event_type = f"{event_prefix}_answer"
        title = "智能问数结果"

    log_event(
        category=category,
        event_type=event_type,
        level=level,
        title=title,
        user=user,
        request_info=request_info,
        status_code=500 if has_error else 200,
        duration_ms=duration_ms,
        question=result.get("question") or question,
        thinking_process=_compact_trace_events(trace_events or []),
        sql_text=result.get("sql") or "",
        answer_text=result.get("analysis") or "",
        confidence=result.get("confidence") or {},
        error_message=result.get("error") or "",
        details={
            "effective_question": result.get("effective_question") or "",
            "route": result.get("route") or {},
            "data_source": result.get("data_source") or "",
            "row_count": result.get("row_count"),
            "columns": result.get("columns") or [],
            "rows_preview": (result.get("rows") or [])[:20],
            "steps": result.get("steps") or [],
            "dataset_results": _compact_dataset_results(result),
            "requires_confirmation": bool(result.get("requires_confirmation")),
            "conversation_session_id": result.get("conversation_session_id") or "",
            "confirmation_session_id": result.get("session_id") or "",
        },
    )


@smart_chat_bp.route("/api/smart-chat", methods=["POST"])
def smart_chat():
    started = time.time()
    user = get_current_user()
    req_info = request_snapshot(request)
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
        allowed_dataset_ids = _allowed_dataset_ids(user)
        selected_dataset_ids = _filter_requested_dataset_ids(user, selected_dataset_ids)
        if payload.get("selected_dataset_ids") is not None and not selected_dataset_ids:
            return jsonify({"error": "当前账号没有访问所选数据集的权限"}), 403

        _append_controller_debug(
            "smart_chat.service.ask.start",
            question=question,
            selected_dataset_ids=selected_dataset_ids,
            allowed_dataset_ids=allowed_dataset_ids,
        )
        result = four_agent_ask_service.ask(
            question,
            preferred_dataset_ids=selected_dataset_ids,
            allowed_dataset_ids=allowed_dataset_ids,
            session_id=session_id,
            conversation_history=conversation_history if isinstance(conversation_history, list) else None,
        )
        _append_controller_debug(
            "smart_chat.service.ask.done",
            has_error=bool(result.get("error")),
            keys=sorted(result.keys()),
        )
        result["total_duration"] = round(time.time() - started, 2)
        _log_smart_chat_result(
            result=result,
            question=question,
            started=started,
            user=user,
            request_info=req_info,
            event_prefix="smart_chat",
        )

        if result.get("error"):
            _append_controller_debug("smart_chat.response.error", error=result.get("error"))
            return jsonify(result), 400
        _append_controller_debug("smart_chat.response.success", total_duration=result["total_duration"])
        return jsonify(result)
    except Exception as exc:
        _append_controller_debug("smart_chat.response.exception", error=str(exc))
        _log_smart_chat_result(
            result={"error": f"smart-chat failed: {exc}", "question": (request.get_json(silent=True) or {}).get("question", "")},
            question=(request.get_json(silent=True) or {}).get("question", ""),
            started=started,
            user=user,
            request_info=req_info,
            event_prefix="smart_chat",
        )
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
    user = get_current_user()
    req_info = request_snapshot(request)
    question = (payload.get("question") or "").strip()
    session_id = (payload.get("session_id") or "").strip()
    conversation_history = payload.get("conversation_history")
    selected_dataset_ids = payload.get("selected_dataset_ids")
    model_id = payload.get("model_id")  # None = AUTO (use default)

    if not question:
        return jsonify({"error": "Question cannot be empty."}), 400
    if selected_dataset_ids is not None and not isinstance(selected_dataset_ids, list):
        return jsonify({"error": "selected_dataset_ids must be a list when provided."}), 400
    allowed_dataset_ids = _allowed_dataset_ids(user)
    selected_dataset_ids = _filter_requested_dataset_ids(user, selected_dataset_ids)
    if payload.get("selected_dataset_ids") is not None and not selected_dataset_ids:
        return jsonify({"error": "当前账号没有访问所选数据集的权限"}), 403

    # Normalize model_id
    if model_id is not None:
        try:
            model_id = int(model_id)
        except (ValueError, TypeError):
            model_id = None

    def event_stream():
        event_queue: "queue.Queue[dict]" = queue.Queue()
        completed = threading.Event()
        trace_events = []

        def emit(payload: dict) -> None:
            if payload.get("type") == "summary" or len(trace_events) < 500:
                trace_events.append(payload)
            event_queue.put(payload)

        def run_ask() -> None:
            try:
                result = four_agent_ask_service.ask(
                    question,
                    preferred_dataset_ids=selected_dataset_ids,
                    allowed_dataset_ids=allowed_dataset_ids,
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
                _log_smart_chat_result(
                    result=result,
                    question=question,
                    started=started,
                    user=user,
                    request_info=req_info,
                    trace_events=trace_events,
                    event_prefix="smart_chat_stream",
                )
                event_queue.put({"type": "result", "result": result})
            except Exception as exc:
                error_result = {
                    "error": f"smart-chat failed: {exc}",
                    "question": question,
                    "total_duration": round(time.time() - started, 2),
                }
                _log_smart_chat_result(
                    result=error_result,
                    question=question,
                    started=started,
                    user=user,
                    request_info=req_info,
                    trace_events=trace_events,
                    event_prefix="smart_chat_stream",
                )
                event_queue.put(
                    {
                        "type": "result",
                        "result": error_result,
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
    user = get_current_user()
    req_info = request_snapshot(request)
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
        allowed_dataset_ids = _allowed_dataset_ids(user)
        selected_dataset_ids = _filter_requested_dataset_ids(user, selected_dataset_ids)
        if payload.get("selected_dataset_ids") is not None and not selected_dataset_ids:
            return jsonify({"error": "当前账号没有访问所选数据集的权限"}), 403

        result = four_agent_ask_service.confirm_by_boss(
            session_id=session_id,
            selected_option=selected_option,
            selected_dataset_ids=selected_dataset_ids,
            allowed_dataset_ids=allowed_dataset_ids,
            option_id=option_id,
        )
        result["total_duration"] = round(time.time() - started, 2)
        _log_smart_chat_result(
            result=result,
            question=selected_option or session_id,
            started=started,
            user=user,
            request_info=req_info,
            event_prefix="boss_confirm",
        )

        if result.get("error"):
            return jsonify(result), 400
        return jsonify(result)
    except Exception as exc:
        _log_smart_chat_result(
            result={"error": f"confirm-by-boss failed: {exc}", "question": selected_option or session_id},
            question=selected_option or session_id,
            started=started,
            user=user,
            request_info=req_info,
            event_prefix="boss_confirm",
        )
        return jsonify(
            {
                "error": f"confirm-by-boss failed: {exc}",
                "total_duration": round(time.time() - started, 2),
            }
        ), 500


@smart_chat_bp.route("/api/smart-chat/confirm-by-boss/stream", methods=["POST"])
def confirm_by_boss_stream():
    started = time.time()
    payload = request.get_json() or {}
    user = get_current_user()
    req_info = request_snapshot(request)
    session_id = (payload.get("session_id") or "").strip()
    selected_option = (payload.get("selected_option") or "").strip()
    option_id = (payload.get("option_id") or "").strip()
    selected_dataset_ids = payload.get("selected_dataset_ids")

    if not session_id:
        return jsonify({"error": "session_id is required."}), 400
    if selected_dataset_ids is not None and not isinstance(selected_dataset_ids, list):
        return jsonify({"error": "selected_dataset_ids must be a list when provided."}), 400
    allowed_dataset_ids = _allowed_dataset_ids(user)
    selected_dataset_ids = _filter_requested_dataset_ids(user, selected_dataset_ids)
    if payload.get("selected_dataset_ids") is not None and not selected_dataset_ids:
        return jsonify({"error": "当前账号没有访问所选数据集的权限"}), 403

    def event_stream():
        event_queue: "queue.Queue[dict]" = queue.Queue()
        completed = threading.Event()
        trace_events = []

        def emit(trace_payload: dict) -> None:
            if trace_payload.get("type") == "summary" or len(trace_events) < 500:
                trace_events.append(trace_payload)
            event_queue.put(trace_payload)

        def run_confirm() -> None:
            try:
                result = four_agent_ask_service.confirm_by_boss(
                    session_id=session_id,
                    selected_option=selected_option,
                    selected_dataset_ids=selected_dataset_ids,
                    allowed_dataset_ids=allowed_dataset_ids,
                    option_id=option_id,
                    live_callback=emit,
                )
                result["total_duration"] = round(time.time() - started, 2)
                ds_id = result.get("dataset_id")
                if ds_id:
                    rc = drc.get_config(int(ds_id))
                    if rc:
                        result["report_config"] = rc
                _log_smart_chat_result(
                    result=result,
                    question=selected_option or session_id,
                    started=started,
                    user=user,
                    request_info=req_info,
                    trace_events=trace_events,
                    event_prefix="boss_confirm_stream",
                )
                event_queue.put({"type": "result", "result": result})
            except Exception as exc:
                error_result = {
                    "error": f"confirm-by-boss failed: {exc}",
                    "question": selected_option or session_id,
                    "total_duration": round(time.time() - started, 2),
                }
                _log_smart_chat_result(
                    result=error_result,
                    question=selected_option or session_id,
                    started=started,
                    user=user,
                    request_info=req_info,
                    trace_events=trace_events,
                    event_prefix="boss_confirm_stream",
                )
                event_queue.put(
                    {
                        "type": "result",
                        "result": error_result,
                    }
                )
            finally:
                completed.set()

        worker = threading.Thread(target=run_confirm, daemon=True)
        worker.start()
        yield _sse_frame("ready", {"ok": True, "session_id": session_id})

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
