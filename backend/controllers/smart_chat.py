"""
智能聊天控制器 - 支持多数据源自动识别
"""

from flask import Blueprint, jsonify, request
import sys, os
import time

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datasource_router import router

smart_chat_bp = Blueprint('smart_chat', __name__)

@smart_chat_bp.route('/api/smart-chat', methods=['POST'])
def smart_chat():
    """
    智能聊天接口 - 自动识别数据源
    请求体: {"question": "查询飞书业绩数据"}
    返回: 包含数据源识别、SQL生成、执行结果的完整响应
    """
    start_time = time.time()
    
    try:
        data = request.get_json()
        if not data or not data.get('question'):
            return jsonify({"error": "问题不能为空"}), 400

        question = data['question'].strip()
        
        # 使用智能路由器处理
        result = router.smart_chat(question)
        
        # 添加执行时间
        result['total_duration'] = round((time.time() - start_time) * 1000, 2)
        
        # 如果有错误，返回错误状态
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "error": f"智能聊天处理失败: {str(e)}",
            "total_duration": round((time.time() - start_time) * 1000, 2)
        }), 500

@smart_chat_bp.route('/api/data-sources', methods=['GET'])
def list_data_sources():
    """列出所有可用的数据源"""
    try:
        sources = []
        for ds_id, config in router.data_sources.items():
            sources.append({
                'id': ds_id,
                'name': config['name'],
                'type': config['type'],
                'keywords': router.keywords.get(ds_id, [])
            })
        
        return jsonify({
            'data_sources': sources,
            'total': len(sources)
        })
        
    except Exception as e:
        return jsonify({"error": f"获取数据源列表失败: {str(e)}"}), 500

@smart_chat_bp.route('/api/test-source-identification', methods=['POST'])
def test_source_identification():
    """测试数据源识别功能"""
    try:
        data = request.get_json()
        question = data.get('question', '')
        
        if not question:
            return jsonify({"error": "问题不能为空"}), 400
        
        source_id, confidence = router.identify_data_source(question)
        
        if source_id is None:
            return jsonify({
                'question': question,
                'identified_source': None,
                'confidence': 0.0,
                'message': '无法识别数据源'
            })
        
        return jsonify({
            'question': question,
            'identified_source': {
                'id': source_id,
                'name': router.data_sources[source_id]['name'],
                'type': router.data_sources[source_id]['type']
            },
            'confidence': confidence,
            'keywords': router.keywords.get(source_id, [])
        })
        
    except Exception as e:
        return jsonify({"error": f"测试失败: {str(e)}"}), 500

@smart_chat_bp.route('/api/train-source/<int:source_id>', methods=['POST'])
def train_data_source(source_id):
    """为特定数据源添加训练数据"""
    try:
        data = request.get_json()
        
        if source_id not in router.data_sources:
            return jsonify({"error": "数据源不存在"}), 404
        
        # 获取该数据源的Vanna实例
        vn, error = router.get_vanna_for_source(source_id)
        if error:
            return jsonify({"error": error}), 500
        
        train_type = data.get('type', 'sql')  # sql / ddl / documentation
        result_id = None
        
        if train_type == 'sql':
            question = data.get('question', '').strip()
            sql = data.get('sql', '').strip()
            if not question or not sql:
                return jsonify({"error": "问题和SQL都不能为空"}), 400
            result_id = vn.train(question=question, sql=sql)
            
        elif train_type == 'ddl':
            ddl = data.get('ddl', '').strip()
            if not ddl:
                return jsonify({"error": "DDL内容不能为空"}), 400
            result_id = vn.train(ddl=ddl)
            
        elif train_type == 'documentation':
            doc = data.get('documentation', '').strip()
            if not doc:
                return jsonify({"error": "文档内容不能为空"}), 400
            result_id = vn.train(documentation=doc)
        
        return jsonify({
            "message": f"训练数据已添加到数据源 {router.data_sources[source_id]['name']}",
            "source_id": source_id,
            "source_name": router.data_sources[source_id]['name'],
            "training_id": result_id
        })
        
    except Exception as e:
        return jsonify({"error": f"训练失败: {str(e)}"}), 500

@smart_chat_bp.route('/api/source-training/<int:source_id>', methods=['GET'])
def get_source_training_data(source_id):
    """获取特定数据源的训练数据"""
    try:
        if source_id not in router.data_sources:
            return jsonify({"error": "数据源不存在"}), 404
        
        vn, error = router.get_vanna_for_source(source_id)
        if error:
            return jsonify({"error": error}), 500
        
        training_data = vn.get_training_data()
        if training_data is None or training_data.empty:
            return jsonify({"training_data": [], "total": 0})
        
        records = training_data.to_dict('records')
        return jsonify({
            "source_id": source_id,
            "source_name": router.data_sources[source_id]['name'],
            "training_data": records,
            "total": len(records)
        })
        
    except Exception as e:
        return jsonify({"error": f"获取训练数据失败: {str(e)}"}), 500
