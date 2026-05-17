from __future__ import annotations

import time
import os
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional, Set
from uuid import uuid4

from config_manager import read_json, resolve_read_path, write_json


RBAC_FILE = "rbac_permissions.json"
RESOURCE_LEVELS = {"none": 0, "view": 1, "edit": 2, "manage": 3}
LEVEL_LABELS = {"none": "无权限", "view": "查看", "edit": "编辑", "manage": "管理/授权"}
BUILTIN_ROLE_IDS = {"super_admin", "admin", "business_admin", "user"}


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


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


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def normalize_resource_level(value: Any) -> str:
    text = _as_text(value).lower()
    return text if text in RESOURCE_LEVELS else "none"


def level_rank(value: Any) -> int:
    return RESOURCE_LEVELS.get(normalize_resource_level(value), 0)


def max_level(values: Iterable[Any]) -> str:
    best = "none"
    for value in values:
        current = normalize_resource_level(value)
        if level_rank(current) > level_rank(best):
            best = current
    return best


def _feature_keys_from_flags(feature_flags: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(feature_flags, dict):
        return []
    features = feature_flags.get("features") if isinstance(feature_flags.get("features"), dict) else feature_flags
    return [str(key) for key in (features or {}).keys()]


def _role_default_functions(feature_flags: Any, role_id: str) -> List[str]:
    if not isinstance(feature_flags, dict):
        return list(feature_flags or []) if role_id == "super_admin" else []
    features = feature_flags.get("features") if isinstance(feature_flags.get("features"), dict) else feature_flags
    result: List[str] = []
    for key, feature in (features or {}).items():
        roles = feature.get("roles") if isinstance(feature, dict) else []
        if role_id in set(_as_list(roles)):
            result.append(str(key))
    return result


def _rbac_file_exists() -> bool:
    try:
        return os.path.exists(resolve_read_path(RBAC_FILE))
    except Exception:
        return False


def _default_feature_flags() -> Dict[str, Any]:
    try:
        from feature_flags import DEFAULT_FEATURE_FLAGS

        return DEFAULT_FEATURE_FLAGS
    except Exception:
        return {}


def builtin_roles(feature_flags: Optional[Any] = None) -> List[Dict[str, Any]]:
    source_flags = feature_flags if isinstance(feature_flags, dict) else _default_feature_flags()
    feature_keys = _feature_keys_from_flags(source_flags) if isinstance(source_flags, dict) else list(feature_flags or [])
    return [
        {
            "id": "super_admin",
            "name": "超管",
            "code": "super_admin",
            "description": "系统最高权限，内置角色不可修改、删除、停用。",
            "builtin": True,
            "locked": True,
            "function_permissions": _role_default_functions(source_flags or feature_keys, "super_admin"),
            "resource_permissions": {},
        },
        {
            "id": "admin",
            "name": "管理员",
            "code": "admin",
            "description": "内置管理员角色，默认可维护配置和数据资产。",
            "builtin": True,
            "locked": True,
            "function_permissions": _role_default_functions(source_flags, "admin"),
            "resource_permissions": {},
        },
        {
            "id": "business_admin",
            "name": "业务管理员",
            "code": "business_admin",
            "description": "内置业务管理员角色，默认可维护业务数据资产，数据范围受组织树约束。",
            "builtin": True,
            "locked": True,
            "function_permissions": _role_default_functions(source_flags, "business_admin"),
            "resource_permissions": {},
        },
        {
            "id": "user",
            "name": "普通用户",
            "code": "user",
            "description": "内置普通用户角色，默认可使用智能分析工作台。",
            "builtin": True,
            "locked": True,
            "function_permissions": _role_default_functions(source_flags, "user"),
            "resource_permissions": {},
        },
    ]


def _clean_role(item: Dict[str, Any], feature_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    item = item if isinstance(item, dict) else {}
    role_id = _as_text(item.get("id") or item.get("code")) or _new_id("role")
    builtin = role_id in BUILTIN_ROLE_IDS or bool(item.get("builtin"))
    role = {
        "id": role_id,
        "name": _as_text(item.get("name")) or role_id,
        "code": _as_text(item.get("code")) or role_id,
        "description": _as_text(item.get("description")),
        "builtin": builtin,
        "locked": bool(item.get("locked") or builtin),
        "function_permissions": _as_list(item.get("function_permissions")),
        "resource_permissions": {},
    }
    feature_set = set(feature_keys or [])
    if feature_set:
        role["function_permissions"] = [key for key in role["function_permissions"] if key in feature_set]
    resource_permissions = item.get("resource_permissions") if isinstance(item.get("resource_permissions"), dict) else {}
    for dataset_id, level in resource_permissions.items():
        try:
            clean_id = str(int(dataset_id))
        except (TypeError, ValueError):
            continue
        clean_level = normalize_resource_level(level)
        if clean_level != "none":
            role["resource_permissions"][clean_id] = clean_level
    return role


def _clean_group(item: Dict[str, Any]) -> Dict[str, Any]:
    item = item if isinstance(item, dict) else {}
    group_id = _as_text(item.get("id")) or _new_id("group")
    parent_id = _as_text(item.get("parent_id"))
    if parent_id == group_id:
        parent_id = ""
    return {
        "id": group_id,
        "name": _as_text(item.get("name")) or "未命名分组",
        "parent_id": parent_id,
        "description": _as_text(item.get("description")),
        "role_ids": _as_list(item.get("role_ids")),
        "user_ids": _as_list(item.get("user_ids")),
    }


def load_rbac(feature_flags: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    feature_keys = _feature_keys_from_flags(feature_flags)
    data = read_json(RBAC_FILE)
    if not isinstance(data, dict) or not data.get("roles"):
        data = {"version": 1, "roles": builtin_roles(feature_flags or feature_keys), "groups": [], "updated_at": _now()}

    roles_by_id: Dict[str, Dict[str, Any]] = {}
    for role in builtin_roles(feature_flags or feature_keys):
        roles_by_id[role["id"]] = role
    for item in data.get("roles") or []:
        clean = _clean_role(item, feature_keys)
        if clean["id"] in BUILTIN_ROLE_IDS:
            base = roles_by_id.get(clean["id"], clean)
            base.update({
                "function_permissions": clean.get("function_permissions") or base.get("function_permissions") or [],
                "resource_permissions": clean.get("resource_permissions") or base.get("resource_permissions") or {},
            })
            roles_by_id[clean["id"]] = base
        else:
            roles_by_id[clean["id"]] = clean

    groups = [_clean_group(item) for item in (data.get("groups") or []) if isinstance(item, dict)]
    valid_role_ids = set(roles_by_id.keys())
    valid_group_ids = {group["id"] for group in groups}
    for group in groups:
        group["role_ids"] = [role_id for role_id in group["role_ids"] if role_id in valid_role_ids]
        group["parent_id"] = group["parent_id"] if group["parent_id"] in valid_group_ids else ""

    return {
        "version": 1,
        "roles": list(roles_by_id.values()),
        "groups": groups,
        "updated_at": _as_text(data.get("updated_at")) or _now(),
        "updated_by": _as_text(data.get("updated_by")),
    }


def save_rbac(data: Dict[str, Any], feature_flags: Optional[Dict[str, Any]] = None, operator: str = "") -> Dict[str, Any]:
    current = load_rbac(feature_flags)
    incoming_roles = data.get("roles") if isinstance(data.get("roles"), list) else current["roles"]
    incoming_groups = data.get("groups") if isinstance(data.get("groups"), list) else current["groups"]
    result = {
        "version": 1,
        "roles": [_clean_role(item, _feature_keys_from_flags(feature_flags)) for item in incoming_roles if isinstance(item, dict)],
        "groups": [_clean_group(item) for item in incoming_groups if isinstance(item, dict)],
        "updated_at": _now(),
        "updated_by": operator,
    }
    normalized = load_rbac(feature_flags={**(feature_flags or {}), "_direct": True})
    # Re-run against the just-built data rather than the previous file.
    old_read = deepcopy(result)
    roles_by_id = {role["id"]: role for role in builtin_roles(feature_flags or _feature_keys_from_flags(feature_flags))}
    for role in old_read["roles"]:
        if role["id"] in BUILTIN_ROLE_IDS:
            roles_by_id[role["id"]].update({
                "function_permissions": role.get("function_permissions") or roles_by_id[role["id"]].get("function_permissions") or [],
                "resource_permissions": role.get("resource_permissions") or {},
            })
        else:
            roles_by_id[role["id"]] = role
    valid_role_ids = set(roles_by_id.keys())
    valid_group_ids = {group["id"] for group in old_read["groups"]}
    for group in old_read["groups"]:
        group["role_ids"] = [role_id for role_id in group.get("role_ids", []) if role_id in valid_role_ids]
        group["parent_id"] = group.get("parent_id") if group.get("parent_id") in valid_group_ids else ""
    normalized.update({
        "roles": list(roles_by_id.values()),
        "groups": old_read["groups"],
        "updated_at": result["updated_at"],
        "updated_by": operator,
    })
    write_json(RBAC_FILE, normalized)
    return normalized


def user_key(user: Dict[str, Any]) -> str:
    for key in ("employee_id", "id", "account", "username", "union_id", "open_id", "user_id", "identifier", "name"):
        text = _as_text((user or {}).get(key))
        if text:
            return text
    return ""


def get_role_map(data: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    source = data or load_rbac()
    return {role["id"]: role for role in source.get("roles", [])}


def group_ancestor_ids(group_id: str, groups: List[Dict[str, Any]]) -> List[str]:
    by_id = {group["id"]: group for group in groups}
    result: List[str] = []
    cursor = by_id.get(group_id)
    seen = set()
    while cursor and cursor.get("parent_id") and cursor.get("parent_id") not in seen:
        parent_id = cursor["parent_id"]
        result.append(parent_id)
        seen.add(parent_id)
        cursor = by_id.get(parent_id)
    return result


def groups_for_user(user_id: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    groups = data.get("groups") or []
    direct = [group for group in groups if user_id and user_id in set(group.get("user_ids") or [])]
    by_id = {group["id"]: group for group in groups}
    all_ids: List[str] = []
    for group in direct:
        if group["id"] not in all_ids:
            all_ids.append(group["id"])
        for parent_id in group_ancestor_ids(group["id"], groups):
            if parent_id not in all_ids:
                all_ids.append(parent_id)
    return [by_id[item] for item in all_ids if item in by_id]


def effective_role_sources(user: Dict[str, Any], employee: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    data = data or load_rbac()
    role_map = get_role_map(data)
    employee = employee if isinstance(employee, dict) else user
    uid = user_key(employee or user)
    sources: List[Dict[str, Any]] = []

    legacy_role = _as_text((employee or {}).get("role") or (user or {}).get("role"))
    if legacy_role in role_map:
        sources.append({"role_id": legacy_role, "source_type": "legacy", "source_id": "", "source_name": "固定角色"})

    for role_id in _as_list((employee or {}).get("role_ids")):
        if role_id in role_map:
            sources.append({"role_id": role_id, "source_type": "direct", "source_id": uid, "source_name": "直接分配"})

    for group in groups_for_user(uid, data):
        for role_id in _as_list(group.get("role_ids")):
            if role_id in role_map:
                sources.append({"role_id": role_id, "source_type": "group", "source_id": group["id"], "source_name": group.get("name") or "用户分组"})

    seen = set()
    result = []
    for item in sources:
        key = (item["role_id"], item["source_type"], item["source_id"])
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def effective_permissions(user: Dict[str, Any], employee: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = data or load_rbac()
    role_map = get_role_map(data)
    if (user or {}).get("role") == "super_admin" or (employee or {}).get("role") == "super_admin":
        roles = [role_map["super_admin"]] if "super_admin" in role_map else []
        return {
            "role_sources": [{"role_id": "super_admin", "source_type": "system", "source_id": "", "source_name": "超管最高权限"}],
            "role_ids": ["super_admin"],
            "roles": roles,
            "function_permissions": sorted({key for role in roles for key in role.get("function_permissions", [])}),
            "resource_permissions": {"*": "manage"},
            "is_super_admin": True,
        }
    sources = effective_role_sources(user, employee, data)
    role_ids = list(dict.fromkeys(item["role_id"] for item in sources))
    roles = [role_map[item] for item in role_ids if item in role_map]
    functions = sorted({key for role in roles for key in role.get("function_permissions", [])})
    resource_levels: Dict[str, List[str]] = {}
    for role in roles:
        for dataset_id, level in (role.get("resource_permissions") or {}).items():
            resource_levels.setdefault(str(dataset_id), []).append(level)
    return {
        "role_sources": sources,
        "role_ids": role_ids,
        "roles": roles,
        "function_permissions": functions,
        "resource_permissions": {dataset_id: max_level(levels) for dataset_id, levels in resource_levels.items()},
        "is_super_admin": False,
    }


def user_has_function(user: Dict[str, Any], key: str, fallback: bool = False) -> bool:
    if not user:
        return fallback
    if user.get("role") == "super_admin":
        return True
    perms = effective_permissions(user)
    if key in set(perms.get("function_permissions") or []):
        return True
    return fallback if not _rbac_file_exists() else False


def user_dataset_level(user: Dict[str, Any], dataset_id: Any) -> str:
    if not user:
        return "none"
    if user.get("role") == "super_admin":
        return "manage"
    try:
        key = str(int(dataset_id))
    except (TypeError, ValueError):
        return "none"
    perms = effective_permissions(user)
    return normalize_resource_level((perms.get("resource_permissions") or {}).get(key))


def role_usage(role_id: str, employees: List[Dict[str, Any]], data: Dict[str, Any]) -> Dict[str, Any]:
    direct_users = [item for item in employees if role_id in _as_list(item.get("role_ids")) or item.get("role") == role_id]
    groups = [item for item in data.get("groups", []) if role_id in _as_list(item.get("role_ids"))]
    return {"users": direct_users, "groups": groups, "count": len(direct_users) + len(groups)}


def dataset_access_view(dataset_id: Any, employees: List[Dict[str, Any]], data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = data or load_rbac()
    key = str(int(dataset_id))
    role_map = get_role_map(data)
    role_rows = []
    for role in data.get("roles", []):
        level = "manage" if role["id"] == "super_admin" else normalize_resource_level((role.get("resource_permissions") or {}).get(key))
        if level != "none":
            role_rows.append({"role": role, "level": level, "level_label": LEVEL_LABELS[level]})
    group_rows = []
    for group in data.get("groups", []):
        levels = []
        role_items = []
        for role_id in _as_list(group.get("role_ids")):
            role = role_map.get(role_id)
            if not role:
                continue
            level = "manage" if role_id == "super_admin" else normalize_resource_level((role.get("resource_permissions") or {}).get(key))
            if level != "none":
                levels.append(level)
                role_items.append(role)
        best = max_level(levels)
        if best != "none":
            group_rows.append({"group": group, "roles": role_items, "level": best, "level_label": LEVEL_LABELS[best]})
    user_rows = []
    for employee in employees:
        pseudo_user = {**employee, "employee_id": employee.get("id"), "username": employee.get("account")}
        perms = effective_permissions(pseudo_user, employee, data)
        level = "manage" if perms.get("is_super_admin") else normalize_resource_level((perms.get("resource_permissions") or {}).get(key))
        if level != "none":
            user_rows.append({"user": employee, "role_sources": perms.get("role_sources", []), "level": level, "level_label": LEVEL_LABELS[level]})
    return {"dataset_id": int(dataset_id), "roles": role_rows, "groups": group_rows, "users": user_rows}
