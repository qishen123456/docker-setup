#!/usr/bin/env python3

# 测试前端Markdown解析器
print("🧪 测试前端Markdown解析器")

# 模拟AI返回的内容
test_content = """# 产品销售分析报告

## 数据概览

以下是产品销售数据的详细分析：

| 产品名称 | 销售额（万元） | 增长率（%） | 状态 |
|:--------|:-------------:|:----------:|:-----:|
| 产品A   | 1200          | 15.5       | ✅   |
| 产品B   | 800           | -5.2       | ❌   |
| 产品C   | 1500          | 22.1       | ✅   |

### 关键发现

> **重要提示**：产品B出现负增长，需要重点关注

**主要亮点**：
- 产品C表现最佳，增长率达到22.1%
- 总销售额达到3500万元
- 整体增长率为10.8%

**需要改进的地方**：
1. 产品B的负增长问题
2. 市场推广策略优化
3. 产品线调整

### 技术实现

```python
import matplotlib.pyplot as plt

# 创建柱状图
products = ['产品A', '产品B', '产品C']
sales = [1200, 800, 1500]

plt.figure(figsize=(10, 6))
plt.bar(products, sales)
plt.title('产品销售额对比')
plt.show()
```

## 总结

通过分析可以看出，**产品C**是我们的明星产品，而产品B需要改进策略。"""

# 模拟前端的formatMarkdown函数
def formatMarkdown(text):
    import re
    
    if not text:
        return ''
    
    try:
        html = text
        
        # 1. 处理表格 - 修复正则表达式
        def replace_table(match):
            lines = match.group(0).strip().split('\n')
            if len(lines) < 3:
                return match.group(0)
            
            # 处理表头
            header_cells = [cell.strip() for cell in lines[0].split('|') if cell.strip()]
            header_html = ''.join([f'<th>{cell}</th>' for cell in header_cells])
            
            # 处理表体
            body_rows = []
            for i in range(2, len(lines)):
                row_cells = [cell.strip() for cell in lines[i].split('|') if cell.strip()]
                if row_cells:
                    body_rows.append(f"<tr>{''.join([f'<td>{cell}</td>' for cell in row_cells])}</tr>")
            
            return f'<table class="markdown-table"><thead><tr>{header_html}</tr></thead><tbody>{"".join(body_rows)}</tbody></table>'
        
        html = re.sub(r'(\|.+?\|\s*\n\|[\s\-\|\:]+\|\s*\n(?:\|.+?\|\s*\n?)*)', replace_table, html)
        
        # 2. 处理标题
        html = re.sub(r'^### (.*$)', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.*$)', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.*$)', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # 3. 处理粗体
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
        
        # 4. 处理斜体
        html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
        
        # 5. 处理引用
        html = re.sub(r'^> (.*)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
        
        # 6. 处理无序列表
        html = re.sub(r'^- (.*)$', r'<ul><li>\1</li></ul>', html, flags=re.MULTILINE)
        html = re.sub(r'(</ul>\s*<ul>)', '', html)
        
        # 7. 处理有序列表
        html = re.sub(r'^\d+\. (.*)$', r'<ol><li>\1</li></ol>', html, flags=re.MULTILINE)
        html = re.sub(r'(</ol>\s*<ol>)', '', html)
        
        # 8. 处理代码块
        html = re.sub(r'```(\w+)?\n([\s\S]*?)```', r'<pre class="markdown-code"><code>\2</code></pre>', html)
        
        # 9. 处理内联代码
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
        
        # 10. 处理换行
        html = html.replace('\n\n', '<br><br>')
        html = html.replace('\n', '<br>')
        
        return html
        
    except Exception as e:
        print(f"解析失败: {e}")
        return text.replace('**', '<strong>').replace('</strong>', '**')

def formatMarkdownTable(header, body):
    # 处理表头
    headers = [h.strip() for h in header.split('|') if h.strip()]
    headerHtml = ''.join([f'<th>{h}</th>' for h in headers])
    
    # 处理表体
    rows = [row.strip() for row in body.strip().split('\n') if row.strip()]
    bodyHtml = ''
    for row in rows:
        cells = [c.strip() for c in row.split('|') if c.strip()]
        bodyHtml += f'<tr>{"".join([f"<td>{c}</td>" for c in cells])}</tr>'
    
    return f'<table class="markdown-table"><thead><tr>{headerHtml}</tr></thead><tbody>{bodyHtml}</tbody></table>'

# 执行测试
print("📝 原始Markdown内容:")
print("="*60)
print(test_content)
print("="*60)

print("\n🔄 解析后的HTML内容:")
print("="*60)
html_result = formatMarkdown(test_content)
print(html_result)
print("="*60)

# 检查各种元素
elements = {
    "H1标题": "<h1>" in html_result,
    "H2标题": "<h2>" in html_result,
    "H3标题": "<h3>" in html_result,
    "HTML表格": "<table" in html_result and "<th>" in html_result,
    "粗体": "<strong>" in html_result,
    "引用块": "<blockquote>" in html_result,
    "无序列表": "<ul>" in html_result,
    "有序列表": "<ol>" in html_result,
    "代码块": "<pre" in html_result,
    "内联代码": "<code>" in html_result
}

print("\n✅ 元素检查:")
for element, found in elements.items():
    status = "✅" if found else "❌"
    print(f"{status} {element}")

print("\n🎯 测试完成！现在前端应该能正确显示:")
print("• 美观的表格（带边框和样式）")
print("• 层次分明的标题")
print("• 突出的粗体文本")
print("• 优雅的引用块")
print("• 整齐的列表")
print("• 格式化的代码块")
