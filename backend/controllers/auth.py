"""
Feishu, local super-admin, and generic auth APIs.
"""
from __future__ import annotations

import os
import secrets
import hashlib
from datetime import datetime
from urllib.parse import urlencode

import requests
from flask import Blueprint, jsonify, redirect, request, session

from config_manager import read_json, write_json
from auth_store import create_session_token, get_current_user, revoke_token
from secret_codec import decrypt_secret_value
from system_log_store import log_event, request_snapshot


auth_bp = Blueprint("auth", __name__)
PERMISSIONS_FILE = "employee_permissions.json"
DEFAULT_EMPLOYEE_PASSWORD = "12345678"
ROLE_LABELS = {
    "super_admin": "超级管理员",
    "admin": "管理员",
    "business_admin": "业务管理员",
    "user": "普通用户",
}


def _log_auth_event(event_type: str, level: str, title: str, user: dict | None = None, **details) -> None:
    log_event(
        category="auth",
        event_type=event_type,
        level=level,
        title=title,
        user=user or {},
        request_info=request_snapshot(request),
        status_code=details.pop("status_code", None),
        details=details,
    )


def _env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return decrypt_secret_value(str(value).strip())
    return default


def _feishu_config() -> dict:
    return {
        "app_id": _env("FEISHU_APP_ID", "SMARTASK_FEISHU_APP_ID"),
        "app_secret": _env("FEISHU_APP_SECRET", "SMARTASK_FEISHU_APP_SECRET"),
        "base_url": _env("FEISHU_BASE_URL", "SMARTASK_FEISHU_BASE_URL", default="https://open.feishu.cn").rstrip("/"),
        "backend_url": _env("BACKEND_URL", "SMARTASK_BACKEND_URL").rstrip("/"),
        "frontend_url": _env("FRONTEND_URL", "SMARTASK_FRONTEND_URL", default="http://localhost:5173").rstrip("/"),
        "redirect_uri": _env("FEISHU_REDIRECT_URI", "SMARTASK_FEISHU_REDIRECT_URI").strip(),
        "frontend_callback_url": _env("FEISHU_FRONTEND_CALLBACK_URL", "SMARTASK_FEISHU_FRONTEND_CALLBACK_URL").strip(),
    }


def _admin_config() -> dict:
    return {
        "username": _env("SMARTASK_ADMIN_USERNAME", "ADMIN_USERNAME", default="admin"),
        "password": _env("SMARTASK_ADMIN_PASSWORD", "ADMIN_PASSWORD"),
        "display_name": _env("SMARTASK_ADMIN_DISPLAY_NAME", default="超级管理员"),
    }


def _load_permissions() -> dict:
    data = read_json(PERMISSIONS_FILE)
    if not isinstance(data, dict):
        data = {}
    employees = data.get("employees")
    if not isinstance(employees, list):
        employees = []
    return {"employees": employees}


def _save_permissions(data: dict) -> None:
    write_json(PERMISSIONS_FILE, {"employees": data.get("employees", [])})


def _clean_role(role: str) -> str:
    role = str(role or "").strip()
    return role if role in {"admin", "business_admin", "user"} else "user"


