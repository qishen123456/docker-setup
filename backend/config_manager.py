"""
配置文件管理器
职责：读写存储在 config/ 目录下的 JSON 配置文件
- datasources.json：数据库连接信息（密码 Base64 混淆）
- ai_settings.json：AI 模型配置（API Key 混淆）
- app_config.json：系统基础配置
- query_history.json：问答历史记录
"""

import json
import os
import base64
from datetime import datetime
from typing import Optional, Dict, Any

# 配置目录：backend/ 同级的 config/ 文件夹
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
LOCAL_OVERRIDE_FILES = {'datasources.json'}

# ─────────────────────────────────────────────────────────
# 工具函数：文件路径
# ─────────────────────────────────────────────────────────
def _path(filename):
    return os.path.join(CONFIG_DIR, filename)


def _local_path(filename):
    if not filename.endswith('.json'):
        return None
    base, ext = os.path.splitext(filename)
    return os.path.join(CONFIG_DIR, f'{base}.local{ext}')


def resolve_read_path(filename: str) -> str:
    local_path = _local_path(filename)
    if filename in LOCAL_OVERRIDE_FILES and local_path and os.path.exists(local_path):
        return local_path
    return _path(filename)


def resolve_write_paths(filename: str):
    primary = _path(filename)
    if filename in LOCAL_OVERRIDE_FILES:
        local_path = _local_path(filename)
        if local_path:
            return [primary, local_path]
    return [primary]


