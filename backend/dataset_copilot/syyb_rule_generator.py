"""Deterministic payload generator for the syyb briefing.

This is the Phase-0 fallback when the configured LLM is slow/unavailable.
It uses the known structure in docs/提示词和数据.md and still produces the same
Bookshelf payload shape as DatasetCopilot.generate().
"""

from __future__ import annotations

from typing import Any, Dict, List


AGENT1_PROMPT = """
你是 Agent1（语义路由、上下文指代消解与口径澄清）。

任务：识别用户问题对应的数据集、统计主体、统计层级和必要的澄清动作。

硬性规则：
1. 围绕 angel_group_data（2026年）语义做判断；涉及当前年/最新年/本年统一按 2026。
2. 必须读取最近对话上下文：用户问“那东部呢”“南部也看一下”“两个相比呢”等省略表达时，沿用上一轮的数据集、维度和分析口径，只替换新主体。
3. 当问题包含“分公司/代表处/业务部/业务代表/条线”且可能产生统计口径歧义，先判断是否可由上下文消解；不可消解时触发确认。
4. 多数据集候选接近时，必须返回 confirmation_question 与 2-4 个 options，每个 option 需要包含 dataset_id、label、scope_filter。
5. 置信度高且上下文明确时不要打断用户，不要为了保险而反复确认。
6. 单体组织分析要识别“管理链路”：事业部 -> 分公司/业务部 -> 代表处 -> 业务代表。用户问某分公司/代表处/业务部“怎么样”时，应让下游返回命中节点及全部下级节点，方便报告下钻。
7. 统计上级层级时，必须提醒下游“不含下级明细行”的层级隔离口径，同时保留下级节点用于展开分析。
8. 输出偏好：若样本命中高，优先 direct_execute，否则 generate_sql。
""".strip()


AGENT2_PROMPT = """
你是 Agent2（SQL生成专家），专门处理飞书多维表格落库到 PostgreSQL 的 JSONB 数据。
只允许输出只读 SQL（SELECT/WITH/SHOW），禁止增删改。

固定上下文：
1. 当前数据库：{database_name}（PostgreSQL）。
2. 仅使用 angel_group_data 表（字段 fields 为 JSONB）。
3. 年份口径固定：2026。

必须遵守：
1. 统一 CTE：WITH raw_data/字段提取 -> flattened_tree/层级树 -> summarized_nodes/汇总节点。单体组织分析优先使用 WITH RECURSIVE 递归下钻。
2. JSONB 字段必须使用 jsonb_typeof 兼容数组/文本。
3. 金额字段必须使用 regexp_replace(..., '[^0-9.-]', '', 'g') 清理后转 NUMERIC。
4. WHERE 必须包含 当前年 = '2026'；如果源数据当前年为空，可按 2026 兜底。
5. 层级隔离和去重：
   - 第一层必须按 分公司、代表处、业务代表、业务部 GROUP BY 后再汇总，避免源表重复行导致金额翻倍。
   - 代表处统计：代表处<>'' AND (业务代表 IS NULL OR 业务代表='')。
   - 分公司/业务部统计：(代表处 IS NULL OR 代表处='') AND (业务代表 IS NULL OR 业务代表='')。
   - 业务代表统计：业务代表<>''。
6. 涉及多个主体对比时，必须保留 条线、层级、节点名称、上级名称，禁止把多个主体合成一行。
7. 追问场景应沿用上轮口径；如 scope_filter 已由确认流程给出，必须写入 WHERE。
8. 单体组织分析（如“某分公司/某代表处业绩怎么样”）必须返回完整管理链路：命中节点 + 子节点 + 孙级明细节点。必须基于汇总结果使用 WITH RECURSIVE 命中链路，按 子节点.上级名称 = 父节点.节点名称 下钻，不能只写“节点名称=主体 OR 上级名称=主体”导致只返回直接下级。
9. 只输出 SQL 正文，不要解释、不要 Markdown。
""".strip()


