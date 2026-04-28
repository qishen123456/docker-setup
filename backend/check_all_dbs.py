#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import psycopg2
import base64
import json
import os

print("🧪 检查所有PostgreSQL数据源中的表")

# 从配置文件读取数据源配置
config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'datasources.json')
with open(config_path, 'r', encoding='utf-8-sig') as f:
    config = json.load(f)

# 检查所有PostgreSQL数据源
for ds in config['databases']:
    if ds.get('type') == 'postgresql':
        print(f"\n{'='*60}")
        print(f"📊 数据源: {ds['name']} (ID: {ds['id']})")
        print(f"💾 数据库: {ds['database_name']}")
        print(f"🔗 主机: {ds['host']}:{ds['port']}")
        
        # 解码密码
        password = base64.b64decode(ds['password_b64']).decode('utf-8')
        
        try:
            conn = psycopg2.connect(
                host=ds['host'],
                port=ds['port'],
                database=ds['database_name'],
                user=ds['username'],
                password=password
            )
            cursor = conn.cursor()
            
            print("✅ 数据库连接成功")
            
            # 查询所有表
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            
            print(f"📋 数据库中的表 (共{len(tables)}个):")
            for table in tables:
                table_name = table[0]
                # 查询表记录数
                cursor.execute(f"SELECT COUNT(*) FROM \"{table_name}\";")
                count = cursor.fetchone()[0]
                marker = " 🔥" if table_name == "angel_group_data" else ""
                print(f"  - {table_name}: {count} 条记录{marker}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"❌ 错误: {e}")

print(f"\n{'='*60}")
