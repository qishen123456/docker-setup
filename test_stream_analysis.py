#!/usr/bin/env python3
import requests
import json

print("🧪 测试流式分析报告生成")

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

print("📊 发送流式分析请求...")

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
                        print(f"📝 片段 {chunk_count}: {content[:50]}...")
                        
                    elif data['type'] == 'done':
                        print(f"\n✅ 流式接收完成!")
                        print(f"📊 总共接收 {chunk_count} 个片段")
                        print(f"📄 报告总长度: {len(full_content)} 字符")
                        
                        print(f"\n📋 报告内容预览（前500字符）:")
                        print("="*60)
                        print(full_content[:500] + "..." if len(full_content) > 500 else full_content)
                        print("="*60)
                        break
                        
                    elif data['type'] == 'error':
                        print(f"❌ 错误: {data['error']}")
                        break
                        
                except json.JSONDecodeError as e:
                    print(f"⚠️ 解析JSON失败: {e}")
                    print(f"原始数据: {line}")
        
    else:
        print(f"❌ 请求失败: {response.text}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*60)
print("🎯 流式功能特点:")
print("✅ 实时显示：内容一点点生成，一点点显示")
print("✅ 用户体验：不再需要等待全部生成完成")
print("✅ 进度可见：可以看到AI正在思考和写作")
print("✅ 可中断：用户可以看到进度，不会以为卡住了")
print("")
print("🚀 前端现在会:")
print("• 点击'生成分析报告'后立即开始显示内容")
print("• 内容像打字机一样一个字一个字出现")
print("• 自动滚动到最新内容")
print("• 完成时显示成功消息")
print("="*60)
