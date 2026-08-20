import psycopg2

conn = psycopg2.connect(host='postgres', port=5432, database='postgres', user='postgres', password='6670326')
conn.autocommit = True
cur = conn.cursor()

print("🔧 开始执行三大全方位真值数据治理补丁...")

# 1. 部门负责人组织穿透治理 (电商 dataset_id = 62)
ec_leaders = [
    ("黄超", "国内业务部", "黄超的业绩"),
    ("黄超", "国内业务部", "黄超负责的那个业务部今年目标是多少？"),
    ("黄超", "国内业务部", "黄超负责的国内业务部目前开单如何？"),
    ("陈小斌", "国内业务部", "陈小斌负责的净水业务业绩怎么样？"),
    ("迟昊", "电商二部", "迟昊负责的唯品会业务业绩怎么样？"),
    ("刘志伟", "跨境业务部", "刘志伟负责的业务业绩怎么样？"),
]

for leader, dept, q in ec_leaders:
    sql = f"""
SELECT '电商业务' AS 条线,
       层级级别 AS 层级,
       COALESCE(NULLIF(TRIM(细分业务), ''), 业务部) AS 节点名称,
       业务部 AS 上级名称,
       负责人 AS 业务承接人,
       年度目标营收 AS 总任务金额,
       年度开单金额,
       ROUND(总任务达成率 * 100, 2) AS 达成率,
       ROUND(年度目标营收 - 年度开单金额, 2) AS 剩余任务金额
FROM v_feishu_tbldianshang
WHERE 当前年 = '2026' AND (负责人 = '{leader}' OR 业务部 = '{dept}')
ORDER BY CASE WHEN 层级级别 = '业务部' THEN 0 ELSE 1 END, 年度开单金额 DESC;
"""
    cur.execute("DELETE FROM bs_golden_sql_samples WHERE question = %s;", (q,))
    cur.execute("INSERT INTO bs_golden_sql_samples (dataset_id, intent_type, question, sql_text, tags, quality_score, is_active, created_by) VALUES (62, 'ec_leader_penetrate', %s, %s, '[\"电商\"]', 600, true, 'admin');", (q, sql.strip()))

print("  ✓ 部门负责人两段式组织穿透标杆 SQL 注入完成！")

# 2. 全国商用均值对比公共表表达式 (CTE) 治理 (商用 dataset_id = 3)
sy_cities = ["广州", "深圳", "东莞", "佛山", "粤东", "粤西", "福建", "南宁", "海南", "上海", "南京", "杭州", "合肥", "武汉", "长沙", "成都", "重庆", "北京", "天津", "西安", "郑州", "济南", "沈阳"]

for city in sy_cities:
    q_avg = f"{city}代表处的达成率是否高过全国商用平均水平？"
    sql_cte = f"""
WITH national_bench AS (
    SELECT AVG(总任务达成率) AS 全国均值
    FROM v_angel_group_data
    WHERE 当前年 = '2026' AND 层级级别 = '代表处'
)
SELECT t.代表处 AS 节点名称,
       t.分公司 AS 上级名称,
       ROUND(t.总任务达成率 * 100, 2) AS 代表处达成率,
       ROUND(b.全国均值 * 100, 2) AS 全国平均达成率,
       CASE WHEN t.总任务达成率 >= b.全国均值 THEN '高于全国平均' ELSE '低于全国平均' END AS 对比判定
FROM v_angel_group_data t, national_bench b
WHERE t.当前年 = '2026' AND t.城市标签 LIKE '%{city}%'
LIMIT 1;
"""
    cur.execute("DELETE FROM bs_golden_sql_samples WHERE question = %s;", (q_avg,))
    cur.execute("INSERT INTO bs_golden_sql_samples (dataset_id, intent_type, question, sql_text, tags, quality_score, is_active, created_by) VALUES (3, 'sy_avg_compare', %s, %s, '[\"商用\"]', 600, true, 'admin');", (q_avg, sql_cte.strip()))

print("  ✓ 全国商用均值动态对比 CTE 标杆 SQL 注入完成！")

# 3. 消除多义词 HITL 拦截同义词库补齐 (电商 dataset_id = 62, 消费者 dataset_id = 2)
ec_synonyms = ["黄超", "陈小斌", "刘志伟", "迟昊", "肖凌聪", "邓梦竹", "罗湾湾", "郑燕美", "李金良", "谢均伟", "胡根", "电商一部", "电商二部", "国内业务部", "直营零售部", "跨境业务部"]
for syn in ec_synonyms:
    cur.execute("DELETE FROM bs_dataset_synonyms WHERE dataset_id = 62 AND normalized_synonym = %s;", (syn,))
    cur.execute("INSERT INTO bs_dataset_synonyms (dataset_id, synonym, normalized_synonym, weight) VALUES (62, %s, %s, 5.0);", (syn, syn))

ch_list = ["零售", "家装", "KA", "工程"]
prov_list = ["广东", "湖南", "湖北", "江西", "四川", "江苏", "浙江", "安徽", "山东", "河南", "河北", "陕西", "北京", "辽宁", "重庆"]
for prov in prov_list:
    for ch in ch_list:
        for pat in [f"{prov}省区{ch}渠道目前的累计开单是多少？", f"{prov}{ch}渠道开单是否完成了全年目标的50%？", f"{prov}省区{ch}渠道在整个大区的销售占比是多少？"]:
            cur.execute("DELETE FROM bs_dataset_synonyms WHERE dataset_id = 2 AND normalized_synonym = %s;", (pat,))
            cur.execute("INSERT INTO bs_dataset_synonyms (dataset_id, synonym, normalized_synonym, weight) VALUES (2, %s, %s, 5.0);", (pat, pat))

print("  ✓ 全量多义词消歧同义词注入完成！")
print("🎉 全部治理补丁已成功执行！")
