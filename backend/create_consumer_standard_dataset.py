# -*- coding: utf-8 -*-
"""Create or update a standalone consumer business dataset in Bookshelf.

This script does not touch the existing consumer dataset.  It creates an
idempotent comparison dataset with code ``consumer_business_standard_v1``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from psycopg2.extras import Json, RealDictCursor


DATASET_CODE = "consumer_business_standard_v1"
DATASET_NAME = "消费者事业部任务达成分析（标准版）"
TABLE_NAME = "public.feishu_tbl_xioafeizhe"


DDL_SQL = """-- 飞书多维表同步：消费者事业部任务数据表
CREATE TABLE public.feishu_tbl_xioafeizhe
(
  id BIGINT PRIMARY KEY,
  record_id VARCHAR(64) NOT NULL,
  fields JSONB NOT NULL,
  created_time TIMESTAMP(3),
  updated_time TIMESTAMP(3),
  sync_time TIMESTAMP(3)
);
COMMENT ON TABLE public.feishu_tbl_xioafeizhe IS '飞书多维表-消费者事业部任务数据（原始表）';
COMMENT ON COLUMN public.feishu_tbl_xioafeizhe.id IS '主键ID';
COMMENT ON COLUMN public.feishu_tbl_xioafeizhe.record_id IS '飞书记录ID';
COMMENT ON COLUMN public.feishu_tbl_xioafeizhe.fields IS '飞书业务JSON字段体';
COMMENT ON COLUMN public.feishu_tbl_xioafeizhe.created_time IS '创建时间';
COMMENT ON COLUMN public.feishu_tbl_xioafeizhe.updated_time IS '更新时间';
COMMENT ON COLUMN public.feishu_tbl_xioafeizhe.sync_time IS '同步时间';"""


FIELD_DEFINITIONS = [
    ("2601", "1季度金额", "字符串（带¥）"),
    ("2602", "2季度金额", "字符串（带¥）"),
    ("2603", "3季度金额", "字符串（带¥）"),
    ("2604", "4季度金额", "字符串（带¥）"),
    ("1季度比例", "1季度占比", "字符串（带%）"),
    ("2季度比例", "2季度占比", "字符串（带%）"),
    ("3季度比例", "3季度占比", "字符串（带%）"),
    ("4季度比例", "4季度占比", "字符串（带%）"),
    ("aaa", "备用字段", "字符串"),
    ("业务经理已分配金额-公共办公", "业务经理公共办公分配金额", "数字"),
    ("业务经理已分配金额-工业医疗", "业务经理工业医疗分配金额", "数字"),
    ("业务经理已分配金额-餐饮部", "业务经理餐饮部分配金额", "数字"),
    ("业务经理父级已审批金额-公共办公", "父级审批-公共办公", "数字"),
    ("业务经理父级已审批金额-工业医疗", "父级审批-工业医疗", "数字"),
    ("业务经理父级已审批金额-餐饮部", "父级审批-餐饮部", "数字"),
    ("事业部", "事业部名称", "字符串"),
    ("事业部下派分公司总任务金额", "事业部下派任务金额", "数字"),
    ("事业部剩余未分配金额", "剩余未分配金额", "字符串（带¥/-）"),
    ("代表处下派业务经理总任务金额", "代表处下派金额", "字符串（带¥）"),
    ("任务维护人", "任务负责人", "字符串"),
    ("公式", "计算系数", "数字字符串"),
    ("分公司", "分公司名称", "字符串"),
    ("分公司下派代表处总任务金额", "分公司下派金额", "数字"),
    ("分公司已分配金额-新零售", "分公司新零售分配", "数字"),
    ("分公司已分配金额-燃气定制", "分公司燃气定制分配", "数字"),
    ("分公司已分配金额-线下", "分公司线下分配", "数字"),
    ("分公司总任务金额", "分公司总任务", "字符串（带¥）"),
    ("创建人", "创建人姓名", "字符串"),
    ("剩余分配百分比", "剩余分配比例", "字符串（带%）"),
    ("地产", "地产板块金额", "数字"),
    ("地产-年度开单金额", "地产年度开单", "数字"),
    ("地产-年度开单金额（万）", "地产年度开单(万)", "字符串"),
    ("地产（万）", "地产金额(万)", "字符串"),
    ("城市公司", "城市公司名称", "字符串"),
    ("城市公司已分配金额-新零售", "城市公司新零售", "数字"),
    ("城市公司已分配金额-燃气定制", "城市公司燃气定制", "数字"),
    ("城市公司已分配金额-线下", "城市公司线下", "数字"),
    ("城市公司父级已审批金额-新零售", "城市公司父审批新零售", "数字"),
    ("城市公司父级已审批金额-燃气定制", "城市公司父审批燃气定制", "数字"),
    ("城市公司父级已审批金额-线下", "城市公司父审批线下", "数字"),
    ("层级级别", "层级：事业部/分公司", "字符串"),
    ("年度开单金额", "年度累计开单金额", "数字"),
    ("年度开单金额转换（以万为单位）", "年度开单(万)", "字符串"),
    ("年度阈值|开单差额（万）", "年度差额(万)", "字符串"),
    ("当前年", "当前年份", "数字"),
    ("当前日期", "当前日", "数字"),
    ("当前月", "当前月", "数字"),
    ("当前月份任务达成率", "月达成率", "字符串"),
    ("当前月最后一天", "当月天数", "数字"),
    ("总任务承接人", "总任务负责人", "字符串"),
    ("总任务达成率", "总达成率", "字符串"),
    ("总任务（金额）", "总任务金额", "数字"),
    ("总金额转换（以万为单位）", "总任务(万)", "字符串"),
    ("总额的待分配任务（金额）", "待分配金额", "字符串"),
    ("截止当前目标阈值", "目标阈值", "数字"),
    ("截止当前目标阈值达成率", "阈值达成率", "字符串"),
    ("截止当前目标阈值（万）", "目标阈值(万)", "字符串"),
    ("截止当天累计目标阈值", "累计阈值", "数字"),
    ("截止当天累计目标阈值（万）", "累计阈值(万)", "字符串"),
    ("拒绝按钮", "按钮状态", "字符串"),
    ("新零售", "新零售金额", "数字"),
    ("新零售-年度开单金额", "新零售年度开单", "数字"),
    ("新零售-年度开单金额（万）", "新零售年度开单(万)", "字符串"),
    ("新零售（万）", "新零售(万)", "字符串"),
    ("月度阈值|开单差额（万）", "月度差额", "字符串"),
    ("本月开单金额", "当月开单", "数字"),
    ("本月开单金额（万）", "当月开单(万)", "字符串"),
    ("本月当前目标阈值", "月度目标", "字符串"),
    ("本月当前目标阈值（万）", "月度目标(万)", "字符串"),
    ("本月总目标（万）", "月度总目标", "字符串"),
    ("燃气定制", "燃气定制金额", "数字"),
    ("燃气定制-年度开单金额", "燃气年度开单", "数字"),
    ("燃气定制-年度开单金额（万）", "燃气年度开单(万)", "字符串"),
    ("燃气定制（万）", "燃气(万)", "字符串"),
    ("父级已审批金额-新零售", "父审批新零售", "数字"),
    ("父级已审批金额-燃气定制", "父审批燃气", "数字"),
    ("父级已审批金额-线下", "父审批线下", "数字"),
    ("父级引用", "父级引用编号", "字符串"),
    ("状态", "审批状态：已审批/待确认", "字符串"),
    ("确认按钮", "按钮状态", "字符串"),
    ("线下", "线下金额", "数字"),
    ("线下-年度开单金额", "线下年度开单", "数字"),
    ("线下-年度开单金额（万）", "线下年度开单(万)", "字符串"),
    ("线下（万）", "线下(万)", "字符串"),
    ("经营主体", "经营主体", "字符串"),
    ("编号", "单据编号", "数字"),
    ("行业线已分配金额-新零售", "行业线新零售", "数字"),
    ("行业线已分配金额-燃气定制", "行业线燃气", "数字"),
    ("行业线已分配金额-线下", "行业线线下", "数字"),
    ("行业线父级已审批金额-新零售", "行业线父审批新零售", "数字"),
    ("行业线父级已审批金额-燃气定制", "行业线父审批燃气", "数字"),
    ("行业线父级已审批金额-线下", "行业线父审批线下", "数字"),
    ("链接字段(勿删)", "组织关联字段", "数组"),
]


NUM = "COALESCE(NULLIF(regexp_replace(fields ->> '{field}', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC"
BASE_STANDARD_SQL = f"""WITH 源数据 AS (
  SELECT
    fields,
    {NUM.format(field='总任务（金额）')} AS 总任务原值,
    {NUM.format(field='年度开单金额')} AS 年度开单原值,
    {NUM.format(field='线下')} AS 线下任务原值,
    {NUM.format(field='线下-年度开单金额')} AS 线下实际原值,
    {NUM.format(field='新零售')} AS 新零售任务原值,
    {NUM.format(field='新零售-年度开单金额')} AS 新零售实际原值,
    {NUM.format(field='燃气定制')} AS 燃气定制任务原值,
    {NUM.format(field='燃气定制-年度开单金额')} AS 燃气定制实际原值,
    {NUM.format(field='地产')} AS 地产任务原值,
    {NUM.format(field='地产-年度开单金额')} AS 地产实际原值,
    {NUM.format(field='总任务达成率')} AS 达成率原值
  FROM public.feishu_tbl_xioafeizhe
),
标准结果 AS (
  SELECT
    '消费者事业部' AS 条线,
    CASE
      WHEN NULLIF(fields ->> '分公司', '') IS NULL THEN '消费者事业部总体'
      WHEN NULLIF(fields ->> '城市公司', '') IS NULL THEN '分公司'
      ELSE '城市公司'
    END AS 层级,
    CASE
      WHEN NULLIF(fields ->> '分公司', '') IS NULL THEN '消费者事业部'
      WHEN NULLIF(fields ->> '城市公司', '') IS NULL THEN fields ->> '分公司'
      ELSE fields ->> '城市公司'
    END AS 节点名称,
    CASE
      WHEN NULLIF(fields ->> '分公司', '') IS NULL THEN NULL
      WHEN NULLIF(fields ->> '城市公司', '') IS NULL THEN '消费者事业部'
      ELSE fields ->> '分公司'
    END AS 上级名称,
    ROUND(总任务原值 / 10000, 2) AS 总任务金额,
    ROUND(年度开单原值 / 10000, 2) AS 年度开单金额,
    ROUND(CASE WHEN 总任务原值 > 0 THEN 年度开单原值 / 总任务原值 * 100 ELSE 达成率原值 END, 2) AS 达成率,
    ROUND(GREATEST(总任务原值 - 年度开单原值, 0) / 10000, 2) AS 剩余任务金额,
    ROUND(线下任务原值 / 10000, 2) AS 线下任务金额,
    ROUND(线下实际原值 / 10000, 2) AS 线下开单金额,
    ROUND(新零售任务原值 / 10000, 2) AS 新零售任务金额,
    ROUND(新零售实际原值 / 10000, 2) AS 新零售开单金额,
    ROUND(燃气定制任务原值 / 10000, 2) AS 燃气定制任务金额,
    ROUND(燃气定制实际原值 / 10000, 2) AS 燃气定制开单金额,
    ROUND(地产任务原值 / 10000, 2) AS 地产任务金额,
    ROUND(地产实际原值 / 10000, 2) AS 地产开单金额
  FROM 源数据
  WHERE 总任务原值 > 0
)"""


def build_lld_content() -> str:
    fields_markdown = "\n".join(
        f"| {name} | {meaning} | {dtype} | `fields ->> '{name}'` |"
        for name, meaning, dtype in FIELD_DEFINITIONS
    )
    return f"""# 飞书消费者事业部任务达成分析 LLD（标准版）

