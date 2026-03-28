"""
飞书同步日志管理
"""

import json
import os
from datetime import datetime
from typing import List, Dict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, 'logs')

# 确保日志目录存在
os.makedirs(LOG_DIR, exist_ok=True)

def get_log_file_path(config_id: int) -> str:
    """获取指定配置的日志文件路径"""
    return os.path.join(LOG_DIR, f'feishu_sync_{config_id}.log')

def write_log(config_id: int, level: str, message: str, extra_data: Dict = None):
    """写入日志"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'level': level,
        'message': message,
        'config_id': config_id
    }
    
    if extra_data:
        log_entry.update(extra_data)
    
    # 写入到文件
    log_file = get_log_file_path(config_id)
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"写入日志失败: {e}")
    
    # 同时输出到控制台
    print(f"[{log_entry['timestamp']}] [{level}] Config-{config_id}: {message}")

def get_logs(config_id: int, limit: int = 100) -> List[Dict]:
    """获取指定配置的日志"""
    log_file = get_log_file_path(config_id)
    
    if not os.path.exists(log_file):
        return []
    
    try:
        logs = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        log_entry = json.loads(line)
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        continue
        
        # 返回最新的日志（倒序）
        return logs[-limit:] if len(logs) > limit else logs
    except Exception as e:
        print(f"读取日志失败: {e}")
        return []

def get_all_logs(limit: int = 50) -> List[Dict]:
    """获取所有配置的日志"""
    all_logs = []
    
    try:
        # 遍历所有日志文件
        for filename in os.listdir(LOG_DIR):
            if filename.startswith('feishu_sync_') and filename.endswith('.log'):
                config_id = filename.replace('feishu_sync_', '').replace('.log', '')
                try:
                    config_id = int(config_id)
                    logs = get_logs(config_id, limit)
                    all_logs.extend(logs)
                except ValueError:
                    continue
        
        # 按时间排序（最新的在前）
        all_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return all_logs[:limit]
    except Exception as e:
        print(f"获取所有日志失败: {e}")
        return []

def clear_logs(config_id: int = None):
    """清空日志"""
    try:
        if config_id:
            # 清空指定配置的日志
            log_file = get_log_file_path(config_id)
            if os.path.exists(log_file):
                os.remove(log_file)
        else:
            # 清空所有日志
            for filename in os.listdir(LOG_DIR):
                if filename.startswith('feishu_sync_') and filename.endswith('.log'):
                    os.remove(os.path.join(LOG_DIR, filename))
    except Exception as e:
        print(f"清空日志失败: {e}")

def get_log_stats() -> Dict:
    """获取日志统计信息"""
    stats = {
        'total_configs': 0,
        'total_logs': 0,
        'error_count': 0,
        'success_count': 0,
        'latest_log': None
    }
    
    try:
        for filename in os.listdir(LOG_DIR):
            if filename.startswith('feishu_sync_') and filename.endswith('.log'):
                stats['total_configs'] += 1
                config_id = filename.replace('feishu_sync_', '').replace('.log', '')
                try:
                    config_id = int(config_id)
                    logs = get_logs(config_id)
                    stats['total_logs'] += len(logs)
                    
                    for log in logs:
                        level = log.get('level', '')
                        if level == 'ERROR':
                            stats['error_count'] += 1
                        elif level == 'SUCCESS':
                            stats['success_count'] += 1
                        
                        if not stats['latest_log'] or log.get('timestamp', '') > stats['latest_log']:
                            stats['latest_log'] = log.get('timestamp')
                except ValueError:
                    continue
    except Exception as e:
        print(f"获取日志统计失败: {e}")
    
    return stats
