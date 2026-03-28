"""
数据源管理控制器
GET    /api/datasources          - 获取所有数据源
POST   /api/datasources          - 新增数据源
PUT    /api/datasources/<id>     - 更新数据源
DELETE /api/datasources/<id>     - 删除数据源
POST   /api/datasources/<id>/test - 测试连接
"""

from flask import Blueprint, jsonify, request
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_manager import (
    get_datasources_safe, get_datasource_by_id,
    save_datasource, update_datasource, delete_datasource
)
from vanna_core import test_db_connection, mark_reinit

datasources_bp = Blueprint('datasources', __name__)


@datasources_bp.route('/api/datasources', methods=['GET'])
def list_datasources():
    try:
        return jsonify({"databases": get_datasources_safe()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@datasources_bp.route('/api/datasources', methods=['POST'])
def create_datasource():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
        if not data.get('name'):
            return jsonify({"error": "连接名称不能为空"}), 400

        new_db = save_datasource(data)
        mark_reinit()  # 通知 Vanna 重新初始化

        # 返回脱敏版本
        safe = dict(new_db)
        safe.pop('password_b64', None)
        safe['password'] = '***' if new_db.get('password_b64') else ''
        return jsonify({"message": "数据源已添加", "database": safe}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@datasources_bp.route('/api/datasources/<int:db_id>', methods=['PUT'])
def update_datasource_route(db_id):
    try:
        data = request.get_json()
        updated = update_datasource(db_id, data)
        if updated is None:
            return jsonify({"error": f"未找到 ID={db_id} 的数据源"}), 404

        mark_reinit()
        safe = dict(updated)
        safe.pop('password_b64', None)
        safe['password'] = '***' if updated.get('password_b64') else ''
        return jsonify({"message": "数据源已更新", "database": safe})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@datasources_bp.route('/api/datasources/<int:db_id>', methods=['DELETE'])
def delete_datasource_route(db_id):
    try:
        success = delete_datasource(db_id)
        if not success:
            return jsonify({"error": f"未找到 ID={db_id} 的数据源"}), 404
        mark_reinit()
        return jsonify({"message": "数据源已删除"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@datasources_bp.route('/api/datasources/<int:db_id>/test', methods=['POST'])
def test_datasource(db_id):
    try:
        db = get_datasource_by_id(db_id)
        if db is None:
            return jsonify({"error": f"未找到 ID={db_id} 的数据源"}), 404

        success, message = test_db_connection(db)
        return jsonify({
            "success": success,
            "message": message
        }), 200 if success else 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500