def _clean_role_ids(value) -> list[str]:
    raw = value if isinstance(value, list) else []
    result = []
    seen = set()
    for item in raw:
        text = str(item or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return salt, digest


def _verify_password(password: str, salt: str, password_hash: str) -> bool:
    if not salt or not password_hash:
        return False
    _, digest = _hash_password(password, salt)
    return secrets.compare_digest(digest, password_hash)


def _first_text(*values) -> str:
    for value in values:
        if isinstance(value, list):
            text = _first_text(*value)
            if text:
                return text
            continue
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _pick_text(data: dict | None, *keys: str) -> str:
    if not isinstance(data, dict):
        return ""
    for key in keys:
        text = _first_text(data.get(key))
        if text:
            return text
    return ""


def _clean_employee(item: dict, index: int, existing: dict | None = None) -> dict:
    account = str(item.get("account") or item.get("username") or "").strip()
    union_id = str(item.get("union_id") or item.get("unionId") or item.get("identifier") or "").strip()
    identifier = str(item.get("identifier") or union_id).strip()
    name = str(item.get("name") or "").strip() or account or identifier or f"员工{index + 1}"
    role = _clean_role(item.get("role"))
    existing = existing or {}
    salt = str(item.get("password_salt") or existing.get("password_salt") or "").strip()
    password_hash = str(item.get("password_hash") or existing.get("password_hash") or "").strip()
    if item.get("reset_password") or not salt or not password_hash:
        salt, password_hash = _hash_password(DEFAULT_EMPLOYEE_PASSWORD)
    return {
        "id": str(item.get("id") or f"employee_{index + 1}").strip(),
        "name": name,
        "account": account,
        "identifier": identifier,
        "union_id": union_id,
        "open_id": str(item.get("open_id") or item.get("openId") or "").strip(),
        "user_id": str(item.get("user_id") or item.get("userId") or "").strip(),
        "department": str(item.get("department") or item.get("department_name") or "").strip(),
        "department_ids": item.get("department_ids") if isinstance(item.get("department_ids"), list) else [],
        "position": str(item.get("position") or item.get("job_title") or "").strip(),
        "organization": str(item.get("organization") or "").strip(),
        "company": str(item.get("company") or "").strip(),
        "role": role,
        "role_ids": _clean_role_ids(item.get("role_ids")),
        "role_label": ROLE_LABELS.get(role, "普通用户"),
        "enabled": bool(item.get("enabled", True)),
        "note": str(item.get("note") or "").strip(),
        "password_salt": salt,
        "password_hash": password_hash,
    }


def _employee_public(employee: dict) -> dict:
    return {
        key: value
        for key, value in employee.items()
        if key not in {"password_salt", "password_hash"}
    }


def _identity_values(user: dict) -> set[str]:
    values = set()
    for key in ("union_id", "unionId", "open_id", "openId", "user_id", "userId", "identifier", "account", "email", "mobile", "username", "name"):
        raw = user.get(key)
        if isinstance(raw, list):
            for item in raw:
                value = str(item or "").strip().lower()
                if value:
                    values.add(value)
        else:
            value = str(raw or "").strip().lower()
            if value:
                values.add(value)
    return values


def _apply_employee_permission(user: dict) -> dict:
    if not isinstance(user, dict) or not user:
        return {}
    if user.get("role") == "super_admin":
        user["role_label"] = ROLE_LABELS["super_admin"]
        return user
    identities = _identity_values(user)
    matched = None
    for item in _load_permissions().get("employees", []):
        employee = _clean_employee(item, 0)
        candidates = {
            employee.get("identifier", "").strip().lower(),
            employee.get("union_id", "").strip().lower(),
            employee.get("open_id", "").strip().lower(),
            employee.get("user_id", "").strip().lower(),
            employee.get("account", "").strip().lower(),
        }
        if candidates.intersection(identities):
            if not employee["enabled"]:
                return {}
            matched = employee
            break
    role = matched["role"] if matched else "user"
    user["role"] = role
    user["role_label"] = ROLE_LABELS.get(role, "普通用户")
    if matched:
        user["employee_id"] = matched["id"]
        user["permission_name"] = matched["name"]
        user["role_ids"] = matched.get("role_ids", [])
        for key in ("identifier", "union_id", "open_id", "user_id", "account"):
            if matched.get(key) and not user.get(key):
                user[key] = matched[key]
        user["permission_identifier"] = (
            matched.get("identifier")
            or matched.get("union_id")
            or matched.get("open_id")
            or matched.get("user_id")
            or matched.get("account")
            or ""
        )
        for key in ("department", "department_ids", "position", "organization", "company"):
            if matched.get(key) and not user.get(key):
                user[key] = matched[key]
    return user


def _find_employee_match(user: dict) -> dict | None:
    identities = _identity_values(user)
    if not identities:
        return None
    for index, item in enumerate(_load_permissions().get("employees", [])):
        employee = _clean_employee(item, index)
        candidates = {
            employee.get("identifier", "").strip().lower(),
            employee.get("union_id", "").strip().lower(),
            employee.get("open_id", "").strip().lower(),
            employee.get("user_id", "").strip().lower(),
            employee.get("account", "").strip().lower(),
        }
        if candidates.intersection(identities):
            return employee
    return None


def _ensure_feishu_employee_user(user: dict) -> dict:
    """确保飞书用户在员工列表中存在（支持手机号自动合并）

    合并策略（增强版）：
    - 优先级 1：精确匹配 + 检查是否需要合并（如果匹配到的是 feishu 自动创建账号，且存在同手机号的本地账号 → 强制合并）
    - 优先级 2：手机号模糊匹配（合并到已有账号，保留权限，更新飞书信息）
    - 优先级 3：创建新账号
    """
    if not isinstance(user, dict) or user.get("source") != "feishu":
        return user

    mobile = str(user.get("mobile") or "").strip()

    # 优先级 1：精确匹配
    existing = _find_employee_match(user)

    # DEBUG: 打印匹配结果
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"[DEBUG-FEISHU-MERGE] mobile={mobile}, existing_id={existing.get('id') if existing else None}, is_feishu_account={existing.get('id', '').startswith('emp_feishu_') if existing else False}")

    if existing:
        # 检查：如果匹配到的是 feishu 自动创建账号（emp_feishu_*），且存在同手机号的本地账号 → 强制合并
        if existing.get("id", "").startswith("emp_feishu_") and mobile:
            local_account = _find_employee_by_mobile(mobile)

            # DEBUG: 打印查找结果
            logger.warning(f"[DEBUG-FEISHU-MERGE] local_account found={local_account is not None}, local_id={local_account.get('id') if local_account else None}")

            # 如果找到了不同的本地账号（不是当前这个 feishu 账号）→ 合并到本地账号
            if local_account and local_account["id"] != existing["id"]:
                _log_auth_event(
                    "feishu_force_merge",
                    "info",
                    f"检测到重复账号：{existing['name']}({existing['id']}) 将合并到 {local_account['name']}({local_account['id']})",
                    account=mobile,
                    status_code=200,
                )
                # 1. 将飞书信息合并到本地账号
                _merge_feishu_to_existing(local_account, user)
                # 2. 禁用旧的 feishu 账号（而不是删除，保留审计记录）
                _disable_employee(existing["id"], f"已合并到 {local_account['id']}({local_account['name']})")

                _log_auth_event(
                    "feishu_user_merged",
                    "info",
                    f"飞书登录：手机号 {mobile} 强制合并到已有用户 {local_account['name']}({local_account['id']})",
                    user=local_account,
                    account=mobile,
                    union_id=user.get("union_id") or "",
                    status_code=200,
                )
                # 返回合并后的用户信息
                merged_user = _employee_user_info(local_account)
                merged_user["source"] = "feishu"
                return merged_user

        # 正常情况：精确匹配到非 feishu 账号 或 无需合并 → 更新飞书字段
        _update_feishu_fields(existing, user)
        return user

    # 优先级 2：按手机号查找并合并
    if mobile:
        existing_by_mobile = _find_employee_by_mobile(mobile)
        if existing_by_mobile:
            # 找到手机号相同的用户 → 合并（保留权限 + 更新飞书信息）
            _merge_feishu_to_existing(existing_by_mobile, user)
            _log_auth_event(
                "feishu_user_merged",
                "info",
                f"飞书登录：手机号 {mobile} 匹配已有用户 {existing_by_mobile['name']}({existing_by_mobile['id']})，已合并",
                user=existing_by_mobile,
                account=mobile,
                union_id=user.get("union_id") or "",
                status_code=200,
            )
            # 返回合并后的用户信息（使用原账号 ID）
            merged_user = _employee_user_info(existing_by_mobile)
            merged_user["source"] = "feishu"
            return merged_user

    # 优先级 3：完全无匹配 → 创建新账号
    identity = (
        user.get("union_id")
        or user.get("open_id")
        or user.get("user_id")
        or user.get("mobile")
        or user.get("email")
    )
    account = user.get("mobile") or user.get("email") or user.get("user_id") or user.get("union_id") or user.get("open_id")
    if not identity or not account:
        return user
    permissions = _load_permissions()
    employees = permissions.get("employees", [])
    employee = _clean_employee({
        "id": f"emp_feishu_{secrets.token_hex(8)}",
        "name": user.get("name") or account,
        "account": account,
        "identifier": identity,
        "union_id": user.get("union_id") or "",
        "open_id": user.get("open_id") or "",
        "user_id": user.get("user_id") or "",
        "department": user.get("department") or "",
        "department_ids": user.get("department_ids") or [],
        "position": user.get("position") or "",
        "organization": user.get("organization") or "",
        "company": user.get("company") or "",
        "role": "user",
        "role_ids": [],
        "enabled": True,
        "note": "飞书首次登录自动创建",
        "reset_password": True,
    }, len(employees))
    employees.append(employee)
    _save_permissions({"employees": employees})
    _log_auth_event(
        "feishu_user_auto_created",
        "info",
        "飞书首次登录自动创建普通用户",
        user=employee,
        account=account,
        union_id=user.get("union_id") or "",
        open_id=user.get("open_id") or "",
        user_id=user.get("user_id") or "",
        status_code=200,
    )
    return user


