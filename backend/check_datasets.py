#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import psycopg2
import base64
import json
import os

print("🧪 检查数据集表和数据")

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
print(f"🔗 主机: {default_ds['host']}:{default_ds['port']}")
print(f"💾 数据库: {default_ds['database_name']}")

# 解码密码
password = base64.b64decode(default_ds['password_b64']).decode('utf-8')
print(f"👤 用户: {default_ds['username']}")

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
    
    # 检查bs_datasets表是否存在
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'bs_datasets';
    """)
    table_exists = cursor.fetchone()
    
    if table_exists:
        print("✅ bs_datasets表存在")
        
        # 查询数据集数量
        cursor.execute("SELECT COUNT(*) FROM bs_datasets;")
        count = cursor.fetchone()[0]
        print(f"📈 数据集总数: {count}")
        
        if count > 0:
            # 显示数据集列表
            cursor.execute("""
                SELECT id, dataset_code, dataset_name, business_domain, is_active 
                FROM bs_datasets ORDER BY id;
            """)
            datasets = cursor.fetchall()
            print("\n📋 数据集列表:")
            for ds in datasets:
                status = "✅" if ds[4] else "❌"
                print(f"  {status} [{ds[0]}] {ds[1]} - {ds[2]} ({ds[3]})")
        else:
            print("⚠️  bs_datasets表为空，需要创建数据集")
    else:
        print("❌ bs_datasets表不存在")
        print("🔧 需要运行数据库迁移脚本创建表结构")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
