#!/usr/bin/env python3
"""
检查数据库表结构
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vanna_core import get_vanna_instance

def check_table_structure():
    """检查数据库表结构"""
    try:
        # 获取Vanna实例
        vn, error = get_vanna_instance()
        if error:
            print(f"❌ Vanna实例获取失败: {error}")
            return
        
        print("✅ Vanna实例获取成功")
        
        # 查看所有表
        print("\n📋 查看所有表:")
        tables_sql = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
        df = vn.run_sql(sql=tables_sql)
        if df is not None and not df.empty:
            for idx, row in df.iterrows():
                print(f"  - {row['table_name']}")
        
        # 查看angel_group_data表结构（如果存在）
        print("\n📋 查看angel_group_data表结构:")
        try:
            structure_sql = """
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'angel_group_data' 
            ORDER BY ordinal_position;
            """
            df = vn.run_sql(sql=structure_sql)
            if df is not None and not df.empty:
                for idx, row in df.iterrows():
                    print(f"  - {row['column_name']}: {row['data_type']} (nullable: {row['is_nullable']})")
            else:
                print("  ❌ 表angel_group_data不存在或无列信息")
        except Exception as e:
            print(f"  ❌ 查看表结构失败: {str(e)}")
        
        # 查看表的前几行数据
        print("\n📋 查看angel_group_data表的前5行数据:")
        try:
            sample_sql = "SELECT * FROM angel_group_data LIMIT 5;"
            df = vn.run_sql(sql=sample_sql)
            if df is not None and not df.empty:
                print(f"  ✅ 表有{len(df)}行数据")
                print(df.columns.tolist())
                print(df.head())
            else:
                print("  ❌ 表angel_group_data无数据")
        except Exception as e:
            print(f"  ❌ 查看表数据失败: {str(e)}")
            
    except Exception as e:
        print(f"❌ 检查失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_table_structure()
