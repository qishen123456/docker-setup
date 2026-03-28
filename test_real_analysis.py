#!/usr/bin/env python3
import requests
import json

# 首先获取真实的查询数据
print("🧪 获取查询数据")
try:
    chat_response = requests.post(
        'http://localhost:5000/api/chat',
        json={'question': '今年商用事业部业绩分析'},
        headers={'Content-Type': 'application/json'}
    )
    
    if chat_response.status_code == 200:
        chat_data = chat_response.json()
        print("✅ 查询成功!")
        print(f"SQL长度: {len(chat_data.get('sql', ''))}")
        print(f"数据行数: {chat_data.get('row_count', 0)}")
        print(f"数据列数: {len(chat_data.get('columns', []))}")
        
        # 准备分析数据
        analysis_data = {
            "query_data": {
                "question": chat_data.get('question', ''),
                "sql": chat_data.get('sql', ''),
                "rows": chat_data.get('rows', [])[:10],  # 只取前10行作为测试
                "columns": chat_data.get('columns', [])
            }
        }
        
        print(f"\n📊 准备分析的数据:")
        print(f"问题: {analysis_data['query_data']['question']}")
        print(f"列名: {analysis_data['query_data']['columns']}")
        print(f"数据样本: {len(analysis_data['query_data']['rows'])} 行")
        
        # 生成分析报告
        print(f"\n🔍 生成分析报告...")
        analysis_response = requests.post(
            'http://localhost:5000/api/analysis-prompts/generate',
            json=analysis_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if analysis_response.status_code == 200:
            analysis_result = analysis_response.json()
            print("✅ 分析报告生成成功!")
            print(f"分析报告长度: {len(analysis_result.get('analysis', ''))}")
            print(f"\n📋 分析报告:")
            print("="*60)
            print(analysis_result.get('analysis', ''))
            print("="*60)
        else:
            print(f"❌ 分析生成失败: {analysis_response.status_code}")
            print(f"错误: {analysis_response.text}")
            
    else:
        print(f"❌ 查询失败: {chat_response.status_code}")
        print(f"错误: {chat_response.text}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "="*60)
