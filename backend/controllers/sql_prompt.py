"""
SQL提示词管理控制器
支持前端配置SQL生成提示词
"""

from flask import Blueprint, jsonify, request
import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sql_prompt_manager import sql_prompt_manager

sql_prompt_bp = Blueprint('sql_prompt', __name__)

@sql_prompt_bp.route('/api/sql-prompts', methods=['GET'])
def list_sql_prompts():
    """获取所有SQL提示词"""
    try:
        prompts = sql_prompt_manager.list_prompts()
        settings = sql_prompt_manager.get_settings()
        
        return jsonify({
            'prompts': prompts,
            'settings': settings,
            'total': len(prompts)
        })
    except Exception as e:
        return jsonify({'error': f'获取SQL提示词失败: {str(e)}'}), 500

@sql_prompt_bp.route('/api/sql-prompts/<prompt_id>', methods=['GET'])
def get_sql_prompt(prompt_id):
    """获取指定的SQL提示词"""
    try:
        prompt = sql_prompt_manager.get_prompt(prompt_id)
        if not prompt:
            return jsonify({'error': '提示词不存在'}), 404
        
        return jsonify({
            'id': prompt_id,
            'prompt': prompt
        })
    except Exception as e:
        return jsonify({'error': f'获取SQL提示词失败: {str(e)}'}), 500

@sql_prompt_bp.route('/api/sql-prompts', methods=['POST'])
def create_sql_prompt():
    """创建新的SQL提示词"""
    try:
        data = request.get_json()
        prompt_id = data.get('id', '').strip()
        name = data.get('name', '').strip()
        content = data.get('content', '').strip()
        is_active = data.get('is_active', False)
        
        if not prompt_id or not name or not content:
            return jsonify({'error': '提示词ID、名称和内容不能为空'}), 400
        
        if sql_prompt_manager.add_prompt(prompt_id, name, content, is_active):
            return jsonify({
                'message': 'SQL提示词创建成功',
                'id': prompt_id,
                'name': name
            })
        else:
            return jsonify({'error': '创建失败，提示词ID可能已存在'}), 400
            
    except Exception as e:
        return jsonify({'error': f'创建SQL提示词失败: {str(e)}'}), 500

@sql_prompt_bp.route('/api/sql-prompts/<prompt_id>', methods=['PUT'])
def update_sql_prompt(prompt_id):
    """更新SQL提示词"""
    try:
        data = request.get_json()
        name = data.get('name')
        content = data.get('content')
        is_active = data.get('is_active')
        
        if sql_prompt_manager.update_prompt(prompt_id, name, content, is_active):
            return jsonify({
                'message': 'SQL提示词更新成功',
                'id': prompt_id
            })
        else:
            return jsonify({'error': '更新失败，提示词不存在'}), 404
            
    except Exception as e:
        return jsonify({'error': f'更新SQL提示词失败: {str(e)}'}), 500

@sql_prompt_bp.route('/api/sql-prompts/<prompt_id>', methods=['DELETE'])
def delete_sql_prompt(prompt_id):
    """删除SQL提示词"""
    try:
        if sql_prompt_manager.delete_prompt(prompt_id):
            return jsonify({
                'message': 'SQL提示词删除成功',
                'id': prompt_id
            })
        else:
            return jsonify({'error': '删除失败，提示词不存在或不能删除默认提示词'}), 404
            
    except Exception as e:
        return jsonify({'error': f'删除SQL提示词失败: {str(e)}'}), 500

@sql_prompt_bp.route('/api/sql-prompts/<prompt_id>/set-default', methods=['POST'])
def set_default_sql_prompt(prompt_id):
    """设置默认SQL提示词"""
    try:
        if sql_prompt_manager.set_default_prompt(prompt_id):
            return jsonify({
                'message': '默认SQL提示词设置成功',
                'default_prompt_id': prompt_id
            })
        else:
            return jsonify({'error': '设置失败，提示词不存在'}), 404
            
    except Exception as e:
        return jsonify({'error': f'设置默认SQL提示词失败: {str(e)}'}), 500

@sql_prompt_bp.route('/api/sql-prompts/settings', methods=['GET'])
def get_sql_prompt_settings():
    """获取SQL提示词全局设置"""
    try:
        settings = sql_prompt_manager.get_settings()
        return jsonify(settings)
    except Exception as e:
        return jsonify({'error': f'获取设置失败: {str(e)}'}), 500

@sql_prompt_bp.route('/api/sql-prompts/settings', methods=['PUT'])
def update_sql_prompt_settings():
    """更新SQL提示词全局设置"""
    try:
        data = request.get_json()
        if sql_prompt_manager.update_settings(**data):
            return jsonify({
                'message': 'SQL提示词设置更新成功',
                'settings': sql_prompt_manager.get_settings()
            })
        else:
            return jsonify({'error': '设置更新失败'}), 400
            
    except Exception as e:
        return jsonify({'error': f'更新设置失败: {str(e)}'}), 500

@sql_prompt_bp.route('/api/sql-prompts/test', methods=['POST'])
def test_sql_prompt():
    """测试SQL提示词效果"""
    try:
        data = request.get_json()
        prompt_id = data.get('prompt_id')
        database_name = data.get('database_name', 'test_db')
        database_type = data.get('database_type', 'postgresql')
        
        formatted_prompt = sql_prompt_manager.format_prompt(
            prompt_id=prompt_id,
            database_name=database_name,
            database_type=database_type
        )
        
        return jsonify({
            'prompt_id': prompt_id,
            'formatted_prompt': formatted_prompt,
            'test_variables': {
                'database_name': database_name,
                'database_type': database_type
            }
        })
    except Exception as e:
        return jsonify({'error': f'测试SQL提示词失败: {str(e)}'}), 500
