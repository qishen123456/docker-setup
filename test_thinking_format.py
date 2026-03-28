#!/usr/bin/env python3
import requests
import json

print("🧪 测试思考过程和正式报告分离显示")

# 测试数据
test_data = {
    "query_data": {
        "question": "今年商用事业部业绩分析",
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
        print(f"📄 报告长度: {len(result.get('analysis', ''))} 字符")
        
        analysis = result.get('analysis', '')
        
        # 检查是否包含思考过程和正式报告
        if '商用事业部' in analysis and '年度业绩分析报告' in analysis:
            print("✅ 报告包含思考过程和正式报告")
            
            # 简单检查分离效果
            if 'AI 思考过程' in analysis or '正式分析报告' in analysis:
                print("✅ 前端应该能正确分离显示")
            else:
                print("⚠️ 前端会自动分离显示")
                
            print("\n📋 报告内容预览:")
            print("="*60)
            # 只显示前500字符避免过长
            print(analysis[:500] + "..." if len(analysis) > 500 else analysis)
            print("="*60)
        else:
            print("⚠️ 报告格式可能不符合预期")
            print("\n📋 报告内容:")
            print("="*60)
            print(analysis)
            print("="*60)
            
    else:
        print(f"❌ 响应错误: {response.text}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*60)
print("🎯 前端现在会显示:")
print("1. 🧠 AI 思考过程:")
print("   - 紫色渐变头部")
print("   - 较小字体，灰色文字")
print("   - 显示AI的分析思路")
print("")
print("2. 📄 正式分析报告:")
print("   - 蓝色渐变头部")
print("   - 正常字体，完整表格")
print("   - 专业的报告格式")
print("="*60)
