#!/usr/bin/env python3
import requests
import json
import time

print("🧪 测试修复后的分析报告生成功能")

# 测试数据
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

print("📊 测试数据准备完成")
print(f"数据行数: {len(test_data['query_data']['rows'])}")
print(f"数据列数: {len(test_data['query_data']['columns'])}")

print("\n🚀 开始测试分析报告生成...")
start_time = time.time()

try:
    response = requests.post(
        'http://localhost:5000/api/analysis-prompts/generate',
        json=test_data,
        headers={'Content-Type': 'application/json'},
        timeout=60  # 60秒超时
    )
    
    elapsed_time = time.time() - start_time
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 分析报告生成成功!")
        print(f"⏱️  耗时: {elapsed_time:.2f} 秒")
        print(f"📄 报告长度: {len(result['analysis'])} 字符")
        print(f"📊 数据行数: {result['data_summary']['row_count']}")
        
        print(f"\n📋 分析报告预览:")
        print("="*60)
        print(result['analysis'][:500] + "..." if len(result['analysis']) > 500 else result['analysis'])
        print("="*60)
        
    else:
        print(f"❌ 生成失败: {response.status_code}")
        print(f"错误信息: {response.text}")
        print(f"⏱️  耗时: {elapsed_time:.2f} 秒")
        
except requests.exceptions.Timeout:
    print(f"❌ 请求超时 (60秒)")
    print(f"⏱️  耗时: {time.time() - start_time:.2f} 秒")
except Exception as e:
    print(f"❌ 错误: {e}")
    print(f"⏱️  耗时: {time.time() - start_time:.2f} 秒")

print("\n" + "="*60)
print("🎯 修复内容:")
print("1. ✅ 修复了submit_prompt调用方式")
print("2. ✅ 添加了调试信息输出")
print("3. ✅ 优化了大数据集性能（限制100行样本）")
print("4. ✅ 增加了超时处理")
print("="*60)
