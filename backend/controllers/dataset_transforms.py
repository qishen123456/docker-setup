"""
数据集数据转换 API 控制器
"""

from flask import Blueprint, jsonify, request
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataset_transform_service import transform_service, TransformError
from auth_store import get_current_user
from security import require_feature


dataset_transform_bp = Blueprint("dataset_transform", __name__)


def _require_feature(key: str, error_text: str):
    _, denied = require_feature(key, error_text)
    return denied


@dataset_transform_bp.route("/api/datasets/<int:dataset_id>/transforms", methods=["GET"])
def list_dataset_transforms(dataset_id: int):
    """获取某数据集下的转换任务列表。"""
    denied = _require_feature("dataset_transform_edit", "当前账号没有查看数据转换任务权限")
    if denied:
        return denied
    try:
        transforms = transform_service.get_transforms(dataset_id=dataset_id)
        return jsonify({
            "transforms": transforms,
            "message": "获取数据转换任务列表成功",
        })
    except Exception as e:
        return jsonify({"error": f"获取数据转换任务列表失败: {e}"}), 500


@dataset_transform_bp.route("/api/datasets/<int:dataset_id>/transforms", methods=["POST"])
def create_dataset_transform(dataset_id: int):
    """创建转换任务。"""
    denied = _require_feature("dataset_transform_edit", "当前账号没有创建数据转换任务权限")
    if denied:
        return denied
    try:
        data = request.get_json() or {}
        data["dataset_id"] = dataset_id
        new_id = transform_service.create_transform(data)
        return jsonify({
            "id": new_id,
            "message": "数据转换任务创建成功",
        }), 201
    except TransformError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"创建数据转换任务失败: {e}"}), 500


@dataset_transform_bp.route("/api/dataset-transforms/<int:transform_id>", methods=["PUT"])
def update_dataset_transform(transform_id: int):
    """更新转换任务。"""
    denied = _require_feature("dataset_transform_edit", "当前账号没有编辑数据转换任务权限")
    if denied:
        return denied
    try:
        data = request.get_json() or {}
        success = transform_service.update_transform(transform_id, data)
        if success:
            return jsonify({"message": "数据转换任务更新成功"})
        return jsonify({"error": "数据转换任务不存在或无需更新"}), 404
    except TransformError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"更新数据转换任务失败: {e}"}), 500


@dataset_transform_bp.route("/api/dataset-transforms/<int:transform_id>", methods=["DELETE"])
def delete_dataset_transform(transform_id: int):
    """删除转换任务。"""
    denied = _require_feature("dataset_transform_edit", "当前账号没有删除数据转换任务权限")
    if denied:
        return denied
    try:
        success = transform_service.delete_transform(transform_id)
        if success:
            return jsonify({"message": "数据转换任务删除成功"})
        return jsonify({"error": "数据转换任务不存在"}), 404
    except Exception as e:
        return jsonify({"error": f"删除数据转换任务失败: {e}"}), 500


@dataset_transform_bp.route("/api/dataset-transforms/<int:transform_id>/run", methods=["POST"])
def run_dataset_transform(transform_id: int):
    """手动执行转换任务。"""
    denied = _require_feature("dataset_transform_edit", "当前账号没有执行数据转换任务权限")
    if denied:
        return denied
    try:
        result = transform_service.execute_transform(transform_id, triggered_by="manual")
        if result.get("success"):
            return jsonify({
                "success": True,
                "message": result.get("message"),
                "executed_at": result.get("executed_at"),
            })
        return jsonify({
            "success": False,
            "error": result.get("message"),
            "executed_at": result.get("executed_at"),
        }), 500
    except TransformError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"执行数据转换任务失败: {e}"}), 500


@dataset_transform_bp.route("/api/dataset-transforms/test-sql", methods=["POST"])
def test_dataset_transform_sql():
    """测试转换 SQL（不保存）。"""
    denied = _require_feature("dataset_transform_edit", "当前账号没有测试数据转换 SQL 权限")
    if denied:
        return denied
    try:
        data = request.get_json() or {}
        result = transform_service.test_transform_sql(data)
        if result.get("success"):
            return jsonify({
                "success": True,
                "message": result.get("message"),
            })
        return jsonify({
            "success": False,
            "error": result.get("message"),
        }), 400
    except TransformError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"测试 SQL 失败: {e}"}), 500
