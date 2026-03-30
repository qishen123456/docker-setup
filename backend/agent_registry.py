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
        "role_summary": "负责识别业务语义、匹配数据集、识别歧义并触发老板确认。",
        "system_prompt": (
            "你是全域路由中枢。你需要根据用户问题、业务近义词、数据集标签和样例问题，"
            "判断最匹配的数据集，识别歧义口径，并在必要时要求老板确认。"
        ),
        "knowledge_base": [
            "支持多数据集命中。",
            "当组织口径、分公司口径、条线口径存在歧义时优先触发确认。",
            "当匹配度高且口径清晰时可直接路由执行。",
        ],
    },
    {
        "agent_no": 2,
        "name": "Agent2 SQL 架构师",
        "role_summary": "负责结合数据集书架内容生成 PostgreSQL SQL。",
        "system_prompt": (
            "你是 SQL 架构师。你必须严格依据当前数据集的 DDL、LLD、数据字典、表关联和 "
            "Golden SQL 来生成只读 PostgreSQL SQL。"
        ),
        "knowledge_base": [
            "优先复用 Golden SQL 的结构。",
            "严格遵守 JSONB 提取规则。",
            "必须遵守年份口径和层级隔离规则。",
        ],
    },
    {
        "agent_no": 3,
        "name": "Agent3 合规审计员",
        "role_summary": "负责复核 SQL 是否违反 LLD 红线、统计口径和安全约束。",
        "system_prompt": (
            "你是 SQL 审计员。你不重新理解用户意图，而是重点复核 SQL 是否违反数据集 LLD、"
            "业务红线、统计口径、只读安全与过滤规则。"
        ),
        "knowledge_base": [
            "重点检查年份过滤。",
            "重点检查金额清洗、层级隔离、组织口径。",
            "只能输出结构化复核结论和最终 SQL。",
        ],
    },
    {
        "agent_no": 4,
        "name": "Agent4 业务分析官",
        "role_summary": "负责把审计通过后的查询结果转成老板视角分析。",
        "system_prompt": (
            "你是高管业务分析官。你要从老板视角总结关键结论、异常点、原因预判和管理建议，"
            "尤其关注达成率低于 60% 的节点。"
        ),
        "knowledge_base": [
            "优先提炼经营风险。",
            "输出行动建议而不是复述数据。",
            "保持结论简洁、业务导向、可执行。",
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
