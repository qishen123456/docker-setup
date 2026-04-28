#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import psycopg2
import base64
import json
import os

print("🧪 创建 angel_group_data 表")

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
    
    # 检查表是否已存在
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'angel_group_data';
    """)
    table_exists = cursor.fetchone()
    
    if table_exists:
        print("⚠️  angel_group_data 表已存在，跳过创建")
    else:
        # 创建表
        create_sql = """
        CREATE TABLE angel_group_data (
            id BIGSERIAL PRIMARY KEY,
            fields JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        
        CREATE INDEX idx_angel_group_data_fields ON angel_group_data USING GIN (fields);
        """
        cursor.execute(create_sql)
        conn.commit()
        print("✅ angel_group_data 表创建成功")
    
    # 插入一些示例数据（用于测试）
    cursor.execute("SELECT COUNT(*) FROM angel_group_data;")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("📝 插入示例数据...")
        sample_data = [
            {
                "fields": {
                    "事业部": "商用事业部",
                    "分公司": "东部分公司",
                    "代表处": "上海代表处",
                    "业务代表": "",
                    "当前年": "2026",
                    "总任务（金额）": "1000000",
                    "年度开单金额": "850000"
                }
            },
            {
                "fields": {
                    "事业部": "商用事业部",
                    "分公司": "西部分公司",
                    "代表处": "成都代表处",
                    "业务代表": "",
                    "当前年": "2026",
                    "总任务（金额）": "800000",
                    "年度开单金额": "600000"
                }
            },
            {
                "fields": {
                    "事业部": "商用事业部",
                    "分公司": "商用业务部",
                    "代表处": "",
                    "业务代表": "张三",
                    "当前年": "2026",
                    "总任务（金额）": "500000",
                    "年度开单金额": "450000"
                }
            }
        ]
        
        for data in sample_data:
            cursor.execute(
                "INSERT INTO angel_group_data (fields) VALUES (%s::jsonb)",
                (json.dumps(data["fields"], ensure_ascii=False),)
            )
        
        conn.commit()
        print(f"✅ 插入了 {len(sample_data)} 条示例数据")
    
    # 验证表和数据
    cursor.execute("SELECT COUNT(*) FROM angel_group_data;")
    total_count = cursor.fetchone()[0]
    print(f"📈 angel_group_data 表当前记录数: {total_count}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
