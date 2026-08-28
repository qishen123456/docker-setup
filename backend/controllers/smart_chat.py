"""
Smart chat controller for dataset-isolated four-agent orchestration.
"""

from flask import Blueprint, Response, jsonify, request, stream_with_context
import json
import inspect
import math
import os
import queue
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ask_flow import ask_flow_controller
from ask_flow.contracts import AskRequest, ConfirmRequest
import dataset_report_config as drc
from disambiguation.shadow_gatekeeper import schedule_shadow_log, build_correction, is_visible_user
from disambiguation.typo_fastpath import detect_obvious_typo, build_early_clarify_result, log_fastpath
from auth_store import get_current_user
from data_permission_store import allowed_dataset_ids_for_user
from feature_flags import feature_available
from system_log_store import log_event, request_snapshot
from smartask_report_history_store import (
    StaleHistorySnapshotError,
    clear_history as clear_report_history,
    filter_history_dataset_results,
    list_history as list_report_history,
    remove_history as remove_report_history,
    upsert_history as upsert_report_history,
)


smart_chat_bp = Blueprint("smart_chat", __name__)


def _require_feature(user: dict, key: str):
    if feature_available(key, user or {}):
        return None
    return jsonify({"error": "当前账号没有使用该功能的权限。"}), 403


def _require_any_feature(user: dict, keys: list[str]):
    if any(feature_available(key, user or {}) for key in keys):
        return None
    return jsonify({"error": "当前账号没有使用该功能的权限。"}), 403


@smart_chat_bp.route("/api/smart-chat/report-history", methods=["GET"])
def get_report_history():
    user = get_current_user()
    limit = _safe_int(request.args.get("limit"), 50)
    history = list_report_history(user, limit=limit)
    # A-05 后端最小权限校验：按当前账号的数据集权限裁剪历史快照中的 dataset_results
    try:
        allowed_ids = _allowed_dataset_ids(user or {})
    except Exception:
        # 权限系统异常时，降级为不返回任何数据集结果（保留元信息）
        allowed_ids = []
    history = filter_history_dataset_results(history, allowed_ids)
    return jsonify({"history": history})


@smart_chat_bp.route("/api/smart-chat/report-history", methods=["POST"])
def save_report_history():
    user = get_current_user()
    payload = request.get_json() or {}
    item = payload.get("item") if isinstance(payload.get("item"), dict) else payload
    if not isinstance(item, dict) or not item.get("id"):
        return jsonify({"error": "history item id is required."}), 400
    try:
        saved = upsert_report_history(user, item)
        return jsonify({"success": True, "item": saved})
    except StaleHistorySnapshotError as exc:
        return jsonify({"error": str(exc), "code": exc.code}), 409
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@smart_chat_bp.route("/api/smart-chat/report-history/<item_id>", methods=["DELETE"])
def delete_report_history_item(item_id):
    user = get_current_user()
    denied = _require_feature(user, "app_history_delete")
    if denied:
        return denied
    remove_report_history(user, item_id)
    return jsonify({"success": True})


@smart_chat_bp.route("/api/smart-chat/report-history", methods=["DELETE"])
def clear_report_history_items():
    user = get_current_user()
    denied = _require_feature(user, "app_history_clear")
    if denied:
        return denied
    clear_report_history(user)
    return jsonify({"success": True})


def _active_dataset_ids() -> list[int]:
    try:
        return [int(item.get("id")) for item in ask_flow_controller.active_service().repository.get_agent1_catalog() if item.get("id") is not None]
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


def _permission_denied_response(user: dict, requested_dataset_ids, allowed_dataset_ids):
    return jsonify({
        "error": "当前账号没有访问所选数据集的权限。",
        "diagnostics": {
            "requested_dataset_ids": requested_dataset_ids or [],
            "allowed_dataset_ids": allowed_dataset_ids or [],
            "user_role": (user or {}).get("role"),
            "user_org_codes": (user or {}).get("organization_codes") or [],
            "user_org_node_ids": (user or {}).get("organization_node_ids") or [],
        },
    }), 403


def _mark_request_event_logged() -> None:
    try:
        request._smartask_event_logged = True
    except Exception:
        pass


