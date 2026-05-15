from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Set

from config_manager import read_json, write_json
from organization_tree_store import load_organization_trees


DATA_PERMISSIONS_FILE = "data_permissions.json"


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _as_list(value: Any) -> List[str]:
    if isinstance(value, list):
        raw = value
    elif isinstance(value, str):
        raw = value.replace("\n", ",").split(",")
    else:
        raw = []
    result: List[str] = []
    seen = set()
    for item in raw:
        text = _as_text(item)
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result


def _as_int_list(value: Any) -> List[int]:
    result: List[int] = []
    seen = set()
    raw = value if isinstance(value, list) else []
    for item in raw:
        try:
            number = int(item)
        except (TypeError, ValueError):
            continue
        if number not in seen:
            seen.add(number)
            result.append(number)
    return result


def _clean_scope(scope: Any) -> Dict[str, Any]:
    scope = scope if isinstance(scope, dict) else {}
    return {
        "organization_field": _as_text(scope.get("organization_field")) or "组织编码",
        "organization_values": _as_list(scope.get("organization_values")),
        "company_field": _as_text(scope.get("company_field")),
        "company_values": _as_list(scope.get("company_values")),
        "row_filter_note": _as_text(scope.get("row_filter_note")),
    }


def clean_rule(item: Dict[str, Any], dataset_id: int | None = None) -> Dict[str, Any]:
    raw_dataset_id = dataset_id if dataset_id is not None else item.get("dataset_id")
    try:
        clean_dataset_id = int(raw_dataset_id)
    except (TypeError, ValueError):
        clean_dataset_id = 0
    mode = _as_text(item.get("mode") or "public")
    if mode not in {"public", "restricted", "org_tree", "disabled"}:
        mode = "public"
    tree_type_ids = _as_list(item.get("tree_type_ids"))
    legacy_tree_type_id = _as_text(item.get("tree_type_id"))
    if legacy_tree_type_id and legacy_tree_type_id not in tree_type_ids:
        tree_type_ids.insert(0, legacy_tree_type_id)
    legacy_allowed_roles = [role for role in _as_list(item.get("allowed_roles")) if role in {"admin", "user"}]
    legacy_allowed_departments = _as_list(item.get("allowed_departments"))
    legacy_allowed_positions = _as_list(item.get("allowed_positions"))
    legacy_allowed_employee_ids = _as_list(item.get("allowed_employee_ids"))
    legacy_allowed_union_ids = _as_list(item.get("allowed_union_ids"))
    if mode == "org_tree":
        legacy_allowed_roles = []
        legacy_allowed_departments = []
        legacy_allowed_positions = []
        legacy_allowed_employee_ids = []
        legacy_allowed_union_ids = []
    return {
        "dataset_id": clean_dataset_id,
        "mode": mode,
        "tree_type_id": tree_type_ids[0] if tree_type_ids else "",
        "tree_type_ids": tree_type_ids,
        "organization_node_ids": _as_list(item.get("organization_node_ids")),
        "organization_codes": _as_list(item.get("organization_codes")),
        "allowed_roles": legacy_allowed_roles,
        "allowed_departments": legacy_allowed_departments,
        "allowed_positions": legacy_allowed_positions,
        "allowed_employee_ids": legacy_allowed_employee_ids,
        "allowed_union_ids": legacy_allowed_union_ids,
        "scope": _clean_scope(item.get("scope")),
        "note": _as_text(item.get("note")),
    }


def load_data_permissions() -> Dict[str, Any]:
    data = read_json(DATA_PERMISSIONS_FILE)
    if not isinstance(data, dict):
        data = {}
    raw_rules = data.get("rules")
    rules: Dict[str, Dict[str, Any]] = {}
    if isinstance(raw_rules, dict):
        iterable = raw_rules.items()
    elif isinstance(raw_rules, list):
        iterable = [(item.get("dataset_id") if isinstance(item, dict) else None, item) for item in raw_rules]
    else:
        iterable = []
    for key, value in iterable:
        if not isinstance(value, dict):
            continue
        rule = clean_rule(value, key)
        if rule["dataset_id"] > 0:
            rules[str(rule["dataset_id"])] = rule
    return {"rules": rules}


def save_data_permissions(payload: Dict[str, Any]) -> Dict[str, Any]:
    raw_rules = payload.get("rules", {})
    rules: Dict[str, Dict[str, Any]] = {}
    if isinstance(raw_rules, dict):
        iterable = raw_rules.items()
    elif isinstance(raw_rules, list):
        iterable = [(item.get("dataset_id") if isinstance(item, dict) else None, item) for item in raw_rules]
    else:
        iterable = []
    for key, value in iterable:
        if not isinstance(value, dict):
            continue
        rule = clean_rule(value, key)
        if rule["dataset_id"] > 0:
            rules[str(rule["dataset_id"])] = rule
    data = {"rules": rules}
    write_json(DATA_PERMISSIONS_FILE, data)
    return data