## 1. 数据源与物理结构

数据源表为 `{TABLE_NAME}`。表结构只有 6 个固定字段：`id`、`record_id`、`fields`、`created_time`、`updated_time`、`sync_time`。所有业务字段均在 `fields JSONB` 内部，AI 生成 SQL 时不能把业务字段当成物理列直接引用。

## 2. 字段访问红线

- 取字符串：`fields ->> '字段名'`
- 转数字：`COALESCE(NULLIF(regexp_replace(fields ->> '字段名', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC`
- 字段名必须原样照搬，包括中文、括号、竖线、特殊符号。
- 禁止直接写 `"层级级别"`、`"分公司"`、`"年度开单金额"` 这类物理列引用；这些都是 `fields` 内部字段。

## 3. 组织层级规则

事业部总体：`分公司` 为空。
分公司：`分公司` 有值且 `城市公司` 为空。
城市公司：`分公司` 有值且 `城市公司` 有值。

SQL 必须投影标准列：

| 标准列 | 生成规则 |
| --- | --- |
| 条线 | 固定为 `消费者事业部` |
| 层级 | `消费者事业部总体` / `分公司` / `城市公司` |
| 节点名称 | 总体显示 `消费者事业部`，分公司层显示分公司，城市公司层显示城市公司 |
| 上级名称 | 总体为空，分公司上级为 `消费者事业部`，城市公司上级为所属分公司 |

