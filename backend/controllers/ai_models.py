"""
AI 模型配置控制器
GET    /api/ai-models          - 获取所有模型
POST   /api/ai-models          - 新增模型
PUT    /api/ai-models/<id>     - 更新模型
DELETE /api/ai-models/<id>     - 删除模型
POST   /api/ai-models/<id>/test - 测试模型连通性
POST   /api/ai-models/<id>/set-default - 设为默认
"""

from flask import Blueprint, jsonify, request
import sys, os
from typing import Optional, List, Dict, Any
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_manager import (
    get_ai_models_safe, get_ai_model_by_id,
    save_ai_model, update_ai_model, delete_ai_model,
    read_json, write_json
)
from security import require_feature, require_login
from vanna_core import test_ai_model, mark_reinit

ai_models_bp = Blueprint('ai_models', __name__)


@ai_models_bp.route('/api/ai-models', methods=['GET'])
def list_ai_models():
    _, denied = require_feature("ai_model_config", "当前账号没有查看模型服务配置权限")
    if denied:
        return denied
    try:
        return jsonify({"models": get_ai_models_safe()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_models_bp.route('/api/ai-models', methods=['POST'])
def create_ai_model():
    _, denied = require_feature("ai_model_edit", "当前账号没有维护模型配置权限")
    if denied:
        return denied
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        if not data.get('name'):
            return jsonify({"error": "模型名称不能为空"}), 400
        if not data.get('api_key'):
            return jsonify({"error": "API Key 不能为空"}), 400

        new_model = save_ai_model(data)
        mark_reinit()

        safe = dict(new_model)
        safe.pop('api_key_b64', None)
        safe['api_key'] = '***已保存***'
        return jsonify({"message": "AI模型已添加", "model": safe}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_models_bp.route('/api/ai-models/<int:model_id>', methods=['PUT'])
def update_ai_model_route(model_id):
    _, denied = require_feature("ai_model_edit", "当前账号没有维护模型配置权限")
    if denied:
        return denied
    try:
        data = request.get_json()
        updated = update_ai_model(model_id, data)
        if updated is None:
            return jsonify({"error": f"未找到 ID={model_id} 的模型"}), 404

        mark_reinit()
        safe = dict(updated)
        safe.pop('api_key_b64', None)
        safe['api_key'] = '***已保存***'
        return jsonify({"message": "AI模型已更新", "model": safe})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_models_bp.route('/api/ai-models/<int:model_id>', methods=['DELETE'])
def delete_ai_model_route(model_id):
    _, denied = require_feature("ai_model_edit", "当前账号没有维护模型配置权限")
    if denied:
        return denied
    try:
        success = delete_ai_model(model_id)
        if not success:
            return jsonify({"error": f"未找到 ID={model_id} 的模型"}), 404
        mark_reinit()
        return jsonify({"message": "AI模型已删除"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_models_bp.route('/api/ai-models/<int:model_id>/test', methods=['POST'])
def test_ai_model_route(model_id):
    _, denied = require_feature("ai_model_test", "当前账号没有测试模型连接权限")
    if denied:
        return denied
    try:
        model = get_ai_model_by_id(model_id)
        if model is None:
            return jsonify({"error": f"未找到 ID={model_id} 的模型"}), 404

        success, message, response_time = test_ai_model(model)

        # 持久化测通状态（bug/需求 2026-08-25：模型下拉只显示实测连通过的模型，
        # 测试结果写回 ai_settings.json 的 test_ok / last_test_at）
        try:
            config = read_json('ai_settings.json')
            for m in config.get('models', []):
                if m.get('id') == model_id:
                    m['test_ok'] = bool(success)
                    import time as _t
                    m['last_test_at'] = _t.strftime('%Y-%m-%d %H:%M:%S')
                    break
            write_json('ai_settings.json', config)
            mark_reinit()
        except Exception:
            # 持久化失败不影响本次测试结果返回
            pass

        return jsonify({
            "success": success,
            "message": message,
            "response_time": response_time
        }), 200 if success else 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_models_bp.route('/api/ai-models/<int:model_id>/set-default', methods=['POST'])
def set_default_model(model_id):
    _, denied = require_feature("ai_model_edit", "当前账号没有维护模型配置权限")
    if denied:
        return denied
    try:
        config = read_json('ai_settings.json')
        models = config.get('models', [])
        found = False
        for m in models:
            m['is_default'] = (m['id'] == model_id)
            if m['id'] == model_id:
                found = True
        if not found:
            return jsonify({"error": f"未找到 ID={model_id} 的模型"}), 404
        write_json('ai_settings.json', config)
        mark_reinit()
        return jsonify({"message": "已设为默认模型"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _get_effective_allowed_model_ids(user: Dict[str, Any]) -> Optional[List[int]]:
    """
    双层模型权限解析（方案A：默认模型全局通用）：
    
    优先级：
    1. 用户独立配置 (employee_permissions.allowed_model_ids)
    2. 角色默认配置 (rbac_permissions.roles[].allowed_model_ids)
    3. 无限制 (返回 None)
    
    特殊规则：
    - super_admin / admin 角色不限制，返回 None
    - is_default=True 的模型始终可用（在调用层处理）
    - 空列表 [] 等同于无限制（向后兼容）
    """
    if not user:
        return None
    
    # 超管和管理员不限制
    role = user.get("role", "")
    if role in ("super_admin", "admin"):
        return None
    
    # Step 1: 检查用户独立配置（优先）
    try:
        emp_config = read_json("employee_permissions.json")
        employees = emp_config.get("employees", [])
        user_id = user.get("id", "")
        
        emp = next((e for e in employees if e.get("id") == user_id), None)
        if emp and "allowed_model_ids" in emp:
            allowed = emp.get("allowed_model_ids")
            # 空列表视为无限制
            if isinstance(allowed, list) and len(allowed) > 0:
                return allowed
            elif isinstance(allowed, list) and len(allowed) == 0:
                return None  # 显式空列表 = 不限制
    except Exception:
        pass
    
    # Step 2: 回退到角色配置
    try:
        rbac_config = read_json("rbac_permissions.json")
        roles = rbac_config.get("roles", [])
        
        role_config = next((r for r in roles if r.get("id") == role or r.get("code") == role), None)
        if role_config and "allowed_model_ids" in role_config:
            allowed = role_config.get("allowed_model_ids")
            if isinstance(allowed, list) and len(allowed) > 0:
                return allowed
            elif isinstance(allowed, list) and len(allowed) == 0:
                return None
    except Exception:
        pass
    
    # Step 3: 无限制
    return None


@ai_models_bp.route('/api/ai-models/active', methods=['GET'])
def list_active_models():
    """
    返回当前用户可用的模型列表（方案A：默认模型全局通用）
    
    规则：
    1. 默认模型 (is_default=True) 对所有用户可见且排在首位
    2. 其他模型根据用户角色/个人配置过滤
    3. super_admin / admin 可见所有活跃模型
    """
    from security import get_current_user

    _, denied = require_login()
    if denied:
        return denied

    user = get_current_user()  # 必须在 require_login 之后获取用户信息

    try:
        models = get_ai_models_safe()
        # 只保留启用且「默认模型 或 实测连通过」的模型（需求 2026-08-25）
        active = [
            m for m in models
            if m.get("is_active") and (m.get("is_default") or m.get("test_ok"))
        ]

        # 去重：同名+同 provider 重复时优先保留通道名非空的，其次 id 小的
        # （bug 2026-08-25：历史遗留 MiniMax-M2.5 ×2，id=4 有通道 vs id=10 通道空，
        # 重复让下拉列表"看着混乱"）
        seen_keys = {}
        for m in active:
            key = (m.get("name"), m.get("provider"))
            cur = seen_keys.get(key)
            if cur is None:
                seen_keys[key] = m
                continue
            cur_has_channel = bool((cur.get("channel_display_name") or "").strip())
            new_has_channel = bool((m.get("channel_display_name") or "").strip())
            if new_has_channel and not cur_has_channel:
                seen_keys[key] = m
            elif new_has_channel == cur_has_channel and int(m.get("id", 0)) < int(cur.get("id", 0)):
                seen_keys[key] = m
        active = list(seen_keys.values())

        # 获取用户权限范围（非默认模型）
        allowed_ids = _get_effective_allowed_model_ids(user)

        # 分离默认模型和非默认模型
        default_models = [m for m in active if m.get("is_default")]
        non_default_models = [m for m in active if not m.get("is_default")]

        # 过滤非默认模型
        # 超管/管理员看全部活跃模型（bug 2026-08-25：超管 id=None 曾误触下面"未识别用户"清空分支，
        # 导致非默认模型被清空、下拉只剩默认模型）
        role = str(user.get("role") or "") if isinstance(user, dict) else ""
        if role in ("super_admin", "admin"):
            # 超管/管理员：保留全部非默认模型
            pass
        elif allowed_ids is not None:
            # 有权限配置 → 按配置过滤
            non_default_models = [m for m in non_default_models if m["id"] in allowed_ids]
        elif not user or not user.get("id"):
            # 无法识别用户身份时，不显示任何非默认模型（防止未授权访问）
            non_default_models = []
        
        # 组装结果（默认模型始终在前）
        result_models = default_models + non_default_models
        
        # 转换为前端格式（不含敏感字段；含通道展示字段）
        result = [
            {
                "id": m["id"],
                "name": m["name"],
                "model": m.get("model", ""),
                "is_default": m.get("is_default", False),
                "channel_display_name": m.get("channel_display_name", ""),
                "channel_icon": m.get("channel_icon", ""),
            }
            for m in result_models
        ]
        
        return jsonify({"models": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