def _disable_employee(employee_id: str, reason: str = ""):
    """禁用员工账号（用于合并后清理旧账号）"""
    permissions = _load_permissions()
    employees = permissions.get("employees", [])

    for idx, emp in enumerate(employees):
        if emp.get("id") == employee_id:
            employees[idx]["enabled"] = False
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            old_note = employees[idx].get("note", "")
            employees[idx]["note"] = f"{old_note}; [{timestamp}] 已禁用: {reason}".strip("; ").lstrip("; ")
            break

    _save_permissions({"employees": employees})


def _find_employee_by_mobile(mobile: str) -> dict | None:
    """根据手机号查找员工（用于飞书合并）"""
    mobile = str(mobile or "").strip().lower().replace("+", "").replace("-", "").replace(" ", "")
    if not mobile or len(mobile) < 7:
        return None
    for index, item in enumerate(_load_permissions().get("employees", [])):
        employee = _clean_employee(item, index)
        emp_mobile = str(employee.get("account") or "").strip().lower().replace("+", "").replace("-", "").replace(" ", "")
        if emp_mobile == mobile or emp_mobile.endswith(mobile[-8:]) or mobile.endswith(emp_mobile[-8:]):
            return employee
    return None


def _update_feishu_fields(employee: dict, feishu_user: dict):
    """更新已有员工的飞书相关字段（不改变权限）"""
    permissions = _load_permissions()
    employees = permissions.get("employees", [])

    for idx, emp in enumerate(employees):
        if emp.get("id") == employee.get("id"):
            # 只更新飞书信息字段，保留权限配置
            employees[idx]["union_id"] = feishu_user.get("union_id") or employees[idx].get("union_id", "")
            employees[idx]["open_id"] = feishu_user.get("open_id") or employees[idx].get("open_id", "")
            employees[idx]["user_id"] = feishu_user.get("user_id") or employees[idx].get("user_id", "")
            # 可选：更新姓名（如果飞书的更准确）
            if feishu_user.get("name"):
                employees[idx]["name"] = feishu_user["name"]
            # 更新部门信息
            if feishu_user.get("department"):
                employees[idx]["department"] = feishu_user["department"]
            if feishu_user.get("department_ids"):
                employees[idx]["department_ids"] = feishu_user["department_ids"]
            if feishu_user.get("position"):
                employees[idx]["position"] = feishu_user["position"]
            # 更新备注
            old_note = employees[idx].get("note", "")
            if "飞书同步" not in old_note:
                employees[idx]["note"] = f"{old_note}; 已从飞书同步信息".strip("; ").lstrip("; ")
            break

    _save_permissions({"employees": employees})


