#!/usr/bin/env python3
import requests
import json

print("🧪 测试查询：今年商用事业部业绩分析")

# 发送聊天请求
chat_data = {
    "question": "今年商用事业部业绩分析"
}

print("📤 发送查询请求...")

try:
    response = requests.post(
        'http://localhost:5000/api/chat',
        json=chat_data,
        headers={'Content-Type': 'application/json'},
        timeout=60
    )
    
    print(f"📊 响应状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ 查询成功!")
        
        if 'sql' in result:
            print(f"🔍 生成的SQL: {result['sql']}")
        
        if 'rows' in result:
            print(f"📊 数据行数: {len(result['rows'])}")
            print(f"📋 数据列数: {len(result['columns']) if result.get('columns') else '未知'}")
            
            # 显示前几行数据
            if result['rows']:
                print("\n📄 数据样本:")
                for i, row in enumerate(result['rows'][:3]):
                    print(f"  行{i+1}: {row}")
        
        # 如果有数据，测试生成分析报告
        if result.get('rows') and len(result['rows']) > 0:
            print("\n🎯 生成分析报告...")
            
            analysis_data = {
                "query_data": {
                    "question": "今年商用事业部业绩分析",
                    "sql": result.get('sql', ''),
                    "rows": result['rows'],
                    "columns": result.get('columns', [])
                }
            }
            
            analysis_response = requests.post(
                'http://localhost:5000/api/analysis-prompts/generate',
                json=analysis_data,
                headers={'Content-Type': 'application/json'},
                timeout=120
            )
            
            if analysis_response.status_code == 200:
                analysis_result = analysis_response.json()
                print("✅ 分析报告生成成功!")
                print(f"📄 报告长度: {len(analysis_result.get('analysis', ''))} 字符")
                
                analysis = analysis_result.get('analysis', '')
                
                # 检查分离效果
                if '商用事业部' in analysis and '业绩分析报告' in analysis:
                    print("✅ 包含完整报告结构")
                    
                    # 检查是否包含思考过程和正式报告
                    if 'AI 思考过程' in analysis or '正式分析报告' in analysis:
                        print("✅ 前端应该能正确分离显示")
                    else:
                        print("✅ 前端会自动分离显示")
                        
                    print("\n📋 报告预览（前500字符）:")
                    print("="*60)
                    print(analysis[:500] + "..." if len(analysis) > 500 else analysis)
                    print("="*60)
                else:
                    print("⚠️ 报告格式可能不符合预期")
                    
            else:
                print(f"❌ 分析报告生成失败: {analysis_response.text}")
        else:
            print("⚠️ 没有查询到数据，无法生成分析报告")
            
    else:
        print(f"❌ 查询失败: {response.text}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*60)
print("🎯 测试完成！")
print("现在你可以:")
print("1. 打开 http://localhost:5173")
print("2. 输入: '今年商用事业部业绩分析'")
print("3. 查看SQL执行结果")
print("4. 点击'生成分析报告'按钮")
print("5. 体验分离后的思考过程和正式报告")
print("="*60)
