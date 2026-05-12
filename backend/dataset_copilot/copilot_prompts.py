"""Meta-prompts driving the Dataset Copilot LLM call.

The single goal: take a business briefing and produce ONE JSON object that
can be PUT to /api/bookshelves/datasets/<id>/full without any manual fix-up.
"""

# Output JSON contract — mirrors backend/controllers/bookshelf.py:_validate_full_payload
# and the schema consumed by save_bookshelf_dataset_full.
PAYLOAD_JSON_SCHEMA_HINT = """
{
  "synonyms": [{"synonym": "string", "normalized_synonym": "string", "weight": 1}],
  "lld_documents": [
    {
      "version": 1,
      "title": "string",
      "content": "string  (markdown, 业务上下文/口径/层级/红线规则/不可编造)",
      "redline_rules": ["string", "..."],
      "is_active": true
    }
  ],
  "schema_definition": [
    {"table_name": "string", "ddl_sql": "CREATE TABLE ...", "description": "string"}
  ],
  "data_dictionary": [
    {
      "table_name": "string",
      "column_name": "string",
      "jsonb_key": "string|null",
      "semantic_name": "string",
      "data_type": "string",
      "enum_mapping": {},
      "extraction_rule": "string",
      "is_active": true
    }
  ],
  "table_relations": [
    {"left_table": "string", "left_key": "string", "right_table": "string",
     "right_key": "string", "relation_type": "1:N", "description": "string"}
  ],
  "golden_sql_samples": [
    {
      "intent_type": "string  (single_entity|drilldown|comparative|aggregation|...)",
      "question": "string",
      "sql_text": "string",
      "tags": ["string"],
      "quality_score": 90
    }
  ],
  "agent_prompts": [
    {"agent_no": 1, "prompt_content": "string"},
    {"agent_no": 2, "prompt_content": "string"},
    {"agent_no": 3, "prompt_content": "string"},
    {"agent_no": 4, "prompt_content": "string"}
  ],
  "common_questions": [
    {"question_text": "string", "intent_hint": "string", "sort_order": 1}
  ],
  "regression_cases": [
    {"question_text": "string", "expected_intent": "string",
     "expected_sql_keywords": ["string"], "sort_order": 1}
  ],
  "external_configs": [],
  "report_config": {
    "nameColumn": "SQL结果中的节点名称列；源表没有时由SQL别名生成",
    "parentColumn": "SQL结果中的上级名称列；源表没有时由SQL别名生成",
    "trackColumn": "SQL结果中的条线/大类列，可选",
    "levelColumn": "SQL结果中的层级列，可选",
    "businessContext": "业务背景和报告总体意图",
    "sourceFields": {"organization": ["源字段"], "metrics": ["源指标字段"], "time": ["源时间字段"]},
    "sqlOutputContract": {
      "requiredColumns": ["条线", "层级", "节点名称", "上级名称"],
      "metricColumns": ["总任务金额", "年度开单金额", "达成率", "剩余任务金额"],
      "notes": ["说明Agent2如何把源字段投影成标准报告列"]
    },
    "analysisDimensions": [
      {"key": "string", "label": "管理链路名", "path": ["上层", "下层"], "sourceFields": ["源字段"], "purpose": "分析目的"}
    ],
    "metrics": [
      {"key": "string", "label": "string", "column": "SQL结果指标列", "format": "amount|number|percent|text"}
    ],
    "levels": [{"name": "机构层", "values": ["SQL结果层级枚举"]}],
    "riskThreshold": 80,
    "signalRules": [{"key": "rate", "op": "<|<=|>|>=", "value": 80, "tone": "danger|warn|good", "label": "红灯"}],
    "sections": ["core", "group", "risk", "strategy"],
    "reportTitle": "经营分析报告",
    "agentReportGuidance": "Agent4只补洞察和建议，不维护组织树"
  }
}
""".strip()