def _merge_feishu_to_existing(employee: dict, feishu_user: dict):
    """将飞书用户信息合并到已有员工账号（保留权限 + 更新飞书信息）"""
    permissions = _load_permissions()
    employees = permissions.get("employees", [])

    for idx, emp in enumerate(employees):
        if emp.get("id") == employee.get("id"):
            # === 保留原有权限配置 ===
            # role, role_ids, organization_node_ids, allowed_model_ids 等保持不变

            # === 更新为飞书信息 ===
            if feishu_user.get("name"):
                employees[idx]["name"] = feishu_user["name"]
            employees[idx]["union_id"] = feishu_user.get("union_id") or ""
            employees[idx]["open_id"] = feishu_user.get("open_id") or ""
            employees[idx]["user_id"] = feishu_user.get("user_id") or ""
            if feishu_user.get("department"):
                employees[idx]["department"] = feishu_user["department"]
            if feishu_user.get("department_ids"):
                employees[idx]["department_ids"] = feishu_user["department_ids"]
            if feishu_user.get("position"):
                employees[idx]["position"] = feishu_user["position"]
            if feishu_user.get("organization"):
                employees[idx]["organization"] = feishu_user["organization"]
            if feishu_user.get("company"):
                employees[idx]["company"] = feishu_user["company"]

            # 更新标识符（便于后续精确匹配）
            if feishu_user.get("union_id"):
                employees[idx]["identifier"] = feishu_user["union_id"]

            # 更新备注
            old_note = employees[idx].get("note", "")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            employees[idx]["note"] = f"{old_note}; [{timestamp}] 飞书账号已合并（手机号匹配）".strip("; ").lstrip("; ")
            break

    _save_permissions({"employees": employees})


