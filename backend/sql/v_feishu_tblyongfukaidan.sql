-- v_feishu_tblyongfukaidan 视图定义存档（2026-09-06 修订）
-- 修订内容：其他业务口径——"其它"/"网销商"的层级级别输出为"其他业务"而非"分公司"，
-- 使报告统计分公司=13 个真实分公司（网销商/其它为用服的其他业务，不算分公司，2026-09-06 用户拍板）。
-- 原始表 feishu_tblyongfukaidan 不动；分公司字段的"用户服务与运营"后缀冗余由本视图 replace 剥离。
-- 本视图为手工创建（不在 feishu 同步逻辑内，不会被重建覆盖）；如重建环境按本文件执行。

CREATE OR REPLACE VIEW v_feishu_tblyongfukaidan AS
SELECT id,
  record_id,
  fields ->> '状态'::text AS "审批状态",
  fields ->> '编号'::text AS "编号",
  CASE WHEN fields ->> '分公司'::text IN ('其它'::text, '网销商'::text)
       THEN '其他业务'::text
       ELSE fields ->> '层级级别'::text END AS "层级级别",
  fields ->> '事业部'::text AS "事业部",
  NULLIF(replace(fields ->> '分公司'::text, '用户服务与运营'::text, ''::text), ''::text) AS "分公司",
  fields ->> '链接字段(勿删)'::text AS "组织路径",
  NULLIF(TRIM(BOTH FROM fields ->> '年度开单金额(滤芯+产品配件) （万）'::text), ''::text)::numeric AS "年度开单金额_滤芯产品配件_万",
  NULLIF(TRIM(BOTH FROM fields ->> '年度开单金额(增值配件+服务关联品) （万）'::text), ''::text)::numeric AS "年度开单金额_增值配件服务关联品_万",
  NULLIF(TRIM(BOTH FROM fields ->> '年度开单总额（万）'::text), ''::text)::numeric AS "年度开单总额_万",
  NULLIF(TRIM(BOTH FROM fields ->> '总任务（万）'::text), ''::text)::numeric AS "总任务_万",
  round(NULLIF(TRIM(BOTH FROM fields ->> '年度开单总额（万）'::text), ''::text)::numeric / NULLIF(NULLIF(TRIM(BOTH FROM fields ->> '总任务（万）'::text), ''::text)::numeric, 0::numeric) * 100::numeric, 1) AS "总任务达成率_百分比",
  NULLIF(TRIM(BOTH FROM fields ->> '本月开单总金额（万）'::text), ''::text)::numeric AS "本月开单总额_万",
  NULLIF(TRIM(BOTH FROM fields ->> '本月总目标（万）'::text), ''::text)::numeric AS "本月总目标_万",
  fields ->> '当前年'::text AS "当前年",
  fields ->> '当前月'::text AS "当前月"
FROM feishu_tblyongfukaidan
WHERE fields IS NOT NULL AND fields <> '{}'::jsonb
  AND NULLIF(fields ->> '编号'::text, ''::text) IS NOT NULL
  AND COALESCE(fields ->> '分公司'::text, '') NOT IN ('其它', '网销商');
