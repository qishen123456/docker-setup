"""
飞书同步服务启动脚本
"""

import sys
import os

# 确保 backend 目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from feishu_sync_service import start_feishu_sync

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 飞书同步服务启动")
    print("=" * 50)
    print("📡 同步服务: 飞书多维表格 -> PostgreSQL")
    print("📋 功能: 定时同步、增量同步、全量同步")
    print("=" * 50)
    
    try:
        start_feishu_sync()
    except KeyboardInterrupt:
        print("\n飞书同步服务已停止")
    except Exception as e:
        print(f"飞书同步服务异常: {e}")
