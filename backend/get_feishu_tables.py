#!/usr/bin/env python3
import requests
import json

print("🧪 获取飞书表格列表")

app_id = "cli_a94aae39fe38dcc7"
app_secret = "DegvsVgTJZkI4sSvBzTtJbZJoz0vS6Um"
base_id = "MRxHbj3LpaOJwRsSF4lcvzBinqg"

try:
    # 获取访问令牌
    payload = {"app_id": app_id, "app_secret": app_secret}
    headers = {'Content-Type': 'application/json'}
    
    response = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        headers=headers, json=payload, timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get("code") == 0:
            token = data["tenant_access_token"]
            headers['Authorization'] = f'Bearer {token}'
            
            # 获取表格列表
            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_id}/tables"
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    tables = data.get("data", {}).get("items", [])
                    print(f"✅ 找到 {len(tables)} 个表格:")
                    
                    for i, table in enumerate(tables):
                        print(f"\n表格 {i+1}:")
                        print(f"  ID: {table.get('table_id')}")
                        print(f"  名称: {table.get('name')}")
                        
                else:
                    print(f"❌ 获取表格失败: {data.get('msg')}")
            else:
                print(f"❌ HTTP错误: {response.status_code}")
        else:
            print(f"❌ 获取令牌失败: {data.get('msg')}")
    else:
        print(f"❌ HTTP错误: {response.status_code}")
        
except Exception as e:
    print(f"❌ 错误: {e}")
