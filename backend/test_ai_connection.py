#!/usr/bin/env python3
import sys
import os

print("🧪 测试AI模型连接")

try:
    from vanna_core import get_vanna_instance
    
    vn, error = get_vanna_instance()
    
    if error:
        print(f"❌ Vanna初始化失败: {error}")
        sys.exit(1)
    
    print(f"✅ Vanna初始化成功")
    print(f"🤖 AI模型: {vn.model}")
    
    # 测试简单的prompt
    print("\n📝 测试简单prompt...")
    
    test_messages = [
        {"role": "system", "content": "你是一个测试助手"},
        {"role": "user", "content": "请回复数字1"}
    ]
    
    result = vn.submit_prompt(test_messages)
    print(f"✅ 测试成功，响应: {result}")
    
except Exception as e:
    print(f"❌ 测试失败: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
