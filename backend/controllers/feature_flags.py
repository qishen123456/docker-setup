from __future__ import annotations

from flask import Blueprint, jsonify, request

from auth_store import get_current_user
from feature_flags import ensure_feature_flags, load_feature_flags, save_feature_flags, view_for_user


feature_flags_bp = Blueprint("feature_flags", __name__)


def _require_super_admin():
    user = get_current_user()
    if user.get("role") != "super_admin":
        return None, (jsonify({"success": False, "error": "只有超级管理员可以维护系统控制台"}), 403)
    return user, None


@feature_flags_bp.route("/api/feature-flags", methods=["GET"])
def get_current_feature_flags():
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "error": "请先登录"}), 401
    flags = view_for_user(load_feature_flags(), user)
    return jsonify({"success": True, "data": flags})


@feature_flags_bp.route("/api/admin/feature-flags", methods=["GET"])
def get_admin_feature_flags():
    _, error = _require_super_admin()
    if error:
        return error
    return jsonify({"success": True, "data": ensure_feature_flags()})


@feature_flags_bp.route("/api/admin/feature-flags", methods=["PUT"])
def update_admin_feature_flags():
    user, error = _require_super_admin()
    if error:
        return error
    try:
        flags = save_feature_flags(request.get_json(silent=True) or {}, operator=user.get("username") or user.get("name") or "")
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    return jsonify({"success": True, "data": flags})


@feature_flags_bp.route("/api/admin/feature-flags/reset", methods=["POST"])
def reset_admin_feature_flags():
    _, error = _require_super_admin()
    if error:
        return error
    from feature_flags import DEFAULT_FEATURE_FLAGS, FEATURE_FLAGS_FILE
    from config_manager import write_json

    write_json(FEATURE_FLAGS_FILE, DEFAULT_FEATURE_FLAGS)
    return jsonify({"success": True, "data": ensure_feature_flags()})
