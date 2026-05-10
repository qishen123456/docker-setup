-- 报告配置解耦：bs_dataset_report_config 表
-- 每个数据集可选配一份报告配置，驱动 Agent4 输出格式和前端报告渲染

CREATE TABLE IF NOT EXISTS bs_dataset_report_config (
    id          BIGSERIAL PRIMARY KEY,
    dataset_id  BIGINT NOT NULL REFERENCES bs_datasets(id) ON DELETE CASCADE,
    config_json JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(dataset_id)
);

CREATE INDEX IF NOT EXISTS idx_report_config_dataset ON bs_dataset_report_config(dataset_id);

-- 为 syyb (angel_business_2026) 数据集插入默认配置
INSERT INTO bs_dataset_report_config (dataset_id, config_json)
SELECT id, '{
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
    {"key": "rate", "op": ">=", "value": 15, "tone": "good",  "label": "标杆"},
    {"key": "rate", "op": ">=", "value": 10, "tone": "warn",  "label": "中等"},
    {"key": "rate", "op": "<",  "value": 10, "tone": "danger","label": "风险"}
  ],
  "sections": ["core", "group", "risk", "strategy"],
  "reportTitle": "经营分析报告"
}'::jsonb
FROM bs_datasets
WHERE dataset_code IN ('angel_business_2026', 'angel_business_2026_phase1')
   OR dataset_name LIKE '%商用事业部%'
ON CONFLICT (dataset_id) DO NOTHING;
