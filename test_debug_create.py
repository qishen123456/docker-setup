#!/usr/bin/env python3
import requests
import json

print("🧪 测试创建提示词（带调试信息）")

# 创建新提示词
new_prompt = {
    "name": "调试测试提示词",
    "category": "调试分类",
    "prompt": "这是一个用于调试的提示词。",
    "is_default": False
}

try:
    response = requests.post(
        "http://localhost:5000/api/analysis-prompts",
        json=new_prompt,
        headers={'Content-Type': 'application/json'}
    )
    print(f"📊 响应状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ 创建成功")
        print(f"📄 返回消息: {data.get('message', '')}")
    else:
        print(f"❌ 创建失败: {response.text}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n🔍 现在检查后端日志，应该能看到调试信息")