def _user_values(user: Dict[str, Any], keys: Iterable[str]) -> Set[str]:
    values: Set[str] = set()
    for key in keys:
        value = user.get(key)
        if isinstance(value, list):
            for item in value:
                text = _as_text(item).lower()
                if text:
                    values.add(text)
        else:
            text = _as_text(value).lower()
            if text:
                values.add(text)
    return values


def _org_node_tree_map() -> Dict[str, Dict[str, Any]]:
    data = load_organization_trees()
    return {str(node.get("id")): node for node in data.get("nodes", []) if isinstance(node, dict)}


def _expand_node_ids_for_tree(node_ids: List[str], tree_type_id: str) -> List[str]:
    if not tree_type_id:
        return []
    nodes = _org_node_tree_map()
    selected = {
        str(node_id)
        for node_id in _as_list(node_ids)
        if nodes.get(str(node_id)) and str(nodes[str(node_id)].get("tree_type_id")) == str(tree_type_id)
    }
    if not selected:
        return []
    result: List[str] = []
    for node_id, node in nodes.items():
        if str(node.get("tree_type_id")) != str(tree_type_id):
            continue
        path_ids = [str(item) for item in (node.get("path_ids") or [node_id])]
        if node_id in selected or any(item in selected for item in path_ids):
            result.append(node_id)
    return result


def _codes_for_node_ids(node_ids: List[str], tree_type_id: str) -> List[str]:
    nodes = _org_node_tree_map()
    codes: List[str] = []
    seen = set()
    for node_id in _expand_node_ids_for_tree(node_ids, tree_type_id):
        node = nodes.get(str(node_id))
        code = _as_text((node or {}).get("code"))
        if code and code.lower() not in seen:
            seen.add(code.lower())
            codes.append(code)
    return codes


def _rule_org_codes(rule: Dict[str, Any]) -> List[str]:
    codes: List[str] = []
    seen = set()
    for tree_type_id in _rule_tree_type_ids(rule):
        for code in _codes_for_node_ids(_as_list(rule.get("organization_node_ids")), tree_type_id):
            key = code.lower()
            if key not in seen:
                seen.add(key)
                codes.append(code)
    if codes:
        return codes
    return _as_list(rule.get("organization_codes")) or _as_list((rule.get("scope") or {}).get("organization_values"))


