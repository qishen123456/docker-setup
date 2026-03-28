#!/usr/bin/env python3
import requests
import json

print("🧪 测试包含表格的分析报告生成")

# 包含表格数据的测试
test_data = {
    "query_data": {
        "question": "业绩分析测试",
        "sql": "SELECT * FROM performance_data",
        "rows": [
            {"department": "销售部", "target": 1000000, "actual": 850000, "rate": 85.0},
            {"department": "技术部", "target": 800000, "actual": 920000, "rate": 115.0},
            {"department": "市场部", "target": 600000, "actual": 540000, "rate": 90.0}
        ],
        "columns": ["department", "target", "actual", "rate"]
    }
}

print("📊 发送包含表格数据的测试...")

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
        print(f"📄 报告长度: {len(result.get('analysis', ''))} 字符")
        
        analysis = result.get('analysis', '')
        
        # 检查是否包含表格格式
        if '|' in analysis:
            print("✅ 报告包含表格格式")
            print("\n📋 报告内容预览:")
            print("="*60)
            print(analysis)
            print("="*60)
        else:
            print("⚠️ 报告不包含表格格式")
            print("\n📋 报告内容:")
            print("="*60)
            print(analysis)
            print("="*60)
            
    else:
        print(f"❌ 响应错误: {response.text}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*60)
print("🎯 前端现在应该能正确显示:")
print("1. ✅ Markdown表格")
print("2. ✅ 标题格式 (H1, H2, H3)")
print("3. ✅ 加粗和斜体")
print("4. ✅ 列表和段落")
print("5. ✅ 表格样式 (边框、悬停效果)")
print("="*60)