def _find_employee_by_account(account: str) -> dict | None:
    account = str(account or "").strip().lower()
    if not account:
        return None
    for index, item in enumerate(_load_permissions().get("employees", [])):
        employee = _clean_employee(item, index)
        if employee["enabled"] and employee["account"].strip().lower() == account:
            return employee
    return None


def _employee_user_info(employee: dict) -> dict:
    return {
        "source": "password",
        "employee_id": employee["id"],
        "role": employee["role"],
        "role_ids": employee.get("role_ids", []),
        "role_label": ROLE_LABELS.get(employee["role"], "普通用户"),
        "username": employee["account"],
        "name": employee["name"],
        "permission_name": employee["name"],
        "union_id": employee.get("union_id", ""),
        "open_id": employee.get("open_id", ""),
        "user_id": employee.get("user_id", ""),
        "identifier": employee.get("identifier", ""),
        "account": employee.get("account", ""),
        "permission_identifier": employee.get("identifier") or employee.get("union_id") or employee.get("account") or "",
        "department": employee.get("department", ""),
        "department_ids": employee.get("department_ids", []),
        "position": employee.get("position", ""),
        "organization": employee.get("organization", ""),
        "company": employee.get("company", ""),
    }


def _login_by_password(username: str, password: str):
    admin_cfg = _admin_config()
    if (
        admin_cfg["password"]
        and username == admin_cfg["username"]
        and secrets.compare_digest(password, admin_cfg["password"])
    ):
        return {
            "source": "admin",
            "role": "super_admin",
            "role_label": ROLE_LABELS["super_admin"],
            "username": username,
            "name": admin_cfg["display_name"],
        }
    employee = _find_employee_by_account(username)
    if employee and _verify_password(password, employee["password_salt"], employee["password_hash"]):
        return _employee_user_info(employee)
    return None


def _require_super_admin():
    user = get_current_user()
    if user.get("role") != "super_admin":
        return None, (jsonify({"success": False, "error": "只有超级管理员可以维护员工权限"}), 403)
    return user, None


def _require_feishu_config() -> tuple[dict, tuple | None]:
    cfg = _feishu_config()
    missing = [key for key in ("app_id", "app_secret") if not cfg.get(key)]
    if missing:
        return cfg, (jsonify({"success": False, "error": f"缺少飞书登录配置: {', '.join(missing)}"}), 500)
    return cfg, None


def _normalize_user(data: dict) -> dict:
    data = data or {}
    departments = data.get("departments") or data.get("department_names") or data.get("departmentNames") or []
    if isinstance(departments, str):
        departments = [departments]
    department_ids = data.get("department_ids") or data.get("departmentIds") or []
    if isinstance(department_ids, str):
        department_ids = [department_ids]
    return {
        "union_id": _pick_text(data, "union_id", "unionId", "unionid"),
        "open_id": _pick_text(data, "open_id", "openId", "openid"),
        "user_id": _pick_text(data, "user_id", "userId", "userid"),
        "name": _pick_text(data, "name", "en_name", "nickname") or "飞书用户",
        "avatar_url": _pick_text(data, "avatar_url", "avatarUrl", "avatar_thumb", "avatarThumb", "avatar_big", "avatarBig"),
        "email": _pick_text(data, "email"),
        "mobile": _pick_text(data, "mobile", "phone", "mobile_phone"),
        "department": _pick_text(data, "department", "department_name", "departmentName") or (departments[0] if departments else ""),
        "departments": departments,
        "department_ids": department_ids,
        "position": _pick_text(data, "position", "job_title", "jobTitle"),
        "organization": _pick_text(data, "organization"),
        "company": _pick_text(data, "company"),
        "source": "feishu",
    }


