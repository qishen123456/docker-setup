#!/usr/bin/env python3
import requests
import json

print("🧪 测试新的Markdown解析器和图表渲染功能")

# 包含各种Markdown元素和图表的测试数据
test_data = {
    "query_data": {
        "question": "Markdown和图表渲染测试",
        "sql": "SELECT * FROM test_data",
        "rows": [
            {"name": "产品A", "sales": 1200, "growth": 15.5},
            {"name": "产品B", "sales": 800, "growth": -5.2},
            {"name": "产品C", "sales": 1500, "growth": 22.1}
        ],
        "columns": ["name", "sales", "growth"]
    }
}

print("📊 发送测试数据...")

try:
    response = requests.post(
        'http://localhost:5000/api/analysis-prompts/generate-stream',
        json=test_data,
        headers={'Content-Type': 'application/json'},
        stream=True,
        timeout=180
    )
    
    print(f"📊 响应状态码: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ 开始接收流式内容...")
        
        full_content = ""
        chunk_count = 0
        
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    
                    if data['type'] == 'content':
                        content = data['content']
                        full_content += content
                        chunk_count += 1
                        if chunk_count % 50 == 0:  # 每50个片段显示一次进度
                            print(f"📝 已接收 {chunk_count} 个片段...")
                        
                    elif data['type'] == 'done':
                        print(f"\n✅ 流式接收完成!")
                        print(f"📊 总共接收 {chunk_count} 个片段")
                        print(f"📄 报告总长度: {len(full_content)} 字符")
                        
                        print(f"\n📋 完整报告内容:")
                        print("="*80)
                        print(full_content)
                        print("="*80)
                        
                        # 检查包含的元素
                        elements_found = {
                            "表格": "|" in full_content,
                            "代码块": "```" in full_content,
                            "ECharts图表": "```echarts" in full_content,
                            "Mermaid图表": "```mermaid" in full_content,
                            "Python图表": "```python" in full_content and "matplotlib" in full_content,
                            "标题": "# " in full_content,
                            "粗体": "**" in full_content,
                            "引用": "> " in full_content
                        }
                        
                        print(f"\n🔍 内容检查:")
                        for element, found in elements_found.items():
                            status = "✅" if found else "❌"
                            print(f"{status} {element}")
                        
                        break
                        
                    elif data['type'] == 'error':
                        print(f"❌ 错误: {data['error']}")
                        break
                        
                except json.JSONDecodeError as e:
                    print(f"⚠️ 解析JSON失败: {e}")
        
    else:
        print(f"❌ 请求失败: {response.text}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*80)
print("🎯 新功能特点:")
print("")
print("📝 专业Markdown解析器 (marked.js):")
print("✅ GitHub风格表格渲染")
print("✅ 完整的标题层级 (H1-H6)")
print("✅ 美观的代码块样式")
print("✅ 引用块、列表、链接")
print("✅ 内联代码高亮")
print("")
print("📊 图表渲染拦截器:")
print("✅ 自动识别 ```echarts 并渲染ECharts图表")
print("✅ 自动识别 ```mermaid 并显示Mermaid代码")
print("✅ 自动识别 ```python matplotlib 并显示可复制代码")
print("✅ 错误处理和降级显示")
print("")
print("🎨 GitHub风格CSS:")
print("✅ 专业的表格样式 (边框、悬停、斑马纹)")
print("✅ 优雅的代码块 (等宽字体、背景色)")
print("✅ 美观的标题 (下划线、层次)")
print("✅ 精致的引用块 (左边框、背景)")
print("✅ 响应式设计")
print("")
print("🚀 前端现在会:")
print("• 使用marked.js解析Markdown，而不是简单的正则表达式")
print("• 自动检测并渲染图表代码块")
print("• 应用GitHub风格的CSS样式")
print("• 支持复杂的表格、代码、标题格式")
print("• 提供专业的文档阅读体验")
print("="*80)
