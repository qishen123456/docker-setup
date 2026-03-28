"""
训练数据控制器
GET    /api/training          - 获取训练数据列表（来自 ChromaDB）
POST   /api/training          - 添加训练数据（DDL/文档/问答对）
DELETE /api/training/<id>     - 删除训练数据（ChromaDB id）
POST   /api/training/train    - 批量触发 vn.train()
"""

from flask import Blueprint, jsonify, request
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vanna_core import get_vanna_instance

training_bp = Blueprint('training', __name__)


@training_bp.route('/api/training', methods=['GET'])
def list_training_data():
    try:
        vn, error = get_vanna_instance()
        if error:
            return jsonify({"error": error}), 503

        training_data = vn.get_training_data()
        if training_data is None or training_data.empty:
            return jsonify({"training_data": [], "total": 0})

        # 转换为 JSON 可序列化格式
        records = training_data.to_dict('records')
        return jsonify({
            "training_data": records,
            "total": len(records)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@training_bp.route('/api/training', methods=['POST'])
def add_training_data():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400

        train_type = data.get('type', 'documentation')  # ddl / documentation / sql

        vn, error = get_vanna_instance()
        if error:
            return jsonify({"error": error}), 503

        result_id = None

        if train_type == 'ddl':
            ddl = data.get('ddl', '').strip()
            if not ddl:
                return jsonify({"error": "DDL 内容不能为空"}), 400
            result_id = vn.train(ddl=ddl)
            return jsonify({"message": f"DDL 训练数据已添加", "id": result_id})

        elif train_type == 'documentation':
            doc = data.get('documentation', '').strip()
            if not doc:
                return jsonify({"error": "文档内容不能为空"}), 400
            result_id = vn.train(documentation=doc)
            return jsonify({"message": f"文档训练数据已添加", "id": result_id})

        elif train_type == 'sql':
            question = data.get('question', '').strip()
            sql = data.get('sql', '').strip()
            if not question or not sql:
                return jsonify({"error": "问题和 SQL 不能为空"}), 400
            result_id = vn.train(question=question, sql=sql)
            return jsonify({"message": f"问答对训练数据已添加", "id": result_id})

        else:
            return jsonify({"error": f"不支持的训练类型：{train_type}，请使用 ddl/documentation/sql"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@training_bp.route('/api/training/<string:training_id>', methods=['DELETE'])
def delete_training_data(training_id):
    try:
        vn, error = get_vanna_instance()
        if error:
            return jsonify({"error": error}), 503

        vn.remove_training_data(id=training_id)
        return jsonify({"message": "训练数据已删除"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@training_bp.route('/api/training/train', methods=['POST'])
def batch_train():
    """批量训练：接收 DDL 列表、文档列表、问答对列表"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400

        vn, error = get_vanna_instance()
        if error:
            return jsonify({"error": error}), 503

        results = {"success": 0, "failed": 0, "errors": []}

        # 批量 DDL
        for ddl in data.get('ddls', []):
            try:
                vn.train(ddl=ddl)
                results['success'] += 1
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(str(e))

        # 批量文档
        for doc in data.get('documentations', []):
            try:
                vn.train(documentation=doc)
                results['success'] += 1
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(str(e))

        # 批量问答对
        for pair in data.get('sql_pairs', []):
            try:
                vn.train(question=pair.get('question', ''), sql=pair.get('sql', ''))
                results['success'] += 1
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(str(e))

        return jsonify({
            "message": f"批量训练完成：成功 {results['success']} 条，失败 {results['failed']} 条",
            **results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
