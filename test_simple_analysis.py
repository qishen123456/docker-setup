#!/usr/bin/env python3
import requests
import json

print("🧪 简化测试分析报告生成")

# 最简单的测试数据
simple_test_data = {
    "query_data": {
        "question": "简单测试",
        "sql": "SELECT 1",
        "rows": [{"name": "测试", "value": 100}],
        "columns": ["name", "value"]
    }
}

print("📊 发送最简单的测试数据...")

try:
    response = requests.post(
        'http://localhost:5000/api/analysis-prompts/generate',
        json=simple_test_data,
        headers={'Content-Type': 'application/json'},
        timeout=10  # 10秒超时
    )
    
    print(f"📊 响应状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ 简单测试成功!")
        print(f"📄 报告长度: {len(result.get('analysis', ''))} 字符")
        if result.get('analysis'):
            print(f"📋 报告内容: {result['analysis'][:100]}...")
    else:
        print(f"❌ 响应错误: {response.text}")
        
except requests.exceptions.Timeout:
    print("❌ 10秒超时 - 可能是AI模型调用问题")
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*50)
print("🔍 如果超时，可能的原因:")
print("1. AI模型配置错误")
print("2. API密钥或URL问题")
print("3. submit_prompt方法仍有问题")
print("4. 网络连接问题")
print("="*50)
