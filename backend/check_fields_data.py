#!/usr/bin/env python3
"""
查看fields字段中的实际数据
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vanna_core import get_vanna_instance

def check_fields_data():
    """查看fields字段中的实际数据"""
    try:
        # 获取Vanna实例
        vn, error = get_vanna_instance()
        if error:
            print(f"❌ Vanna实例获取失败: {error}")
            return
        
        print("✅ Vanna实例获取成功")
        
        # 查看fields字段中的所有key
        print("\n📋 查看fields字段中的所有key:")
        try:
            keys_sql = """
            SELECT DISTINCT jsonb_object_keys(fields) as field_key
            FROM angel_group_data
            ORDER BY field_key;
            """
            df = vn.run_sql(sql=keys_sql)
            if df is not None and not df.empty:
                for idx, row in df.iterrows():
                    print(f"  - {row['field_key']}")
            else:
                print("  ❌ 没有找到字段key")
        except Exception as e:
            print(f"  ❌ 查看字段key失败: {str(e)}")
        
        # 查看分公司数据
        print("\n📋 查看所有分公司数据:")
        try:
            division_sql = """
            SELECT DISTINCT fields ->> '分公司' AS division
            FROM angel_group_data
            WHERE fields ->> '分公司' IS NOT NULL
            ORDER BY division;
            """
            df = vn.run_sql(sql=division_sql)
            if df is not None and not df.empty:
                for idx, row in df.iterrows():
                    print(f"  - {row['division']}")
            else:
                print("  ❌ 没有找到分公司数据")
        except Exception as e:
            print(f"  ❌ 查看分公司数据失败: {str(e)}")
        
        # 查看前3行的完整fields数据
        print("\n📋 查看前3行的完整fields数据:")
        try:
            sample_sql = """
            SELECT fields
            FROM angel_group_data
            LIMIT 3;
            """
            df = vn.run_sql(sql=sample_sql)
            if df is not None and not df.empty:
                for idx, row in df.iterrows():
                    print(f"  行{idx+1}: {row['fields']}")
            else:
                print("  ❌ 没有数据")
        except Exception as e:
            print(f"  ❌ 查看样本数据失败: {str(e)}")
            
    except Exception as e:
        print(f"❌ 检查失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_fields_data()
