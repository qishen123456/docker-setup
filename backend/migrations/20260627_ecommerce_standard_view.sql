CREATE OR REPLACE VIEW public.v_feishu_tbldianshang AS
WITH extracted AS (
  SELECT
    id,
    record_id,
    fields,
    fields->>'状态' AS 审批状态,
    fields->>'编号' AS 编号,
    fields->>'经营主体' AS 集团,
    fields->>'事业部' AS 事业部,
    NULLIF(fields->>'业务部', '') AS 业务部,
    COALESCE(NULLIF(fields->>'业务承接角色', ''), NULLIF(fields->>'细分业务', '')) AS 细分业务,
    fields->>'层级级别' AS 层级级别,
    fields->>'任务承接人' AS 负责人,
    fields->>'任务维护人' AS 上级负责人,
    fields->>'链接字段(勿删)' AS 组织路径,
    fields->>'当前年' AS 当前年,
    fields->>'当前月' AS 当前月
  FROM public.feishu_tbldianshang
  WHERE fields IS NOT NULL
    AND fields <> '{}'::jsonb
    AND NULLIF(fields->>'编号', '') IS NOT NULL
)
SELECT
  id,
  record_id,
  审批状态,
  编号,
  集团,
  事业部,
  业务部,
  细分业务,
  层级级别,
  负责人,
  上级负责人,
  COALESCE(NULLIF(regexp_replace(fields->>'总任务（金额）', '[^0-9.-]', '', 'g'), ''), '0')::numeric AS 年度目标营收,
  COALESCE(NULLIF(regexp_replace(fields->>'年度开单金额', '[^0-9.-]', '', 'g'), ''), '0')::numeric AS 年度开单金额,
  COALESCE(NULLIF(regexp_replace(fields->>'总任务达成率', '[^0-9.-]', '', 'g'), ''), '0')::numeric AS 总任务达成率,
  COALESCE(NULLIF(regexp_replace(fields->>'当前月份任务达成率', '[^0-9.-]', '', 'g'), ''), '0')::numeric AS 当前月份任务达成率,
  COALESCE(NULLIF(regexp_replace(fields->>'截止当前目标阈值达成率', '[^0-9.-]', '', 'g'), ''), '0')::numeric AS 截止当前目标阈值达成率,
  COALESCE(NULLIF(regexp_replace(fields->>'本月开单金额', '[^0-9.-]', '', 'g'), ''), '0')::numeric AS 本月开单金额,
  COALESCE(NULLIF(regexp_replace(fields->>'本月当前目标阈值', '[^0-9.-]', '', 'g'), ''), '0')::numeric AS 本月当前目标阈值,
  COALESCE(NULLIF(regexp_replace(fields->>'年度阈值/开单差额（万）', '[^0-9.-]', '', 'g'), ''), '0')::numeric AS 年度阈值开单差额万,
  COALESCE(NULLIF(regexp_replace(fields->>'月度阈值/开单差额（万）', '[^0-9.-]', '', 'g'), ''), '0')::numeric AS 月度阈值开单差额万,
  COALESCE(NULLIF(regexp_replace(fields->>'总金额转换（以万为单位）', '[^0-9.-]', '', 'g'), ''), '0')::numeric AS 总金额转换万,
  COALESCE(NULLIF(regexp_replace(fields->>'年度开单金额转换（以万为单位）', '[^0-9.-]', '', 'g'), ''), '0')::numeric AS 年度开单金额转换万,
  组织路径,
  当前年,
  当前月,
  COALESCE(NULLIF(regexp_replace(fields->>'2601', '[^0-9.-]', '', 'g'), ''), '0')::numeric AS q1目标,
  COALESCE(NULLIF(regexp_replace(fields->>'2602', '[^0-9.-]', '', 'g'), ''), '0')::numeric AS q2目标,
  COALESCE(NULLIF(regexp_replace(fields->>'2603', '[^0-9.-]', '', 'g'), ''), '0')::numeric AS q3目标,
  COALESCE(NULLIF(regexp_replace(fields->>'2604', '[^0-9.-]', '', 'g'), ''), '0')::numeric AS q4目标
FROM extracted;
