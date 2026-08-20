import psycopg2

conn = psycopg2.connect(host='postgres', port=5432, database='postgres', user='postgres', password='6670326')
cur = conn.cursor()

cur.execute("DROP VIEW IF EXISTS v_angel_group_data CASCADE;")
cur.execute('''
CREATE VIEW v_angel_group_data AS
WITH base AS (
    SELECT id, record_id,
        CASE WHEN jsonb_typeof(fields->'事业部') = 'array' THEN fields->'事业部'->0->>'text' ELSE fields->>'事业部' END AS 事业部,
        CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END AS 分公司,
        CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END AS 代表处,
        CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END AS 业务代表,
        COALESCE(NULLIF(regexp_replace(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 年度目标营收,
        COALESCE(NULLIF(regexp_replace(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 年度开单金额,
        COALESCE(NULLIF(regexp_replace(CASE WHEN jsonb_typeof(fields->'总任务达成率') = 'array' THEN fields->'总任务达成率'->0->>'text' ELSE fields->>'总任务达成率' END, '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 总任务达成率,
        CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END AS 当前年,
        fields
    FROM angel_group_data
)
SELECT 
    id, record_id,
    CASE 
        WHEN 分公司 LIKE '%分公司' THEN '区域条线'
        WHEN 分公司 LIKE '%业务部' THEN '行业条线'
        ELSE '全事业部'
    END AS 条线,
    CASE 
        WHEN 业务代表 IS NOT NULL AND 业务代表 <> '' THEN '业务代表'
        WHEN 代表处 IS NOT NULL AND 代表处 <> '' THEN '代表处'
        WHEN 分公司 IS NOT NULL AND 分公司 <> '' THEN (CASE WHEN 分公司 LIKE '%分公司' THEN '分公司' ELSE '业务部' END)
        ELSE '事业部'
    END AS 层级级别,
    COALESCE(NULLIF(业务代表, ''), NULLIF(代表处, ''), NULLIF(分公司, ''), '商用事业部') AS 节点名称,
    CASE 
        WHEN 业务代表 IS NOT NULL AND 业务代表 <> '' THEN 代表处
        WHEN 代表处 IS NOT NULL AND 代表处 <> '' THEN 分公司
        WHEN 分公司 IS NOT NULL AND 分公司 <> '' THEN '商用事业部'
        ELSE NULL
    END AS 上级名称,
    事业部, 分公司, 代表处, 
    COALESCE(NULLIF(业务代表, ''), fields->>'总任务承接人', COALESCE(NULLIF(代表处, ''), NULLIF(分公司, ''), '商用事业部')) AS 业务代表,
    COALESCE(NULLIF(业务代表, ''), fields->>'总任务承接人', COALESCE(NULLIF(代表处, ''), NULLIF(分公司, ''), '商用事业部')) AS 负责人,
    年度目标营收, 年度开单金额, 总任务达成率, 当前年,
    -- 智能构造商用城市与代表处映射标签
    CONCAT(
        COALESCE(代表处, ''), ' ', COALESCE(分公司, ''), ' ',
        CASE 
            WHEN 代表处 LIKE '%粤东%' THEN '广州 深圳 东莞 佛山 粤东'
            WHEN 代表处 LIKE '%粤西%' THEN '粤西 南宁 广西 海南'
            WHEN 代表处 LIKE '%江苏%' THEN '南京 江苏 苏州'
            WHEN 代表处 LIKE '%浙江%' THEN '杭州 浙江 宁波'
            WHEN 代表处 LIKE '%安徽%' THEN '合肥 安徽'
            WHEN 代表处 LIKE '%湖北%' THEN '武汉 湖北'
            WHEN 代表处 LIKE '%湖南%' THEN '长沙 湖南'
            WHEN 代表处 LIKE '%江西%' THEN '南昌 江西'
            WHEN 代表处 LIKE '%四川%' THEN '成都 四川'
            WHEN 代表处 LIKE '%重庆%' THEN '重庆'
            WHEN 代表处 LIKE '%云贵%' THEN '昆明 贵阳 云南 贵州'
            WHEN 代表处 LIKE '%福建%' THEN '福建 福州 厦门'
            WHEN 代表处 LIKE '%上海%' THEN '上海'
            WHEN 代表处 LIKE '%北京%' THEN '北京'
            WHEN 代表处 LIKE '%辽宁%' THEN '辽宁 沈阳'
            WHEN 代表处 LIKE '%陕西%' THEN '陕西 西安'
            WHEN 代表处 LIKE '%山东%' THEN '山东 济南 青岛'
            WHEN 代表处 LIKE '%河南%' THEN '河南 郑州'
            ELSE ''
        END
    ) AS 城市标签,
    fields
FROM base;
''')

conn.commit()
print("SUCCESS: 商用带城市别名映射的标准视图重建完成！")
