"""
Feishu, local super-admin, and generic auth APIs.
"""
from __future__ import annotations

import os
import secrets
import hashlib
from urllib.parse import urlencode

import requests
from flask import Blueprint, jsonify, redirect, request, session

from config_manager import read_json, write_json
from auth_store import create_session_token, get_current_user, revoke_token
from system_log_store import log_event, request_snapshot


auth_bp = Blueprint("auth", __name__)
PERMISSIONS_FILE = "employee_permissions.json"
DEFAULT_EMPLOYEE_PASSWORD = "12345678"
ROLE_LABELS = {
    "super_admin": "超级管理员",
    "admin": "管理员",
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
            return str(value).strip()
    return default


def _feishu_config() -> dict:
    return {
        "app_id": _env("FEISHU_APP_ID", "SMARTASK_FEISHU_APP_ID"),
        "app_secret": _env("FEISHU_APP_SECRET", "SMARTASK_FEISHU_APP_SECRET"),
        "base_url": _env("FEISHU_BASE_URL", "SMARTASK_FEISHU_BASE_URL", default="https://open.feishu.cn").rstrip("/"),
        "backend_url": _env("BACKEND_URL", "SMARTASK_BACKEND_URL").rstrip("/"),
        "frontend_url": _env("FRONTEND_URL", "SMARTASK_FRONTEND_URL", default="http://localhost:5173").rstrip("/"),
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
    return role if role in {"admin", "user"} else "user"


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return salt, digest


def _verify_password(password: str, salt: str, password_hash: str) -> bool:
    if not salt or not password_hash:
        return False
    _, digest = _hash_password(password, salt)
    return secrets.compare_digest(digest, password_hash)


def _clean_employee(item: dict, index: int, existing: dict | None = None) -> dict:
    account = str(item.get("account") or item.get("username") or "").strip()
    identifier = str(item.get("identifier") or "").strip()
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
        "role": role,
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
    for key in ("union_id", "open_id", "user_id", "email", "mobile", "username", "name"):
        value = str(user.get(key) or "").strip().lower()
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
        if not employee["enabled"]:
            continue
        candidates = {employee.get("identifier", "").strip().lower(), employee.get("account", "").strip().lower()}
        if candidates.intersection(identities):
            matched = employee
            break
    role = matched["role"] if matched else "user"
    user["role"] = role
    user["role_label"] = ROLE_LABELS.get(role, "普通用户")
    if matched:
        user["permission_name"] = matched["name"]
    return user


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
        "role": employee["role"],
        "role_label": ROLE_LABELS.get(employee["role"], "普通用户"),
        "username": employee["account"],
        "name": employee["name"],
        "permission_name": employee["name"],
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
    return {
        "union_id": data.get("union_id") or data.get("unionId") or "",
        "open_id": data.get("open_id") or data.get("openId") or "",
        "user_id": data.get("user_id") or data.get("userId") or "",
        "name": data.get("name") or data.get("en_name") or data.get("nickname") or "飞书用户",
        "avatar_url": data.get("avatar_url") or data.get("avatar_thumb") or data.get("avatar_big") or "",
        "email": data.get("email") or "",
        "mobile": data.get("mobile") or "",
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
    redirect_uri = f"{cfg['backend_url'] or request.host_url.rstrip('/')}/api/auth/feishu/callback"
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
    if expected_state and state and state != expected_state:
        return jsonify({"success": False, "error": "飞书 OAuth state 校验失败"}), 400
    try:
        user_data = _exchange_web_code(cfg, code)
        user_info = _apply_employee_permission(_normalize_user(user_data))
        session_token = create_session_token(user_info)
        frontend_url = cfg["frontend_url"] or "/"
        _log_auth_event("feishu_login_success", "info", "飞书网页登录成功", user=user_info, status_code=302)
        return redirect(f"{frontend_url}/auth/callback?token={session_token}")
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
        user_data = _exchange_oidc_code(cfg, auth_code)
        user_info = _apply_employee_permission(_normalize_user(user_data))
        session_token = create_session_token(user_info)
        _log_auth_event("feishu_in_app_login_success", "info", "飞书免登录成功", user=user_info, status_code=200)
        return jsonify({"success": True, "token": session_token, "user": user_info})
    except Exception as exc:
        _log_auth_event("feishu_in_app_login_failed", "error", "飞书免登录失败", error=str(exc), status_code=500)
        return jsonify({"success": False, "error": f"飞书免登失败: {exc}"}), 500
