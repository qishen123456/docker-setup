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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_manager import (
    get_ai_models_safe, get_ai_model_by_id,
    save_ai_model, update_ai_model, delete_ai_model,
    read_json, write_json
)
from vanna_core import test_ai_model, mark_reinit

ai_models_bp = Blueprint('ai_models', __name__)


@ai_models_bp.route('/api/ai-models', methods=['GET'])
def list_ai_models():
    try:
        return jsonify({"models": get_ai_models_safe()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_models_bp.route('/api/ai-models', methods=['POST'])
def create_ai_model():
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
    try:
        model = get_ai_model_by_id(model_id)
        if model is None:
            return jsonify({"error": f"未找到 ID={model_id} 的模型"}), 404

        success, message, response_time = test_ai_model(model)
        return jsonify({
            "success": success,
            "message": message,
            "response_time": response_time
        }), 200 if success else 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_models_bp.route('/api/ai-models/<int:model_id>/set-default', methods=['POST'])
def set_default_model(model_id):
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
