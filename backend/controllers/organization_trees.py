from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, jsonify, request

from auth_store import get_current_user
from feature_flags import feature_available
from organization_tree_store import (
    apply_import,
    create_node,
    create_tree_type,
    delete_node,
    delete_tree_type,
    overview,
    preview_import,
    update_node,
    update_tree_type,
)
from system_log_store import log_event, request_snapshot


organization_trees_bp = Blueprint("organization_trees", __name__, url_prefix="/api/admin/organization-trees")


def _require_super_admin():
    user = get_current_user()
    if user.get("role") != "super_admin":
        return None, (jsonify({"success": False, "error": "只有超级管理员可以维护组织树"}), 403)
    return user, None


def _require_feature(key: str, error_text: str):
    user, error = _require_super_admin()
    if error:
        return user, error
    if not feature_available(key, user):
        return user, (jsonify({"success": False, "error": error_text}), 403)
    return user, None


def _payload() -> Dict[str, Any]:
    return request.get_json(silent=True) or {}


def _operator(user: Dict[str, Any]) -> str:
    return str(user.get("username") or user.get("name") or user.get("employee_id") or "").strip()


def _log(event_type: str, title: str, user: Dict[str, Any], **details) -> None:
    log_event(
        category="organization_tree",
        event_type=event_type,
        level="info",
        title=title,
        user=user,
        request_info=request_snapshot(request),
        details=details,
    )


@organization_trees_bp.route("", methods=["GET"])
def get_organization_trees():
    user, error = _require_super_admin()
    if error:
        return error
    return jsonify({"success": True, **overview(), "operator": _operator(user)})


@organization_trees_bp.route("/types", methods=["POST"])
def add_tree_type():
    user, error = _require_feature("organization_tree_type_create", "当前账号没有新增组织树权限")
    if error:
        return error
    try:
        tree = create_tree_type(_payload(), _operator(user))
        _log("tree_type_create", "创建组织树类型", user, tree_type_id=tree.get("id"), tree_type_name=tree.get("name"))
        return jsonify({"success": True, "tree_type": tree, **overview()})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@organization_trees_bp.route("/import/preview", methods=["POST"])
def preview_tree_import():
    user, error = _require_feature("organization_tree_import_preview", "当前账号没有预检导入组织树权限")
    if error:
        return error
    try:
        return jsonify({"success": True, **preview_import(_payload())})
    except Exception as exc:
        return jsonify({"success": False, "error": f"导入预检失败: {exc}"}), 400


@organization_trees_bp.route("/import/apply", methods=["POST"])
def apply_tree_import():
    user, error = _require_feature("organization_tree_import_apply", "当前账号没有确认导入组织树权限")
    if error:
        return error
    try:
        result = apply_import(_payload(), _operator(user))
        _log(
            "tree_import_apply",
            "导入组织树",
            user,
            mode=result.get("preview", {}).get("mode"),
            stats=result.get("preview", {}).get("stats"),
            tree_type_id=(result.get("preview", {}).get("tree_type") or {}).get("id"),
        )
        return jsonify({"success": True, **result})
    except Exception as exc:
        return jsonify({"success": False, "error": f"确认导入失败: {exc}"}), 400


@organization_trees_bp.route("/types/<tree_id>", methods=["PUT"])
def edit_tree_type(tree_id: str):
    user, error = _require_feature("organization_tree_type_update", "当前账号没有编辑组织树权限")
    if error:
        return error
    try:
        tree = update_tree_type(tree_id, _payload(), _operator(user))
        _log("tree_type_update", "更新组织树类型", user, tree_type_id=tree.get("id"), tree_type_name=tree.get("name"))
        return jsonify({"success": True, "tree_type": tree, **overview()})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@organization_trees_bp.route("/types/<tree_id>", methods=["DELETE"])
def remove_tree_type(tree_id: str):
    user, error = _require_feature("organization_tree_type_delete", "当前账号没有删除组织树权限")
    if error:
        return error
    try:
        delete_tree_type(tree_id, _operator(user))
        _log("tree_type_delete", "删除组织树类型", user, tree_type_id=tree_id)
        return jsonify({"success": True, **overview()})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@organization_trees_bp.route("/nodes", methods=["POST"])
def add_node():
    user, error = _require_feature("organization_tree_node_create", "当前账号没有新增组织节点权限")
    if error:
        return error
    try:
        node = create_node(_payload(), _operator(user))
        _log("tree_node_create", "创建组织节点", user, node_id=node.get("id"), tree_type_id=node.get("tree_type_id"))
        return jsonify({"success": True, "node": node, **overview()})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@organization_trees_bp.route("/nodes/<node_id>", methods=["PUT"])
def edit_node(node_id: str):
    user, error = _require_feature("organization_tree_node_update", "当前账号没有编辑组织节点权限")
    if error:
        return error
    try:
        node = update_node(node_id, _payload(), _operator(user))
        _log("tree_node_update", "更新组织节点", user, node_id=node.get("id"), tree_type_id=node.get("tree_type_id"))
        return jsonify({"success": True, "node": node, **overview()})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@organization_trees_bp.route("/nodes/<node_id>", methods=["DELETE"])
def remove_node(node_id: str):
    user, error = _require_feature("organization_tree_node_delete", "当前账号没有删除组织节点权限")
    if error:
        return error
    try:
        delete_node(node_id, _operator(user))
        _log("tree_node_delete", "删除组织节点", user, node_id=node_id)
        return jsonify({"success": True, **overview()})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