def _feishu_post(url: str, *, headers: dict | None = None, payload: dict | None = None) -> dict:
    resp = requests.post(url, headers=headers or {}, json=payload or {}, timeout=20)
    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text}
    if resp.status_code >= 400:
        raise RuntimeError(f"Feishu HTTP {resp.status_code}: {body}")
    if body.get("code") not in (None, 0):
        raise RuntimeError(body.get("msg") or body.get("message") or str(body))
    return body


def _feishu_get(url: str, *, headers: dict | None = None, params: dict | None = None) -> dict:
    resp = requests.get(url, headers=headers or {}, params=params or {}, timeout=20)
    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text}
    if resp.status_code >= 400:
        raise RuntimeError(f"Feishu HTTP {resp.status_code}: {body}")
    if body.get("code") not in (None, 0):
        raise RuntimeError(body.get("msg") or body.get("message") or str(body))
    return body


def _get_app_access_token(cfg: dict) -> str:
    url = f"{cfg['base_url']}/open-apis/auth/v3/app_access_token/internal"
    body = _feishu_post(url, payload={"app_id": cfg["app_id"], "app_secret": cfg["app_secret"]})
    token = body.get("app_access_token") or body.get("data", {}).get("app_access_token")
    if not token:
        raise RuntimeError("飞书未返回 app_access_token")
    return token


def _exchange_web_code(cfg: dict, code: str) -> dict:
    app_token = _get_app_access_token(cfg)
    url = f"{cfg['base_url']}/open-apis/authen/v1/access_token"
    body = _feishu_post(
        url,
        headers={"Authorization": f"Bearer {app_token}"},
        payload={"grant_type": "authorization_code", "code": code},
    )
    return body.get("data") or {}


def _exchange_oidc_code(cfg: dict, code: str) -> dict:
    url = f"{cfg['base_url']}/open-apis/authen/v1/oidc/access_token"
    body = _feishu_post(
        url,
        payload={
            "grant_type": "authorization_code",
            "code": code,
            "app_id": cfg["app_id"],
            "app_secret": cfg["app_secret"],
        },
    )
    return body.get("data") or {}


def _enrich_feishu_user(cfg: dict, data: dict) -> dict:
    user_id = _pick_text(data, "user_id", "userId", "userid")
    if not user_id:
        return data or {}
    try:
        app_token = _get_app_access_token(cfg)
        body = _feishu_get(
            f"{cfg['base_url']}/open-apis/contact/v3/users/{user_id}",
            headers={"Authorization": f"Bearer {app_token}"},
            params={"user_id_type": "user_id", "department_id_type": "open_department_id"},
        )
        profile = body.get("data", {}).get("user") or body.get("data") or {}
        if not isinstance(profile, dict):
            return data or {}
        merged = dict(data or {})
        merged.update({
            "name": _pick_text(profile, "name", "en_name", "nickname") or _pick_text(merged, "name", "en_name", "nickname"),
            "union_id": _pick_text(profile, "union_id", "unionId", "unionid") or _pick_text(merged, "union_id", "unionId", "unionid"),
            "open_id": _pick_text(profile, "open_id", "openId", "openid") or _pick_text(merged, "open_id", "openId", "openid"),
            "user_id": _pick_text(profile, "user_id", "userId", "userid") or _pick_text(merged, "user_id", "userId", "userid"),
            "email": _pick_text(profile, "email") or _pick_text(merged, "email"),
            "mobile": _pick_text(profile, "mobile", "phone", "mobile_phone") or _pick_text(merged, "mobile", "phone", "mobile_phone"),
            "department_ids": profile.get("department_ids") or profile.get("departmentIds") or merged.get("department_ids") or [],
            "position": _pick_text(profile, "job_title", "jobTitle", "position") or _pick_text(merged, "position", "job_title", "jobTitle"),
            "job_title": _pick_text(profile, "job_title", "jobTitle") or _pick_text(merged, "job_title", "jobTitle"),
        })
        return merged
    except Exception as exc:
        _log_auth_event("feishu_profile_enrich_failed", "warning", "飞书用户详情补全失败", error=str(exc), status_code=200)
        return data or {}