## 4. 指标口径

金额统一转换为万元，保留 2 位小数。总任务来自 `总任务（金额）`，实际开单来自 `年度开单金额`，达成率优先按 `年度开单金额 / 总任务（金额） * 100` 计算；若总任务为 0，再参考 `总任务达成率` 原始字段。四条业务线包括：线下、新零售、燃气定制、地产，分别输出任务金额与年度开单金额。

## 5. 查询与报告原则

用户问“消费者事业部业绩”时，需要返回事业部总体、各分公司、各城市公司三层数据；用户问某个分公司时，需要返回该分公司以及下属城市公司；用户问排名/最低/最高时，优先在同一层级内比较，不混合总体、分公司和城市公司。

## 6. 完整 fields 数据字典

| 字段名 | 字段含义 | 类型 | SQL 访问 |
| --- | --- | --- | --- |
{fields_markdown}
"""


def dictionary_items() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = [
        {
            "table_name": TABLE_NAME,
            "column_name": "id",
            "semantic_name": "主键ID",
            "data_type": "bigint",
            "extraction_rule": "id",
            "is_active": True,
        },
        {
            "table_name": TABLE_NAME,
            "column_name": "record_id",
            "semantic_name": "飞书记录ID",
            "data_type": "varchar",
            "extraction_rule": "record_id",
            "is_active": True,
        },
        {
            "table_name": TABLE_NAME,
            "column_name": "fields",
            "semantic_name": "飞书业务JSON字段体",
            "data_type": "jsonb",
            "extraction_rule": "fields",
            "is_active": True,
        },
        {
            "table_name": TABLE_NAME,
            "column_name": "created_time",
            "semantic_name": "创建时间",
            "data_type": "timestamp",
            "extraction_rule": "created_time",
            "is_active": True,
        },
        {
            "table_name": TABLE_NAME,
            "column_name": "updated_time",
            "semantic_name": "更新时间",
            "data_type": "timestamp",
            "extraction_rule": "updated_time",
            "is_active": True,
        },
        {
            "table_name": TABLE_NAME,
            "column_name": "sync_time",
            "semantic_name": "同步时间",
            "data_type": "timestamp",
            "extraction_rule": "sync_time",
            "is_active": True,
        },
    ]
    for name, meaning, dtype in FIELD_DEFINITIONS:
        is_numeric = "数字" in dtype or "金额" in meaning or "比例" in meaning or "率" in meaning
        extraction = NUM.format(field=name) if is_numeric else f"fields ->> '{name}'"
        items.append(
            {
                "table_name": TABLE_NAME,
                "column_name": "fields",
                "jsonb_key": name,
                "semantic_name": meaning,
                "data_type": dtype,
                "extraction_rule": extraction,
                "is_active": True,
            }
        )
    return items


def golden_sql_samples() -> List[Dict[str, Any]]:
    return [
        {
            "intent_type": "summary",
            "question": "消费者事业部业绩怎么样？",
            "sql_text": f"""{BASE_STANDARD_SQL}
