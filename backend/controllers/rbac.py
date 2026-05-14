from __future__ import annotations

import hashlib
import secrets
import time
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request

from auth_store import get_current_user
from bookshelf_repository import BookshelfRepository
from config_manager import read_json, write_json
from feature_flags import load_feature_flags
from rbac_store import (
    BUILTIN_ROLE_IDS,
    LEVEL_LABELS,
    RESOURCE_LEVELS,
    dataset_access_view,
    effective_permissions,
    load_rbac,
    max_level,
    normalize_resource_level,
    role_usage,
    save_rbac,
    user_key,
)
from system_log_store import log_event, request_snapshot


rbac_bp = Blueprint("rbac", __name__)
repo = BookshelfRepository()
PERMISSIONS_FILE = "employee_permissions.json"
DEFAULT_EMPLOYEE_PASSWORD = "12345678"


def _require_super_admin():
    user = get_current_user()
    if user.get("role") != "super_admin":
        return None, (jsonify({"success": False, "error": "只有超级管理员可以维护 RBAC 权限"}), 403)
    return user, None


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _as_list(value: Any) -> List[str]:
    raw = value if isinstance(value, list) else []
    result: List[str] = []
    seen = set()
    for item in raw:
        text = _as_text(item)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return salt, digest


def _reset_employee_password(employee: Dict[str, Any], password: str = DEFAULT_EMPLOYEE_PASSWORD) -> None:
    salt, password_hash = _hash_password(password)
    employee["password_salt"] = salt
    employee["password_hash"] = password_hash
    employee.pop("reset_password", None)


def _load_employees() -> List[Dict[str, Any]]:
    data = read_json(PERMISSIONS_FILE)
    employees = data.get("employees") if isinstance(data, dict) else []
    return [item for item in employees if isinstance(item, dict)]


def _save_employees(employees: List[Dict[str, Any]]) -> None:
    write_json(PERMISSIONS_FILE, {"employees": employees})