@auth_bp.route("/api/auth/me", methods=["GET"])
def auth_me():
    user = _apply_employee_permission(get_current_user())
    return jsonify({"success": True, "authenticated": bool(user), "user": user})


@auth_bp.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    token = request.headers.get("X-Auth-Token") or session.get("auth_token") or ""
    user = get_current_user()
    revoked = revoke_token(token)
    session.clear()
    _log_auth_event("logout", "info", "用户退出登录", user=user, revoked=revoked, status_code=200)
    return jsonify({"success": True, "revoked": revoked})


@auth_bp.route("/api/auth/employee-permissions", methods=["GET"])
def employee_permissions_get():
    _, error = _require_super_admin()
    if error:
        return error
    employees = [_clean_employee(item, index) for index, item in enumerate(_load_permissions().get("employees", []))]
    return jsonify({
        "success": True,
        "employees": [_employee_public(item) for item in employees],
        "roles": ROLE_LABELS,
        "default_password": DEFAULT_EMPLOYEE_PASSWORD,
    })


@auth_bp.route("/api/auth/employee-permissions", methods=["PUT"])
def employee_permissions_put():
    _, error = _require_super_admin()
    if error:
        return error
    payload = request.get_json() or {}
    raw_employees = payload.get("employees", [])
    if not isinstance(raw_employees, list):
        return jsonify({"success": False, "error": "employees 必须是数组"}), 400
    employees = []
    seen = set()
    existing_by_account = {}
    for index, item in enumerate(_load_permissions().get("employees", [])):
        employee = _clean_employee(item, index)
        if employee.get("account"):
            existing_by_account[employee["account"].strip().lower()] = employee
    for index, item in enumerate(raw_employees):
        if not isinstance(item, dict):
            continue
        account_key = str(item.get("account") or item.get("username") or "").strip().lower()
        employee = _clean_employee(item, index, existing_by_account.get(account_key))
        key = employee["account"].strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        employee["id"] = employee["id"] or f"employee_{index + 1}"
        employees.append(employee)
    _save_permissions({"employees": employees})
    return jsonify({
        "success": True,
        "employees": [_employee_public(item) for item in employees],
        "roles": ROLE_LABELS,
        "default_password": DEFAULT_EMPLOYEE_PASSWORD,
    })


@auth_bp.route("/api/auth/login", methods=["POST"])
def password_login():
    payload = request.get_json() or {}
    username = str(payload.get("username") or payload.get("account") or "").strip()
    password = str(payload.get("password") or "")
    user_info = _login_by_password(username, password)
    if not user_info:
        _log_auth_event("password_login_failed", "warning", "账号密码登录失败", username=username, status_code=401)
        return jsonify({"success": False, "error": "账号或密码不正确"}), 401
    session_token = create_session_token(user_info)
    _log_auth_event("password_login_success", "info", "账号密码登录成功", user=user_info, username=username, status_code=200)
    return jsonify({"success": True, "token": session_token, "user": user_info})


@auth_bp.route("/api/auth/change-password", methods=["POST"])
def change_password():
    user = get_current_user()
    username = str(user.get("username") or "").strip()
    if not username:
        return jsonify({"success": False, "error": "请先登录后再修改密码"}), 401
    if user.get("role") == "super_admin":
        return jsonify({"success": False, "error": "超级管理员密码由 .env 管理，请修改 SMARTASK_ADMIN_PASSWORD"}), 400
    payload = request.get_json() or {}
    old_password = str(payload.get("old_password") or "")
    new_password = str(payload.get("new_password") or "")
    if len(new_password) < 8:
        return jsonify({"success": False, "error": "新密码至少需要 8 位"}), 400
    data = _load_permissions()
    changed = False
    for index, item in enumerate(data.get("employees", [])):
        employee = _clean_employee(item, index)
        if employee["account"].strip().lower() != username.lower():
            continue
        if not _verify_password(old_password, employee["password_salt"], employee["password_hash"]):
            return jsonify({"success": False, "error": "原密码不正确"}), 401
        salt, password_hash = _hash_password(new_password)
        item["password_salt"] = salt
        item["password_hash"] = password_hash
        item.pop("reset_password", None)
        changed = True
        break
    if not changed:
        return jsonify({"success": False, "error": "未找到当前员工账号"}), 404
    _save_permissions(data)
    return jsonify({"success": True})