SYSTEM_PROMPT = """\
你是【数据集 Copilot】，专注把业务底稿转成可直接落库的智能问数数据集 payload。

强制约束：
1. 只输出一个 JSON 对象，不要任何 markdown、注释、解释、代码块。
2. JSON 字段必须严格遵循给定 schema；未知字段一律不要出现。
3. 必须给出 ≥ 5 条高质量 Golden SQL（覆盖：单体下钻、下级单体、多体对比、Top N、整体汇总）。
4. 必须给出 4 个 Agent prompt（agent_no 1/2/3/4），覆盖：路由识别、SQL 生成、SQL 复核、业务解读。
5. 所有 SQL 全中文别名，禁止编造未在底稿出现的字段；金额类必须使用 regexp_replace 清洗；JSONB 字段必须用 jsonb_typeof 兼容数组与文本。
6. 如果底稿是飞书多维表格落库（fields JSONB），DDL 必须保留 fields JSONB；否则按底稿真实结构出 DDL。
7. LLD 必须包含：业务背景、组织/层级口径、关键指标定义、统计口径红线、禁止编造规则。
8. Agent2 prompt 必须显式重申"层级隔离"规则，避免上级与下级明细汇总冲突。
9. Agent4 prompt 必须强制"基于查询结果给结论 + 给出可执行动作"，禁止空话。
10. report_config 必须同时服务 Agent2 和前端：提供 nameColumn/parentColumn/levelColumn/trackColumn/metrics/levels/signalRules，并用 sqlOutputContract + analysisDimensions 说明源字段如何被 SQL 投影成标准报告列。
11. 保证 PUT /api/bookshelves/datasets/<id>/full 校验通过：≥1 条 LLD，≥1 张 schema，≥若干字段字典，≥3 条 Golden SQL，4 个 Agent prompt 全配齐。
12. Agent1 prompt 必须显式包含两条硬规则：
    (a) 对话上下文指代消解：用户出现"那东部呢""跟去年比""加上华南"等指代/省略时，要把上一轮的数据集、主体、维度沿用过来；
    (b) 主动歧义澄清：当问题中实体名可能命中多个数据集，或当前置信度低，必须以 JSON 形式抛出 confirmation_question + 2-4 个 options（含 dataset_id 与 scope_filter），交由用户确认；置信度高时禁止追问。
13. Agent4 prompt 必须接受可选的"上一轮分析摘要"作为上下文，在追问场景里复用上一轮的口径与节点选择，避免重新铺开整张报告。
"""


def build_user_prompt(doc_text: str, dataset_meta: dict, sample_rows_text: str = "") -> str:
    parts = [
        "## 任务",
        "把以下业务底稿，转换成完整的智能问数数据集 payload。",
        "",
        "## 数据集元信息",
        f"- dataset_id: {dataset_meta.get('id')}",
        f"- dataset_code: {dataset_meta.get('dataset_code')}",
        f"- dataset_name: {dataset_meta.get('dataset_name')}",
        f"- business_domain: {dataset_meta.get('business_domain')}",
        f"- database_name: {dataset_meta.get('database_name', 'postgres')}",
        "",
        "## 业务底稿（含 Agent 提示词、SQL、样例数据）",
        "```markdown",
        doc_text.strip(),
        "```",
    ]
    if sample_rows_text:
        parts.extend(["", "## 额外样例数据", "```", sample_rows_text.strip(), "```"])
    parts += [
        "",
        "## 输出要求",
        "请严格按以下 JSON Schema 输出一个 JSON 对象（一行也行，但必须可被 json.loads 解析）：",
        "```json",
        PAYLOAD_JSON_SCHEMA_HINT,
        "```",
        "",
        "## 关键提示",
        "- 把底稿里给出的 Agent2/Agent4 提示词原文落入 agent_prompts，并按本任务约束补强。",
        "- 把底稿里的标准 SQL / 示例 SQL 作为最高质量分(95+)的 Golden SQL 主样本，再围绕同一业务域衍生 4-6 个变体。",
        "- 衍生场景必须来自底稿中的真实组织层级、指标字段、时间字段和业务语境；不得沿用其他数据集里的固定主体名称。",
        "- 衍生场景至少覆盖：① 整体汇总 ② 单一主体分析 ③ 多主体对比 ④ Top/排名/风险 ⑤ 下钻/分层分析。",
        "- common_questions 至少给 6 条用户最可能问的问题，问题必须贴合当前底稿。",
        "- regression_cases 至少给 4 条覆盖单体/下钻/对比/排名的回归题。",
        "- 只输出 JSON，不要任何前缀或后缀。",
    ]
    return "\n".join(parts)
