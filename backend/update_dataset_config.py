#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新数据集配置以匹配实际的飞书表结构
"""
import json
import requests

print("🧪 更新数据集配置")

# 数据集ID
DATASET_ID = 1

# 新的DDL定义（匹配实际表结构）
NEW_DDL = """
CREATE TABLE angel_group_data (
    id INTEGER PRIMARY KEY,
    record_id VARCHAR(255),
    fields JSONB,
    created_time TIMESTAMP,
    updated_time TIMESTAMP,
    sync_time TIMESTAMP
);
"""

# 新的数据字典（使用实际的字段ID）
NEW_DATA_DICTIONARY = [
    {
        "table_name": "angel_group_data",
        "column_name": "fields",
        "jsonb_key": "事业部",
        "semantic_name": "事业部",
        "data_type": "text",
        "enum_mapping": {},
        "extraction_rule": "fields->>'事业部'",
        "is_active": True,
    },
    {
        "table_name": "angel_group_data",
        "column_name": "fields",
        "jsonb_key": "当前年",
        "semantic_name": "当前年",
        "data_type": "text",
        "enum_mapping": {},
        "extraction_rule": "fields->>'当前年'",
        "is_active": True,
    },
    {
        "table_name": "angel_group_data",
        "column_name": "fields",
        "jsonb_key": "总任务（金额）",
        "semantic_name": "总任务金额",
        "data_type": "numeric",
        "enum_mapping": {},
        "extraction_rule": "COALESCE(NULLIF(regexp_replace(fields->>'总任务（金额）','[^0-9.-]','','g'),''),'0')::NUMERIC",
        "is_active": True,
    },
    {
        "table_name": "angel_group_data",
        "column_name": "fields",
        "jsonb_key": "年度开单金额",
        "semantic_name": "年度开单金额",
        "data_type": "numeric",
        "enum_mapping": {},
        "extraction_rule": "COALESCE(NULLIF(regexp_replace(fields->>'年度开单金额','[^0-9.-]','','g'),''),'0')::NUMERIC",
        "is_active": True,
    },
]

# 新的Schema定义
NEW_SCHEMA_DEFINITION = [
    {
        "table_name": "angel_group_data",
        "ddl_sql": NEW_DDL,
        "description": "飞书多维表格落库主表，业务字段位于 fields(JSONB)。",
        "is_active": True,
        "source_id": 5,
    }
]

# 构建更新payload
payload = {
    "schema_definition": NEW_SCHEMA_DEFINITION,
    "data_dictionary": NEW_DATA_DICTIONARY,
}

# 调用API更新
client = requests.Session()
try:
    response = client.put(
        f"http://localhost:5000/api/bookshelves/datasets/{DATASET_ID}/full",
        json=payload,
        timeout=30
    )
    
    if response.status_code in (200, 201):
        print("✅ 数据集配置更新成功")
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
    else:
        print(f"❌ 更新失败: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