def _is_allowed_employee(user: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    employee_values = _user_values(user, ["employee_id", "username", "account", "name"])
    return bool(employee_values.intersection({item.lower() for item in rule.get("allowed_employee_ids") or []}))


def _rule_tree_type_ids(rule: Dict[str, Any]) -> List[str]:
    ids = _as_list(rule.get("tree_type_ids"))
    legacy = _as_text(rule.get("tree_type_id"))
    if legacy and legacy not in ids:
        ids.insert(0, legacy)
    return ids


def user_org_codes_for_rule(user: Dict[str, Any], rule: Dict[str, Any]) -> List[str]:
    tree_type_ids = _rule_tree_type_ids(rule)
    if not tree_type_ids:
        return []
    scoped: List[str] = []
    seen = set()
    for tree_type_id in tree_type_ids:
        rule_codes = _codes_for_node_ids(_as_list(rule.get("organization_node_ids")), tree_type_id)
        if not rule_codes:
            continue
        user_codes = _codes_for_node_ids(_as_list(user.get("organization_node_ids")), tree_type_id)
        if not user_codes:
            matched = []
        else:
            user_set = {item.lower() for item in user_codes}
            matched = [item for item in rule_codes if item.lower() in user_set]
        for code in matched:
            key = code.lower()
            if key not in seen:
                seen.add(key)
                scoped.append(code)
    if scoped:
        return scoped
    return []


def is_dataset_allowed(user: Dict[str, Any], dataset_id: int, permissions: Optional[Dict[str, Any]] = None) -> bool:
    user = user if isinstance(user, dict) else {}
    if user.get("role") == "super_admin":
        return True
    if not user:
        return False
    data = permissions or load_data_permissions()
    rule = (data.get("rules") or {}).get(str(int(dataset_id)))
    if not rule:
        return False
    if rule.get("mode") == "disabled":
        return False
    if rule.get("mode") == "public":
        return True
    if rule.get("mode") == "org_tree":
        if user_org_codes_for_rule(user, rule):
            return True
        return False

    role = _as_text(user.get("role"))
    if role and role in set(rule.get("allowed_roles") or []):
        return True

    employee_values = _user_values(user, ["employee_id", "username", "account", "name"])
    if employee_values.intersection({item.lower() for item in rule.get("allowed_employee_ids") or []}):
        return True

    union_values = _user_values(user, ["union_id", "open_id", "user_id", "identifier"])
    if union_values.intersection({item.lower() for item in rule.get("allowed_union_ids") or []}):
        return True

    department_values = _user_values(user, ["department", "department_name", "departments", "department_ids", "organization", "company"])
    if department_values.intersection({item.lower() for item in rule.get("allowed_departments") or []}):
        return True

    position_values = _user_values(user, ["position", "job_title"])
    if position_values.intersection({item.lower() for item in rule.get("allowed_positions") or []}):
        return True

    return False


def dataset_scope_hit_for_user(user: Dict[str, Any], dataset_id: int, permissions: Optional[Dict[str, Any]] = None) -> bool:
    """Whether the user's organization scope intersects this dataset's scope."""
    user = user if isinstance(user, dict) else {}
    if user.get("role") == "super_admin":
        return True
    if not user:
        return False
    data = permissions or load_data_permissions()
    rule = (data.get("rules") or {}).get(str(int(dataset_id)))
    if not rule:
        return False
    if rule.get("mode") == "disabled":
        return False
    if rule.get("mode") == "public":
        return True
    if rule.get("mode") == "org_tree":
        if user_org_codes_for_rule(user, rule):
            return True
        return False
    return is_dataset_allowed(user, dataset_id, data)


def dataset_visible_for_user(user: Dict[str, Any], dataset_id: int, permissions: Optional[Dict[str, Any]] = None) -> bool:
    user = user if isinstance(user, dict) else {}
    if user.get("role") == "super_admin":
        return True
    if user.get("role") == "admin":
        return True
    return dataset_scope_hit_for_user(user, dataset_id, permissions)


def dataset_access_summary(user: Dict[str, Any], dataset_id: int, permissions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    user = user if isinstance(user, dict) else {}
    scope_hit = dataset_scope_hit_for_user(user, dataset_id, permissions)
    is_super = user.get("role") == "super_admin"
    is_admin = user.get("role") == "admin"
    can_view = is_super or is_admin or scope_hit
    return {
        "can_view": can_view,
        "dataset_scope_hit": scope_hit,
        "dataset_readonly": bool(can_view and is_admin and not scope_hit),
        "dataset_access": "manage" if is_super else "view" if can_view else "none",
        "dataset_access_reason": (
            "super_admin" if is_super else
            "scope_matched" if scope_hit else
            "admin_readonly" if is_admin else
            "no_scope"
        ),
    }


def _quote_identifier(identifier: str) -> str:
    text = _as_text(identifier)
    if not text or not re.match(r"^[\w\u4e00-\u9fff ]{1,80}$", text):
        raise ValueError("组织过滤字段只能是结果列名，不能包含 SQL 表达式")
    return '"' + text.replace('"', '""') + '"'


def _sql_literal(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def apply_row_level_filter(sql: str, user: Dict[str, Any], dataset_id: int, permissions: Optional[Dict[str, Any]] = None) -> str:
    data = permissions or load_data_permissions()
    rule = (data.get("rules") or {}).get(str(int(dataset_id))) or {}
    if (user or {}).get("role") == "super_admin" or rule.get("mode") != "org_tree":
        return sql
    field = _as_text((rule.get("scope") or {}).get("organization_field")) or "组织编码"
    if not field:
        return sql
    values = user_org_codes_for_rule(user or {}, rule)
    if not values:
        condition = "1 = 0"
    else:
        literals = ", ".join(_sql_literal(item) for item in values)
        condition = f"CAST({_quote_identifier(field)} AS TEXT) IN ({literals})"
    return f"SELECT * FROM (\n{sql.strip().rstrip(';')}\n) AS __smartask_row_scope\nWHERE {condition}"


def filter_dataset_rows_for_user(rows: List[Dict[str, Any]], user: Dict[str, Any]) -> List[Dict[str, Any]]:
    permissions = load_data_permissions()
    result: List[Dict[str, Any]] = []
    for row in rows:
        dataset_id = int(row.get("id") or row.get("dataset_id") or 0)
        access = dataset_access_summary(user, dataset_id, permissions)
        if access["can_view"]:
            result.append({**row, **access})
    return result


def allowed_dataset_ids_for_user(user: Dict[str, Any], dataset_ids: Iterable[Any]) -> List[int]:
    permissions = load_data_permissions()
    allowed: List[int] = []
    for item in dataset_ids:
        try:
            dataset_id = int(item)
        except (TypeError, ValueError):
            continue
        if is_dataset_allowed(user, dataset_id, permissions):
            allowed.append(dataset_id)
    return allowed
