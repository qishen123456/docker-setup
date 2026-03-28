#!/usr/bin/env python3
import requests
import json

print("🧪 测试分析报告生成（简化版）")

# 最简单的测试数据
simple_test_data = {
    "query_data": {
        "question": "测试",
        "sql": "SELECT 1",
        "rows": [{"name": "测试", "value": 100}],
        "columns": ["name", "value"]
    }
}

print("📊 发送测试数据...")

try:
    response = requests.post(
        'http://localhost:5000/api/analysis-prompts/generate',
        json=simple_test_data,
        headers={'Content-Type': 'application/json'},
        timeout=120  # 2分钟超时
    )
    
    print(f"📊 响应状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ 分析报告生成成功!")
        print(f"📄 报告长度: {len(result.get('analysis', ''))} 字符")
        if result.get('analysis'):
            print(f"📋 报告内容: {result['analysis']}")
    else:
        print(f"❌ 响应错误: {response.text}")
        
except requests.exceptions.Timeout:
    print("❌ 120秒超时 - AI模型响应太慢")
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*50)
