#!/usr/bin/env python3
"""
通过API测试聊天功能
"""
import requests
import json

def test_chat_api():
    """测试聊天API"""
    url = "http://localhost:5000/api/chat"
    headers = {"Content-Type": "application/json"}
    data = {
        "question": "东部分公司业绩"
    }
    
    try:
        print("🔄 发送请求到聊天API...")
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        print(f"📊 响应状态码: {response.status_code}")
        print(f"📊 响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 请求成功")
            print(f"📝 问题: {result.get('question', 'N/A')}")
            print(f"📝 SQL: {result.get('sql', 'N/A')}")
            print(f"📊 行数: {result.get('row_count', 0)}")
            if result.get('steps'):
                print("📋 处理步骤:")
                for step in result.get('steps', []):
                    print(f"  - {step.get('title', '')}: {step.get('status', '')} ({step.get('duration', 0)}ms)")
        else:
            print(f"❌ 请求失败: {response.status_code}")
            try:
                error_data = response.json()
                print(f"📝 错误信息: {json.dumps(error_data, ensure_ascii=False, indent=2)}")
            except:
                print(f"📝 响应内容: {response.text}")
                
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")

if __name__ == "__main__":
    test_chat_api()
