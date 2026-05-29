from __future__ import annotations

from typing import Iterable

from flask import jsonify

from auth_store import get_current_user
from feature_flags import feature_available


def require_login():
    user = get_current_user()
    if not user:
        return None, (jsonify({"error": "请先登录"}), 401)
    return user, None


def require_feature(key: str, error_text: str = "当前账号没有使用该功能的权限。"):
    user, error = require_login()
    if error:
        return user, error
    if user.get("role") == "super_admin" or feature_available(key, user):
        return user, None
    return user, (jsonify({"error": error_text}), 403)


def require_any_feature(keys: Iterable[str], error_text: str = "当前账号没有使用该功能的权限。"):
    user, error = require_login()
    if error:
        return user, error
    if user.get("role") == "super_admin" or any(feature_available(key, user) for key in keys):
        return user, None
    return user, (jsonify({"error": error_text}), 403)


def require_super_admin(error_text: str = "只有超级管理员可以执行该操作"):
    user, error = require_login()
    if error:
        return user, error
    if user.get("role") == "super_admin":
        return user, None
    return user, (jsonify({"error": error_text}), 403)
