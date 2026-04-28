import json
import psycopg2

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': '6670326'
}

DDL_SQL = """
CREATE TABLE IF NOT EXISTS angel_group_data (
    id BIGSERIAL PRIMARY KEY,
    record_id TEXT,
    fields JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

AGENT_PROMPT = """
你是 Agent1（语义路由与口径守卫）。
任务：识别用户问题对应的数据集与统计口径，必要时触发老板确认。

硬性规则：
1. 仅围绕 angel_group_data（2026年）语义做判断。
2. 如果问题包含"分公司/代表处/业务部/业务代表/条线"且可能产生歧义，必须进入确认流程。
3. 统计上级层级时，必须强调"不含下级明细行"的口径。
4. 涉及"当前年/最新年/本年"统一按 2026。
5. 输出偏好：若样本命中高，优先 direct_execute，否则 generate_sql。
6. 若用户明确指定"东部分公司"，保留该过滤意图并透传给下游Agent。
""".strip()

SYNONYMS = json.dumps({
    "销售": ["业绩", "开单", "成交", "订单"],
    "任务": ["目标", "指标", "KPI"],
    "分公司": ["分部", "分支"],
    "代表处": ["办事处", "网点"],
    "事业部": ["部门", "业务单元"],
    "金额": ["钱", "数额", "数值"]
}, ensure_ascii=False)

COMMON_QUESTIONS = json.dumps([
    {"question_text": "商用事业部2026年整体销售业绩如何？"},
    {"question_text": "各分公司任务完成情况分析"},
    {"question_text": "业务代表业绩排名"},
    {"question_text": "年度开单金额趋势分析"}
], ensure_ascii=False)

def update_dataset_content():
    """直接更新数据集内容"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 更新数据集
        update_sql = """
            UPDATE bs_datasets 
            SET agent_prompt = %s,
                ddl_context = %s,
                synonyms = %s,
                common_questions = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE dataset_code = 'angel_business_2026'
        """
        
        cursor.execute(update_sql, (
            AGENT_PROMPT,
            DDL_SQL,
            SYNONYMS,
            COMMON_QUESTIONS
        ))
        
        conn.commit()
        
        # 检查更新结果
        cursor.execute("""
            SELECT 
                LENGTH(agent_prompt) as agent_len,
                LENGTH(ddl_context) as ddl_len,
                LENGTH(synonyms) as syn_len,
                LENGTH(common_questions) as q_len
            FROM bs_datasets 
            WHERE dataset_code = 'angel_business_2026'
        """)
        
        result = cursor.fetchone()
        print(f"✅ 数据集内容更新成功")
        print(f"  - Agent提示词: {result[0]} 字符")
        print(f"  - DDL上下文: {result[1]} 字符")
        print(f"  - 同义词: {result[2]} 字符")
        print(f"  - 常用问题: {result[3]} 字符")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == '__main__':
    update_dataset_content()
