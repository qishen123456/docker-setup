#!/usr/bin/env python3
import requests
import json

# 测试模糊匹配
test_question = "商用 分公司的业绩"

print(f"🧪 测试问题: {test_question}")
print("=" * 50)

try:
    response = requests.post(
        'http://localhost:5000/api/chat',
        json={'question': test_question},
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ 请求成功!")
        print(f"问题: {data.get('question', '')}")
        print(f"SQL长度: {len(data.get('sql', ''))}")
        print(f"行数: {data.get('row_count', 0)}")
        
        # 检查步骤信息
        if 'steps' in data:
            for step in data['steps']:
                print(f"步骤: {step.get('title', '')} - {step.get('status', '')}")
        
        # 显示SQL的前200个字符
        sql = data.get('sql', '')
        if sql:
            print(f"\nSQL预览:\n{sql[:200]}...")
            if "训练数据" in str(data.get('steps', [])):
                print("🎉 成功使用训练数据!")
            else:
                print("⚠️  使用了大模型生成")
        else:
            print("❌ 没有生成SQL")
        
    else:
        print(f"❌ 请求失败: {response.status_code}")
        print(f"错误信息: {response.text}")
        
except Exception as e:
    print(f"❌ 测试失败: {e}")

print("\n" + "=" * 50)
