#!/usr/bin/env python3
"""
测试Vanna实例初始化
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vanna_core import get_vanna_instance

def test_vanna_init():
    """测试Vanna实例初始化"""
    try:
        print("🔄 开始获取Vanna实例...")
        vn, error = get_vanna_instance()
        
        if error:
            print(f"❌ Vanna实例获取失败: {error}")
            return False
        
        print("✅ Vanna实例获取成功")
        
        # 测试生成SQL
        print("🔄 测试生成SQL...")
        question = "东部分公司业绩"
        sql = vn.generate_sql(question=question)
        print(f"✅ SQL生成成功: {sql}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_vanna_init()
