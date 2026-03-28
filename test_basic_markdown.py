#!/usr/bin/env python3
import requests
import json

print("🧪 测试基础Markdown渲染功能")

# 创建一个简单的测试提示词，专注于基础Markdown
test_prompt = {
    "name": "基础Markdown测试",
    "category": "测试",
    "prompt": """请基于以下数据生成一份包含基础Markdown格式的分析报告：

**必须包含以下格式：**
1. 标题：使用 # ## ### 
2. 表格：使用 | 分隔的Markdown表格
3. 粗体：使用 **粗体文本**
4. 列表：使用 - 或 1. 2. 3.
5. 引用：使用 > 引用文本

**数据：**
- 产品A: 销售额1200万，增长率15.5%
- 产品B: 销售额800万，增长率-5.2%
- 产品C: 销售额1500万，增长率22.1%

请生成简洁、清晰的分析报告，重点展示表格和基础格式。""",
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
        
        # 使用新提示词生成报告
        analysis_data = {
            "query_data": {
                "question": "基础Markdown测试",
                "sql": "SELECT name, sales, growth FROM products",
                "rows": [
                    {"name": "产品A", "sales": 1200, "growth": 15.5},
                    {"name": "产品B", "sales": 800, "growth": -5.2},
                    {"name": "产品C", "sales": 1500, "growth": 22.1}
                ],
                "columns": ["name", "sales", "growth"]
            },
            "prompt": created_prompt['prompt']
        }
        
        print(f"\n📊 生成分析报告...")
        
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
                            
                        elif data['type'] == 'done':
                            print(f"\n✅ 报告生成完成!")
                            print(f"📊 总共接收 {chunk_count} 个片段")
                            print(f"📄 报告总长度: {len(full_content)} 字符")
                            
                            print(f"\n📋 完整报告内容:")
                            print("="*80)
                            print(full_content)
                            print("="*80)
                            
                            # 检查Markdown元素
                            elements = {
                                "标题 (#)": "# " in full_content,
                                "二级标题 (##)": "## " in full_content,
                                "表格 (|)": "|" in full_content and "-" in full_content,
                                "粗体 (**)": "**" in full_content,
                                "列表 (-)": "- " in full_content or "1. " in full_content,
                                "引用 (>)": "> " in full_content
                            }
                            
                            print(f"\n🔍 Markdown元素检查:")
                            for element, found in elements.items():
                                status = "✅" if found else "❌"
                                print(f"{status} {element}")
                            
                            break
                            
                    except json.JSONDecodeError:
                        continue
        
    else:
        print(f"❌ 创建失败: {response.text}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*80)
print("🎯 基础Markdown功能测试完成！")
print("")
print("🌐 现在去前端测试:")
print("1. 打开 http://localhost:5173")
print("2. 输入: '基础Markdown测试'") 
print("3. 点击'生成分析报告'")
print("4. 观察表格、标题、粗体是否正确显示")
print("")
print("✅ 期待效果:")
print("• 表格有边框和斑马纹")
print("• 标题有不同大小")
print("• 粗体文本加粗显示")
print("• 列表有缩进和符号")
print("• 引用有左边框和背景")
print("="*80)
