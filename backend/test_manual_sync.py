#!/usr/bin/env python3
import requests
import json
import psycopg2
import base64

print("🧪 手动测试飞书数据同步")

# 配置
app_id = "cli_a94aae39fe38dcc7"
app_secret = "DegvsVgTJZkI4sSvBzTtJbZJoz0vS6Um"
base_id = "MRxHbj3LpaOJwRsSF4lcvzBinqg"
table_id = "tbl3hnhHgjX3zwwd"

# 数据库配置
db_config = {
    'host': 'localhost',
    'port': 5432,
    'database_name': 'postgres',
    'username': 'postgres',
    'password_b64': 'MTIzNDU2'
}

try:
    # 1. 获取飞书访问令牌
    print("\n🔑 获取飞书访问令牌...")
    payload = {"app_id": app_id, "app_secret": app_secret}
    headers = {'Content-Type': 'application/json'}
    
    response = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        headers=headers, json=payload, timeout=30
    )
    
    if response.status_code != 200 or response.json().get("code") != 0:
        print(f"❌ 获取令牌失败: {response.text}")
        exit(1)
    
    token = response.json()["tenant_access_token"]
    print(f"✅ 令牌获取成功")
    
    # 2. 获取飞书数据
    print(f"\n📊 获取飞书数据...")
    headers['Authorization'] = f'Bearer {token}'
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_id}/tables/{table_id}/records"
    params = {'page_size': 10}
    
    response = requests.get(url, headers=headers, params=params, timeout=30)
    
    if response.status_code != 200 or response.json().get("code") != 0:
        print(f"❌ 获取数据失败: {response.text}")
        exit(1)
    
    data = response.json()
    records = data.get("data", {}).get("items", [])
    print(f"✅ 获取到 {len(records)} 条记录")
    
    if not records:
        print("❌ 没有数据可同步")
        exit(0)
    
    print(f"📄 第一条记录示例: {json.dumps(records[0], indent=2, ensure_ascii=False)}")
    
    # 3. 连接数据库
    print(f"\n🔗 连接数据库...")
    password = base64.b64decode(db_config['password_b64']).decode('utf-8')
    
    conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        database=db_config['database_name'],
        user=db_config['username'],
        password=password
    )
    
    cursor = conn.cursor()
    print(f"✅ 数据库连接成功")
    
    # 4. 插入数据
    print(f"\n💾 插入数据到数据库...")
    
    from datetime import datetime
    sync_time = datetime.now()
    
    inserted_count = 0
    for record in records[:5]:  # 只插入前5条作为测试
        record_id = record.get('record_id', '')
        fields_json = json.dumps(record.get('fields', {}), ensure_ascii=False)
        
        cursor.execute(f"""
            INSERT INTO angel_group_data (record_id, fields, sync_time, created_time, updated_time)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (record_id) 
            DO UPDATE SET 
                fields = EXCLUDED.fields,
                sync_time = EXCLUDED.sync_time,
                updated_time = EXCLUDED.updated_time
        """, (record_id, fields_json, sync_time, sync_time, sync_time))
        
        inserted_count += 1
        print(f"  ✅ 插入记录: {record_id}")
    
    conn.commit()
    print(f"✅ 成功插入 {inserted_count} 条记录")
    
    # 5. 验证数据
    cursor.execute("SELECT COUNT(*) FROM angel_group_data")
    total_count = cursor.fetchone()[0]
    print(f"📈 数据库中总记录数: {total_count}")
    
    cursor.close()
    conn.close()
    
    print(f"\n🎉 手动同步测试完成!")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
