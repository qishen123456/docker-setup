"""Golden SQL 样本二次修复 - 确保返回正确的单行结果

上次修复的 SQL 返回了多行结果，需要改用标量子查询确保正确性。

用法: docker cp 到容器后执行
"""

import sys
import json
sys.path.insert(0, '/app/backend')

import psycopg2

DB = "host=smartask-postgres dbname=postgres user=postgres password=6670326"


def main():
    conn = psycopg2.connect(DB)
    cur = conn.cursor()
    
    print("=" * 60)
    print("🔧 Golden SQL 二次修复 - 确保单行结果")
    print("=" * 60)
    
    # 1. 查找需要修复的样本（上次修复的 + 新增的）
    print("\n[1/3] 查找需要修复的样本 ...")
    cur.execute("""
        SELECT id, question, sql_text, intent_type, tags
        FROM bs_golden_sql_samples
        WHERE is_active = TRUE
          AND (tags::text LIKE '%贡献率%' OR 
               tags::text LIKE '%占比%' OR
               question LIKE '%贡献率%' OR
               question LIKE '%占所属%')
          AND dataset_id = 3
    """)
    
    samples = cur.fetchall()
    print(f"  找到 {len(samples)} 条相关样本")
    
    # 2. 用正确的模板重新生成 SQL
    print("\n[2/3] 重新生成正确 SQL ...")
    
    # 正确的 SQL 模板（标量子查询方式）
    def gen_representative_sql(node_name):
        """代表处占分公司比例"""
        return f"""WITH node_data AS (
    SELECT 
        代表处 AS 节点名称,
        分公司 AS 上级分公司,
        SUM(年度开单金额) AS 本节点开单
    FROM v_angel_group_data
    WHERE 层级级别 = '代表处' AND 代表处 = '{node_name}'
    GROUP BY 代表处, 分公司
)
SELECT 
    n.节点名称,
    n.上级分公司 AS 所属分公司,
    n.本节点开单,
    (SELECT SUM(年度开单金额) 
     FROM v_angel_group_data 
     WHERE 层级级别 = '分公司' AND 分公司 = n.上级分公司) AS 分公司总开单,
    ROUND(n.本节点开单 * 100.0 / NULLIF((SELECT SUM(年度开单金额) 
     FROM v_angel_group_data 
     WHERE 层级级别 = '分公司' AND 分公司 = n.上级分公司), 0), 2) AS 占比_百分比
FROM node_data n"""
    
    def gen_manager_sql(manager_name):
        """业务经理占代表处比例"""
        return f"""WITH node_data AS (
    SELECT 
        业务代表 AS 节点名称,
        代表处 AS 上级代表处,
        SUM(年度开单金额) AS 本节点开单
    FROM v_angel_group_data
    WHERE 层级级别 = '业务经理' AND 业务代表 = '{manager_name}'
    GROUP BY 业务代表, 代表处
)
SELECT 
    n.节点名称,
    n.上级代表处,
    n.本节点开单,
    (SELECT SUM(年度开单金额) 
     FROM v_angel_group_data 
     WHERE 层级级别 = '代表处' AND 代表处 = n.上级代表处) AS 代表处总开单,
    ROUND(n.本节点开单 * 100.0 / NULLIF((SELECT SUM(年度开单金额) 
     FROM v_angel_group_data 
     WHERE 层级级别 = '代表处' AND 代表处 = n.上级代表处), 0), 2) AS 占比_百分比
FROM node_data n"""
    
    def gen_all_managers_sql(representative_name):
        """代表处内所有业务经理占比"""
        return f"""SELECT 
    业务代表,
    SUM(年度开单金额) AS 个人开单,
    (SELECT SUM(年度开单金额) 
     FROM v_angel_group_data 
     WHERE 层级级别 = '代表处' AND 代表处 = '{representative_name}') AS 代表处总开单,
    ROUND(SUM(年度开单金额) * 100.0 / NULLIF((SELECT SUM(年度开单金额) 
     FROM v_angel_group_data 
     WHERE 层级级别 = '代表处' AND 代表处 = '{representative_name}'), 0), 2) AS 占代表处比例
FROM v_angel_group_data
WHERE 层级级别 = '业务经理' AND 代表处 = '{representative_name}'
GROUP BY 业务代表
ORDER BY 个人开单 DESC"""
    
    updated = 0
    for sid, question, sql, intent_type, tags in samples:
        # 分析样本类型和参数
        question_lower = question.lower()
        
        if "代表处" in question and "分公司" in question:
            # 代表处占分公司
            import re
            match = re.search(r"占(.+?)代表处", question)
            if not match:
                match = re.search(r"(.+?)代表处", question)
            if match:
                node_name = match.group(1) + "代表处"
                if "重庆" in question:
                    node_name = "重庆代表处"
                elif "上海" in question:
                    node_name = "上海代表处"
                new_sql = gen_representative_sql(node_name)
            else:
                continue
        elif "业务经理" in question or "业务代表" in question:
            if "分别" in question or "所有" in question or "3位" in question:
                # 代表处内所有业务经理
                rep_match = re.search(r"(.+?)代表处", question)
                if rep_match:
                    rep_name = rep_match.group(1) + "代表处"
                    if "重庆" in question:
                        rep_name = "重庆代表处"
                    elif "上海" in question:
                        rep_name = "上海代表处"
                    new_sql = gen_all_managers_sql(rep_name)
                else:
                    continue
            else:
                # 单个业务经理
                match = re.search(r"(.+?)占", question)
                if match:
                    manager_name = match.group(1).strip()
                    new_sql = gen_manager_sql(manager_name)
                else:
                    continue
        else:
            continue
        
        # 更新
        cur.execute("""
            UPDATE bs_golden_sql_samples
            SET sql_text = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (new_sql, sid))
        updated += 1
        print(f"  [更新] id={sid}: {question[:40]}")
    
    conn.commit()
    print(f"  更新完成：{updated} 条")
    
    # 3. 验证所有修复的 SQL
    print("\n[3/3] 验证修复结果 ...")
    
    cur.execute("""
        SELECT id, question, sql_text
        FROM bs_golden_sql_samples
        WHERE is_active = TRUE
          AND (tags::text LIKE '%贡献率%' OR 
               tags::text LIKE '%占比%')
          AND dataset_id = 3
        ORDER BY id DESC
        LIMIT 10
    """)
    
    for sid, question, sql in cur.fetchall():
        try:
            test_conn = psycopg2.connect(DB)
            test_cur = test_conn.cursor()
            test_cur.execute(sql)
            result = test_cur.fetchall()
            row_count = len(result)
            test_cur.close()
            test_conn.close()
            
            # 检查结果行数
            if "3位" in question or "分别" in question or "所有" in question:
                # 多结果是正常的
                print(f"  ✅ [{sid}] {question[:35]}: {row_count} 行 (预期多行)")
                if result:
                    print(f"     结果: {result[0]}")
            elif row_count == 1:
                print(f"  ✅ [{sid}] {question[:35]}: {result}")
            else:
                print(f"  ⚠️ [{sid}] {question[:35]}: 返回 {row_count} 行 (预期单行)")
                print(f"     {result[:2]}")
                
        except Exception as e:
            print(f"  ❌ [{sid}] {question[:35]}: {str(e)[:100]}")
    
    cur.close()
    conn.close()
    
    print("\n✅ 二次修复完成！")


if __name__ == "__main__":
    main()