SELECT *
FROM 标准结果
ORDER BY
  CASE 层级 WHEN '消费者事业部总体' THEN 1 WHEN '分公司' THEN 2 WHEN '城市公司' THEN 3 ELSE 9 END,
  上级名称 NULLS FIRST,
  达成率 DESC,
  节点名称
LIMIT 10000;""",
            "tags": ["整体业绩", "三级层级", "标准输出"],
            "quality_score": 100,
            "is_active": True,
        },
        {
            "intent_type": "ranking",
            "question": "各分公司业绩排名",
            "sql_text": f"""{BASE_STANDARD_SQL}
SELECT *
FROM 标准结果
WHERE 层级 = '分公司'
ORDER BY 达成率 DESC, 年度开单金额 DESC, 节点名称
LIMIT 100;""",
            "tags": ["分公司", "排名"],
            "quality_score": 96,
            "is_active": True,
        },
        {
            "intent_type": "single_entity",
            "question": "某个分公司业绩怎么样？",
            "sql_text": f"""{BASE_STANDARD_SQL}
SELECT *
FROM 标准结果
WHERE 节点名称 = '华南分公司'
   OR 上级名称 = '华南分公司'
ORDER BY
  CASE 层级 WHEN '分公司' THEN 1 WHEN '城市公司' THEN 2 ELSE 9 END,
  达成率 DESC,
  节点名称
LIMIT 1000;""",
            "tags": ["单体分析", "分公司下钻"],
            "quality_score": 94,
            "is_active": True,
        },
        {
            "intent_type": "risk",
            "question": "哪些城市公司达成率低于10%？",
            "sql_text": f"""{BASE_STANDARD_SQL}
SELECT *
FROM 标准结果
WHERE 层级 = '城市公司'
  AND 达成率 < 10
ORDER BY 达成率 ASC, 剩余任务金额 DESC, 上级名称, 节点名称
LIMIT 200;""",
            "tags": ["风险节点", "城市公司"],
            "quality_score": 95,
            "is_active": True,
        },
        {
            "intent_type": "comparative",
            "question": "四条业务线贡献如何？",
            "sql_text": f"""{BASE_STANDARD_SQL}
SELECT
  节点名称,
  业务线,
  任务金额,
  开单金额,
  ROUND(CASE WHEN 任务金额 > 0 THEN 开单金额 / 任务金额 * 100 ELSE 0 END, 2) AS 达成率
FROM 标准结果
CROSS JOIN LATERAL (
  VALUES
    ('线下', 线下任务金额, 线下开单金额),
    ('新零售', 新零售任务金额, 新零售开单金额),
    ('燃气定制', 燃气定制任务金额, 燃气定制开单金额),
    ('地产', 地产任务金额, 地产开单金额)
) AS 业务线明细(业务线, 任务金额, 开单金额)
WHERE 层级 = '消费者事业部总体'
ORDER BY 开单金额 DESC;""",
            "tags": ["业务线", "贡献度"],
            "quality_score": 95,
            "is_active": True,
        },
        {
            "intent_type": "gap",
            "question": "消费者事业部剩余缺口最大的组织有哪些？",
            "sql_text": f"""{BASE_STANDARD_SQL}
