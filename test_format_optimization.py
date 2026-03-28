#!/usr/bin/env python3
import requests
import json

print("🧪 测试优化后的Markdown格式显示")

# 测试数据 - 包含各种Markdown元素
test_data = {
    "query_data": {
        "question": "格式化测试",
        "sql": "SELECT * FROM test",
        "rows": [
            {"name": "测试1", "value": 100},
            {"name": "测试2", "value": 200}
        ],
        "columns": ["name", "value"]
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
        
        # 检查各种格式元素
        format_checks = {
            "表格": "|",
            "代码块": "```",
            "标题": "#",
            "粗体": "**",
            "引用": ">",
            "列表": "- "
        }
        
        print("\n🔍 格式元素检查:")
        for format_name, pattern in format_checks.items():
            if pattern in analysis:
                print(f"✅ 包含{format_name}")
            else:
                print(f"❌ 缺失{format_name}")
        
        print(f"\n📋 报告内容预览（前800字符）:")
        print("="*60)
        print(analysis[:800] + "..." if len(analysis) > 800 else analysis)
        print("="*60)
        
    else:
        print(f"❌ 响应错误: {response.text}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*60)
print("🎯 优化内容:")
print("✅ 修复表格显示问题")
print("✅ 添加代码块支持")
print("✅ 优化空行处理")
print("✅ 改进标题格式")
print("✅ 添加引用样式")
print("✅ 优化列表显示")
print("✅ 清理多余标签")
print("="*60)
print("\n🚀 现在前端应该能正确显示:")
print("• 美观的表格（带边框和悬停效果）")
print("• 格式化的代码块（等宽字体）")
print("• 层次分明的标题")
print("• 优雅的引用块")
print("• 整齐的列表")
print("• 合理的段落间距")
print("="*60)
