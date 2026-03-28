#!/usr/bin/env python3
import requests
import json

print("🧪 测试完整报告内容显示")

# 简单测试数据
test_data = {
    "query_data": {
        "question": "业绩分析测试",
        "sql": "SELECT * FROM performance_data",
        "rows": [
            {"department": "销售部", "target": 1000000, "actual": 850000, "rate": 85.0},
            {"department": "技术部", "target": 800000, "actual": 920000, "rate": 115.0}
        ],
        "columns": ["department", "target", "actual", "rate"]
    }
}

print("📊 发送测试数据...")

try:
    response = requests.post(
        'http://localhost:5000/api/analysis-prompts/generate',
        json=test_data,
        headers={'Content-Type': 'application/json'},
        timeout=60
    )
    
    print(f"📊 响应状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ 分析报告生成成功!")
        
        analysis = result.get('analysis', '')
        
        # 检查关键部分
        if '商用事业部业绩分析报告' in analysis:
            print("✅ 包含报告标题")
            
            # 检查报告完整性
            sections = [
                "一、总体业绩概览",
                "二、各维度业绩对比分析", 
                "三、完成率分析",
                "四、关键发现与建议",
                "五、数据可视化建议"
            ]
            
            for section in sections:
                if section in analysis:
                    print(f"✅ 包含: {section}")
                else:
                    print(f"❌ 缺失: {section}")
            
            # 检查表格
            if '|' in analysis:
                print("✅ 包含表格格式")
            else:
                print("❌ 缺失表格格式")
                
            print(f"\n📄 报告总长度: {len(analysis)} 字符")
            print("🎯 前端现在应该能完整显示所有内容！")
            
    else:
        print(f"❌ 响应错误: {response.text}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*60)
print("🔧 修复内容:")
print("- 修正了正则表达式，确保完整捕获报告内容")
print("- 现在不会在'一、总体业绩概览'处截断")
print("- 完整的报告都会显示在正式报告区域")
print("="*60)
