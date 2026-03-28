#!/usr/bin/env python3
"""
数据源恢复工具
检查并恢复可能丢失的数据源配置
"""

import os
import json
from datetime import datetime

def backup_current_config():
    """备份当前配置"""
    config_dir = "config"
    backup_dir = "config/backup"
    
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 备份所有配置文件
    for filename in ["datasources.json", "ai_settings.json", "app_config.json"]:
        src = os.path.join(config_dir, filename)
        if os.path.exists(src):
            dst = os.path.join(backup_dir, f"{filename}.{timestamp}.bak")
            with open(src, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(dst, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 备份完成: {filename} -> {dst}")

def check_datasource_integrity():
    """检查数据源配置完整性"""
    config_file = "config/datasources.json"
    
    if not os.path.exists(config_file):
        print("❌ 数据源配置文件不存在")
        return False
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        databases = config.get('databases', [])
        next_id = config.get('next_id', 1)
        
        print(f"📊 当前数据源数量: {len(databases)}")
        print(f"📝 下一个ID: {next_id}")
        
        for i, db in enumerate(databases):
            print(f"  {i+1}. {db['name']} ({db['type']}) - ID: {db['id']}")
        
        # 检查ID连续性
        ids = [db['id'] for db in databases]
        if ids != sorted(range(1, len(databases) + 1)):
            print("⚠️  警告: 数据源ID不连续，可能存在数据丢失")
            return False
        
        print("✅ 数据源配置完整性检查通过")
        return True
        
    except Exception as e:
        print(f"❌ 检查数据源配置时出错: {e}")
        return False

if __name__ == "__main__":
    print("🔍 开始检查数据源配置...")
    
    # 先备份当前配置
    backup_current_config()
    
    # 检查完整性
    check_datasource_integrity()
    
    print("\n📋 检查完成。如果发现数据丢失，请检查:")
    print("1. 是否有浏览器缓存问题")
    print("2. 是否有并发写入冲突")
    print("3. 查看浏览器开发者工具的网络请求记录")
