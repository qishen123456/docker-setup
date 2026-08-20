-- =========================================================================
-- 20260820: 全量标准视图初始化与升级 (包含商用事业部 v_angel_group_data 等)
-- =========================================================================

-- 1. 商用事业部基础表与标准增强视图
CREATE TABLE IF NOT EXISTS public.angel_group_data (
    id BIGSERIAL PRIMARY KEY,
    record_id TEXT UNIQUE,
    fields JSONB DEFAULT '{}'::jsonb,
    sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_angel_group_data_record_id ON public.angel_group_data(record_id);
CREATE INDEX IF NOT EXISTS idx_angel_group_data_sync_time ON public.angel_group_data(sync_time);

CREATE OR REPLACE VIEW public.v_angel_group_data AS
WITH base AS (
    SELECT 
        angel_group_data.id,
        angel_group_data.record_id,
        CASE
            WHEN jsonb_typeof(angel_group_data.fields -> '事业部') = 'array' THEN ((angel_group_data.fields -> '事业部') -> 0) ->> 'text'
            ELSE angel_group_data.fields ->> '事业部'
        END AS "事业部",
        CASE
            WHEN jsonb_typeof(angel_group_data.fields -> '分公司') = 'array' THEN ((angel_group_data.fields -> '分公司') -> 0) ->> 'text'
            ELSE angel_group_data.fields ->> '分公司'
        END AS "分公司",
        CASE
            WHEN jsonb_typeof(angel_group_data.fields -> '代表处') = 'array' THEN ((angel_group_data.fields -> '代表处') -> 0) ->> 'text'
            ELSE angel_group_data.fields ->> '代表处'
        END AS "代表处",
        CASE
            WHEN jsonb_typeof(angel_group_data.fields -> '业务代表') = 'array' THEN ((angel_group_data.fields -> '业务代表') -> 0) ->> 'text'
            ELSE angel_group_data.fields ->> '业务代表'
        END AS "业务代表",
        COALESCE(NULLIF(regexp_replace(
            CASE
                WHEN jsonb_typeof(angel_group_data.fields -> '总任务（金额）') = 'array' THEN ((angel_group_data.fields -> '总任务（金额）') -> 0) ->> 'text'
                ELSE angel_group_data.fields ->> '总任务（金额）'
            END, '[^0-9.-]', '', 'g'), ''), '0')::numeric AS "年度目标营收",
        COALESCE(NULLIF(regexp_replace(
            CASE
                WHEN jsonb_typeof(angel_group_data.fields -> '年度开单金额') = 'array' THEN ((angel_group_data.fields -> '年度开单金额') -> 0) ->> 'text'
                ELSE angel_group_data.fields ->> '年度开单金额'
            END, '[^0-9.-]', '', 'g'), ''), '0')::numeric AS "年度开单金额",
        COALESCE(NULLIF(regexp_replace(
            CASE
                WHEN jsonb_typeof(angel_group_data.fields -> '总任务达成率') = 'array' THEN ((angel_group_data.fields -> '总任务达成率') -> 0) ->> 'text'
                ELSE angel_group_data.fields ->> '总任务达成率'
            END, '[^0-9.-]', '', 'g'), ''), '0')::numeric AS "总任务达成率",
        CASE
            WHEN jsonb_typeof(angel_group_data.fields -> '当前年') = 'array' THEN ((angel_group_data.fields -> '当前年') -> 0) ->> 'text'
            ELSE angel_group_data.fields ->> '当前年'
        END AS "当前年",
        angel_group_data.fields
    FROM public.angel_group_data
)
SELECT 
    id,
    record_id,
    CASE
        WHEN "分公司" LIKE '%分公司' THEN '区域条线'
        WHEN "分公司" LIKE '%业务部' THEN '行业条线'
        ELSE '全事业部'
    END AS "条线",
    CASE
        WHEN "业务代表" IS NOT NULL AND "业务代表" <> '' THEN '业务代表'
        WHEN "代表处" IS NOT NULL AND "代表处" <> '' THEN '代表处'
        WHEN "分公司" IS NOT NULL AND "分公司" <> '' THEN
            CASE WHEN "分公司" LIKE '%分公司' THEN '分公司' ELSE '业务部' END
        ELSE '事业部'
    END AS "层级级别",
    COALESCE(NULLIF("业务代表", ''), NULLIF("代表处", ''), NULLIF("分公司", ''), '商用事业部') AS "节点名称",
    CASE
        WHEN "业务代表" IS NOT NULL AND "业务代表" <> '' THEN "代表处"
        WHEN "代表处" IS NOT NULL AND "代表处" <> '' THEN "分公司"
        WHEN "分公司" IS NOT NULL AND "分公司" <> '' THEN '商用事业部'
        ELSE NULL
    END AS "上级名称",
    "事业部",
    "分公司",
    "代表处",
    COALESCE(NULLIF("业务代表", ''), fields ->> '总任务承接人', COALESCE(NULLIF("代表处", ''), NULLIF("分公司", ''), '商用事业部')) AS "业务代表",
    COALESCE(NULLIF("业务代表", ''), fields ->> '总任务承接人', COALESCE(NULLIF("代表处", ''), NULLIF("分公司", ''), '商用事业部')) AS "负责人",
    "年度目标营收",
    "年度开单金额",
    "总任务达成率",
    "当前年",
    concat(COALESCE("代表处", ''), ' ', COALESCE("分公司", ''), ' ',
        CASE
            WHEN "代表处" LIKE '%粤东%' THEN '广州 深圳 东莞 佛山 粤东'
            WHEN "代表处" LIKE '%粤西%' THEN '粤西 南宁 广西 海南'
            WHEN "代表处" LIKE '%江苏%' THEN '南京 江苏 苏州'
            WHEN "代表处" LIKE '%浙江%' THEN '杭州 浙江 宁波'
            WHEN "代表处" LIKE '%安徽%' THEN '合肥 安徽'
            WHEN "代表处" LIKE '%湖北%' THEN '武汉 湖北'
            WHEN "代表处" LIKE '%湖南%' THEN '长沙 湖南'
            WHEN "代表处" LIKE '%江西%' THEN '南昌 江西'
            WHEN "代表处" LIKE '%四川%' THEN '成都 四川'
            WHEN "代表处" LIKE '%重庆%' THEN '重庆'
            WHEN "代表处" LIKE '%云贵%' THEN '昆明 贵阳 云南 贵州'
            WHEN "代表处" LIKE '%福建%' THEN '福建 福州 厦门'
            WHEN "代表处" LIKE '%上海%' THEN '上海'
            WHEN "代表处" LIKE '%北京%' THEN '北京'
            WHEN "代表处" LIKE '%辽宁%' THEN '辽宁 沈阳'
            WHEN "代表处" LIKE '%陕西%' THEN '陕西 西安'
            WHEN "代表处" LIKE '%山东%' THEN '山东 济南 青岛'
            WHEN "代表处" LIKE '%河南%' THEN '河南 郑州'
            ELSE ''
        END) AS "城市标签",
    fields
FROM base;

-- 2. 同步更新 bs_schema_definitions 里的标准视图 DDL
INSERT INTO public.bs_schema_definitions (dataset_id, table_name, ddl_sql, description, is_active)
SELECT d.id, 'v_angel_group_data', 'CREATE OR REPLACE VIEW v_angel_group_data AS ...', '商用事业部标准增强视图(含条线与节点名称)', true
FROM public.bs_datasets d
WHERE d.dataset_name LIKE '%商用%' OR d.dataset_code LIKE '%syyb%' OR d.id = 3
ON CONFLICT (dataset_id, table_name) DO UPDATE 
SET is_active = true, updated_at = NOW();
