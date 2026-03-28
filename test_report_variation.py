#!/usr/bin/env python3
import requests
import json

print("🧪 测试报告内容是否每次都一样")

# 测试数据
test_data = {
    "query_data": {
        "question": "今年商用事业部业绩分析",
        "sql": "SELECT * FROM performance_data",
        "rows": [
            {"department": "销售部", "target": 1000000, "actual": 850000, "rate": 85.0},
            {"department": "技术部", "target": 800000, "actual": 920000, "rate": 115.0},
            {"department": "市场部", "target": 600000, "actual": 540000, "rate": 90.0}
        ],
        "columns": ["department", "target", "actual", "rate"]
    }
}

reports = []

print("🔄 连续生成3次报告，检查内容是否相同...")

for i in range(3):
    print(f"\n📊 第{i+1}次生成报告...")
    
    try:
        response = requests.post(
            'http://localhost:5000/api/analysis-prompts/generate',
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            analysis = result.get('analysis', '')
            reports.append(analysis)
            print(f"✅ 第{i+1}次成功，报告长度: {len(analysis)} 字符")
            
            # 显示前200字符
            print(f"📋 前200字符: {analysis[:200]}...")
            
        else:
            print(f"❌ 第{i+1}次失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 第{i+1}次错误: {e}")

# 比较报告内容
print("\n" + "="*60)
print("🔍 报告内容对比分析:")

if len(reports) >= 2:
    # 检查是否完全相同
    all_same = all(report == reports[0] for report in reports)
    
    if all_same:
        print("❌ 所有报告内容完全相同！可能存在问题")
        print("\n📋 报告内容:")
        print("="*40)
        print(reports[0])
        print("="*40)
    else:
        print("✅ 报告内容不同，AI生成正常")
        
        # 显示差异
        for i in range(len(reports)):
            print(f"\n📊 第{i+1}次报告长度: {len(reports[i])} 字符")
            
        # 检查开头和结尾是否相同
        start_same = all(report[:100] == reports[0][:100] for report in reports)
        end_same = all(report[-100:] == reports[0][-100:] for report in reports)
        
        if start_same:
            print("⚠️ 报告开头部分相同")
        if end_same:
            print("⚠️ 报告结尾部分相同")
        if not start_same and not end_same:
            print("✅ 报告开头和结尾都不同")

else:
    print("⚠️ 生成的报告数量不足，无法对比")

print("\n" + "="*60)
print("🎯 可能的原因:")
print("1. AI模型温度设置过低，导致输出过于固定")
print("2. 提示词过于具体，限制了AI的创造性")
print("3. 缓存机制导致返回相同结果")
print("4. 数据过于简单，AI只能生成类似的分析")
print("="*60)
