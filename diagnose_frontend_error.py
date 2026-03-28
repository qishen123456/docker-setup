#!/usr/bin/env python3

import requests
import json

print("🔍 前端错误诊断工具")
print("="*50)

# 测试后端连接
def test_backend_connection():
    try:
        response = requests.get('http://localhost:5000/api/dashboard', timeout=5)
        print(f"✅ 后端连接正常: {response.status_code}")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ 后端连接失败 - 后端可能未启动")
        return False
    except requests.exceptions.Timeout:
        print("❌ 后端连接超时")
        return False
    except Exception as e:
        print(f"❌ 后端连接错误: {e}")
        return False

# 测试聊天接口
def test_chat_api():
    try:
        data = {"question": "查询前10条数据"}
        response = requests.post('http://localhost:5000/api/chat', 
                               json=data, timeout=30)
        print(f"✅ 聊天接口响应: {response.status_code}")
        
        if response.status_code == 400:
            result = response.json()
            print(f"❌ 400错误详情: {result}")
            return False
        elif response.status_code == 200:
            result = response.json()
            print(f"✅ 聊天接口正常响应")
            print(f"   - 问题: {result.get('question', 'N/A')}")
            print(f"   - SQL: {result.get('sql', 'N/A')[:50]}...")
            print(f"   - 数据行数: {result.get('row_count', 'N/A')}")
            print(f"   - 步骤数量: {len(result.get('steps', []))}")
            return True
        else:
            print(f"❌ 意外状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 聊天接口测试失败: {e}")
        return False

# 测试Vanna状态
def test_vanna_status():
    try:
        response = requests.get('http://localhost:5000/api/chat/vanna-status', timeout=10)
        print(f"✅ Vanna状态接口响应: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   - Vanna状态: {result.get('status', 'N/A')}")
            print(f"   - 错误信息: {result.get('error', 'N/A')}")
            return True
        else:
            print(f"❌ Vanna状态异常: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Vanna状态测试失败: {e}")
        return False

# 主测试流程
def main():
    print("🚀 开始诊断前端错误...")
    print()
    
    # 1. 测试后端连接
    print("1. 测试后端连接...")
    if not test_backend_connection():
        print("\n💡 解决方案:")
        print("   - 启动后端: python backend/app.py")
        print("   - 或运行: start_backend.bat")
        return
    
    print()
    
    # 2. 测试Vanna状态
    print("2. 测试Vanna状态...")
    if not test_vanna_status():
        print("\n💡 解决方案:")
        print("   - 检查AI模型配置")
        print("   - 检查数据库连接")
        print("   - 查看backend日志")
        return
    
    print()
    
    # 3. 测试聊天接口
    print("3. 测试聊天接口...")
    if not test_chat_api():
        print("\n💡 解决方案:")
        print("   - 检查问题格式")
        print("   - 查看后端错误日志")
        print("   - 检查训练数据")
        return
    
    print()
    print("🎉 所有测试通过！前端应该可以正常工作。")
    
    # 4. 前端检查建议
    print("\n📋 前端检查清单:")
    print("✅ 确认前端正在运行 (npm run dev)")
    print("✅ 确认浏览器控制台无网络错误")
    print("✅ 确认API代理配置正确")
    print("✅ 确认前端代码语法正确")

if __name__ == "__main__":
    main()
