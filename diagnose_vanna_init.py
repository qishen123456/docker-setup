#!/usr/bin/env python3

import sys
import os

# 添加backend目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

print("🔍 诊断Vanna初始化问题")
print("="*50)

try:
    from config_manager import get_default_ai_model, get_default_datasource
    
    print("1. 检查AI模型配置...")
    ai_model = get_default_ai_model()
    if ai_model:
        print(f"✅ 找到默认AI模型: {ai_model['name']}")
        print(f"   模型: {ai_model['model']}")
        print(f"   Base URL: {ai_model['base_url']}")
        print(f"   API Key: {'已设置' if ai_model['api_key'] else '未设置'}")
    else:
        print("❌ 未找到默认AI模型")
        print("   请检查AI模型配置")
    
    print()
    print("2. 检查数据源配置...")
    db_config = get_default_datasource()
    if db_config:
        print(f"✅ 找到默认数据源: {db_config['name']}")
        print(f"   类型: {db_config['type']}")
        print(f"   主机: {db_config['host']}:{db_config['port']}")
        print(f"   数据库: {db_config['database_name']}")
        print(f"   用户名: {db_config['username']}")
        print(f"   密码: {'已设置' if db_config['password'] else '未设置'}")
    else:
        print("❌ 未找到默认数据源")
        print("   请检查数据源配置")
    
    print()
    print("3. 测试Vanna初始化...")
    
    if ai_model and db_config:
        try:
            from vanna_core import get_vanna_instance
            vn, error = get_vanna_instance()
            
            if vn:
                print("✅ Vanna初始化成功")
                print("   实例已创建，可以正常使用")
            else:
                print(f"❌ Vanna初始化失败: {error}")
                print("   这是导致400错误的原因")
                
        except Exception as e:
            print(f"❌ Vanna初始化异常: {str(e)}")
            print("   请检查依赖包是否正确安装")
    else:
        print("❌ 配置不完整，跳过Vanna初始化测试")
    
    print()
    print("4. 测试数据库连接...")
    
    if db_config:
        try:
            if db_config['type'] == 'postgresql':
                import psycopg2
                conn = psycopg2.connect(
                    host=db_config['host'],
                    port=int(db_config['port']),
                    user=db_config['username'],
                    password=db_config['password'],
                    database=db_config['database_name'],
                    connect_timeout=5
                )
                conn.close()
                print("✅ PostgreSQL连接成功")
            elif db_config['type'] == 'sqlite':
                import sqlite3
                sqlite_path = db_config.get('sqlite_path', ':memory:')
                if not os.path.isabs(sqlite_path):
                    sqlite_path = os.path.join(os.path.dirname(__file__), sqlite_path)
                conn = sqlite3.connect(sqlite_path)
                conn.close()
                print("✅ SQLite连接成功")
            else:
                print(f"⚠️ 未测试的数据库类型: {db_config['type']}")
                
        except ImportError as e:
            print(f"❌ 缺少数据库驱动: {str(e)}")
        except Exception as e:
            print(f"❌ 数据库连接失败: {str(e)}")
            print("   这可能是Vanna初始化失败的原因")

except Exception as e:
    print(f"❌ 配置加载失败: {str(e)}")
    print("   请检查config目录和文件权限")

print()
print("="*50)
print("🎯 请将以上输出结果发给我，我会根据具体问题提供解决方案！")
