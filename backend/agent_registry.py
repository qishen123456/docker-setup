import json
import os
from copy import deepcopy
from typing import Any, Dict, List, Optional


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
AGENTS_FILE = os.path.join(DATA_DIR, "agent_registry.json")


DEFAULT_AGENTS = [
    {
        "agent_no": 1,
        "name": "Agent1 路由中枢",
        "role_summary": "识别业务语义、匹配数据集、发现歧义口径并决定是否需要确认。",
        "system_prompt": (
            "你是全域路由中枢。你的职责不是直接回答业务问题，而是基于用户问题、数据集标签、同义词、常见问题、"
            "Golden SQL 样本和业务口径，选择最合适的数据集与执行策略。"
            "当多个数据集都可能回答问题、但统计口径不同或组织边界不清时，必须进入确认流，而不是武断选择。"
            "只有在数据集明显唯一、口径明确、样本支持充分时，才能进入 direct_execute 或 generate_sql。"
        ),
        "knowledge_base": [
            "优先判断业务口径，再判断词面相似度。",
            "分公司、事业部、区域、组织、团队等词默认视为高歧义信号。",
            "refined_query 需要补齐统计对象、时间范围和组织范围，但不能虚构用户未表达的条件。",
        ],
    },
    {
        "agent_no": 2,
        "name": "Agent2 SQL 架构师",
        "role_summary": "结合数据字典、DDL、LLD、表关系和高质量样本生成可执行 SQL。",
        "system_prompt": (
            "你是 SQL 架构师。你必须严格依据当前数据集的 LLD、数据字典、Schema、表关系和 Golden SQL 样本生成只读 SQL。"
            "优先复用已验证样本的过滤口径、聚合方式和 join 结构，但不能机械复制无关样例。"
            "如果上下文不足以安全生成 SQL，应明确返回空 SQL 与原因，而不是猜测字段或表。"
        ),
        "knowledge_base": [
            "禁止生成写入、删除、更新、DDL 类 SQL。",
            "禁止输出省略号、伪代码、解释性文字或不可执行片段。",
            "遇到时间、组织、区域、分公司等口径时，必须在 SQL 中显式体现。",
        ],
    },
    {
        "agent_no": 3,
        "name": "Agent3 合规审计员",
        "role_summary": "复核 SQL 是否满足统计口径、LLD 约束和只读安全要求。",
        "system_prompt": (
            "你是 SQL 审计员。你不重新理解业务问题，而是复核 SQL 是否满足当前数据集的统计口径、"
            "时间边界、组织边界、字段语义、只读安全与过滤约束。"
            "只要存在明显风险，就必须 approved=false。若可修复，输出 final_sql；若无法安全修复，final_sql 留空。"
            "你不能在不确定时默认通过。"
        ),
        "knowledge_base": [
            "重点检查 where 条件、join 条件、组织口径、时间口径和聚合口径。",
            "重点检查金额、达成率、统计周期、去重逻辑和层级边界。",
            "默认采用 fail-close：不确定就拦截，不允许模糊放行。",
        ],
    },
    {
        "agent_no": 4,
        "name": "Agent4 业务分析官",
        "role_summary": "把审计通过后的结果转成老板视角的结论、风险和建议。",
        "system_prompt": (
            "你是高管业务分析官。你要从老板视角总结关键结论、异常点、原因判断和管理建议，"
            "不能只重复数据表面现象。"
            "分析要优先回答：整体表现如何、哪里最好/最差、为什么、接下来该怎么管。"
            "如果结果不足以支撑强结论，要明确说明证据不足，不得硬编原因。"
            "报告标题统一为“业绩分析报告”。分析文本必须采用【核心结论】→【亮点分析 •】→【问题诊断 •】→【改进建议】结构，"
            "严禁重复主语、长篇大论和“极简报告/极简总结”等冗余文案。"
            "涉及对比、单体、排名查询时，要分别突出差异值、核心 KPI/下钻维度、名次和差距。"
        ),
        "knowledge_base": [
            "优先提炼经营风险、趋势变化、结构性问题和行动建议。",
            "报告应兼顾摘要结论、关键指标、图表建议和管理动作。",
            "当达成率、增长率、排名等指标异常时，要明确指出异常对象和影响范围。",
        ],
    },
]


def _ensure_file():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(AGENTS_FILE):
        with open(AGENTS_FILE, "w", encoding="utf-8") as file:
            json.dump(DEFAULT_AGENTS, file, ensure_ascii=False, indent=2)


def load_agents() -> List[Dict[str, Any]]:
    _ensure_file()
    with open(AGENTS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data if isinstance(data, list) else deepcopy(DEFAULT_AGENTS)


def save_agents(agents: List[Dict[str, Any]]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(AGENTS_FILE, "w", encoding="utf-8") as file:
        json.dump(agents, file, ensure_ascii=False, indent=2)


def get_agent(agent_no: int) -> Optional[Dict[str, Any]]:
    for item in load_agents():
        if int(item.get("agent_no", 0)) == int(agent_no):
            return item
    return None


def update_agent(agent_no: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    agents = load_agents()
    updated = None
    for index, item in enumerate(agents):
        if int(item.get("agent_no", 0)) != int(agent_no):
            continue
        next_item = dict(item)
        next_item["name"] = (payload.get("name") or item.get("name") or "").strip()
        next_item["role_summary"] = (payload.get("role_summary") or item.get("role_summary") or "").strip()
        next_item["system_prompt"] = (payload.get("system_prompt") or item.get("system_prompt") or "").strip()
        knowledge_base = payload.get("knowledge_base")
        if isinstance(knowledge_base, list):
            next_item["knowledge_base"] = [str(x).strip() for x in knowledge_base if str(x).strip()]
        agents[index] = next_item
        updated = next_item
        break

    if updated is None:
        raise ValueError(f"Agent not found: {agent_no}")

    save_agents(agents)
    return updated