def _public_employee(item: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
    account = _as_text(item.get("account") or item.get("username"))
    employee_id = _as_text(item.get("id")) or f"employee_{index + 1}"
    role = _as_text(item.get("role")) or "user"
    if role not in {"admin", "user", "super_admin"}:
        role = "user"
    return {
        "id": employee_id,
        "name": _as_text(item.get("name")) or account or employee_id,
        "account": account,
        "username": account,
        "identifier": _as_text(item.get("identifier") or item.get("union_id")),
        "union_id": _as_text(item.get("union_id") or item.get("identifier")),
        "open_id": _as_text(item.get("open_id")),
        "user_id": _as_text(item.get("user_id")),
        "department": _as_text(item.get("department") or item.get("department_name")),
        "department_ids": item.get("department_ids") if isinstance(item.get("department_ids"), list) else [],
        "position": _as_text(item.get("position") or item.get("job_title")),
        "organization": _as_text(item.get("organization")),
        "company": _as_text(item.get("company")),
        "role": role,
        "role_ids": _as_list(item.get("role_ids")),
        "enabled": bool(item.get("enabled", True)),
        "note": _as_text(item.get("note")),
    }


def _feature_options() -> List[Dict[str, Any]]:
    flags = load_feature_flags()
    result = []
    for key, feature in (flags.get("features") or {}).items():
        if not isinstance(feature, dict):
            continue
        result.append({
            "key": key,
            "label": feature.get("label") or key,
            "module": feature.get("module") or "",
            "module_label": feature.get("module_label") or feature.get("category") or "",
            "kind": feature.get("kind") or "button",
            "category": feature.get("category") or "",
            "order": feature.get("order") or 999,
        })
    return sorted(result, key=lambda item: (str(item["module_label"]), int(item["order"] or 999), str(item["label"])))


def _dataset_options() -> List[Dict[str, Any]]:
    repo.ensure_schema()
    with repo._connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, dataset_name, dataset_code, business_domain, is_active
            FROM bs_datasets
            WHERE is_active = TRUE
            ORDER BY updated_at DESC, id DESC;
            """
        )
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def _shape_user_permissions(employee: Dict[str, Any], rbac_data: Dict[str, Any], features: List[Dict[str, Any]], datasets: List[Dict[str, Any]]) -> Dict[str, Any]:
    pseudo_user = {**employee, "employee_id": employee.get("id"), "username": employee.get("account")}
    perms = effective_permissions(pseudo_user, employee, rbac_data)
    role_map = {role["id"]: role for role in rbac_data.get("roles", [])}
    feature_map = {item["key"]: item for item in features}
    dataset_map = {str(item["id"]): item for item in datasets}
    sources = []
    for source in perms.get("role_sources", []):
        role = role_map.get(source.get("role_id")) or {}
        sources.append({**source, "role_name": role.get("name") or source.get("role_id")})
    function_permissions = [
        {**feature_map.get(key, {"key": key, "label": key}), "sources": sources}
        for key in perms.get("function_permissions", [])
    ]
    resource_permissions = []
    for dataset_id, level in (perms.get("resource_permissions") or {}).items():
        if dataset_id == "*":
            continue
        dataset = dataset_map.get(str(dataset_id))
        resource_permissions.append({
            "dataset_id": int(dataset_id),
            "dataset_name": dataset.get("dataset_name") if dataset else f"数据集 {dataset_id}",
            "level": level,
            "level_label": LEVEL_LABELS.get(level, level),
            "sources": sources,
        })
    if perms.get("is_super_admin"):
        resource_permissions = [
            {
                "dataset_id": int(item["id"]),
                "dataset_name": item.get("dataset_name"),
                "level": "manage",
                "level_label": LEVEL_LABELS["manage"],
                "sources": sources,
            }
            for item in datasets
        ]
    return {
        "user": employee,
        "role_sources": sources,
        "function_permissions": function_permissions,
        "resource_permissions": resource_permissions,
        "effective_role_ids": perms.get("role_ids", []),
    }


def _log(event_type: str, title: str, user: Dict[str, Any], **details) -> None:
    log_event(
        category="rbac",
        event_type=event_type,
        level="info",
        title=title,
        user=user,
        request_info=request_snapshot(request),
        status_code=details.pop("status_code", 200),
        details=details,
    )


@rbac_bp.route("/api/admin/rbac/overview", methods=["GET"])
def rbac_overview():
    user, error = _require_super_admin()
    if error:
        return error
    features = _feature_options()
    datasets = _dataset_options()
    rbac_data = load_rbac({"features": {item["key"]: item for item in features}})
    employees = [_public_employee(item, index) for index, item in enumerate(_load_employees())]
    user_permissions = [
        _shape_user_permissions(employee, rbac_data, features, datasets)
        for employee in employees
    ]
    return jsonify({
        "success": True,
        "roles": rbac_data.get("roles", []),
        "groups": rbac_data.get("groups", []),
        "users": employees,
        "features": features,
        "datasets": datasets,
        "resource_levels": [{"value": key, "label": label, "rank": RESOURCE_LEVELS[key]} for key, label in LEVEL_LABELS.items()],
        "user_permissions": user_permissions,
        "updated_at": rbac_data.get("updated_at", ""),
        "operator": user.get("username") or user.get("name") or "",
    })


@rbac_bp.route("/api/admin/rbac/roles", methods=["POST"])
def create_role():
    user, error = _require_super_admin()
    if error:
        return error
    payload = request.get_json() or {}
    data = load_rbac(load_feature_flags())
    role_id = _as_text(payload.get("id")) or f"role_{int(time.time() * 1000)}"
    if role_id in {role["id"] for role in data.get("roles", [])}:
        return jsonify({"success": False, "error": "角色 ID 已存在"}), 400
    role = {
        "id": role_id,
        "name": _as_text(payload.get("name")) or "新角色",
        "code": _as_text(payload.get("code")) or role_id,
        "description": _as_text(payload.get("description")),
        "builtin": False,
        "locked": False,
        "function_permissions": _as_list(payload.get("function_permissions")),
        "resource_permissions": {
            str(k): normalize_resource_level(v)
            for k, v in (payload.get("resource_permissions") or {}).items()
            if normalize_resource_level(v) != "none"
        },
    }
    data["roles"].append(role)
    saved = save_rbac(data, load_feature_flags(), user.get("username") or "")
    _log("role_create", "创建 RBAC 角色", user, role_id=role_id)
    return jsonify({"success": True, "role": role, "roles": saved.get("roles", [])})


@rbac_bp.route("/api/admin/rbac/roles/<role_id>", methods=["PUT"])
def update_role(role_id: str):
    user, error = _require_super_admin()
    if error:
        return error
    payload = request.get_json() or {}
    data = load_rbac(load_feature_flags())
    for role in data.get("roles", []):
        if role["id"] != role_id:
            continue
        if role_id == "super_admin":
            return jsonify({"success": False, "error": "超管角色不可修改"}), 400
        if role.get("builtin"):
            role["description"] = _as_text(payload.get("description") or role.get("description"))
        else:
            role["name"] = _as_text(payload.get("name")) or role["name"]
            role["code"] = _as_text(payload.get("code")) or role["code"]
            role["description"] = _as_text(payload.get("description"))
        role["function_permissions"] = _as_list(payload.get("function_permissions"))
        role["resource_permissions"] = {
            str(k): normalize_resource_level(v)
            for k, v in (payload.get("resource_permissions") or {}).items()
            if normalize_resource_level(v) != "none"
        }
        saved = save_rbac(data, load_feature_flags(), user.get("username") or "")
        _log("role_update", "更新 RBAC 角色", user, role_id=role_id)
        return jsonify({"success": True, "role": role, "roles": saved.get("roles", [])})
    return jsonify({"success": False, "error": "角色不存在"}), 404


@rbac_bp.route("/api/admin/rbac/roles/<role_id>", methods=["DELETE"])
def delete_role(role_id: str):
    user, error = _require_super_admin()
    if error:
        return error
    if role_id in BUILTIN_ROLE_IDS:
        return jsonify({"success": False, "error": "内置角色不可删除"}), 400
    data = load_rbac(load_feature_flags())
    employees = [_public_employee(item, index) for index, item in enumerate(_load_employees())]
    usage = role_usage(role_id, employees, data)
    if usage["count"] > 0:
        return jsonify({"success": False, "error": "该角色已被用户或分组使用，删除前请先取消分配", "usage": usage}), 400
    data["roles"] = [role for role in data.get("roles", []) if role["id"] != role_id]
    saved = save_rbac(data, load_feature_flags(), user.get("username") or "")
    _log("role_delete", "删除 RBAC 角色", user, role_id=role_id)
    return jsonify({"success": True, "roles": saved.get("roles", [])})


@rbac_bp.route("/api/admin/rbac/groups", methods=["POST"])
def create_group():
    user, error = _require_super_admin()
    if error:
        return error
    payload = request.get_json() or {}
    data = load_rbac(load_feature_flags())
    group = {
        "id": _as_text(payload.get("id")) or f"group_{int(time.time() * 1000)}",
        "name": _as_text(payload.get("name")) or "新用户分组",
        "parent_id": _as_text(payload.get("parent_id")),
        "description": _as_text(payload.get("description")),
        "role_ids": _as_list(payload.get("role_ids")),
        "user_ids": _as_list(payload.get("user_ids")),
    }
    data["groups"].append(group)
    saved = save_rbac(data, load_feature_flags(), user.get("username") or "")
    _log("group_create", "创建用户分组", user, group_id=group["id"])
    return jsonify({"success": True, "group": group, "groups": saved.get("groups", [])})


@rbac_bp.route("/api/admin/rbac/groups/<group_id>", methods=["PUT"])
def update_group(group_id: str):
    user, error = _require_super_admin()
    if error:
        return error
    payload = request.get_json() or {}
    data = load_rbac(load_feature_flags())
    for group in data.get("groups", []):
        if group["id"] != group_id:
            continue
        group.update({
            "name": _as_text(payload.get("name")) or group["name"],
            "parent_id": _as_text(payload.get("parent_id")),
            "description": _as_text(payload.get("description")),
            "role_ids": _as_list(payload.get("role_ids")),
            "user_ids": _as_list(payload.get("user_ids")),
        })
        saved = save_rbac(data, load_feature_flags(), user.get("username") or "")
        _log("group_update", "更新用户分组", user, group_id=group_id)
        return jsonify({"success": True, "group": group, "groups": saved.get("groups", [])})
    return jsonify({"success": False, "error": "分组不存在"}), 404


@rbac_bp.route("/api/admin/rbac/groups/<group_id>", methods=["DELETE"])
def delete_group(group_id: str):
    user, error = _require_super_admin()
    if error:
        return error
    data = load_rbac(load_feature_flags())
    if any(group.get("parent_id") == group_id for group in data.get("groups", [])):
        return jsonify({"success": False, "error": "该分组存在下级分组，请先调整层级"}), 400
    data["groups"] = [group for group in data.get("groups", []) if group["id"] != group_id]
    saved = save_rbac(data, load_feature_flags(), user.get("username") or "")
    _log("group_delete", "删除用户分组", user, group_id=group_id)
    return jsonify({"success": True, "groups": saved.get("groups", [])})


@rbac_bp.route("/api/admin/rbac/users", methods=["POST"])
def create_user_assignment():
    user, error = _require_super_admin()
    if error:
        return error
    payload = request.get_json() or {}
    account = _as_text(payload.get("account") or payload.get("username"))
    name = _as_text(payload.get("name")) or account
    if not account:
        return jsonify({"success": False, "error": "账号不能为空"}), 400
    employees = _load_employees()
    if any(_as_text(item.get("account") or item.get("username")).lower() == account.lower() for item in employees):
        return jsonify({"success": False, "error": "账号已存在"}), 400
    role = _as_text(payload.get("role")) or "user"
    if role not in {"admin", "user"}:
        role = "user"
    employee = {
        "id": _as_text(payload.get("id")) or f"employee_{int(time.time() * 1000)}",
        "name": name,
        "account": account,
        "username": account,
        "identifier": _as_text(payload.get("identifier") or payload.get("union_id")),
        "union_id": _as_text(payload.get("union_id") or payload.get("identifier")),
        "open_id": _as_text(payload.get("open_id")),
        "user_id": _as_text(payload.get("user_id")),
        "department": _as_text(payload.get("department")),
        "department_ids": payload.get("department_ids") if isinstance(payload.get("department_ids"), list) else [],
        "position": _as_text(payload.get("position")),
        "organization": _as_text(payload.get("organization")),
        "company": _as_text(payload.get("company")),
        "role": role,
        "role_ids": _as_list(payload.get("role_ids")),
        "enabled": bool(payload.get("enabled", True)),
        "note": _as_text(payload.get("note")),
    }
    _reset_employee_password(employee, _as_text(payload.get("password")) or DEFAULT_EMPLOYEE_PASSWORD)
    employees.append(employee)
    _save_employees(employees)
    _log("user_create", "新建用户账号", user, target_user_id=employee["id"], account=account)
    return jsonify({
        "success": True,
        "user": _public_employee(employee, len(employees) - 1),
        "users": [_public_employee(item, index) for index, item in enumerate(employees)],
        "default_password": DEFAULT_EMPLOYEE_PASSWORD,
    })


@rbac_bp.route("/api/admin/rbac/users/<user_id>", methods=["PUT"])
def update_user_assignment(user_id: str):
    user, error = _require_super_admin()
    if error:
        return error
    payload = request.get_json() or {}
    employees = _load_employees()
    changed = False
    for index, employee in enumerate(employees):
        public = _public_employee(employee, index)
        if public["id"] != user_id:
            continue
        if public.get("role") == "super_admin":
            return jsonify({"success": False, "error": "超管不可被修改、停用"}), 400
        if "enabled" in payload:
            employee["enabled"] = bool(payload.get("enabled"))
        if "role" in payload and _as_text(payload.get("role")) in {"admin", "user"}:
            employee["role"] = _as_text(payload.get("role"))
        if "role_ids" in payload:
            employee["role_ids"] = _as_list(payload.get("role_ids"))
        for key in ("name", "account", "identifier", "union_id", "open_id", "user_id", "department", "position", "organization", "company", "note"):
            if key in payload:
                employee[key] = _as_text(payload.get(key))
        changed = True
        break
    if not changed:
        return jsonify({"success": False, "error": "用户不存在"}), 404
    _save_employees(employees)
    _log("user_update", "更新用户授权", user, target_user_id=user_id)
    return jsonify({"success": True, "users": [_public_employee(item, index) for index, item in enumerate(employees)]})


@rbac_bp.route("/api/admin/rbac/users/<user_id>/reset-password", methods=["POST"])
def reset_user_password(user_id: str):
    user, error = _require_super_admin()
    if error:
        return error
    payload = request.get_json() or {}
    password = _as_text(payload.get("password")) or DEFAULT_EMPLOYEE_PASSWORD
    if len(password) < 8:
        return jsonify({"success": False, "error": "密码长度不能少于 8 位"}), 400
    employees = _load_employees()
    for index, employee in enumerate(employees):
        public = _public_employee(employee, index)
        if public["id"] != user_id:
            continue
        if public.get("role") == "super_admin":
            return jsonify({"success": False, "error": "超管密码不可在此重置"}), 400
        _reset_employee_password(employee, password)
        _save_employees(employees)
        _log("user_password_reset", "重置用户密码", user, target_user_id=user_id, account=public.get("account"))
        return jsonify({
            "success": True,
            "default_password": password,
            "users": [_public_employee(item, idx) for idx, item in enumerate(employees)],
        })
    return jsonify({"success": False, "error": "用户不存在"}), 404


@rbac_bp.route("/api/admin/rbac/users/bulk", methods=["POST"])
def bulk_user_assignment():
    user, error = _require_super_admin()
    if error:
        return error
    payload = request.get_json() or {}
    user_ids = set(_as_list(payload.get("user_ids")))
    action = _as_text(payload.get("action"))
    role_ids = _as_list(payload.get("role_ids"))
    password = _as_text(payload.get("password")) or DEFAULT_EMPLOYEE_PASSWORD
    if action == "reset_password" and len(password) < 8:
        return jsonify({"success": False, "error": "密码长度不能少于 8 位"}), 400
    employees = _load_employees()
    changed_count = 0
    for index, employee in enumerate(employees):
        public = _public_employee(employee, index)
        if public["id"] not in user_ids or public.get("role") == "super_admin":
            continue
        current = set(_as_list(employee.get("role_ids")))
        if action == "remove_roles":
            current.difference_update(role_ids)
        elif action == "set_enabled":
            employee["enabled"] = bool(payload.get("enabled"))
        elif action == "reset_password":
            _reset_employee_password(employee, password)
        else:
            current.update(role_ids)
        employee["role_ids"] = sorted(current)
        changed_count += 1
    _save_employees(employees)
    _log("user_bulk_update", "批量更新用户授权", user, count=changed_count, action=action)
    return jsonify({
        "success": True,
        "users": [_public_employee(item, index) for index, item in enumerate(employees)],
        "default_password": password if action == "reset_password" else DEFAULT_EMPLOYEE_PASSWORD,
    })


@rbac_bp.route("/api/admin/rbac/users/<user_id>/permissions", methods=["GET"])
def user_permission_view(user_id: str):
    _, error = _require_super_admin()
    if error:
        return error
    features = _feature_options()
    datasets = _dataset_options()
    data = load_rbac(load_feature_flags())
    for index, item in enumerate(_load_employees()):
        employee = _public_employee(item, index)
        if employee["id"] == user_id:
            return jsonify({"success": True, "data": _shape_user_permissions(employee, data, features, datasets)})
    return jsonify({"success": False, "error": "用户不存在"}), 404


@rbac_bp.route("/api/admin/rbac/datasets/<int:dataset_id>/access", methods=["GET"])
def dataset_permission_view(dataset_id: int):
    _, error = _require_super_admin()
    if error:
        return error
    employees = [_public_employee(item, index) for index, item in enumerate(_load_employees())]
    data = load_rbac(load_feature_flags())
    return jsonify({"success": True, "data": dataset_access_view(dataset_id, employees, data)})
