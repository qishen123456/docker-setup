from __future__ import annotations

from flask import Blueprint, jsonify, request

from auth_store import get_current_user
from system_log_store import clear_logs, get_log, get_stats, list_logs


system_logs_bp = Blueprint("system_logs", __name__, url_prefix="/api/admin/system-logs")


def _require_super_admin():
    user = get_current_user()
    if user.get("role") != "super_admin":
        return None, (jsonify({"success": False, "error": "只有超级管理员可以查看系统日志"}), 403)
    return user, None


@system_logs_bp.route("", methods=["GET"])
def list_system_logs():
    _, error = _require_super_admin()
    if error:
        return error
    try:
        logs, total = list_logs(
            {
                "category": request.args.get("category", ""),
                "level": request.args.get("level", ""),
                "keyword": request.args.get("keyword", ""),
                "trace_id": request.args.get("trace_id", ""),
                "date_from": request.args.get("date_from", ""),
                "date_to": request.args.get("date_to", ""),
                "limit": request.args.get("limit", 100),
                "offset": request.args.get("offset", 0),
            }
        )
        return jsonify({"success": True, "logs": logs, "total": total})
    except Exception as exc:
        return jsonify({"success": False, "error": f"获取系统日志失败: {exc}", "logs": []}), 500


@system_logs_bp.route("/stats", methods=["GET"])
def system_log_stats():
    _, error = _require_super_admin()
    if error:
        return error
    try:
        return jsonify({"success": True, "stats": get_stats({
            "date_from": request.args.get("date_from", ""),
            "date_to": request.args.get("date_to", ""),
        })})
    except Exception as exc:
        return jsonify({"success": False, "error": f"获取日志统计失败: {exc}"}), 500


@system_logs_bp.route("/<int:log_id>", methods=["GET"])
def system_log_detail(log_id: int):
    _, error = _require_super_admin()
    if error:
        return error
    item = get_log(log_id)
    if not item:
        return jsonify({"success": False, "error": "日志不存在"}), 404
    return jsonify({"success": True, "log": item})


@system_logs_bp.route("/clear", methods=["POST"])
def clear_system_logs():
    _, error = _require_super_admin()
    if error:
        return error
    payload = request.get_json(silent=True) or {}
    category = str(payload.get("category") or "").strip()
    before_date = str(payload.get("before_date") or "").strip()
    days = int(payload.get("days") or 0)
    if not category and days <= 0 and not before_date:
        return jsonify({"success": False, "error": "请至少指定日志类型或保留天数，避免误清空全部日志"}), 400
    try:
        deleted = clear_logs(category=category, days=days, before_date=before_date)
        return jsonify({"success": True, "deleted": deleted})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": f"清理系统日志失败: {exc}"}), 500
