from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set

from config_manager import read_json, write_json


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
        "organization_field": _as_text(scope.get("organization_field")),
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
    if mode not in {"public", "restricted"}:
        mode = "public"
    return {
        "dataset_id": clean_dataset_id,
        "mode": mode,
        "allowed_roles": [role for role in _as_list(item.get("allowed_roles")) if role in {"admin", "user"}],
        "allowed_departments": _as_list(item.get("allowed_departments")),
        "allowed_positions": _as_list(item.get("allowed_positions")),
        "allowed_employee_ids": _as_list(item.get("allowed_employee_ids")),
        "allowed_union_ids": _as_list(item.get("allowed_union_ids")),
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


def is_dataset_allowed(user: Dict[str, Any], dataset_id: int, permissions: Optional[Dict[str, Any]] = None) -> bool:
    user = user if isinstance(user, dict) else {}
    if user.get("role") == "super_admin":
        return True
    data = permissions or load_data_permissions()
    rule = (data.get("rules") or {}).get(str(int(dataset_id)))
    if not rule or rule.get("mode") != "restricted":
        return True

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


def filter_dataset_rows_for_user(rows: List[Dict[str, Any]], user: Dict[str, Any]) -> List[Dict[str, Any]]:
    permissions = load_data_permissions()
    return [
        row for row in rows
        if is_dataset_allowed(user, int(row.get("id") or row.get("dataset_id") or 0), permissions)
    ]


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
