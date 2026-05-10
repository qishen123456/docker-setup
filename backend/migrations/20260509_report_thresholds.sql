-- 报告阈值优化：适配当前商用事业部低达成率阶段的红黄绿分层
-- 代表处：<10% 风险，10%-15% 中等，>=15% 标杆
-- 业务代表：<10% 风险，10%-20% 中等，>=20% 标杆

INSERT INTO bs_dataset_report_config (dataset_id, config_json)
SELECT dataset.id, '{
  "nameColumn": "节点名称",
  "parentColumn": "上级名称",
  "trackColumn": "条线",
  "levelColumn": "层级",
  "metrics": [
    {"key": "task",   "label": "总任务金额",   "column": "总任务金额",  "format": "amount"},
    {"key": "actual", "label": "年度开单金额", "column": "年度开单金额", "format": "amount"},
    {"key": "rate",   "label": "达成率",       "column": "达成率",       "format": "percent"},
    {"key": "remain", "label": "剩余任务金额", "column": "剩余任务金额", "format": "amount"}
  ],
  "levels": [
    {"name": "机构层", "values": ["代表处", "分公司", "业务部"]},
    {"name": "个人层", "values": ["业务代表", "业务员", "业务"]}
  ],
  "trackValues": {"org": "区域条线", "personal": "行业条线"},
  "riskThreshold": 10,
  "officeRiskThreshold": 10,
  "officeBenchmarkThreshold": 15,
  "personRiskThreshold": 10,
  "personBenchmarkThreshold": 20,
  "signalRules": [
    {"key": "rate", "op": ">=", "value": 15, "tone": "good", "label": "标杆"},
    {"key": "rate", "op": ">=", "value": 10, "tone": "warn", "label": "中等"},
    {"key": "rate", "op": "<",  "value": 10, "tone": "danger", "label": "风险"}
  ],
  "sections": ["core", "group", "risk", "strategy"],
  "reportTitle": "经营分析报告"
}'::jsonb
FROM bs_datasets AS dataset
WHERE dataset.dataset_code IN ('angel_business_2026', 'angel_business_2026_phase1')
   OR dataset.dataset_name LIKE '%商用事业部%'
ON CONFLICT (dataset_id) DO NOTHING;

UPDATE bs_dataset_report_config AS config
SET
    config_json = config.config_json || '{
      "riskThreshold": 10,
      "officeRiskThreshold": 10,
      "officeBenchmarkThreshold": 15,
      "personRiskThreshold": 10,
      "personBenchmarkThreshold": 20,
      "signalRules": [
        {"key": "rate", "op": ">=", "value": 15, "tone": "good", "label": "标杆"},
        {"key": "rate", "op": ">=", "value": 10, "tone": "warn", "label": "中等"},
        {"key": "rate", "op": "<",  "value": 10, "tone": "danger", "label": "风险"}
      ]
    }'::jsonb,
    updated_at = NOW()
FROM bs_datasets AS dataset
WHERE config.dataset_id = dataset.id
  AND (
    dataset.dataset_code IN ('angel_business_2026', 'angel_business_2026_phase1')
    OR dataset.dataset_name LIKE '%商用事业部%'
  );
