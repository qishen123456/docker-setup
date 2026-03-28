#!/usr/bin/env python3
import requests
import json

print("🧪 测试修复后的分析报告生成功能")

# 测试数据
test_data = {
    "query_data": {
        "question": "今年商用事业部业绩分析",
        "sql": "SELECT * FROM test_data",
        "rows": [
            {"track": "区域条线", "level": "分公司", "name": "北京分公司", "total_task": 1000000, "annual_sales": 850000, "completion_rate": 85.0},
            {"track": "区域条线", "level": "分公司", "name": "上海分公司", "total_task": 1200000, "annual_sales": 960000, "completion_rate": 80.0}
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
        result = response.json()
        print("✅ 分析报告生成成功!")
        print(f"数据行数: {result['data_summary']['row_count']}")
        print(f"数据列: {result['data_summary']['columns']}")
        print(f"\n分析报告预览:\n{result['analysis'][:200]}...")
    else:
        print(f"❌ 生成失败: {response.status_code}")
        print(f"错误信息: {response.text}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*60)
print("🎯 现在分析报告生成功能应该正常工作了!")
print("1. 前端点击'生成分析报告'按钮")
print("2. 使用默认提示词进行分析")
print("3. 生成专业的分析报告")
print("="*60)
