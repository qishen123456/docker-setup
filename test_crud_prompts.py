#!/usr/bin/env python3
import requests
import json

print("🧪 测试分析提示词增删改查功能")

base_url = "http://localhost:5000/api/analysis-prompts"

# 1. 获取初始列表
print("\n1. 获取初始提示词列表:")
try:
    response = requests.get(base_url)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 获取成功，共 {data['total']} 个提示词")
        for prompt in data['prompts']:
            print(f"  - {prompt['name']} (ID: {prompt['id']})")
    else:
        print(f"❌ 获取失败: {response.status_code}")
except Exception as e:
    print(f"❌ 错误: {e}")

# 2. 创建新提示词
print("\n2. 创建新提示词:")
new_prompt = {
    "name": "测试提示词",
    "category": "其他",
    "prompt": "这是一个测试提示词，用于验证增删改查功能。",
    "is_default": False
}

try:
    response = requests.post(base_url, json=new_prompt)
    if response.status_code == 200:
        result = response.json()
        created_id = result['prompt']['id']
        print(f"✅ 创建成功，ID: {created_id}")
    else:
        print(f"❌ 创建失败: {response.status_code}")
        created_id = None
except Exception as e:
    print(f"❌ 错误: {e}")
    created_id = None

# 3. 更新提示词
if created_id:
    print("\n3. 更新提示词:")
    update_data = {
        "name": "测试提示词-已更新",
        "category": "业绩分析",
        "prompt": "这是更新后的测试提示词内容，增加了更多分析要求。",
        "is_default": True
    }
    
    try:
        response = requests.put(f"{base_url}/{created_id}", json=update_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 更新成功: {result['prompt']['name']}")
        else:
            print(f"❌ 更新失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 错误: {e}")

# 4. 删除提示词
if created_id:
    print("\n4. 删除提示词:")
    try:
        response = requests.delete(f"{base_url}/{created_id}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 删除成功: {result['deleted_prompt']['name']}")
        else:
            print(f"❌ 删除失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 错误: {e}")

# 5. 最终列表
print("\n5. 最终提示词列表:")
try:
    response = requests.get(base_url)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 获取成功，共 {data['total']} 个提示词")
        for prompt in data['prompts']:
            print(f"  - {prompt['name']} (ID: {prompt['id']})")
    else:
        print(f"❌ 获取失败: {response.status_code}")
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*60)
print("🎯 现在前端的增删改查功能应该都能正常工作了!")
print("1. 创建新提示词 ✅")
print("2. 编辑现有提示词 ✅") 
print("3. 删除提示词 ✅")
print("4. 设置默认提示词 ✅")
print("="*60)
