#!/usr/bin/env python3
import requests
import json

# 测试分析提示词获取
print("🧪 测试分析提示词获取")
try:
    response = requests.get('http://localhost:5000/api/analysis-prompts')
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 获取成功，共 {data['total']} 个提示词")
        for prompt in data['prompts']:
            print(f"  - {prompt['name']} ({prompt['category']})")
    else:
        print(f"❌ 获取失败: {response.status_code}")
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*50)

# 测试分析报告生成（使用模拟数据）
print("🧪 测试分析报告生成")
test_data = {
    "query_data": {
        "question": "今年商用事业部业绩分析",
        "sql": "SELECT * FROM test_data",
        "rows": [
            {"track": "区域条线", "level": "分公司", "name": "北京分公司", "total_task": 1000000, "annual_sales": 850000, "completion_rate": 85.0},
            {"track": "区域条线", "level": "分公司", "name": "上海分公司", "total_task": 1200000, "annual_sales": 960000, "completion_rate": 80.0},
            {"track": "行业条线", "level": "业务部", "name": "金融业务部", "total_task": 800000, "annual_sales": 720000, "completion_rate": 90.0}
        ],
        "columns": ["track", "level", "name", "total_task", "annual_sales", "completion_rate"]
    }
}

try:
    response = requests.post(
        'http://localhost:5000/api/analysis-prompts/generate',
        json=test_data,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ 分析报告生成成功!")
        print(f"数据行数: {data['data_summary']['row_count']}")
        print(f"数据列: {data['data_summary']['columns']}")
        print(f"\n分析报告预览:\n{data['analysis'][:300]}...")
    else:
        print(f"❌ 生成失败: {response.status_code}")
        print(f"错误信息: {response.text}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*50)
