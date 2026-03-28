#!/usr/bin/env python3
import requests
import base64

print("🧪 测试阿里通义千问API连接")

# 从配置文件获取API信息
api_key_b64 = "c2stNzY1ODVhODcxMWY4NGQ0NWE2MGI5ZGMzNjQ5NzIxM2U="
api_key = base64.b64decode(api_key_b64).decode()
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
model = "qwen-max"

print(f"🔑 API Key: {api_key[:10]}...")
print(f"🌐 Base URL: {base_url}")
print(f"🤖 Model: {model}")

# 测试API连接
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

data = {
    "model": model,
    "messages": [
        {"role": "user", "content": "请回复数字1"}
    ],
    "max_tokens": 10
}

print(f"\n📡 发送测试请求...")

try:
    response = requests.post(
        f"{base_url}/chat/completions",
        headers=headers,
        json=data,
        timeout=10
    )
    
    print(f"📊 响应状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content']
        print(f"✅ API连接成功!")
        print(f"📝 响应内容: {content}")
    else:
        print(f"❌ API连接失败: {response.status_code}")
        print(f"📄 错误信息: {response.text}")
        
except requests.exceptions.Timeout:
    print("❌ 请求超时")
except Exception as e:
    print(f"❌ 连接错误: {str(e)}")

print("\n" + "="*50)
