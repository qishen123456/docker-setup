#!/usr/bin/env python3
import requests
import json

print("🧪 创建包含丰富Markdown和图表的测试提示词")

# 创建一个专门用于测试Markdown和图表渲染的提示词
test_prompt = {
    "name": "Markdown和图表渲染测试",
    "category": "测试",
    "prompt": """请基于以下数据生成一份包含丰富Markdown格式和图表代码的分析报告：

**要求包含以下元素：**

1. **多级标题**：使用 # ## ### ####
2. **表格**：创建数据对比表格
3. **代码块**：包含以下类型：
   - Python matplotlib图表代码
   - ECharts JSON配置
   - Mermaid流程图
4. **格式化文本**：粗体、斜体、引用块
5. **列表**：有序和无序列表

**数据说明：**
- 产品销售数据
- 包含名称、销售额、增长率等字段
- 需要进行对比分析和趋势展示

**输出格式要求：**
- 使用专业Markdown格式
- 包含完整的图表生成代码
- 表格要有清晰的表头和数据
- 代码块要有语言标识

请生成一份完整的、格式精美的分析报告。""",
    "is_default": False
}

print("📝 创建测试提示词...")

try:
    response = requests.post(
        'http://localhost:5000/api/analysis-prompts',
        json=test_prompt,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        data = response.json()
        created_prompt = data['prompt']
        print(f"✅ 提示词创建成功: {created_prompt['name']}")
        print(f"📄 ID: {created_prompt['id']}")
        
        # 现在使用这个提示词生成报告
        print(f"\n📊 使用新创建的提示词生成报告...")
        
        analysis_data = {
            "query_data": {
                "question": "请使用Markdown和图表渲染测试提示词生成报告",
                "sql": "SELECT name, sales, growth FROM products",
                "rows": [
                    {"name": "产品A", "sales": 1200, "growth": 15.5},
                    {"name": "产品B", "sales": 800, "growth": -5.2},
                    {"name": "产品C", "sales": 1500, "growth": 22.1},
                    {"name": "产品D", "sales": 950, "growth": 8.7},
                    {"name": "产品E", "sales": 1100, "growth": 12.3}
                ],
                "columns": ["name", "sales", "growth"]
            },
            "prompt": created_prompt['prompt']  # 使用新创建的提示词
        }
        
        # 发送流式请求
        response = requests.post(
            'http://localhost:5000/api/analysis-prompts/generate-stream',
            json=analysis_data,
            headers={'Content-Type': 'application/json'},
            stream=True,
            timeout=180
        )
        
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
                            if chunk_count % 100 == 0:
                                print(f"📝 已接收 {chunk_count} 个片段...")
                            
                        elif data['type'] == 'done':
                            print(f"\n✅ 报告生成完成!")
                            print(f"📊 总共接收 {chunk_count} 个片段")
                            print(f"📄 报告总长度: {len(full_content)} 字符")
                            
                            print(f"\n📋 报告内容预览:")
                            print("="*80)
                            print(full_content[:1000] + "..." if len(full_content) > 1000 else full_content)
                            print("="*80)
                            break
                            
                    except json.JSONDecodeError:
                        continue
        
    else:
        print(f"❌ 创建失败: {response.text}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*80)
print("🎯 测试完成！现在去前端查看效果:")
print("")
print("🌐 前端地址: http://localhost:5173")
print("📝 测试步骤:")
print("1. 打开前端页面")
print("2. 输入查询: 'Markdown和图表渲染测试'")
print("3. 点击'生成分析报告'")
print("4. 观察流式输出效果")
print("5. 查看最终的Markdown渲染效果")
print("")
print("✨ 期待看到的效果:")
print("• 美观的GitHub风格表格")
print("• 专业的代码块样式")
print("• 智能的图表代码识别")
print("• 流畅的打字机效果")
print("• 完整的Markdown格式支持")
print("="*80)
