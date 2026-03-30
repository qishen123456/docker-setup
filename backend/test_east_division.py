#!/usr/bin/env python3
"""
测试东部分公司业绩SQL
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vanna_core import get_vanna_instance

def test_east_division_sql():
    """测试东部分公司业绩SQL"""
    try:
        # 获取Vanna实例
        vn, error = get_vanna_instance()
        if error:
            print(f"❌ Vanna实例获取失败: {error}")
            return
        
        print("✅ Vanna实例获取成功")
        
        # 简化的测试SQL
        test_sql = """
        SELECT DISTINCT fields ->> '分公司' AS division
        FROM angel_group_data
        WHERE fields ->> '分公司' IS NOT NULL
        ORDER BY division
        LIMIT 10;
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
            for idx, row in df.iterrows():
                print(f"  - {row['division']}")
            
    except Exception as e:
        print(f"❌ SQL执行失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_east_division_sql()
