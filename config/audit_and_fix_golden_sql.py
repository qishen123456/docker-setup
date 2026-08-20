"""Golden SQL 样本审计与修复脚本

目标：
1. 审计所有 Golden SQL 样本中"窗口函数 + WHERE"导致计算口径错误的问题
2. 修复这些样本，改用正确的 SQL 写法
3. 新增正确的"代表处占分公司比例"示例

用法: docker cp 到容器后执行
"""

import sys
import json
sys.path.insert(0, '/app/backend')

import psycopg2

DB = "host=smartask-postgres dbname=postgres user=postgres password=6670326"


def audit_and_fix():
    conn = psycopg2.connect(DB)
    cur = conn.cursor()
    
    print("=" * 60)
    print("🔍 Golden SQL 样本审计与修复")
    print("=" * 60)
    
    # 1. 找出"贡献率/占比"类问题样本
    print("\n[1/4] 审计'贡献率/占比'类样本 ...")
    cur.execute("""
        SELECT id, dataset_id, question, sql_text
        FROM bs_golden_sql_samples
        WHERE is_active = TRUE
          AND (question LIKE '%贡献率%' OR question LIKE '%占比%' 
               OR question LIKE '%占整体%' OR question LIKE '%比重%')
          AND sql_text LIKE '%OVER(PARTITION%'
    """)
    
    problem_samples = []
    for row in cur.fetchall():
        sid, did, question, sql = row
        problem_samples.append((sid, did, question, sql))
        print(f"  [问题] id={sid}: {question[:40]}")
    
    print(f"  发现 {len(problem_samples)} 条疑似问题样本")
    
    # 2. 修复问题样本
    print("\n[2/4] 修复问题样本 ...")
    
    # 定义正确的 SQL 模板
    fix_templates = {
        # 代表处占分公司比例
        "代表处": """
WITH node_data AS (
    SELECT 
        代表处 AS 节点名称,
        分公司 AS 上级名称,
        SUM(年度开单金额) AS 本节点开单
    FROM v_angel_group_data
    WHERE 层级级别 = '代表处' AND 代表处 = '{node_name}'
    GROUP BY 代表处, 分公司
),
parent_data AS (
    SELECT 
        分公司,
        SUM(年度开单金额) AS 分公司开单
    FROM v_angel_group_data
    WHERE 层级级别 = '分公司' AND 分公司 = (SELECT 分公司 FROM node_data LIMIT 1)
    GROUP BY 分公司
)
SELECT 
    n.节点名称,
    n.上级名称 AS 所属分公司,
    n.本节点开单,
    p.分公司开单,
    ROUND(n.本节点开单 * 100.0 / NULLIF(p.分公司开单, 0), 2) AS 占比_百分比
FROM node_data n
CROSS JOIN parent_data p
""".strip(),
        
        # 业务经理占代表处比例
        "业务经理": """
WITH node_data AS (
    SELECT 
        业务代表 AS 节点名称,
        代表处 AS 上级名称,
        SUM(年度开单金额) AS 本节点开单
    FROM v_angel_group_data
    WHERE 层级级别 = '业务经理' AND 业务代表 = '{node_name}'
    GROUP BY 业务代表, 代表处
),
parent_data AS (
    SELECT 
        代表处,
        SUM(年度开单金额) AS 代表处开单
    FROM v_angel_group_data
    WHERE 层级级别 = '代表处' AND 代表处 = (SELECT 代表处 FROM node_data LIMIT 1)
    GROUP BY 代表处
)
SELECT 
    n.节点名称,
    n.上级名称 AS 所属代表处,
    n.本节点开单,
    p.代表处开单,
    ROUND(n.本节点开单 * 100.0 / NULLIF(p.代表处开单, 0), 2) AS 占比_百分比
FROM node_data n
CROSS JOIN parent_data p
""".strip(),
    }
    
    # 执行修复
    fixed_count = 0
    for sid, did, question, sql in problem_samples:
        # 判断问题类型
        if sql.find("代表处") >= 0:
            template_key = "代表处"
        elif sql.find("业务经理") >= 0 or sql.find("业务代表") >= 0:
            template_key = "业务经理"
        else:
            continue
        
        # 从原 SQL 中提取节点名称
        import re
        match = re.search(r"=\s*'([^']+)'", sql)
        if not match:
            continue
        node_name = match.group(1)
        
        # 生成新 SQL
        new_sql = fix_templates[template_key].format(node_name=node_name)
        
        # 更新数据库
        cur.execute("""
            UPDATE bs_golden_sql_samples
            SET sql_text = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (new_sql, sid))
        fixed_count += 1
        print(f"  [修复] id={sid}: {question[:40]}")
    
    conn.commit()
    print(f"  修复完成：{fixed_count} 条")
    
    # 3. 新增正确的示例
    print("\n[3/4] 新增正确示例 ...")
    
    new_samples = [
        {
            "question": "重庆代表处占所属分公司总开单的比例是多少？",
            "sql_text": """WITH node_data AS (
    SELECT 
        代表处 AS 节点名称,
        分公司 AS 上级名称,
        SUM(年度开单金额) AS 本节点开单
    FROM v_angel_group_data
    WHERE 层级级别 = '代表处' AND 代表处 = '重庆代表处'
    GROUP BY 代表处, 分公司
),
parent_data AS (
    SELECT 
        分公司,
        SUM(年度开单金额) AS 分公司开单
    FROM v_angel_group_data
    WHERE 层级级别 = '分公司' AND 分公司 = (SELECT 分公司 FROM node_data LIMIT 1)
    GROUP BY 分公司
)
SELECT 
    n.节点名称,
    n.上级名称 AS 所属分公司,
    n.本节点开单 AS 重庆代表处开单,
    p.分公司开单 AS 西部分公司开单,
    ROUND(n.本节点开单 * 100.0 / NULLIF(p.分公司开单, 0), 2) AS 占比_百分比
FROM node_data n
CROSS JOIN parent_data p""",
            "dataset_id": 3,
            "intent_type": "comparison",
            "tags": json.dumps(["占比", "代表处", "分公司", "贡献率", "层级对比"])
        },
        {
            "question": "重庆代表处的3位业务经理分别占代表处多少比例？",
            "sql_text": """WITH managers AS (
    SELECT 
        业务代表,
        SUM(年度开单金额) AS 个人开单
    FROM v_angel_group_data
    WHERE 层级级别 = '业务经理' AND 代表处 = '重庆代表处'
    GROUP BY 业务代表
),
total AS (
    SELECT SUM(年度开单金额) AS 代表处开单
    FROM v_angel_group_data
    WHERE 层级级别 = '代表处' AND 代表处 = '重庆代表处'
)
SELECT 
    m.业务代表,
    m.个人开单,
    t.代表处开单,
    ROUND(m.个人开单 * 100.0 / NULLIF(t.代表处开单, 0), 2) AS 占重庆代表处比例
FROM managers m
CROSS JOIN total t
ORDER BY m.个人开单 DESC""",
            "dataset_id": 3,
            "intent_type": "comparison",
            "tags": json.dumps(["占比", "业务经理", "代表处", "贡献率", "人员对比"])
        },
        {
            "question": "上海代表处占所属分公司总开单的比例是多少？",
            "sql_text": """WITH node_data AS (
    SELECT 
        代表处 AS 节点名称,
        分公司 AS 上级名称,
        SUM(年度开单金额) AS 本节点开单
    FROM v_angel_group_data
    WHERE 层级级别 = '代表处' AND 代表处 = '上海代表处'
    GROUP BY 代表处, 分公司
),
parent_data AS (
    SELECT 
        分公司,
        SUM(年度开单金额) AS 分公司开单
    FROM v_angel_group_data
    WHERE 层级级别 = '分公司' AND 分公司 = (SELECT 分公司 FROM node_data LIMIT 1)
    GROUP BY 分公司
)
SELECT 
    n.节点名称,
    n.上级名称 AS 所属分公司,
    n.本节点开单,
    p.分公司开单,
    ROUND(n.本节点开单 * 100.0 / NULLIF(p.分公司开单, 0), 2) AS 占比_百分比
FROM node_data n
CROSS JOIN parent_data p""",
            "dataset_id": 3,
            "intent_type": "comparison",
            "tags": json.dumps(["占比", "代表处", "分公司", "贡献率"])
        },
    ]
    
    for s in new_samples:
        cur.execute("""
            INSERT INTO bs_golden_sql_samples 
            (dataset_id, question, sql_text, intent_type, tags, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s::jsonb, TRUE, NOW())
        """, (
            s["dataset_id"],
            s["question"],
            s["sql_text"],
            s["intent_type"],
            s["tags"]
        ))
    conn.commit()
    print(f"  新增 {len(new_samples)} 条正确示例")
    
    # 4. 验证修复效果
    print("\n[4/4] 验证修复效果 ...")
    
    # 执行新 SQL 验证
    for sid, did, question, sql in problem_samples[:2]:  # 只验证前2条
        try:
            test_conn = psycopg2.connect(DB)
            test_cur = test_conn.cursor()
            
            # 获取修复后的 SQL
            cur.execute("SELECT sql_text FROM bs_golden_sql_samples WHERE id = %s", (sid,))
            fixed_sql = cur.fetchone()[0]
            
            test_cur.execute(fixed_sql)
            result = test_cur.fetchall()
            test_cur.close()
            test_conn.close()
            
            print(f"  ✅ [{sid}] {question[:30]}")
            print(f"     结果: {result}")
        except Exception as e:
            print(f"  ❌ [{sid}] {question[:30]}: {str(e)[:80]}")
    
    # 验证新增样本
    print("\n  验证新增示例:")
    for s in new_samples:
        try:
            test_conn = psycopg2.connect(DB)
            test_cur = test_conn.cursor()
            test_cur.execute(s["sql_text"])
            result = test_cur.fetchall()
            test_cur.close()
            test_conn.close()
            print(f"  ✅ {s['question'][:40]}")
            print(f"     {result}")
        except Exception as e:
            print(f"  ❌ {s['question'][:40]}: {str(e)[:80]}")
    
    cur.close()
    conn.close()
    
    print("\n✅ 审计与修复完成！")


if __name__ == "__main__":
    audit_and_fix()
