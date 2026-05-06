"""
飞书同步API控制器
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import threading
import sys
import os

# 添加当前目录到路径，以便导入feishu_url_parser
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from feishu_url_parser import parse_feishu_url
from feishu_sync_logger import get_logs, get_all_logs, get_log_stats, clear_logs

from feishu_sync_manager import (
    get_feishu_configs, 
    add_feishu_config, 
    update_feishu_config, 
    delete_feishu_config,
    update_sync_status
)
from feishu_sync_service import sync_service

feishu_bp = Blueprint('feishu', __name__)

@feishu_bp.route('/api/feishu-sync', methods=['GET'])
def get_feishu_sync_configs():
    """获取飞书同步配置列表"""
    try:
        configs = get_feishu_configs()
        return jsonify({
            "sync_configs": configs,
            "message": "获取飞书同步配置成功"
        })
    except Exception as e:
        return jsonify({
            "error": f"获取飞书同步配置失败: {str(e)}",
            "sync_configs": []
        }), 500

@feishu_bp.route('/api/feishu-sync', methods=['POST'])
def create_feishu_sync_config():
    """创建飞书同步配置"""
    try:
        data = request.get_json()
        if data.get('target_table'):
            data['target_table'] = sync_service.normalize_table_name(data['target_table'])
        
        # 验证必填字段
        required_fields = ['name', 'target_table', 'app_id', 'app_secret', 'base_id', 'table_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    "error": f"缺少必填字段: {field}"
                }), 400
        
        success = add_feishu_config(data)
        if success:
            return jsonify({
                "message": "飞书同步配置创建成功",
                "config_id": len(get_feishu_configs())
            }), 201
        else:
            return jsonify({
                "error": "创建飞书同步配置失败"
            }), 500
            
    except Exception as e:
        return jsonify({
            "error": f"创建飞书同步配置失败: {str(e)}"
        }), 500

@feishu_bp.route('/api/feishu-sync/<int:config_id>', methods=['PUT'])
def update_feishu_sync_config(config_id):
    """更新飞书同步配置"""
    try:
        data = request.get_json()
        if data.get('target_table'):
            data['target_table'] = sync_service.normalize_table_name(data['target_table'])
        
        success = update_feishu_config(config_id, data)
        if success:
            return jsonify({
                "message": "飞书同步配置更新成功"
            })
        else:
            return jsonify({
                "error": "更新飞书同步配置失败"
            }), 500
            
    except Exception as e:
        return jsonify({
            "error": f"更新飞书同步配置失败: {str(e)}"
        }), 500

@feishu_bp.route('/api/feishu-sync/<int:config_id>', methods=['DELETE'])
def delete_feishu_sync_config(config_id):
    """删除飞书同步配置"""
    try:
        success = delete_feishu_config(config_id)
        if success:
            return jsonify({
                "message": "飞书同步配置删除成功"
            })
        else:
            return jsonify({
                "error": "删除飞书同步配置失败"
            }), 500
            
    except Exception as e:
        return jsonify({
            "error": f"删除飞书同步配置失败: {str(e)}"
        }), 500

@feishu_bp.route('/api/feishu-sync/<int:config_id>/pause', methods=['POST'])
def pause_sync(config_id):
    """暂停同步配置"""
    try:
        # 更新配置状态为非活跃
        success = update_feishu_config(config_id, {'is_active': False})
        if success:
            return jsonify({
                "message": "同步配置已暂停"
            })
        else:
            return jsonify({
                "error": "暂停同步配置失败"
            }), 500
            
    except Exception as e:
        return jsonify({
            "error": f"暂停同步失败: {str(e)}"
        }), 500

@feishu_bp.route('/api/feishu-sync/<int:config_id>/resume', methods=['POST'])
def resume_sync(config_id):
    """恢复同步配置"""
    try:
        # 更新配置状态为活跃
        success = update_feishu_config(config_id, {'is_active': True})
        if success:
            return jsonify({
                "message": "同步配置已恢复"
            })
        else:
            return jsonify({
                "error": "恢复同步配置失败"
            }), 500
            
    except Exception as e:
        return jsonify({
            "error": f"恢复同步失败: {str(e)}"
        }), 500

@feishu_bp.route('/api/feishu-sync/<int:config_id>/start', methods=['POST'])
def start_sync(config_id):
    """手动启动同步"""
    try:
        configs = get_feishu_configs()
        target_config = None
        
        for config in configs:
            if config['id'] == config_id:
                target_config = config
                break
        
        if not target_config:
            return jsonify({
                "error": "未找到指定的同步配置"
            }), 404
        
        # 在后台线程中执行同步
        def sync_worker():
            sync_service.sync_single_config(target_config)
        
        thread = threading.Thread(target=sync_worker)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "message": f"已启动同步任务: {target_config['name']}"
        })
        
    except Exception as e:
        return jsonify({
            "error": f"启动同步失败: {str(e)}"
        }), 500

@feishu_bp.route('/api/feishu-sync/<int:config_id>/status', methods=['GET'])
def get_sync_status(config_id):
    """获取同步状态"""
    try:
        configs = get_feishu_configs()
        target_config = None
        
        for config in configs:
            if config['id'] == config_id:
                target_config = config
                break
        
        if not target_config:
            return jsonify({
                "error": "未找到指定的同步配置"
            }), 404
        
        return jsonify({
            "config": target_config,
            "message": "获取同步状态成功"
        })
        
    except Exception as e:
        return jsonify({
            "error": f"获取同步状态失败: {str(e)}"
        }), 500

@feishu_bp.route('/api/feishu-sync/start-all', methods=['POST'])
def start_all_sync():
    """启动所有活跃配置的同步"""
    try:
        def sync_worker():
            sync_service.sync_all_active_configs()
        
        thread = threading.Thread(target=sync_worker)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "message": "已启动所有活跃配置的同步任务"
        })
        
    except Exception as e:
        return jsonify({
            "error": f"启动同步失败: {str(e)}"
        }), 500

@feishu_bp.route('/api/feishu-sync/parse-url', methods=['POST'])
def parse_feishu_url_api():
    """解析飞书链接"""
    try:
        data = request.get_json()
        if not data or not data.get('url'):
            return jsonify({
                "success": False,
                "error": "请提供飞书链接"
            }), 400
        
        url = data['url'].strip()
        result = parse_feishu_url(url)
        
        if result.get('success'):
            return jsonify({
                "success": True,
                "parsed": result
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get('error', '链接解析失败')
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"解析失败: {str(e)}"
        }), 500

@feishu_bp.route('/api/feishu-sync/schema-preview', methods=['POST'])
def preview_feishu_schema():
    """预览飞书字段和 PG 目标表字段差异"""
    try:
        data = request.get_json() or {}
        required_fields = ['app_id', 'app_secret', 'base_id', 'table_id', 'target_table']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    "success": False,
                    "error": f"缺少必填字段: {field}"
                }), 400

        data['id'] = int(data.get('id') or 0)
        data['target_table'] = sync_service.normalize_table_name(data['target_table'])
        sample_limit = int(data.get('sample_limit') or 50)
        preview = sync_service.preview_schema(data, sample_limit=sample_limit)
        return jsonify({
            "success": True,
            "preview": preview,
            "message": "字段结构检测完成"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"字段结构检测失败: {str(e)}"
        }), 500

@feishu_bp.route('/api/feishu-sync/logs/<int:config_id>', methods=['GET'])
def get_sync_logs(config_id):
    """获取指定配置的同步日志"""
    try:
        limit = request.args.get('limit', 100, type=int)
        logs = get_logs(config_id, limit)
        return jsonify({
            "logs": logs,
            "config_id": config_id,
            "total": len(logs)
        })
    except Exception as e:
        return jsonify({
            "error": f"获取日志失败: {str(e)}",
            "logs": []
        }), 500

@feishu_bp.route('/api/feishu-sync/logs', methods=['GET'])
def get_all_sync_logs():
    """获取所有配置的同步日志"""
    try:
        limit = request.args.get('limit', 50, type=int)
        logs = get_all_logs(limit)
        return jsonify({
            "logs": logs,
            "total": len(logs)
        })
    except Exception as e:
        return jsonify({
            "error": f"获取日志失败: {str(e)}",
            "logs": []
        }), 500

@feishu_bp.route('/api/feishu-sync/logs/stats', methods=['GET'])
def get_logs_statistics():
    """获取日志统计信息"""
    try:
        stats = get_log_stats()
        return jsonify({
            "stats": stats,
            "message": "获取日志统计成功"
        })
    except Exception as e:
        return jsonify({
            "error": f"获取日志统计失败: {str(e)}"
        }), 500

@feishu_bp.route('/api/feishu-sync/logs/<int:config_id>/clear', methods=['POST'])
def clear_config_logs(config_id):
    """清空指定配置的日志"""
    try:
        clear_logs(config_id)
        return jsonify({
            "message": f"配置 {config_id} 的日志已清空"
        })
    except Exception as e:
        return jsonify({
            "error": f"清空日志失败: {str(e)}"
        }), 500

@feishu_bp.route('/api/feishu-sync/logs/clear', methods=['POST'])
def clear_all_logs():
    """清空所有日志"""
    try:
        clear_logs()
        return jsonify({
            "message": "所有日志已清空"
        })
    except Exception as e:
        return jsonify({
            "error": f"清空日志失败: {str(e)}"
        }), 500

@feishu_bp.route('/api/feishu-sync/test-connection', methods=['POST'])
def test_feishu_connection():
    """测试飞书连接"""
    try:
        data = request.get_json()
        app_id = data.get('app_id')
        app_secret = data.get('app_secret')
        base_id = data.get('base_id')
        table_id = data.get('table_id')
        
        if not all([app_id, app_secret, base_id, table_id]):
            return jsonify({
                "error": "缺少连接测试参数"
            }), 400
        
        # 测试获取访问令牌
        # 使用临时config_id=1进行测试
        access_token = sync_service.get_access_token(app_id, app_secret, 1)
        if not access_token:
            return jsonify({
                "success": False,
                "error": "获取访问令牌失败，请检查App ID和App Secret"
            })
        
        # 测试获取数据（只获取前几条）
        test_records = sync_service.get_feishu_data({
            'id': 0,
            'name': 'connection_test',
            'base_id': base_id,
            'table_id': table_id,
            'view_id': data.get('view_id', '')
        }, access_token, limit=20)
        
        if test_records is not None:
            return jsonify({
                "success": True,
                "message": f"连接成功，共获取到{len(test_records)}条记录"
            })
        else:
            return jsonify({
                "success": False,
                "error": "获取数据失败，请检查Base ID和Table ID"
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"连接测试失败: {str(e)}"
        }), 500
