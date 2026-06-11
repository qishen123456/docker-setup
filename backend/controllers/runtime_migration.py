"""
Runtime migration APIs for export, dry-run import, import, and backups.
"""
from __future__ import annotations

import json

from flask import Blueprint, Response, jsonify, request

from auth_store import get_current_user
from runtime_migration import (
    create_runtime_backup,
    export_runtime_bundle,
    import_runtime_bundle,
    list_runtime_backups,
    preview_runtime_import,
    summarize_runtime_state,
    _json_default,
)


runtime_migration_bp = Blueprint("runtime_migration", __name__, url_prefix="/api/runtime-migration")


def _require_super_admin():
    user = get_current_user()
    if user.get("role") != "super_admin":
        return None, (jsonify({"success": False, "error": "只有超级管理员可以执行运行态迁移"}), 403)
    return user, None


def _request_bundle() -> dict:
    if request.files:
        file = request.files.get("file")
        if file:
            raw = file.read().decode("utf-8")
            return json.loads(raw)
    data = request.get_json(silent=True) or {}
    bundle = data.get("bundle") if isinstance(data, dict) else None
    if isinstance(bundle, dict):
        return bundle
    if isinstance(data, dict) and data.get("type") == "smartask_runtime_bundle":
        return data
    raise ValueError("缺少运行态导入包")


@runtime_migration_bp.route("/summary", methods=["GET"])
def summary():
    _, error = _require_super_admin()
    if error:
        return error
    return jsonify({"success": True, "summary": summarize_runtime_state(), "backups": list_runtime_backups(8)})


@runtime_migration_bp.route("/export", methods=["GET", "POST"])
def export_bundle():
    _, error = _require_super_admin()
    if error:
        return error
    bundle = export_runtime_bundle()
    filename = f"smartask_runtime_{bundle.get('exported_at', '').replace(':', '').replace('-', '').replace('T', '_')}.json"
    payload = json.dumps(bundle, ensure_ascii=False, indent=2, default=_json_default)
    return Response(
        payload,
        mimetype="application/json; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@runtime_migration_bp.route("/preview", methods=["POST"])
def preview_import():
    _, error = _require_super_admin()
    if error:
        return error
    try:
        data = request.get_json(silent=True) or {}
        bundle = _request_bundle()
        result = preview_runtime_import(
            bundle,
            overwrite_configs=bool(data.get("overwrite_configs")),
            mode=str(data.get("mode") or "merge"),
        )
        return jsonify({"success": True, "result": result})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@runtime_migration_bp.route("/import", methods=["POST"])
def import_bundle():
    _, error = _require_super_admin()
    if error:
        return error
    try:
        data = request.get_json(silent=True) or {}
        bundle = _request_bundle()
        result = import_runtime_bundle(
            bundle,
            mode=str(data.get("mode") or "merge"),
            overwrite_configs=bool(data.get("overwrite_configs")),
            dry_run=bool(data.get("dry_run")),
            auto_backup=bool(data.get("auto_backup", True)),
        )
        return jsonify({"success": True, "result": result})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@runtime_migration_bp.route("/backups", methods=["GET"])
def backups():
    _, error = _require_super_admin()
    if error:
        return error
    return jsonify({"success": True, "backups": list_runtime_backups(30)})


@runtime_migration_bp.route("/backup", methods=["POST"])
def backup():
    _, error = _require_super_admin()
    if error:
        return error
    result = create_runtime_backup("manual_api")
    return jsonify({"success": True, "result": result})
