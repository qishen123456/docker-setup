#!/usr/bin/env python3
"""
直接测试生成的SQL
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vanna_core import get_vanna_instance

def test_generated_sql():
    """测试生成的复杂SQL"""
    try:
        # 获取Vanna实例
        vn, error = get_vanna_instance()
        if error:
            print(f"❌ Vanna实例获取失败: {error}")
            return
        
        print("✅ Vanna实例获取成功")
        
        # 简化的东部分公司业绩SQL
        simple_sql = """
        WITH 字段提取 AS (
            SELECT
                fields ->> '分公司' AS 分公司,
                fields ->> '代表处' AS 代表处,
                fields ->> '业务代表' AS 业务代表,
                fields ->> '当前年' AS 当前年,
                fields ->> '总任务（金额）' AS 任务原始值,
                fields ->> '年度开单金额' AS 开单原始值
            FROM angel_group_data
            WHERE fields ->> '分公司' = '东部分公司'
              AND fields ->> '当前年' = '2026'
        ),
        基础数据 AS (
            SELECT
                分公司,
                代表处,
                业务代表,
                当前年,
                COALESCE(NULLIF(regexp_replace(任务原始值, '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 任务金额,
                COALESCE(NULLIF(regexp_replace(开单原始值, '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 开单金额
            FROM 字段提取
        )
        SELECT
            分公司,
            SUM(任务金额) AS 总任务金额,
            SUM(开单金额) AS 年度开单金额,
            CASE
                WHEN SUM(任务金额) > 0 THEN ROUND((SUM(开单金额) / SUM(任务金额) * 100)::NUMERIC, 2)
                ELSE 0
            END AS 达成率
        FROM 基础数据
        GROUP BY 分公司
        LIMIT 100;
        """
        
        print(f"🔍 执行SQL: {simple_sql[:200]}...")
        
        # 执行SQL
        df = vn.run_sql(sql=simple_sql)
        
        if df is None:
            print("❌ SQL执行返回None")
        elif df.empty:
            print("✅ SQL执行成功，但结果为空")
        else:
            print(f"✅ SQL执行成功，返回{len(df)}行数据")
            print(df.to_string())
            
    except Exception as e:
        print(f"❌ SQL执行失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_generated_sql()