AGENT3_PROMPT = """
你是 Agent3（SQL复核官）。你要对 Agent2 SQL 进行口径、安全、可执行性复核，并在必要时修正。

复核清单：
1. 只读安全，仅 SELECT/WITH/SHOW。
2. 仅使用 angel_group_data。
3. JSONB 提取是否使用 jsonb_typeof + ->> 兼容数组/文本。
4. 金额是否使用 regexp_replace 清洗。
5. 是否包含 当前年='2026'。
6. 层级隔离是否正确，上级不含下级明细，且 raw_data 已按组织字段从源头去重。
7. 达成率、剩余任务金额计算是否正确且避免除零。
8. 多主体对比是否保留主体维度。
9. 单体组织分析是否使用递归链路返回全量下级，不允许只返回直接下级。
10. 是否具备 LIMIT。

若发现问题，直接返回修正后的 final_sql。
""".strip()


AGENT4_PROMPT = """
你是 Agent4（业务解读官），面向商用事业部管理层输出结论。

要求：
1. 先给结论：目标达成、风险层级、优先动作。
2. 必须基于查询结果，不编造数据。
3. 分层说明：事业部 -> 条线 -> 分公司/业务部 -> 代表处 -> 业务代表；如果结果包含多层级，必须说明每层最高/最低风险节点。
4. 追问场景必须读取上一轮分析摘要，沿用上一轮的口径与节点选择，只分析用户新增或替换的主体。
5. 涉及对比时，必须明确对比对象、达成率差距、剩余任务差距。
6. 禁止重复复读同一句结论；按“核心结论 -> 亮点 -> 风险 -> 建议”输出，给出 2-3 条可执行动作建议。
""".strip()


BASE_SQL = """
WITH raw_data AS (
    SELECT
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END, '')) AS 分公司,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END, '')) AS 代表处,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
        TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务部') = 'array' THEN fields->'业务部'->0->>'text' ELSE fields->>'业务部' END, '')) AS 业务部,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 总任务金额,
        SUM(COALESCE(NULLIF(regexp_replace(COALESCE(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '0'), '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 年度开单金额
    FROM angel_group_data
    WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    GROUP BY 1, 2, 3, 4
),
flattened_tree AS (
    SELECT
        CASE
            WHEN 业务代表 <> '' THEN '业务代表'
            WHEN 代表处 <> '' THEN '代表处'
            WHEN 分公司 <> '' AND 分公司 LIKE '%业务部' THEN '业务部'
            WHEN 业务部 <> '' THEN '业务部'
            WHEN 分公司 <> '' THEN '分公司'
            ELSE '事业部'
        END AS 层级,
        CASE
            WHEN 业务代表 <> '' THEN COALESCE(NULLIF(代表处, ''), NULLIF(业务部, ''), NULLIF(分公司, ''), '商用事业部')
            WHEN 代表处 <> '' THEN NULLIF(分公司, '')
            WHEN 分公司 <> '' OR 业务部 <> '' THEN '商用事业部'
            ELSE NULL
        END AS 上级名称,
        CASE
            WHEN 业务代表 <> '' THEN 业务代表
            WHEN 代表处 <> '' THEN 代表处
            WHEN 分公司 <> '' THEN 分公司
            WHEN 业务部 <> '' THEN 业务部
            ELSE '商用事业部'
        END AS 节点名称,
        CASE
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%业务部' THEN '行业条线'
            WHEN COALESCE(NULLIF(分公司, ''), NULLIF(业务部, '')) LIKE '%分公司' THEN '区域条线'
            ELSE '事业部层级'
        END AS 条线,
        总任务金额,
        年度开单金额
    FROM raw_data
),
summarized_nodes AS (
    SELECT
        条线,
        层级,
        上级名称,
        节点名称,
        SUM(总任务金额) AS 总任务金额,
        SUM(年度开单金额) AS 年度开单金额
    FROM flattened_tree
    WHERE 节点名称 <> ''
    GROUP BY 条线, 层级, 上级名称, 节点名称
)
SELECT
    条线,
    层级,
    节点名称,
    上级名称,
    总任务金额,
    年度开单金额,
    CASE WHEN 总任务金额 = 0 THEN 0 ELSE ROUND((年度开单金额 / 总任务金额) * 100, 2) END AS 达成率,
    ROUND(总任务金额 - 年度开单金额, 2) AS 剩余任务金额
FROM summarized_nodes
""".strip()


