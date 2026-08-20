import psycopg2

conn = psycopg2.connect(host='postgres', port=5432, database='postgres', user='postgres', password='6670326')
cur = conn.cursor()

cur.execute("DROP VIEW IF EXISTS v_feishu_xiaofeizhe CASCADE;")
cur.execute('''
CREATE VIEW v_feishu_xiaofeizhe AS
WITH base AS (
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
    WHERE fields IS NOT NULL AND fields <> '{}'::jsonb
)
SELECT 
    id, record_id, 事业部, 销售大区, 城市公司, 层级级别, 负责人,
    年度目标营收, 年度开单金额, 总任务达成率,
    线下开单金额, 新零售开单金额, 燃气定制开单金额, 地产开单金额,
    当前年, 当前月,
    -- 智能构造包含别名的省份搜索标签
    CONCAT(
        销售大区, ' ', 城市公司, ' ',
        CASE 
            WHEN 销售大区 LIKE '%粤桂琼%' THEN '广东 广西 海南'
            WHEN 销售大区 LIKE '%豫晋%' THEN '河南 山西'
            WHEN 销售大区 LIKE '%江浙沪%' THEN '江苏 浙江 上海'
            WHEN 销售大区 LIKE '%鄂皖%' THEN '湖北 安徽'
            WHEN 销售大区 LIKE '%川藏%' THEN '四川 西藏'
            WHEN 销售大区 LIKE '%云贵渝%' THEN '云南 贵州 重庆'
            WHEN 销售大区 LIKE '%赣闽%' THEN '江西 福建'
            WHEN 销售大区 LIKE '%黑吉辽%' THEN '辽宁 吉林 黑龙江'
            WHEN 销售大区 LIKE '%西北%' THEN '陕西 甘肃 宁夏'
            WHEN 销售大区 LIKE '%京津%' THEN '北京 天津'
            WHEN 销售大区 LIKE '%山东%' THEN '山东'
            WHEN 销售大区 LIKE '%湖南%' THEN '湖南'
            WHEN 销售大区 LIKE '%河北%' THEN '河北'
            ELSE ''
        END
    ) AS 省份标签,
    fields
FROM base;
''')

conn.commit()
print("SUCCESS: 消费者带省份映射的标准视图重建完成！")