def _ensure_dir():
    """确保 config 目录存在"""
    os.makedirs(CONFIG_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────
# 工具函数：Base64 混淆（密码、API Key 存储用）
# ─────────────────────────────────────────────────────────
def encode_secret(text: str) -> str:
    """对敏感字符串进行 Base64 混淆"""
    if not text:
        return ''
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')


def decode_secret(encoded: str) -> str:
    """解码 Base64 混淆的字符串"""
    if not encoded:
        return ''
    try:
        return base64.b64decode(encoded.encode('utf-8')).decode('utf-8')
    except Exception:
        return encoded  # 如果解码失败，直接返回原始值（兼容旧数据）


# ─────────────────────────────────────────────────────────
# 通用 JSON 读写
# ─────────────────────────────────────────────────────────
def read_json(filename: str) -> dict:
    """读取 JSON 配置文件，文件不存在则返回空 dict"""
    _ensure_dir()
    filepath = resolve_read_path(filename)
    if not os.path.exists(filepath):
        return {}
    encodings = ['utf-8', 'utf-8-sig', 'gb18030', 'gbk']
    last_error = None
    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                return json.load(f)
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except json.JSONDecodeError as e:
            last_error = e
            continue
    raise ValueError(f"无法读取配置文件 {filepath}: {last_error}")


def write_json(filename: str, data: dict):
    """将 dict 写入 JSON 配置文件（格式化输出）"""
    _ensure_dir()
    # 添加变更日志（仅对数据源配置）
    if filename == 'datasources.json':
        log_datasource_change(data, _path(filename))

    for filepath in resolve_write_paths(filename):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def log_datasource_change(data: dict, filepath: str):
    """记录数据源变更日志"""
    try:
        log_file = os.path.join(CONFIG_DIR, 'datasource_changes.log')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n[{timestamp}] 数据源配置更新\n")
            f.write(f"数据源数量: {len(data.get('databases', []))}\n")
            f.write(f"下一个ID: {data.get('next_id', 'N/A')}\n")
            
            for db in data.get('databases', []):
                f.write(f"  - ID:{db['id']} 名称:{db['name']} 类型:{db['type']} 状态:{'启用' if db.get('is_active') else '禁用'}\n")
            
            f.write("-" * 50 + "\n")
    except Exception as e:
        print(f"⚠️  无法记录数据源变更日志: {e}")


# ─────────────────────────────────────────────────────────
# 默认配置模板初始化
# ─────────────────────────────────────────────────────────
DEFAULT_APP_CONFIG = {
    "port": 5000,
    "debug": True,
    "secret_key": "vanna-local-secret-2026",
    "chroma_path": "./chroma_db",
    "app_name": "Vanna 智能问数系统",
    "version": "1.0.0"
}

DEFAULT_DATASOURCES = {
    "databases": [
        {
            "id": 1,
            "name": "本地测试库 (SQLite)",
            "type": "sqlite",
            "sqlite_path": "./test.db",
            "host": "",
            "port": 0,
            "database_name": "",
            "username": "",
            "password_b64": "",
            "driver": "",
            "is_active": True,
            "is_default": True,
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    ],
    "next_id": 2
}

DEFAULT_AI_SETTINGS = {
    "models": [
        {
            "id": 1,
            "name": "通义千问 qwen-max",
            "provider": "dashscope",
            "model": "qwen-max",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key_b64": encode_secret("请填入您的 API Key"),
            "is_active": True,
            "is_default": True,
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    ],
    "next_id": 2
}

DEFAULT_QUERY_HISTORY = {
    "history": [],
    "total_queries": 0
}


def init_default_configs():
    """后端启动时调用：如果配置文件不存在则创建默认模板"""
    _ensure_dir()

    if not os.path.exists(_path('app_config.json')):
        write_json('app_config.json', DEFAULT_APP_CONFIG)
        print("✅ 已创建默认 app_config.json")

    if not os.path.exists(_path('datasources.json')):
        write_json('datasources.json', DEFAULT_DATASOURCES)
        print("✅ 已创建默认 datasources.json（含 SQLite 示例）")

    if not os.path.exists(_path('ai_settings.json')):
        write_json('ai_settings.json', DEFAULT_AI_SETTINGS)
        print("✅ 已创建默认 ai_settings.json（含阿里通义示例）")

    if not os.path.exists(_path('query_history.json')):
        write_json('query_history.json', DEFAULT_QUERY_HISTORY)
        print("✅ 已创建默认 query_history.json")


# ─────────────────────────────────────────────────────────
# 数据源配置 CRUD
# ─────────────────────────────────────────────────────────
def get_datasources() -> list:
    """获取所有数据源（密码解码后返回，仅后端内部使用）"""
    data = read_json('datasources.json')
    return data.get('databases', [])


def get_datasources_safe() -> list:
    """获取所有数据源（密码脱敏，供前端展示）"""
    dbs = get_datasources()
    result = []
    for db in dbs:
        safe_db = dict(db)
        if safe_db.get('password_b64'):
            safe_db['password'] = '***'
        else:
            safe_db['password'] = ''
        safe_db.pop('password_b64', None)
        result.append(safe_db)
    return result


def get_datasource_by_id(db_id: int) -> Optional[Dict]:
    """根据 ID 获取数据源（含解码密码）"""
    for db in get_datasources():
        if db['id'] == db_id:
            db_copy = dict(db)
            db_copy['password'] = decode_secret(db_copy.pop('password_b64', ''))
            return db_copy
    return None


def save_datasource(data: dict) -> dict:
    """新增数据源"""
    config = read_json('datasources.json')
    databases = config.get('databases', [])
    next_id = config.get('next_id', len(databases) + 1)

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_db = {
        "id": next_id,
        "name": data.get('name', ''),
        "type": data.get('type', 'sqlite'),
        "sqlite_path": data.get('sqlite_path', ''),
        "host": data.get('host', ''),
        "port": int(data.get('port', 0) or 0),
        "database_name": data.get('database_name', ''),
        "username": data.get('username', ''),
        "password_b64": encode_secret(data.get('password', '')),
        "driver": data.get('driver', ''),
        "is_active": data.get('is_active', True),
        "is_default": data.get('is_default', False),
        "created_at": now,
        "updated_at": now
    }

    # 如果设为默认，取消其他默认
    if new_db['is_default']:
        for db in databases:
            db['is_default'] = False

    databases.append(new_db)
    config['databases'] = databases
    config['next_id'] = next_id + 1
    write_json('datasources.json', config)
    return new_db


def update_datasource(db_id: int, data: dict) -> Optional[Dict]:
    """更新数据源"""
    config = read_json('datasources.json')
    databases = config.get('databases', [])

    for i, db in enumerate(databases):
        if db['id'] == db_id:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # 如果设为默认，取消其他默认
            if data.get('is_default'):
                for other in databases:
                    other['is_default'] = False

            databases[i].update({
                "name": data.get('name', db['name']),
                "type": data.get('type', db['type']),
                "sqlite_path": data.get('sqlite_path', db.get('sqlite_path', '')),
                "host": data.get('host', db['host']),
                "port": int(data.get('port', db['port']) or 0),
                "database_name": data.get('database_name', db['database_name']),
                "username": data.get('username', db['username']),
                "driver": data.get('driver', db.get('driver', '')),
                "is_active": data.get('is_active', db['is_active']),
                "is_default": data.get('is_default', db['is_default']),
                "updated_at": now
            })
            # 密码：只有传了非空密码才更新
            if data.get('password'):
                databases[i]['password_b64'] = encode_secret(data['password'])

            config['databases'] = databases
            write_json('datasources.json', config)
            return databases[i]
    return None


def delete_datasource(db_id: int) -> bool:
    """删除数据源"""
    config = read_json('datasources.json')
    databases = config.get('databases', [])
    new_dbs = [db for db in databases if db['id'] != db_id]
    if len(new_dbs) == len(databases):
        return False
    config['databases'] = new_dbs
    write_json('datasources.json', config)
    return True


def get_default_datasource() -> Optional[Dict]:
    """获取默认数据源（含解码密码）"""
    for db in get_datasources():
        if db.get('is_default'):
            db_copy = dict(db)
            db_copy['password'] = decode_secret(db_copy.pop('password_b64', ''))
            return db_copy
    # 没有设默认，返回第一个活跃的
    for db in get_datasources():
        if db.get('is_active'):
            db_copy = dict(db)
            db_copy['password'] = decode_secret(db_copy.pop('password_b64', ''))
            return db_copy
    return None


# ─────────────────────────────────────────────────────────
# AI 模型配置 CRUD
# ─────────────────────────────────────────────────────────
def get_ai_models() -> list:
    data = read_json('ai_settings.json')
    return data.get('models', [])


def get_ai_models_safe() -> list:
    """获取所有 AI 模型（API Key 脱敏）"""
    models = get_ai_models()
    result = []
    for m in models:
        safe_m = dict(m)
        if safe_m.get('api_key_b64'):
            safe_m['api_key'] = '***已保存***'
        else:
            safe_m['api_key'] = ''
        safe_m.pop('api_key_b64', None)
        result.append(safe_m)
    return result


def get_ai_model_by_id(model_id: int) -> Optional[Dict]:
    for m in get_ai_models():
        if m['id'] == model_id:
            m_copy = dict(m)
            m_copy['api_key'] = decode_secret(m_copy.pop('api_key_b64', ''))
            return m_copy
    return None


def save_ai_model(data: dict) -> dict:
    config = read_json('ai_settings.json')
    models = config.get('models', [])
    next_id = config.get('next_id', len(models) + 1)

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_model = {
        "id": next_id,
        "name": data.get('name', ''),
        "provider": data.get('provider', 'custom'),
        "model": data.get('model', ''),
        "base_url": data.get('base_url', ''),
        "api_key_b64": encode_secret(data.get('api_key', '')),
        "is_active": data.get('is_active', True),
        "is_default": data.get('is_default', False),
        "created_at": now,
        "updated_at": now
    }

    if new_model['is_default']:
        for m in models:
            m['is_default'] = False

    models.append(new_model)
    config['models'] = models
    config['next_id'] = next_id + 1
    write_json('ai_settings.json', config)
    return new_model


def update_ai_model(model_id: int, data: dict) -> Optional[Dict]:
    config = read_json('ai_settings.json')
    models = config.get('models', [])

    for i, m in enumerate(models):
        if m['id'] == model_id:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if data.get('is_default'):
                for other in models:
                    other['is_default'] = False

            models[i].update({
                "name": data.get('name', m['name']),
                "provider": data.get('provider', m['provider']),
                "model": data.get('model', m['model']),
                "base_url": data.get('base_url', m['base_url']),
                "is_active": data.get('is_active', m['is_active']),
                "is_default": data.get('is_default', m['is_default']),
                "updated_at": now
            })
            if data.get('api_key') and data['api_key'] != '***已保存***':
                models[i]['api_key_b64'] = encode_secret(data['api_key'])

            config['models'] = models
            write_json('ai_settings.json', config)
            return models[i]
    return None


def delete_ai_model(model_id: int) -> bool:
    config = read_json('ai_settings.json')
    models = config.get('models', [])
    new_models = [m for m in models if m['id'] != model_id]
    if len(new_models) == len(models):
        return False
    config['models'] = new_models
    write_json('ai_settings.json', config)
    return True


def get_default_ai_model() -> Optional[Dict]:
    """获取默认 AI 模型（含解码 Key）"""
    for m in get_ai_models():
        if m.get('is_default') and m.get('is_active'):
            m_copy = dict(m)
            m_copy['api_key'] = decode_secret(m_copy.pop('api_key_b64', ''))
            return m_copy
    # 没有默认，取第一个活跃的
    for m in get_ai_models():
        if m.get('is_active'):
            m_copy = dict(m)
            m_copy['api_key'] = decode_secret(m_copy.pop('api_key_b64', ''))
            return m_copy
    return None


# ─────────────────────────────────────────────────────────
# 问答历史
# ─────────────────────────────────────────────────────────
def add_query_history(question: str, sql: str, status: str = 'success', error: str = ''):
    """记录一次问答历史"""
    config = read_json('query_history.json')
    history = config.get('history', [])
    total = config.get('total_queries', 0)

    history.insert(0, {
        "id": total + 1,
        "question": question,
        "sql": sql,
        "status": status,
        "error": error,
        "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

    # 最多保留 200 条
    history = history[:200]
    config['history'] = history
    config['total_queries'] = total + 1
    write_json('query_history.json', config)


def get_query_history(limit: int = 5) -> list:
    config = read_json('query_history.json')
    return config.get('history', [])[:limit]


def get_query_stats() -> dict:
    config = read_json('query_history.json')
    history = config.get('history', [])
    today = datetime.now().strftime('%Y-%m-%d')
    today_count = sum(1 for h in history if h.get('created_at', '').startswith(today))
    return {
        "total_queries": config.get('total_queries', 0),
        "today_queries": today_count
    }
