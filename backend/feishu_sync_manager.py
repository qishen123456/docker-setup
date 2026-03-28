"""
飞书多维表格同步配置管理
"""

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 默认飞书同步配置
DEFAULT_FEISHU_CONFIG = {
    "sync_configs": [
        {
            "id": 1,
            "name": "商用事业部销售结果表",
            "description": "同步飞书多维表格数据到PostgreSQL",
            "app_id": "cli_a94aae39fe38dcc7",
            "app_secret": "DegvsVgTJZkI4sSvBzTtJbZJoz0vS6Um",
            "base_id": "EqXfbrQ98aZdpXsLKyecQUPqn0d",
            "table_id": "tblhZC2W8B2RmfO5",
            "view_id": "vewsDasdeY",
            "sync_mode": "incremental",  # incremental: 增量同步, full: 全量同步
            "sync_frequency": "30",  # 分钟
            "target_table": "feishu_business_sales",
            "is_active": False,
            "last_sync_time": None,
            "last_sync_status": "pending",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    ]
}

def _path(filename):
    """获取配置文件的完整路径"""
    return os.path.join(BASE_DIR, 'config', filename)

def read_feishu_config():
    """读取飞书同步配置"""
    try:
        with open(_path('feishu_sync.json'), 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        write_feishu_config(DEFAULT_FEISHU_CONFIG)
        return DEFAULT_FEISHU_CONFIG
    except Exception as e:
        print(f"读取飞书同步配置失败: {e}")
        return DEFAULT_FEISHU_CONFIG

def write_feishu_config(config):
    """写入飞书同步配置"""
    try:
        os.makedirs(os.path.dirname(_path('feishu_sync.json')), exist_ok=True)
        with open(_path('feishu_sync.json'), 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"写入飞书同步配置失败: {e}")
        return False

def get_feishu_configs():
    """获取所有飞书同步配置"""
    config = read_feishu_config()
    return config.get('sync_configs', [])

def add_feishu_config(data):
    """添加飞书同步配置"""
    config = read_feishu_config()
    sync_configs = config.get('sync_configs', [])
    
    # 生成新ID
    if sync_configs:
        new_id = max(item['id'] for item in sync_configs) + 1
    else:
        new_id = 1
    
    new_config = {
        "id": new_id,
        "name": data.get('name', ''),
        "description": data.get('description', ''),
        "app_id": data.get('app_id', ''),
        "app_secret": data.get('app_secret', ''),
        "base_id": data.get('base_id', ''),
        "table_id": data.get('table_id', ''),
        "view_id": data.get('view_id', ''),
        "sync_mode": data.get('sync_mode', 'incremental'),
        "sync_frequency": data.get('sync_frequency', '30'),
        "target_table": data.get('target_table', ''),
        "is_active": data.get('is_active', False),
        "last_sync_time": None,
        "last_sync_status": "pending",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    sync_configs.append(new_config)
    config['sync_configs'] = sync_configs
    config['next_id'] = new_id + 1
    
    return write_feishu_config(config)

def update_feishu_config(config_id, data):
    """更新飞书同步配置"""
    config = read_feishu_config()
    sync_configs = config.get('sync_configs', [])
    
    for i, item in enumerate(sync_configs):
        if item['id'] == config_id:
            sync_configs[i].update({
                "name": data.get('name', item['name']),
                "description": data.get('description', item['description']),
                "app_id": data.get('app_id', item['app_id']),
                "app_secret": data.get('app_secret', item['app_secret']),
                "base_id": data.get('base_id', item['base_id']),
                "table_id": data.get('table_id', item['table_id']),
                "view_id": data.get('view_id', item['view_id']),
                "sync_mode": data.get('sync_mode', item['sync_mode']),
                "sync_frequency": data.get('sync_frequency', item['sync_frequency']),
                "target_table": data.get('target_table', item['target_table']),
                "is_active": data.get('is_active', item['is_active']),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            break
    
    return write_feishu_config(config)

def delete_feishu_config(config_id):
    """删除飞书同步配置"""
    config = read_feishu_config()
    sync_configs = config.get('sync_configs', [])
    
    sync_configs = [item for item in sync_configs if item['id'] != config_id]
    config['sync_configs'] = sync_configs
    
    return write_feishu_config(config)

def update_sync_status(config_id, status, sync_time=None):
    """更新同步状态"""
    config = read_feishu_config()
    sync_configs = config.get('sync_configs', [])
    
    for item in sync_configs:
        if item['id'] == config_id:
            item['last_sync_status'] = status
            if sync_time:
                item['last_sync_time'] = sync_time
            item['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            break
    
    return write_feishu_config(config)