SELECT *
FROM 标准结果
WHERE 层级 IN ('分公司', '城市公司')
ORDER BY 剩余任务金额 DESC, 达成率 ASC, 节点名称
LIMIT 50;""",
            "tags": ["缺口", "压力"],
            "quality_score": 94,
            "is_active": True,
        },
    ]


def agent_prompts() -> List[Dict[str, Any]]:
    return [
        {
            "agent_no": 1,
            "prompt_key": "consumer_standard_router",
            "prompt_content": """识别消费者事业部年度任务达成场景。常见问法包括：消费者事业、消费者事业部、消费者业绩、分公司业绩、城市公司下钻、四条业务线贡献、达成率排名、剩余缺口。若用户没有指定组织，默认返回事业部总体+分公司+城市公司；若用户指定分公司，默认返回该分公司及其城市公司；若用户问排名/最好/最差/低于阈值，保持同层级比较。""",
            "is_active": True,
        },
        {
            "agent_no": 2,
            "prompt_key": "consumer_standard_sql",
            "prompt_content": """你负责为消费者事业部数据集生成 PostgreSQL 只读 SQL。物理表 public.feishu_tbl_xioafeizhe 只有 id、record_id、fields、created_time、updated_time、sync_time 六列，所有业务字段都在 fields JSONB 里。必须使用 fields ->> '字段名' 读取业务字段，转数字时使用 COALESCE(NULLIF(regexp_replace(fields ->> '字段名', '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC。禁止直接引用 \"层级级别\"、\"分公司\"、\"城市公司\"、\"总任务（金额）\"、\"年度开单金额\" 等不存在的物理列。SQL 必须尽量投影标准列：条线、层级、节点名称、上级名称、总任务金额、年度开单金额、达成率、剩余任务金额。层级规则：分公司为空为消费者事业部总体；分公司有值且城市公司为空为分公司；城市公司有值为城市公司。金额统一输出万元，达成率输出 0-100 数字。用户问整体时返回总体+分公司+城市公司；问某分公司时返回该分公司+城市公司；问风险/排名时必须同层级比较。""",
            "is_active": True,
        },
        {
            "agent_no": 3,
            "prompt_key": "consumer_standard_review",
            "prompt_content": """复核消费者事业部 SQL 时重点检查：1）是否只读；2）是否真实使用 public.feishu_tbl_xioafeizhe；3）业务字段是否全部通过 fields JSONB 读取；4）是否错误引用不存在的物理列或 fields 字段；5）是否输出条线、层级、节点名称、上级名称等报告标准列；6）金额是否统一万元、达成率是否为数字；7）是否混合不同层级做排名。字段必须以数据字典为准，发现字段不存在时应阻断并说明原因，不要猜字段、不要自行替换成相似字段。""",
            "is_active": True,
        },
        {
            "agent_no": 4,
            "prompt_key": "consumer_standard_report",
            "prompt_content": """生成报告时先直接回答用户问题，再展开数据证据。整体场景按“核心结论、关键指标、层级差异、业务线贡献、风险与建议”组织；单一分公司场景先讲该分公司整体进度，再讲下属城市公司分化；排名场景说明排名口径和阈值。不要把 SQL/DDL 放在正文前部。金额展示为万元或亿元，达成率保留 2 位小数；突出标杆、风险节点、剩余缺口和可执行建议。""",
            "is_active": True,
        },
    ]


def build_payload(source_id: int) -> Dict[str, Any]:
    return {
        "synonyms": [
            {"synonym": item, "weight": weight}
            for item, weight in [
                ("消费者事业部", 10),
                ("消费者事业", 9),
                ("消费者业绩", 8),
                ("消费者任务", 8),
                ("消费事业部", 7),
                ("消费者事业部标准版", 7),
                ("粤桂琼分公司", 9),
                ("粤桂琼", 8),
                ("山东分公司", 9),
                ("消费者分公司对比", 7),
                ("feishu_tbl_xioafeizhe", 6),
            ]
        ],
        "lld_documents": [
            {
                "version": 1,
                "title": "消费者事业部任务达成分析 LLD（标准版）",
                "content": build_lld_content(),
                "redline_rules": [
                    "业务字段必须通过 fields JSONB 读取",
                    "不得直接引用不存在的物理列",
                    "整体问题必须返回三级层级数据",
                    "金额统一万元，达成率统一 0-100 数字",
                ],
                "is_active": True,
            }
        ],
        "data_dictionary": dictionary_items(),
        "schema_definition": [
            {
                "table_name": TABLE_NAME,
                "ddl_sql": DDL_SQL,
                "description": "飞书多维表-消费者事业部任务数据（6列固定结构，业务字段在 fields JSONB）",
                "source_id": source_id,
                "is_active": True,
            }
        ],
        "table_relations": [],
        "golden_sql_samples": golden_sql_samples(),
        "agent_prompts": agent_prompts(),
        "common_questions": [
            {"question_text": "消费者事业部业绩怎么样？", "sort_order": 10},
            {"question_text": "各分公司业绩排名", "sort_order": 20},
            {"question_text": "哪些城市公司达成率低于10%？", "sort_order": 30},
            {"question_text": "消费者事业部剩余缺口最大的组织有哪些？", "sort_order": 40},
            {"question_text": "四条业务线贡献如何？", "sort_order": 50},
            {"question_text": "某个分公司业绩怎么样？", "sort_order": 60},
        ],
        "regression_cases": [
            {
                "case_type": "summary",
                "question_text": "消费者事业的业绩咋样",
                "expected_focus": "返回消费者事业部总体、分公司、城市公司，并说明总任务、开单、达成率、缺口。",
                "expected_intent": "generate_sql",
                "sort_order": 10,
            },
            {
                "case_type": "ranking",
                "question_text": "消费者事业部哪个分公司完成最好？",
                "expected_focus": "仅比较分公司层级，不混入城市公司。",
                "expected_intent": "generate_sql",
                "sort_order": 20,
            },
            {
                "case_type": "risk",
                "question_text": "哪些城市公司低于10%风险线？",
                "expected_focus": "城市公司层级风险列表，按达成率升序。",
                "expected_intent": "generate_sql",
                "sort_order": 30,
            },
        ],
        "external_configs": [],
        "report_config": {
            "nameColumn": "节点名称",
            "parentColumn": "上级名称",
            "trackColumn": "条线",
            "levelColumn": "层级",
            "businessContext": "消费者事业部年度任务达成分析。源表只有 6 个固定字段，业务字段来自 fields JSONB，SQL 负责投影标准报告列。",
            "sourceFields": {
                "organization": ["事业部", "分公司", "城市公司"],
                "time": ["当前年", "当前月", "当前日期"],
                "metrics": ["总任务（金额）", "年度开单金额", "总任务达成率", "线下", "新零售", "燃气定制", "地产"],
            },
            "sqlOutputContract": {
                "requiredColumns": ["条线", "层级", "节点名称", "上级名称"],
                "metricColumns": ["总任务金额", "年度开单金额", "达成率", "剩余任务金额"],
                "notes": [
                    "源表没有标准报告列，必须在 SQL 中用 SELECT 别名生成。",
                    "区域链路按 消费者事业部 -> 分公司 -> 城市公司 输出。",
                    "统计上级节点时使用源表对应层级记录，不能把城市公司明细重复累加到分公司。",
                    "用户问整体时返回总体、分公司和城市公司，便于前端动态下钻。",
                ],
            },
            "analysisDimensions": [
                {
                    "key": "consumer_org_chain",
                    "label": "消费者事业部组织链路",
                    "path": ["消费者事业部", "分公司", "城市公司"],
                    "sourceFields": ["分公司", "城市公司"],
                    "trackValue": "消费者事业部",
                    "purpose": "分析消费者事业部整体、分公司、城市公司三级任务达成、缺口和风险。",
                },
                {
                    "key": "consumer_business_line",
                    "label": "消费者四条业务线",
                    "path": ["线下", "新零售", "燃气定制", "地产"],
                    "sourceFields": ["线下", "新零售", "燃气定制", "地产"],
                    "trackValue": "业务线贡献",
                    "purpose": "分析四条业务线任务和年度开单贡献。",
                },
            ],
            "metrics": [
                {"key": "task", "label": "总任务金额", "column": "总任务金额", "format": "amount"},
                {"key": "actual", "label": "年度开单金额", "column": "年度开单金额", "format": "amount"},
                {"key": "rate", "label": "达成率", "column": "达成率", "format": "percent"},
                {"key": "remain", "label": "剩余任务金额", "column": "剩余任务金额", "format": "amount"},
            ],
            "levels": [
                {"name": "整体层", "values": ["消费者事业部总体"]},
                {"name": "管理层", "values": ["分公司"]},
                {"name": "执行层", "values": ["城市公司"]},
            ],
            "trackValues": {"org": "消费者事业部", "line": "业务线贡献"},
            "riskThreshold": 10,
            "benchmarkThreshold": 85,
            "officeRiskThreshold": 10,
            "officeBenchmarkThreshold": 85,
            "personRiskThreshold": 10,
            "personBenchmarkThreshold": 85,
            "signalRules": [
                {"key": "rate", "op": ">=", "value": 85, "tone": "good", "label": "标杆"},
                {"key": "rate", "op": ">=", "value": 10, "tone": "warn", "label": "需推进"},
                {"key": "rate", "op": "<", "value": 10, "tone": "danger", "label": "风险"},
            ],
            "sections": ["core", "group", "line", "risk", "strategy"],
            "reportTitle": "消费者事业部业绩分析报告",
            "agentReportGuidance": "报告由 SQL 标准列和动态树决定。整体场景先讲消费者事业部大盘，再比较分公司，再下钻城市公司；四条业务线作为贡献度补充，不替代组织层级判断。",
        },
    }


def _json_value(value: Any) -> Json:
    return Json(value if value is not None else {})


def _ensure_optional_tables(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bs_common_questions (
            id BIGSERIAL PRIMARY KEY,
            dataset_id BIGINT NOT NULL REFERENCES bs_datasets(id) ON DELETE CASCADE,
            question_text TEXT NOT NULL,
            sort_order INT NOT NULL DEFAULT 100,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bs_dataset_external_configs (
            id BIGSERIAL PRIMARY KEY,
            dataset_id BIGINT NOT NULL REFERENCES bs_datasets(id) ON DELETE CASCADE,
            config_type VARCHAR(64) NOT NULL,
            config_key VARCHAR(128) NOT NULL,
            config_value JSONB NOT NULL DEFAULT '{}'::jsonb,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(dataset_id, config_type, config_key)
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bs_regression_cases (
            id BIGSERIAL PRIMARY KEY,
            dataset_id BIGINT NOT NULL REFERENCES bs_datasets(id) ON DELETE CASCADE,
            case_type VARCHAR(32) NOT NULL DEFAULT 'summary',
            question_text TEXT NOT NULL,
            expected_focus TEXT NOT NULL DEFAULT '',
            expected_intent VARCHAR(32) NOT NULL DEFAULT 'generate_sql',
            sort_order INT NOT NULL DEFAULT 100,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bs_dataset_report_config (
            id BIGSERIAL PRIMARY KEY,
            dataset_id BIGINT NOT NULL,
            config_json JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(dataset_id)
        );
        """
    )
    cur.execute("ALTER TABLE bs_schema_definitions ADD COLUMN IF NOT EXISTS source_id BIGINT;")


def resolve_source_id(cur, explicit_source_id: int = 0) -> int:
    if explicit_source_id:
        return int(explicit_source_id)
    cur.execute(
        """
        SELECT source_id
        FROM bs_datasets
        WHERE (dataset_name LIKE '%%消费者%%' OR dataset_code ILIKE '%%consumer%%')
          AND source_id IS NOT NULL
        ORDER BY CASE WHEN dataset_code = %s THEN 0 ELSE 1 END, updated_at DESC
        LIMIT 1;
        """,
        (DATASET_CODE,),
    )
    row = cur.fetchone()
    if row and row.get("source_id") is not None:
        return int(row["source_id"])
    try:
        from config_manager import get_default_datasource

        ds = get_default_datasource() or {}
        if ds.get("id") is not None:
            return int(ds["id"])
    except Exception:
        pass
    return 1


def apply_payload_direct(source_id: int = 0) -> Dict[str, Any]:
    """Apply the standard dataset directly to Bookshelf tables.

    This is the same logical destination as the frontend Dataset Management
    save action, but usable from Docker bootstrap before Flask starts.
    """
    from bookshelf_repository import BookshelfRepository

    repo = BookshelfRepository()
    repo.ensure_schema()

    with repo._connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        _ensure_optional_tables(cur)
        source_id = resolve_source_id(cur, source_id)
        payload = build_payload(source_id)
        cur.execute(
            """
            INSERT INTO bs_datasets(dataset_code, dataset_name, business_domain, source_id, description, is_active)
            VALUES (%s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (dataset_code)
            DO UPDATE SET
                dataset_name = EXCLUDED.dataset_name,
                business_domain = EXCLUDED.business_domain,
                source_id = COALESCE(EXCLUDED.source_id, bs_datasets.source_id),
                description = EXCLUDED.description,
                is_active = TRUE,
                updated_at = NOW()
            RETURNING id;
            """,
            (
                DATASET_CODE,
                DATASET_NAME,
                "消费者事业部年度任务达成与业务线分析",
                source_id,
                "标准版消费者事业部数据集，用于对比旧数据集问数效果；业务字段全部从 fields JSONB 读取。",
            ),
        )
        dataset_id = int(cur.fetchone()["id"])

        for table_name in (
            "bs_dataset_synonyms",
            "bs_lld_documents",
            "bs_data_dictionary_items",
            "bs_schema_definitions",
            "bs_table_relations",
            "bs_golden_sql_samples",
            "bs_agent_prompt_fragments",
            "bs_common_questions",
            "bs_regression_cases",
            "bs_dataset_external_configs",
        ):
            cur.execute(f"DELETE FROM {table_name} WHERE dataset_id = %s;", (dataset_id,))
        cur.execute("DELETE FROM bs_dataset_report_config WHERE dataset_id = %s;", (dataset_id,))

        for item in payload["synonyms"]:
            synonym = str(item.get("synonym") or "").strip()
            if not synonym:
                continue
            cur.execute(
                """
                INSERT INTO bs_dataset_synonyms(dataset_id, synonym, normalized_synonym, weight)
                VALUES (%s, %s, %s, %s);
                """,
                (dataset_id, synonym, synonym.lower(), int(item.get("weight") or 1)),
            )

        for item in payload["lld_documents"]:
            cur.execute(
                """
                INSERT INTO bs_lld_documents(dataset_id, version, title, content, redline_rules, is_active, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, 'bootstrap');
                """,
                (
                    dataset_id,
                    int(item.get("version") or 1),
                    item.get("title") or "消费者事业部任务达成分析 LLD（标准版）",
                    item.get("content") or "",
                    _json_value(item.get("redline_rules") or []),
                    bool(item.get("is_active", True)),
                ),
            )

        for item in payload["data_dictionary"]:
            cur.execute(
                """
                INSERT INTO bs_data_dictionary_items(
                    dataset_id, table_name, column_name, jsonb_key, semantic_name,
                    data_type, enum_mapping, extraction_rule, is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    dataset_id,
                    item.get("table_name") or TABLE_NAME,
                    item.get("column_name") or "",
                    item.get("jsonb_key") or None,
                    item.get("semantic_name") or "",
                    item.get("data_type") or "text",
                    _json_value(item.get("enum_mapping") or {}),
                    item.get("extraction_rule") or "",
                    bool(item.get("is_active", True)),
                ),
            )

        for item in payload["schema_definition"]:
            cur.execute(
                """
                INSERT INTO bs_schema_definitions(dataset_id, table_name, ddl_sql, description, is_active, source_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (dataset_id, table_name)
                DO UPDATE SET
                    ddl_sql = EXCLUDED.ddl_sql,
                    description = EXCLUDED.description,
                    is_active = EXCLUDED.is_active,
                    source_id = EXCLUDED.source_id,
                    updated_at = NOW();
                """,
                (
                    dataset_id,
                    item.get("table_name") or TABLE_NAME,
                    item.get("ddl_sql") or DDL_SQL,
                    item.get("description") or "",
                    bool(item.get("is_active", True)),
                    source_id,
                ),
            )

        for item in payload["golden_sql_samples"]:
            cur.execute(
                """
                INSERT INTO bs_golden_sql_samples(
                    dataset_id, intent_type, question, sql_text, tags, quality_score, is_active, created_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'bootstrap');
                """,
                (
                    dataset_id,
                    item.get("intent_type") or "detail",
                    item.get("question") or "",
                    item.get("sql_text") or "",
                    _json_value(item.get("tags") or []),
                    int(item.get("quality_score") or 80),
                    bool(item.get("is_active", True)),
                ),
            )

        for item in payload["agent_prompts"]:
            cur.execute(
                """
                INSERT INTO bs_agent_prompt_fragments(
                    dataset_id, agent_no, prompt_key, prompt_content, is_active, created_by
                )
                VALUES (%s, %s, %s, %s, %s, 'bootstrap');
                """,
                (
                    dataset_id,
                    int(item.get("agent_no") or 0),
                    item.get("prompt_key") or "default",
                    item.get("prompt_content") or "",
                    bool(item.get("is_active", True)),
                ),
            )

        for item in payload["common_questions"]:
            cur.execute(
                """
                INSERT INTO bs_common_questions(dataset_id, question_text, sort_order, is_active)
                VALUES (%s, %s, %s, %s);
                """,
                (
                    dataset_id,
                    item.get("question_text") or "",
                    int(item.get("sort_order") or 100),
                    bool(item.get("is_active", True)),
                ),
            )

        for item in payload["regression_cases"]:
            cur.execute(
                """
                INSERT INTO bs_regression_cases(
                    dataset_id, case_type, question_text, expected_focus, expected_intent, sort_order, is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    dataset_id,
                    item.get("case_type") or "summary",
                    item.get("question_text") or "",
                    item.get("expected_focus") or "",
                    item.get("expected_intent") or "generate_sql",
                    int(item.get("sort_order") or 100),
                    bool(item.get("is_active", True)),
                ),
            )

        for item in payload["external_configs"]:
            cur.execute(
                """
                INSERT INTO bs_dataset_external_configs(
                    dataset_id, config_type, config_key, config_value, is_active
                )
                VALUES (%s, %s, %s, %s, %s);
                """,
                (
                    dataset_id,
                    item.get("config_type") or "",
                    item.get("config_key") or "",
                    _json_value(item.get("config_value") or {}),
                    bool(item.get("is_active", True)),
                ),
            )

        cur.execute(
            """
            INSERT INTO bs_dataset_report_config(dataset_id, config_json)
            VALUES (%s, %s)
            ON CONFLICT (dataset_id)
            DO UPDATE SET config_json = EXCLUDED.config_json, updated_at = NOW();
            """,
            (dataset_id, _json_value(payload.get("report_config") or {})),
        )
        cur.execute("UPDATE bs_datasets SET updated_at = NOW() WHERE id = %s;", (dataset_id,))
        conn.commit()

    return {
        "ok": True,
        "dataset_id": dataset_id,
        "dataset_code": DATASET_CODE,
        "source_id": source_id,
        "dictionary_count": len(payload["data_dictionary"]),
        "golden_sql_count": len(payload["golden_sql_samples"]),
        "agent_prompt_count": len(payload["agent_prompts"]),
    }


def request_json(base_url: str, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            text = response.read().decode("utf-8")
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed: HTTP {exc.code}: {detail}") from exc


def find_existing_dataset(base_url: str) -> tuple[Optional[Dict[str, Any]], Optional[int]]:
    data = request_json(base_url, "GET", "/api/bookshelves/datasets")
    datasets = data.get("datasets") or []
    matched = next((item for item in datasets if item.get("dataset_code") == DATASET_CODE), None)
    source_id = None
    consumer = next(
        (
            item
            for item in datasets
            if "消费者" in str(item.get("dataset_name") or "")
            or "consumer" in str(item.get("dataset_code") or "").lower()
        ),
        None,
    )
    if consumer and consumer.get("source_id") is not None:
        source_id = int(consumer["source_id"])
    elif datasets and datasets[0].get("source_id") is not None:
        source_id = int(datasets[0]["source_id"])
    return matched, source_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Create/update consumer standard dataset.")
    parser.add_argument("--base-url", default=os.getenv("SMARTASK_BASE_URL", "http://127.0.0.1:5002"))
    parser.add_argument("--source-id", type=int, default=int(os.getenv("SMARTASK_CONSUMER_SOURCE_ID", "0") or 0))
    parser.add_argument("--dry-run", action="store_true", help="Only write payload JSON; do not call backend API.")
    parser.add_argument("--direct", action="store_true", help="Write directly to Bookshelf tables instead of calling HTTP API.")
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parent / "imports" / "consumer_business_standard_dataset_payload.json"),
    )
    args = parser.parse_args()

    existing = None
    inferred_source_id = None
    if not args.dry_run and not args.direct:
        existing, inferred_source_id = find_existing_dataset(args.base_url)
    source_id = args.source_id or inferred_source_id or 5
    payload = build_payload(source_id)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] payload written: {output_path}")

    if args.dry_run:
        print("[OK] dry-run only, dataset not applied.")
        return 0

    if args.direct:
        result = apply_payload_direct(source_id=source_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if existing:
        dataset_id = int(existing["id"])
        print(f"[INFO] updating existing standard dataset id={dataset_id}")
    else:
        created = request_json(
            args.base_url,
            "POST",
            "/api/bookshelves/datasets",
            {
                "dataset_code": DATASET_CODE,
                "dataset_name": DATASET_NAME,
                "business_domain": "消费者事业部年度任务达成与业务线分析",
                "source_id": source_id,
                "description": "标准版消费者事业部数据集，用于对比旧数据集问数效果；业务字段全部从 fields JSONB 读取。",
            },
        )
        dataset_id = int(created["dataset"]["id"])
        print(f"[OK] created dataset id={dataset_id}")

    request_json(args.base_url, "PUT", f"/api/bookshelves/datasets/{dataset_id}/full", payload)
    print(f"[OK] applied dataset id={dataset_id}, code={DATASET_CODE}, source_id={source_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
