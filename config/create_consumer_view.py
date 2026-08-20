import psycopg2

conn = psycopg2.connect(host='postgres', port=5432, database='postgres', user='postgres', password='6670326')
cur = conn.cursor()

cur.execute("DROP VIEW IF EXISTS v_feishu_xiaofeizhe CASCADE;")
cur.execute('''
CREATE VIEW v_feishu_xiaofeizhe AS
SELECT 
    id,
    record_id,
    fields->>'事业部' AS 事业部,
    COALESCE(NULLIF(fields->>'分公司', ''), split_part(fields->>'链接字段(勿删)', ';', 2)) AS 销售大区,
    COALESCE(NULLIF(fields->>'城市公司', ''), split_part(fields->>'链接字段(勿删)', ';', 3)) AS 城市公司,
    fields->>'层级级别' AS 层级级别,
    fields->>'总任务承接人' AS 负责人,
    NULLIF(TRIM(fields->>'总任务（金额）'), '')::numeric AS 年度目标营收,
    NULLIF(TRIM(fields->>'年度开单金额'), '')::numeric AS 年度开单金额,
    NULLIF(TRIM(fields->>'总任务达成率'), '')::numeric AS 总任务达成率,
    NULLIF(TRIM(fields->>'线下-年度开单金额'), '')::numeric AS 线下开单金额,
    NULLIF(TRIM(fields->>'新零售-年度开单金额'), '')::numeric AS 新零售开单金额,
    NULLIF(TRIM(fields->>'燃气定制-年度开单金额'), '')::numeric AS 燃气定制开单金额,
    NULLIF(TRIM(fields->>'地产-年度开单金额'), '')::numeric AS 地产开单金额,
    fields->>'当前年' AS 当前年,
    fields->>'当前月' AS 当前月,
    fields
FROM feishu_tbl_xioafeizhe
WHERE fields IS NOT NULL AND fields <> '{}'::jsonb;
''')

conn.commit()
print("SUCCESS: 消费者标准视图 v_feishu_xiaofeizhe 创建成功！")
