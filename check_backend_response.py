#!/usr/bin/env python3

import requests
import json

print("🔍 检查后端返回的实际数据结构")
print("="*50)

def test_chat_response():
    try:
        data = {"question": "查询前10条数据"}
        response = requests.post('http://localhost:5000/api/chat', 
                               json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 后端响应数据结构:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print()
            
            print("📊 关键字段检查:")
            print(f"• question: {result.get('question', 'MISSING')}")
            print(f"• sql: {result.get('sql', 'MISSING')}")
            print(f"• row_count: {result.get('row_count', 'MISSING')}")
            print(f"• error: '{result.get('error', '')}'")
            print(f"• columns: {len(result.get('columns', []))} 个")
            print(f"• rows: {len(result.get('rows', []))} 条")
            print(f"• steps: {len(result.get('steps', []))} 个")
            print(f"• total_duration: {result.get('total_duration', 'MISSING')}")
            print()
            
            # 检查是否有隐藏的错误
            if result.get('error'):
                print("❌ 发现错误字段:")
                print(f"   错误信息: {result['error']}")
                return False
            elif result.get('row_count', 0) > 0:
                print("✅ 查询成功，有数据返回")
                return True
            else:
                print("⚠️ 查询成功，但没有数据")
                return True
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            try:
                error_data = response.json()
                print(f"错误详情: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"错误文本: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def main():
    print("🚀 开始检查后端数据结构...")
    print()
    
    if test_chat_response():
        print("\n💡 后端数据正常，问题可能在于:")
        print("1. 前端模板判断逻辑")
        print("2. 前端数据处理")
        print("3. 浏览器缓存")
        print("4. Vue响应式更新")
        
        print("\n🔧 建议的前端检查:")
        print("1. 打开浏览器开发者工具")
        print("2. 在Console中输入: console.log(messages.value)")
        print("3. 查看最新消息的error字段")
        print("4. 检查Network面板的API响应")
    else:
        print("\n❌ 后端存在问题，需要检查后端逻辑")

if __name__ == "__main__":
    main()
