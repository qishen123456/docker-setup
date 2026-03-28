#!/usr/bin/env python3
import requests
import json

print("🧪 测试HTML表格渲染")

# 直接发送包含表格的测试数据
test_data = {
    "query_data": {
        "question": "表格测试",
        "sql": "SELECT * FROM test",
        "rows": [
            {"name": "产品A", "sales": 1200, "growth": 15.5},
            {"name": "产品B", "sales": 800, "growth": -5.2},
            {"name": "产品C", "sales": 1500, "growth": 22.1}
        ],
        "columns": ["name", "sales", "growth"]
    }
}

print("📊 发送测试请求...")

try:
    response = requests.post(
        'http://localhost:5000/api/analysis-prompts/generate-stream',
        json=test_data,
        headers={'Content-Type': 'application/json'},
        stream=True,
        timeout=180
    )
    
    if response.status_code == 200:
        print("✅ 开始接收内容...")
        
        full_content = ""
        
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    
                    if data['type'] == 'content':
                        full_content += data['content']
                        
                    elif data['type'] == 'done':
                        print(f"✅ 接收完成，内容长度: {len(full_content)}")
                        
                        # 检查是否包含表格
                        if "|" in full_content:
                            print("✅ 发现Markdown表格格式")
                            
                            # 提取表格部分进行测试
                            lines = full_content.split('\n')
                            table_start = -1
                            for i, line in enumerate(lines):
                                if '|' in line and i + 1 < len(lines) and '|' in lines[i + 1]:
                                    table_start = i
                                    break
                            
                            if table_start >= 0:
                                print("📋 表格内容预览:")
                                table_lines = []
                                for i in range(table_start, min(table_start + 10, len(lines))):
                                    if '|' in lines[i] or (i > table_start and lines[i].strip() == ''):
                                        table_lines.append(lines[i])
                                    elif table_lines and '|' not in lines[i]:
                                        break
                                
                                for line in table_lines:
                                    print(f"  {line}")
                        else:
                            print("❌ 未发现表格格式")
                        
                        break
                        
                except json.JSONDecodeError:
                    continue
    
    else:
        print(f"❌ 请求失败: {response.text}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*60)
print("🎯 现在前端使用自定义Markdown解析器:")
print("✅ 直接将 | 表格 | 转换为 <table> 标签")
print("✅ 支持 # ## ### 标题")
print("✅ 支持 **粗体** 文本")
print("✅ 支持 - 列表和 1. 有序列表")
print("✅ 支持 > 引用块")
print("✅ 支持 ``` 代码块")
print("")
print("🌐 去前端测试: http://localhost:5173")
print("输入任意查询，查看表格是否正确显示！")
print("="*60)
