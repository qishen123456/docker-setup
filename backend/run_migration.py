"""Run migration: create bs_dataset_report_config + insert syyb defaults."""
import psycopg2
from psycopg2.extras import Json

conn = psycopg2.connect(host='localhost', port=5432, database='postgres', user='postgres', password='6670326')
cur = conn.cursor()

# Create table
cur.execute("""
CREATE TABLE IF NOT EXISTS bs_dataset_report_config (
    id          BIGSERIAL PRIMARY KEY,
    dataset_id  BIGINT NOT NULL,
    config_json JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(dataset_id)
);
""")
cur.execute("CREATE INDEX IF NOT EXISTS idx_report_config_dataset ON bs_dataset_report_config(dataset_id);")
conn.commit()
print("Table created OK")

# Find all datasets
cur.execute("SELECT id, dataset_code, dataset_name FROM bs_datasets")
rows = cur.fetchall()
print(f"Total datasets: {len(rows)}")
for r in rows:
    print(f"  id={r[0]} code={r[1]} name={r[2]}")

# Find syyb datasets
cur.execute("SELECT id, dataset_code, dataset_name FROM bs_datasets WHERE dataset_code LIKE '%%angel%%' OR dataset_name LIKE '%%商用%%' OR dataset_code LIKE '%%syyb%%'")
syyb_rows = cur.fetchall()
print(f"SYYB datasets: {len(syyb_rows)}")

config = {
    "nameColumn": "节点名称",
    "parentColumn": "上级名称",
    "trackColumn": "条线",
    "levelColumn": "层级",
    "metrics": [
        {"key": "task", "label": "总任务金额", "column": "总任务金额", "format": "amount"},
        {"key": "actual", "label": "年度开单金额", "column": "年度开单金额", "format": "amount"},
        {"key": "rate", "label": "达成率", "column": "达成率", "format": "percent"},
        {"key": "remain", "label": "剩余任务金额", "column": "剩余任务金额", "format": "amount"}
    ],
    "levels": [
        {"name": "机构层", "values": ["代表处", "分公司", "业务部"]},
        {"name": "个人层", "values": ["业务代表", "业务员", "业务"]}
    ],
    "trackValues": {"org": "区域条线", "personal": "行业条线"},
    "riskThreshold": 80,
    "signalRules": [
        {"key": "rate", "op": ">=", "value": 100, "tone": "good", "label": "绿灯"},
        {"key": "rate", "op": ">=", "value": 80, "tone": "warn", "label": "黄灯"},
        {"key": "rate", "op": "<", "value": 80, "tone": "danger", "label": "红灯"}
    ],
    "sections": ["core", "group", "risk", "strategy"],
    "reportTitle": "经营分析报告"
}

for row in syyb_rows:
    ds_id = row[0]
    cur.execute("""
        INSERT INTO bs_dataset_report_config (dataset_id, config_json, updated_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (dataset_id) DO UPDATE SET config_json = EXCLUDED.config_json, updated_at = NOW()
    """, (ds_id, Json(config)))
    print(f"Inserted config for dataset_id={ds_id} ({row[1]})")

conn.commit()
cur.close()
conn.close()
print("Done!")
