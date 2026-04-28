#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import psycopg2
import base64
import json
import os

print("🧪 删除 angel_group_data 表")

# 从配置文件读取数据源配置
config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'datasources.json')
with open(config_path, 'r', encoding='utf-8-sig') as f:
    config = json.load(f)

# 找到默认的PostgreSQL数据源
default_ds = None
for ds in config['databases']:
    if ds.get('is_default') and ds.get('type') == 'postgresql':
        default_ds = ds
        break

if not default_ds:
    print("❌ 未找到默认的PostgreSQL数据源")
    exit(1)

print(f"📊 数据源: {default_ds['name']}")
print(f"💾 数据库: {default_ds['database_name']}")

# 解码密码
password = base64.b64decode(default_ds['password_b64']).decode('utf-8')

try:
    conn = psycopg2.connect(
        host=default_ds['host'],
        port=default_ds['port'],
        database=default_ds['database_name'],
        user=default_ds['username'],
        password=password
    )
    cursor = conn.cursor()
    
    print("✅ 数据库连接成功")
    
    # 删除表
    cursor.execute("DROP TABLE IF EXISTS angel_group_data;")
    conn.commit()
    print("✅ angel_group_data 表已删除")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
