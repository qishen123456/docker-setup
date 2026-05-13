from __future__ import annotations

from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from auth_store import get_current_user
from bookshelf_repository import BookshelfRepository
from config_manager import read_json
from data_permission_store import load_data_permissions, save_data_permissions


data_permissions_bp = Blueprint("data_permissions", __name__, url_prefix="/api/admin/data-permissions")
repo = BookshelfRepository()


def _require_super_admin():
    user = get_current_user()
    if user.get("role") != "super_admin":
        return None, (jsonify({"success": False, "error": "只有超级管理员可以维护数据权限"}), 403)
    return user, None


def _public_employee(item: dict, index: int) -> dict:
    return {
        "id": str(item.get("id") or f"employee_{index + 1}").strip(),
        "name": str(item.get("name") or item.get("account") or item.get("identifier") or "").strip(),
        "account": str(item.get("account") or item.get("username") or "").strip(),
        "identifier": str(item.get("identifier") or item.get("union_id") or "").strip(),
        "union_id": str(item.get("union_id") or item.get("identifier") or "").strip(),
        "department": str(item.get("department") or item.get("department_name") or "").strip(),
        "department_ids": item.get("department_ids") if isinstance(item.get("department_ids"), list) else [],
        "position": str(item.get("position") or item.get("job_title") or "").strip(),
        "role": str(item.get("role") or "user").strip(),
        "enabled": bool(item.get("enabled", True)),
    }


def _load_employees() -> list[dict]:
    data = read_json("employee_permissions.json")
    employees = data.get("employees") if isinstance(data, dict) else []
    if not isinstance(employees, list):
        employees = []
    return [_public_employee(item, index) for index, item in enumerate(employees) if isinstance(item, dict)]


def _load_datasets() -> list[dict]:
    repo.ensure_schema()
    with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, dataset_code, dataset_name, business_domain, source_id, description, is_active
            FROM bs_datasets
            WHERE is_active = TRUE
            ORDER BY id DESC;
            """
        )
        return [dict(row) for row in cur.fetchall()]


@data_permissions_bp.route("", methods=["GET"])
def get_data_permissions():
    _, error = _require_super_admin()
    if error:
        return error
    try:
        data = load_data_permissions()
        return jsonify({
            "success": True,
            "datasets": _load_datasets(),
            "employees": _load_employees(),
            "rules": data.get("rules", {}),
        })
    except Exception as exc:
        return jsonify({"success": False, "error": f"获取数据权限失败: {exc}"}), 500


@data_permissions_bp.route("", methods=["PUT"])
def put_data_permissions():
    _, error = _require_super_admin()
    if error:
        return error
    try:
        payload = request.get_json(silent=True) or {}
        data = save_data_permissions({"rules": payload.get("rules", {})})
        return jsonify({"success": True, "rules": data.get("rules", {})})
    except Exception as exc:
        return jsonify({"success": False, "error": f"保存数据权限失败: {exc}"}), 500