def _sql_with_filter(where_clause: str, order_by: str = "条线 DESC, 层级 DESC, 上级名称, 节点名称", limit: int = 10000) -> str:
    return f"""
WITH 汇总结果 AS (
{BASE_SQL}
)
SELECT *
FROM 汇总结果
WHERE {where_clause}
ORDER BY {order_by}
LIMIT {limit};
""".strip()


def _sql_with_descendants(anchor_clause: str) -> str:
    return f"""
WITH RECURSIVE 汇总结果 AS (
{BASE_SQL}
),
命中链路 AS (
    SELECT *
    FROM 汇总结果
    WHERE {anchor_clause}
    UNION ALL
    SELECT 子节点.*
    FROM 汇总结果 子节点
    JOIN 命中链路 父节点
      ON 子节点.上级名称 = 父节点.节点名称
)
SELECT *
FROM 命中链路
ORDER BY 条线 DESC,
  CASE 层级
    WHEN '分公司' THEN 1
    WHEN '代表处' THEN 2
    WHEN '业务代表' THEN 3
    WHEN '业务部' THEN 1
    ELSE 9
  END,
  上级名称,
  节点名称
LIMIT 10000;
""".strip()


def build_syyb_payload(doc_text: str, dataset_meta: Dict[str, Any]) -> Dict[str, Any]:
    lld = f"""
# 商用事业部智能问数 LLD

## 业务范围
安吉尔商用事业部 2026 年销售任务与年度开单分析。数据来自飞书多维表格落库表 `angel_group_data`，业务字段存放在 `fields` JSONB 中。

## 组织链路
- 区域链路：商用事业部 -> 分公司 -> 代表处 -> 业务代表。
- 行业链路：商用事业部 -> 餐饮业务部/工业医疗业务部/公共办公业务部 -> 业务代表。

## 指标
- 总任务金额：`fields->'总任务（金额）'` 清洗后转 NUMERIC。
- 年度开单金额：`fields->'年度开单金额'` 清洗后转 NUMERIC。
- 达成率：年度开单金额 / 总任务金额 * 100。
- 剩余任务金额：总任务金额 - 年度开单金额。

## 红线规则
1. 年份固定为 2026。
2. 统计代表处时必须排除业务代表明细行。
3. 统计分公司/业务部时必须排除代表处与业务代表明细行。
4. 多主体对比不得合并主体。
5. 所有结论必须基于查询结果，禁止编造。

## 对话上下文和歧义确认
- 追问必须沿用上一轮数据集、主体、层级和过滤条件。
- 多数据集候选接近或实体名歧义时，必须触发智能确认。

## 底稿摘要
{doc_text[:2000]}
""".strip()

    fields = [
        ("id", None, "记录ID", "integer", "主键"),
        ("fields", None, "飞书字段JSON", "jsonb", "飞书多维表格原始字段"),
        ("分公司", "分公司", "分公司/业务部", "text", "jsonb_typeof 兼容数组/文本"),
        ("代表处", "代表处", "代表处", "text", "jsonb_typeof 兼容数组/文本"),
        ("业务代表", "业务代表", "业务代表", "text", "jsonb_typeof 兼容数组/文本"),
        ("当前年", "当前年", "年份", "text", "固定过滤 2026"),
        ("总任务（金额）", "总任务（金额）", "总任务金额", "numeric", "regexp_replace 清洗非数字字符"),
        ("年度开单金额", "年度开单金额", "年度开单金额", "numeric", "regexp_replace 清洗非数字字符"),
        ("条线", None, "条线", "text", "分公司 LIKE '%分公司' 为区域条线；LIKE '%业务部' 为行业条线"),
        ("层级", None, "层级", "text", "事业部/分公司/代表处/业务部/业务代表"),
        ("节点名称", None, "节点名称", "text", "当前统计节点"),
        ("上级名称", None, "上级名称", "text", "当前统计节点父级"),
        ("达成率", None, "达成率", "numeric", "开单金额/任务金额*100"),
        ("剩余任务金额", None, "剩余任务金额", "numeric", "任务金额-开单金额"),
    ]

    golden_sql = [
        ("aggregation", "商用事业部整体业绩怎么样？", f"{BASE_SQL}\nORDER BY 条线 DESC, 层级 DESC, 上级名称, 节点名称\nLIMIT 10000;", ["整体", "全维度"]),
        ("single_entity", "东部分公司业绩怎么样？", _sql_with_descendants("节点名称 = '东部分公司'"), ["分公司", "东部", "下钻"]),
        ("single_entity", "安徽代表处业绩怎么样？", _sql_with_descendants("节点名称 = '安徽代表处'"), ["代表处", "安徽", "下钻"]),
        ("comparative", "东部分公司和南部分公司哪个完成得更好？", _sql_with_filter("节点名称 IN ('东部分公司','南部分公司') OR 上级名称 IN ('东部分公司','南部分公司')"), ["对比", "分公司"]),
        ("topn", "行业线 Top5 业务代表是谁？", _sql_with_filter("条线 = '行业条线' AND 层级 = '业务代表'", "年度开单金额 DESC", 5), ["行业", "TopN"]),
        ("risk", "达成率低于10%的单元有哪些？", _sql_with_filter("达成率 < 10", "达成率 ASC", 100), ["风险", "低达成"]),
    ]

    return {
        "synonyms": [
            {"synonym": "商用事业部", "normalized_synonym": "商用事业部", "weight": 10},
            {"synonym": "syyb", "normalized_synonym": "syyb", "weight": 8},
            {"synonym": "安吉尔商用", "normalized_synonym": "安吉尔商用", "weight": 8},
            {"synonym": "业绩", "normalized_synonym": "业绩", "weight": 4},
        ],
        "lld_documents": [{"version": 1, "title": "商用事业部 2026 销售业绩 LLD", "content": lld, "redline_rules": ["年份固定2026", "层级隔离", "多主体保留主体维度", "禁止编造"], "is_active": True}],
        "schema_definition": [{"table_name": "angel_group_data", "ddl_sql": "CREATE TABLE angel_group_data (id BIGSERIAL PRIMARY KEY, fields JSONB NOT NULL, created_at TIMESTAMP DEFAULT NOW(), updated_at TIMESTAMP DEFAULT NOW());", "description": "飞书多维表格商用事业部 2026 销售业绩数据"}],
        "data_dictionary": [{"table_name": "angel_group_data", "column_name": c, "jsonb_key": k, "semantic_name": s, "data_type": t, "enum_mapping": {}, "extraction_rule": r, "is_active": True} for c, k, s, t, r in fields],
        "table_relations": [],
        "golden_sql_samples": [{"intent_type": i, "question": q, "sql_text": sql, "tags": tags, "quality_score": 95 if idx == 0 else 90} for idx, (i, q, sql, tags) in enumerate(golden_sql)],
        "agent_prompts": [
            {"agent_no": 1, "prompt_content": AGENT1_PROMPT},
            {"agent_no": 2, "prompt_content": AGENT2_PROMPT},
            {"agent_no": 3, "prompt_content": AGENT3_PROMPT},
            {"agent_no": 4, "prompt_content": AGENT4_PROMPT},
        ],
        "common_questions": [
            {"question_text": "东部分公司业绩怎么样？", "intent_hint": "single_entity", "sort_order": 1},
            {"question_text": "安徽代表处业绩怎么样？", "intent_hint": "single_entity", "sort_order": 2},
            {"question_text": "东部分公司和南部分公司哪个完成得更好？", "intent_hint": "comparative", "sort_order": 3},
            {"question_text": "行业线 Top5 业务代表是谁？", "intent_hint": "topn", "sort_order": 4},
            {"question_text": "达成率低于10%的单元有哪些？", "intent_hint": "risk", "sort_order": 5},
            {"question_text": "商用事业部整体业绩怎么样？", "intent_hint": "aggregation", "sort_order": 6},
        ],
        "regression_cases": [
            {"question_text": "东部分公司业绩怎么样？", "expected_intent": "single_entity", "expected_sql_keywords": ["东部分公司", "层级", "达成率"], "sort_order": 1},
            {"question_text": "那南部呢？", "expected_intent": "context_followup", "expected_sql_keywords": ["南部分公司"], "sort_order": 2},
            {"question_text": "东部分公司和南部分公司哪个完成得更好？", "expected_intent": "comparative", "expected_sql_keywords": ["IN", "东部分公司", "南部分公司"], "sort_order": 3},
            {"question_text": "安徽代表处业绩怎么样？", "expected_intent": "single_entity", "expected_sql_keywords": ["安徽代表处", "业务代表"], "sort_order": 4},
        ],
        "external_configs": [],
        "report_config": {
            "nameColumn": "节点名称",
            "parentColumn": "上级名称",
            "trackColumn": "条线",
            "levelColumn": "层级",
            "businessContext": "商用事业部 2026 年经营分析。源数据来自 angel_group_data.fields JSONB，组织层级和父子关系由 SQL 投影生成，而不是源表物理列。",
            "sourceFields": {
                "organization": ["分公司", "代表处", "业务代表"],
                "time": ["当前年"],
                "metrics": ["总任务（金额）", "年度开单金额"],
            },
            "sqlOutputContract": {
                "requiredColumns": ["条线", "层级", "节点名称", "上级名称"],
                "metricColumns": ["总任务金额", "年度开单金额", "达成率", "剩余任务金额"],
                "notes": [
                    "源表没有 节点名称/上级名称/层级/条线 时，必须在 SQL 中用 SELECT 别名生成这些标准列。",
                    "区域链路按 商用事业部 -> 分公司 -> 代表处 -> 业务代表 输出。",
                    "行业链路按 商用事业部 -> 业务部 -> 业务代表 输出。",
                    "统计上级节点时必须做层级隔离，不能把下级明细行重复累加到上级汇总行。",
                    "如用户查询某个分公司，应同时返回该分公司、其代表处、以及代表处下业务代表，方便前端动态下钻。",
                ],
            },
            "analysisDimensions": [
                {
                    "key": "regional_chain",
                    "label": "区域管理链条",
                    "path": ["商用事业部", "分公司", "代表处", "业务代表"],
                    "sourceFields": ["分公司", "代表处", "业务代表"],
                    "trackValue": "区域条线",
                    "purpose": "分析各区域市场覆盖深度、分公司/代表处任务完成、业务代表风险和优秀样本。",
                },
                {
                    "key": "industry_chain",
                    "label": "行业管理链条",
                    "path": ["商用事业部", "业务部", "业务代表"],
                    "sourceFields": ["分公司", "业务代表"],
                    "trackValue": "行业条线",
                    "purpose": "分析餐饮、工业医疗、公共办公等行业线专业产出和个人产能。",
                },
            ],
            "metrics": [
                {"key": "task", "label": "总任务金额", "column": "总任务金额", "format": "amount"},
                {"key": "actual", "label": "年度开单金额", "column": "年度开单金额", "format": "amount"},
                {"key": "rate", "label": "达成率", "column": "达成率", "format": "percent"},
                {"key": "remain", "label": "剩余任务金额", "column": "剩余任务金额", "format": "amount"},
            ],
            "levels": [
                {"name": "机构层", "values": ["代表处", "分公司", "业务部"]},
                {"name": "个人层", "values": ["业务代表", "业务员", "业务"]},
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
                    {"key": "rate", "op": "<", "value": 10, "tone": "danger", "label": "风险"},
                ],
            "sections": ["core", "group", "risk", "strategy"],
            "reportTitle": "经营分析报告",
            "agentReportGuidance": "报告结构由 SQL 标准列和动态树决定。分公司场景先横向比较分公司，再纵向下钻直接下级代表处；业务代表只作为代表处后的证据层，不直接替代代表处管理判断。Agent4 不维护组织树，只基于指标、风险节点、优秀节点和 analysisDimensions 输出洞察、风险解释和建议。",
        },
    }
