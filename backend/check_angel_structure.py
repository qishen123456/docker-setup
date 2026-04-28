#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import psycopg2
import base64
import json
import os

print("🧪 检查 angel_group_data 表结构")

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
    
    # 查询表结构
    cursor.execute("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'angel_group_data'
        ORDER BY ordinal_position;
    """)
    columns = cursor.fetchall()
    
    print(f"\n📋 angel_group_data 表结构:")
    for col in columns:
        print(f"  - {col[0]}: {col[1]} (nullable: {col[2]})")
    
    # 查看一条示例数据
    cursor.execute("SELECT * FROM angel_group_data LIMIT 1;")
    sample = cursor.fetchone()
    print(f"\n📝 示例数据 (字段数量: {len(sample)}):")
    print(f"  {sample}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