def _log_smart_chat_rejection(
    *,
    event_prefix: str,
    title: str,
    error_message: str,
    question: str,
    started: float,
    user: dict,
    request_info: dict,
    status_code: int = 400,
    details: dict | None = None,
) -> None:
    duration_ms = int((time.time() - started) * 1000)
    log_event(
        category="error",
        event_type=f"{event_prefix}_rejected",
        level="error" if status_code >= 500 else "warning",
        title=title or "智能问数请求被拒绝",
        user=user,
        request_info=request_info,
        status_code=status_code,
        duration_ms=duration_ms,
        question=question or "",
        error_message=error_message or "",
        details={
            "event_name": title or "智能问数请求被拒绝",
            "what_happened": error_message or "问数请求在进入执行链路前被拒绝。",
            "suggested_action": "检查问题内容、功能权限、数据集权限或确认会话是否过期。",
            "code_hint": "backend/controllers/smart_chat.py；backend/four_agent_ask.py；frontend/src/views/SmartAsk.vue。",
            **(details or {}),
        },
    )
    _mark_request_event_logged()


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


def _token_number(value) -> int:
    try:
        return max(0, int(float(value or 0)))
    except Exception:
        return 0


def _usage_from_mapping(value) -> dict:
    if not isinstance(value, dict):
        return {}
    prompt_tokens = _token_number(value.get("prompt_tokens") or value.get("input_tokens"))
    completion_tokens = _token_number(value.get("completion_tokens") or value.get("output_tokens"))
    total_tokens = _token_number(value.get("total_tokens"))
    if total_tokens <= 0:
        total_tokens = prompt_tokens + completion_tokens
    if total_tokens <= 0:
        return {}
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "source": value.get("source") or "actual",
        "estimated": bool(value.get("estimated", False)),
    }


def _estimate_text_tokens(text) -> int:
    text = str(text or "")
    if not text:
        return 0
    cjk = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    other = len(text) - cjk
    return max(1, int(math.ceil(cjk * 1.1 + other / 4)))


def _extract_event(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {}
    if payload.get("type") == "trace" and isinstance(payload.get("event"), dict):
        return payload.get("event") or {}
    return payload


def _extract_token_usage(result: dict, trace_events: list | None = None) -> dict:
    result = result or {}
    for key in ("token_usage", "usage", "llm_usage"):
        usage = _usage_from_mapping(result.get(key))
        if usage:
            return usage
    details = result.get("details") if isinstance(result.get("details"), dict) else {}
    for key in ("token_usage", "usage"):
        usage = _usage_from_mapping(details.get(key))
        if usage:
            return usage

    prompt_tokens = 0
    completion_tokens = 0
    for payload in trace_events or []:
        event = _extract_event(payload)
        if not event:
            continue
        usage = _usage_from_mapping(event.get("token_usage") or event.get("usage") or {})
        if usage and not usage.get("estimated"):
            prompt_tokens += usage.get("prompt_tokens") or 0
            completion_tokens += usage.get("completion_tokens") or 0
            continue
        if event.get("status") == "request":
            prompt_tokens += _estimate_text_tokens(event.get("system_prompt"))
            prompt_tokens += _estimate_text_tokens(event.get("user_prompt"))
        elif event.get("status") == "response":
            completion_tokens += _estimate_text_tokens(event.get("response_text"))

    if prompt_tokens <= 0 and completion_tokens <= 0:
        prompt_tokens = _estimate_text_tokens(result.get("question"))
        completion_tokens = _estimate_text_tokens(result.get("analysis") or result.get("answer_text") or result.get("sql"))
    total_tokens = prompt_tokens + completion_tokens
    if total_tokens <= 0:
        return {}
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "source": "trace_estimate",
        "estimated": True,
    }


def _trace_id_from_events(trace_events: list | None = None) -> str:
    for payload in trace_events or []:
        if isinstance(payload, dict) and payload.get("trace_id"):
            return str(payload.get("trace_id") or "")
    return ""


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

    token_usage = _extract_token_usage(result, trace_events or [])
    trace_id = result.get("trace_id") or _trace_id_from_events(trace_events or [])

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
            "trace_id": trace_id,
            "effective_question": result.get("effective_question") or "",
            "route": result.get("route") or {},
            "data_source": result.get("data_source") or "",
            "diagnostics": result.get("diagnostics") or {},
            "original_error": result.get("original_error") or "",
            "diagnostic": bool(result.get("diagnostic")),
            "row_count": result.get("row_count"),
            "columns": result.get("columns") or [],
            "rows_preview": (result.get("rows") or [])[:20],
            "steps": result.get("steps") or [],
            "dataset_results": _compact_dataset_results(result),
            "requires_confirmation": bool(result.get("requires_confirmation")),
            "conversation_session_id": result.get("conversation_session_id") or "",
            "confirmation_session_id": result.get("session_id") or "",
            "token_usage": token_usage,
            "total_tokens": token_usage.get("total_tokens") or 0,
        },
    )