@auth_bp.route("/api/auth/admin/login", methods=["POST"])
def admin_login():
    payload = request.get_json() or {}
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    user_info = _login_by_password(username, password)
    if not user_info or user_info.get("role") != "super_admin":
        _log_auth_event("admin_login_failed", "warning", "超管登录失败", username=username, status_code=401)
        return jsonify({"success": False, "error": "超管账号或密码不正确"}), 401
    session_token = create_session_token(user_info)
    _log_auth_event("admin_login_success", "info", "超管登录成功", user=user_info, username=username, status_code=200)
    return jsonify({"success": True, "token": session_token, "user": user_info})


@auth_bp.route("/api/auth/feishu/login-url", methods=["GET"])
def feishu_login_url():
    cfg, error = _require_feishu_config()
    if error:
        return error
    state = secrets.token_urlsafe(16)
    session["feishu_oauth_state"] = state
    redirect_uri = cfg["redirect_uri"] or f"{cfg['backend_url'] or request.host_url.rstrip('/')}/api/auth/feishu/callback"
    params = {
        "app_id": cfg["app_id"],
        "redirect_uri": redirect_uri,
        "state": state,
    }
    url = f"{cfg['base_url']}/open-apis/authen/v1/authorize?{urlencode(params)}"
    return jsonify({"success": True, "url": url, "state": state})


@auth_bp.route("/api/auth/feishu/callback", methods=["GET"])
def feishu_callback():
    cfg, error = _require_feishu_config()
    if error:
        return error
    code = request.args.get("code", "").strip()
    state = request.args.get("state", "").strip()
    expected_state = session.get("feishu_oauth_state")
    if not code:
        return jsonify({"success": False, "error": "缺少飞书 OAuth code"}), 400
    if not expected_state or state != expected_state:
        return jsonify({"success": False, "error": "飞书 OAuth state 校验失败"}), 400
    try:
        user_data = _enrich_feishu_user(cfg, _exchange_web_code(cfg, code))
        normalized_user = _ensure_feishu_employee_user(_normalize_user(user_data))
        user_info = _apply_employee_permission(normalized_user)
        if not user_info:
            _log_auth_event("feishu_login_disabled", "warning", "飞书用户已停用", status_code=403)
            return jsonify({"success": False, "error": "账号已停用，请联系超级管理员"}), 403
        session_token = create_session_token(user_info)
        frontend_base_url = (cfg["frontend_url"] or "").rstrip("/")
        frontend_url = cfg["frontend_callback_url"] or frontend_base_url or "/"
        _log_auth_event("feishu_login_success", "info", "飞书网页登录成功", user=user_info, status_code=302)
        separator = "&" if "?" in frontend_url else "?"
        return redirect(f"{frontend_url}/{separator}token={session_token}")
    except Exception as exc:
        _log_auth_event("feishu_login_failed", "error", "飞书网页登录失败", error=str(exc), status_code=500)
        return jsonify({"success": False, "error": f"飞书登录失败: {exc}"}), 500


@auth_bp.route("/api/feishu/auth", methods=["POST"])
def feishu_in_app_auth():
    cfg, error = _require_feishu_config()
    if error:
        return error
    payload = request.get_json() or {}
    auth_code = str(payload.get("auth_code") or payload.get("code") or "").strip()
    if not auth_code:
        return jsonify({"success": False, "error": "缺少 auth_code"}), 400
    try:
        user_data = _enrich_feishu_user(cfg, _exchange_oidc_code(cfg, auth_code))
        normalized_user = _ensure_feishu_employee_user(_normalize_user(user_data))
        user_info = _apply_employee_permission(normalized_user)
        if not user_info:
            _log_auth_event("feishu_in_app_login_disabled", "warning", "飞书用户已停用", status_code=403)
            return jsonify({"success": False, "error": "账号已停用，请联系超级管理员"}), 403
        session_token = create_session_token(user_info)
        _log_auth_event("feishu_in_app_login_success", "info", "飞书免登录成功", user=user_info, status_code=200)
        return jsonify({"success": True, "token": session_token, "user": user_info})
    except Exception as exc:
        _log_auth_event("feishu_in_app_login_failed", "error", "飞书免登录失败", error=str(exc), status_code=500)
        return jsonify({"success": False, "error": f"飞书免登失败: {exc}"}), 500
