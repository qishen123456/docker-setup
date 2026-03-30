#!/usr/bin/env python3
"""
测试SQL执行脚本
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vanna_core import get_vanna_instance

def test_sql_execution():
    """测试SQL执行"""
    try:
        # 获取Vanna实例
        vn, error = get_vanna_instance()
        if error:
            print(f"❌ Vanna实例获取失败: {error}")
            return
        
        print("✅ Vanna实例获取成功")
        
        # 测试SQL
        test_sql = """
        SELECT DISTINCT (fields ->> '分公司') AS division
        FROM angel_group_data
        WHERE fields ->> '分公司' LIKE '%商用东%';
        """
        
        print(f"🔍 执行SQL: {test_sql.strip()}")
        
        # 执行SQL
        df = vn.run_sql(sql=test_sql)
        
        if df is None:
            print("❌ SQL执行返回None")
        elif df.empty:
            print("✅ SQL执行成功，但结果为空")
        else:
            print(f"✅ SQL执行成功，返回{len(df)}行数据")
            print(df.head())
            
    except Exception as e:
        print(f"❌ SQL执行失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sql_execution()
