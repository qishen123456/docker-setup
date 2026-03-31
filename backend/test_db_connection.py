#!/usr/bin/env python3
import psycopg2
import json

print("🧪 测试PostgreSQL数据库连接")

# 数据库配置
db_config = {
    'host': 'localhost',
    'port': 5432,
    'database_name': 'postgres',
    'username': 'postgres',
    'password_b64': 'MTIzNDU2'
}

import base64
password = base64.b64decode(db_config['password_b64']).decode('utf-8')

try:
    print(f"🔗 连接数据库: {db_config['host']}:{db_config['port']}/{db_config['database_name']}")
    print(f"👤 用户: {db_config['username']}")
    
    conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        database=db_config['database_name'],
        user=db_config['username'],
        password=password
    )
    
    cursor = conn.cursor()
    
    # 测试查询
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"✅ 数据库连接成功!")
    print(f"📊 PostgreSQL版本: {version[0]}")
    
    # 检查目标表是否存在
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'angel_group_data';
    """)
    
    table_exists = cursor.fetchone()
    if table_exists:
        print(f"✅ 目标表 'angel_group_data' 已存在")
        
        # 查看表结构
        cursor.execute("""
            SELECT column_name, data_type FROM information_schema.columns 
            WHERE table_name = 'angel_group_data' ORDER BY ordinal_position;
        """)
        columns = cursor.fetchall()
        print(f"📋 表结构:")
        for col in columns:
            print(f"  - {col[0]}: {col[1]}")
            
        # 查看记录数
        cursor.execute("SELECT COUNT(*) FROM angel_group_data;")
        count = cursor.fetchone()
        print(f"📈 当前记录数: {count[0]}")
        
    else:
        print(f"❌ 目标表 'angel_group_data' 不存在")
        print("🔧 需要先创建表结构")
    
    cursor.close()
    conn.close()
    
except psycopg2.OperationalError as e:
    print(f"❌ 数据库连接失败: {e}")
    print("💡 可能的原因:")
    print("   1. PostgreSQL服务未启动")
    print("   2. 端口5432被占用")
    print("   3. 用户名或密码错误")
    print("   4. 数据库不存在")
    
except Exception as e:
    print(f"❌ 其他错误: {e}")

print("\n" + "="*50)