@smart_chat_bp.route("/api/smart-chat", methods=["POST"])
def smart_chat():
    started = time.time()
    user = get_current_user()
    req_info = request_snapshot(request)
    payload = request.get_json(silent=True) or {}
    denied = _require_feature(user, "smart_send_question")
    if denied:
        _log_smart_chat_rejection(
            event_prefix="smart_chat",
            title="智能问数权限不足",
            error_message="当前账号没有发送智能问数的权限。",
            question=(payload.get("question") or "").strip(),
            started=started,
            user=user,
            request_info=req_info,
            status_code=403,
            details={"feature_key": "smart_send_question"},
        )
        return denied
    try:
        _append_controller_debug("smart_chat.request.enter")
        _append_controller_debug("smart_chat.request.payload", payload=payload)
        service = ask_flow_controller.active_service()
        _append_controller_debug(
            "smart_chat.service.meta",
            controller=ask_flow_controller.__class__.__name__,
            service_module=service.__class__.__module__,
            service_file=inspect.getsourcefile(service.__class__),
        )
        ask_flow_controller.write_controller_probe(
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
            _log_smart_chat_rejection(
                event_prefix="smart_chat",
                title="智能问数问题为空",
                error_message="Question cannot be empty.",
                question=question,
                started=started,
                user=user,
                request_info=req_info,
                status_code=400,
            )
            return jsonify({"error": "Question cannot be empty."}), 400
        if selected_dataset_ids is not None:
            denied = _require_feature(user, "smart_dataset_select")
            if denied:
                _log_smart_chat_rejection(
                    event_prefix="smart_chat",
                    title="智能问数数据集选择权限不足",
                    error_message="当前账号没有选择智能问数数据集的权限。",
                    question=question,
                    started=started,
                    user=user,
                    request_info=req_info,
                    status_code=403,
                    details={"feature_key": "smart_dataset_select", "selected_dataset_ids": selected_dataset_ids},
                )
                return denied
        if selected_dataset_ids is not None and not isinstance(selected_dataset_ids, list):
            _append_controller_debug("smart_chat.request.reject", reason="selected_dataset_ids_not_list")
            _log_smart_chat_rejection(
                event_prefix="smart_chat",
                title="智能问数参数错误",
                error_message="selected_dataset_ids must be a list when provided.",
                question=question,
                started=started,
                user=user,
                request_info=req_info,
                status_code=400,
                details={"selected_dataset_ids": selected_dataset_ids},
            )
            return jsonify({"error": "selected_dataset_ids must be a list when provided."}), 400
        allowed_dataset_ids = _allowed_dataset_ids(user)
        selected_dataset_ids = _filter_requested_dataset_ids(user, selected_dataset_ids)
        if payload.get("selected_dataset_ids") is not None and not selected_dataset_ids:
            _log_smart_chat_rejection(
                event_prefix="smart_chat",
                title="智能问数数据集权限不足",
                error_message="当前账号没有访问所选数据集的权限。",
                question=question,
                started=started,
                user=user,
                request_info=req_info,
                status_code=403,
                details={
                    "requested_dataset_ids": payload.get("selected_dataset_ids") or [],
                    "allowed_dataset_ids": allowed_dataset_ids,
                },
            )
            return _permission_denied_response(user, payload.get("selected_dataset_ids"), allowed_dataset_ids)

        # 第 0 层：明显错字快检（毫秒级纯代码）。命中即短路返回纠正卡，不进问数流水线；
        # 前端"按原问题继续查"会带 skip_typo_check 跳过本层。任何异常静默放行（fail-open）。
        if not payload.get("skip_typo_check") and is_visible_user(user):
            _typo_hit = detect_obvious_typo(question, allowed_dataset_ids)
            if _typo_hit:
                result = build_early_clarify_result(question, _typo_hit, session_id=session_id)
                result["total_duration"] = round(time.time() - started, 2)
                _append_controller_debug(
                    "smart_chat.typo_fastpath.hit",
                    fragment=_typo_hit.get("fragment"),
                    suggestion=_typo_hit.get("suggestion"),
                )
                log_fastpath(question, _typo_hit, user=user, session_id=session_id)
                _log_smart_chat_result(
                    result=result,
                    question=question,
                    started=started,
                    user=user,
                    request_info=req_info,
                    event_prefix="smart_chat",
                )
                return jsonify(result)

        _append_controller_debug(
            "smart_chat.service.ask.start",
            question=question,
            selected_dataset_ids=selected_dataset_ids,
            allowed_dataset_ids=allowed_dataset_ids,
        )
        result = ask_flow_controller.ask(AskRequest(
            question=question,
            preferred_dataset_ids=selected_dataset_ids,
            allowed_dataset_ids=allowed_dataset_ids,
            session_id=session_id,
            conversation_history=conversation_history if isinstance(conversation_history, list) else None,
            current_user=user,
            requested_flow=str(payload.get("ask_flow") or payload.get("flow") or ""),
        ))
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
        # 守门员分流：可见用户走同步纠正条（自身写影子日志）；其余用户走异步影子，一次提问只调一次守门员
        if is_visible_user(user):
            _correction = build_correction(question=question, result=result, user=user, session_id=session_id)
            if _correction:
                result["clarify_suggestion"] = _correction
        else:
            schedule_shadow_log(question=question, result=result, user=user, session_id=session_id)

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
    denied = _require_feature(user, "smart_send_question")
    if denied:
        _log_smart_chat_rejection(
            event_prefix="smart_chat_stream",
            title="智能问数权限不足",
            error_message="当前账号没有发送智能问数的权限。",
            question=(payload.get("question") or "").strip(),
            started=started,
            user=user,
            request_info=req_info,
            status_code=403,
            details={"feature_key": "smart_send_question"},
        )
        return denied
    question = (payload.get("question") or "").strip()
    session_id = (payload.get("session_id") or "").strip()
    conversation_history = payload.get("conversation_history")
    selected_dataset_ids = payload.get("selected_dataset_ids")
    model_id = payload.get("model_id")  # None = AUTO (use default)

    if not question:
        _log_smart_chat_rejection(
            event_prefix="smart_chat_stream",
            title="智能问数问题为空",
            error_message="Question cannot be empty.",
            question=question,
            started=started,
            user=user,
            request_info=req_info,
            status_code=400,
        )
        return jsonify({"error": "Question cannot be empty."}), 400
    if selected_dataset_ids is not None:
        denied = _require_feature(user, "smart_dataset_select")
        if denied:
            _log_smart_chat_rejection(
                event_prefix="smart_chat_stream",
                title="智能问数数据集选择权限不足",
                error_message="当前账号没有选择智能问数数据集的权限。",
                question=question,
                started=started,
                user=user,
                request_info=req_info,
                status_code=403,
                details={"feature_key": "smart_dataset_select", "selected_dataset_ids": selected_dataset_ids},
            )
            return denied
    if model_id is not None:
        denied = _require_feature(user, "smart_model_select")
        if denied:
            _log_smart_chat_rejection(
                event_prefix="smart_chat_stream",
                title="智能问数模型选择权限不足",
                error_message="当前账号没有选择智能问数模型的权限。",
                question=question,
                started=started,
                user=user,
                request_info=req_info,
                status_code=403,
                details={"feature_key": "smart_model_select", "model_id": model_id},
            )
            return denied
    if selected_dataset_ids is not None and not isinstance(selected_dataset_ids, list):
        _log_smart_chat_rejection(
            event_prefix="smart_chat_stream",
            title="智能问数参数错误",
            error_message="selected_dataset_ids must be a list when provided.",
            question=question,
            started=started,
            user=user,
            request_info=req_info,
            status_code=400,
            details={"selected_dataset_ids": selected_dataset_ids},
        )
        return jsonify({"error": "selected_dataset_ids must be a list when provided."}), 400
    allowed_dataset_ids = _allowed_dataset_ids(user)
    selected_dataset_ids = _filter_requested_dataset_ids(user, selected_dataset_ids)
    if payload.get("selected_dataset_ids") is not None and not selected_dataset_ids:
        _log_smart_chat_rejection(
            event_prefix="smart_chat_stream",
            title="智能问数数据集权限不足",
            error_message="当前账号没有访问所选数据集的权限。",
            question=question,
            started=started,
            user=user,
            request_info=req_info,
            status_code=403,
            details={
                "requested_dataset_ids": payload.get("selected_dataset_ids") or [],
                "allowed_dataset_ids": allowed_dataset_ids,
            },
        )
        return _permission_denied_response(user, payload.get("selected_dataset_ids"), allowed_dataset_ids)

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
                result = ask_flow_controller.ask(AskRequest(
                    question=question,
                    preferred_dataset_ids=selected_dataset_ids,
                    allowed_dataset_ids=allowed_dataset_ids,
                    live_callback=emit,
                    model_id=model_id,
                    session_id=session_id,
                    conversation_history=conversation_history if isinstance(conversation_history, list) else None,
                    current_user=user,
                    requested_flow=str(payload.get("ask_flow") or payload.get("flow") or ""),
                ))
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
                print(f"[DEBUG] stream result requires_confirmation={result.get('requires_confirmation')} route_decision={result.get('route', {}).get('decision')} route_requires_confirmation={result.get('route', {}).get('requires_confirmation')} dataset_ids={result.get('route', {}).get('dataset_ids')}", flush=True)
                # 守门员分流：可见用户走同步纠正条（自身写影子日志）；其余用户走异步影子
                if is_visible_user(user):
                    _correction = build_correction(question=question, result=result, user=user, session_id=session_id)
                    if _correction:
                        result["clarify_suggestion"] = _correction
                else:
                    schedule_shadow_log(question=question, result=result, user=user, session_id=session_id)
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

        # 第 0 层：明显错字快检（与同步端点同一层）。命中则不启 worker，直接发纠正卡结果。
        _typo_hit = None
        if not payload.get("skip_typo_check") and is_visible_user(user):
            _typo_hit = detect_obvious_typo(question, allowed_dataset_ids)
        if _typo_hit:
            typo_result = build_early_clarify_result(question, _typo_hit, session_id=session_id)
            typo_result["total_duration"] = round(time.time() - started, 2)
            log_fastpath(question, _typo_hit, user=user, session_id=session_id)
            _log_smart_chat_result(
                result=typo_result,
                question=question,
                started=started,
                user=user,
                request_info=req_info,
                trace_events=trace_events,
                event_prefix="smart_chat_stream",
            )
            event_queue.put({"type": "result", "result": typo_result})
            completed.set()
        else:
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
    payload = request.get_json(silent=True) or {}
    denied = _require_any_feature(user, ["smart_confirm_scope", "smart_submit_note"])
    if denied:
        _log_smart_chat_rejection(
            event_prefix="boss_confirm",
            title="问数确认权限不足",
            error_message="当前账号没有提交问数确认口径的权限。",
            question=(payload.get("selected_option") or payload.get("session_id") or "").strip(),
            started=started,
            user=user,
            request_info=req_info,
            status_code=403,
            details={"feature_keys": ["smart_confirm_scope", "smart_submit_note"]},
        )
        return denied
    try:
        session_id = (payload.get("session_id") or "").strip()
        selected_option = (payload.get("selected_option") or "").strip()
        option_id = (payload.get("option_id") or "").strip()
        selected_dataset_ids = payload.get("selected_dataset_ids")

        if not session_id:
            _log_smart_chat_rejection(
                event_prefix="boss_confirm",
                title="问数确认缺少会话",
                error_message="session_id is required.",
                question=selected_option,
                started=started,
                user=user,
                request_info=req_info,
                status_code=400,
                details={"option_id": option_id, "selected_dataset_ids": selected_dataset_ids},
            )
            return jsonify({"error": "session_id is required."}), 400

        if selected_dataset_ids is not None and not isinstance(selected_dataset_ids, list):
            _log_smart_chat_rejection(
                event_prefix="boss_confirm",
                title="问数确认参数错误",
                error_message="selected_dataset_ids must be a list when provided.",
                question=selected_option or session_id,
                started=started,
                user=user,
                request_info=req_info,
                status_code=400,
                details={"selected_dataset_ids": selected_dataset_ids},
            )
            return jsonify({"error": "selected_dataset_ids must be a list when provided."}), 400
        allowed_dataset_ids = _allowed_dataset_ids(user)
        selected_dataset_ids = _filter_requested_dataset_ids(user, selected_dataset_ids)
        if payload.get("selected_dataset_ids") is not None and not selected_dataset_ids:
            _log_smart_chat_rejection(
                event_prefix="boss_confirm",
                title="问数确认数据集权限不足",
                error_message="当前账号没有访问所选数据集的权限。",
                question=selected_option or session_id,
                started=started,
                user=user,
                request_info=req_info,
                status_code=403,
                details={
                    "requested_dataset_ids": payload.get("selected_dataset_ids") or [],
                    "allowed_dataset_ids": allowed_dataset_ids,
                },
            )
            return _permission_denied_response(user, payload.get("selected_dataset_ids"), allowed_dataset_ids)

        result = ask_flow_controller.confirm_by_boss(ConfirmRequest(
            session_id=session_id,
            selected_option=selected_option,
            selected_dataset_ids=selected_dataset_ids,
            allowed_dataset_ids=allowed_dataset_ids,
            option_id=option_id,
            current_user=user,
            requested_flow=str(payload.get("ask_flow") or payload.get("flow") or ""),
        ))
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
    denied = _require_any_feature(user, ["smart_confirm_scope", "smart_submit_note"])
    if denied:
        _log_smart_chat_rejection(
            event_prefix="boss_confirm_stream",
            title="问数确认权限不足",
            error_message="当前账号没有提交问数确认口径的权限。",
            question=(payload.get("selected_option") or payload.get("session_id") or "").strip(),
            started=started,
            user=user,
            request_info=req_info,
            status_code=403,
            details={"feature_keys": ["smart_confirm_scope", "smart_submit_note"]},
        )
        return denied
    session_id = (payload.get("session_id") or "").strip()
    selected_option = (payload.get("selected_option") or "").strip()
    option_id = (payload.get("option_id") or "").strip()
    selected_dataset_ids = payload.get("selected_dataset_ids")

    if not session_id:
        _log_smart_chat_rejection(
            event_prefix="boss_confirm_stream",
            title="问数确认缺少会话",
            error_message="session_id is required.",
            question=selected_option,
            started=started,
            user=user,
            request_info=req_info,
            status_code=400,
            details={"option_id": option_id, "selected_dataset_ids": selected_dataset_ids},
        )
        return jsonify({"error": "session_id is required."}), 400
    if selected_dataset_ids is not None and not isinstance(selected_dataset_ids, list):
        _log_smart_chat_rejection(
            event_prefix="boss_confirm_stream",
            title="问数确认参数错误",
            error_message="selected_dataset_ids must be a list when provided.",
            question=selected_option or session_id,
            started=started,
            user=user,
            request_info=req_info,
            status_code=400,
            details={"selected_dataset_ids": selected_dataset_ids},
        )
        return jsonify({"error": "selected_dataset_ids must be a list when provided."}), 400
    allowed_dataset_ids = _allowed_dataset_ids(user)
    selected_dataset_ids = _filter_requested_dataset_ids(user, selected_dataset_ids)
    if payload.get("selected_dataset_ids") is not None and not selected_dataset_ids:
        _log_smart_chat_rejection(
            event_prefix="boss_confirm_stream",
            title="问数确认数据集权限不足",
            error_message="当前账号没有访问所选数据集的权限。",
            question=selected_option or session_id,
            started=started,
            user=user,
            request_info=req_info,
            status_code=403,
            details={
                "requested_dataset_ids": payload.get("selected_dataset_ids") or [],
                "allowed_dataset_ids": allowed_dataset_ids,
            },
        )
        return _permission_denied_response(user, payload.get("selected_dataset_ids"), allowed_dataset_ids)

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
                result = ask_flow_controller.confirm_by_boss(ConfirmRequest(
                    session_id=session_id,
                    selected_option=selected_option,
                    selected_dataset_ids=selected_dataset_ids,
                    allowed_dataset_ids=allowed_dataset_ids,
                    option_id=option_id,
                    live_callback=emit,
                    current_user=user,
                    requested_flow=str(payload.get("ask_flow") or payload.get("flow") or ""),
                ))
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
