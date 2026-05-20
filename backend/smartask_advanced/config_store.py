from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Dict, List

from config_manager import read_json, write_json


ADVANCED_CAPABILITIES_FILE = "advanced_capabilities.json"
ALLOWED_TOOL_TYPES = {"dataset", "sql", "python", "report", "fact", "confirm", "mcp", "sqlserver", "default"}


DEFAULT_SKILLS: List[Dict[str, Any]] = [
    {
        "key": "dataset_route",
        "label": "数据集路由 Skill",
        "stage": "advanced.skill.dataset_route",
        "toolType": "dataset",
        "enabled": True,
        "order": 10,
        "description": "根据问题、数据集名称、业务域和路由词识别候选数据资产。",
    },
    {
        "key": "asset_pack",
        "label": "资产打包 Skill",
        "stage": "advanced.skill.asset_pack",
        "toolType": "dataset",
        "enabled": True,
        "order": 20,
        "description": "读取字段字典、DDL、LLD、Golden SQL、常见问题和报告模板。",
    },
    {
        "key": "route_guard",
        "label": "路由守门 Skill",
        "stage": "advanced.skill.route_guard",
        "toolType": "dataset",
        "enabled": True,
        "order": 25,
        "description": "结合组织树和候选数据集得分判断是否自动锁定、提示确认或识别错配。",
    },
    {
        "key": "planner",
        "label": "任务规划 Planner",
        "stage": "advanced.planner",
        "toolType": "fact",
        "enabled": True,
        "order": 30,
        "description": "识别排名、对比、下钻、汇总等意图，规划后续工具链路。",
    },
    {
        "key": "golden_sql",
        "label": "Golden SQL Skill",
        "stage": "advanced.skill.golden_sql",
        "toolType": "sql",
        "enabled": True,
        "order": 40,
        "description": "优先检索人工确认过的 SQL 样例，作为生成或改写依据。",
    },
    {
        "key": "sql_generate",
        "label": "SQL 生成 Skill",
        "stage": "advanced.skill.sql_generate",
        "toolType": "sql",
        "enabled": True,
        "order": 50,
        "description": "基于数据资产与业务口径生成查询语句。",
    },
    {
        "key": "sql_review",
        "label": "SQL 复核 Skill",
        "stage": "advanced.skill.sql_review",
        "toolType": "sql",
        "enabled": True,
        "order": 60,
        "description": "检查只读安全、字段来源、统计口径和组织路径。",
    },
    {
        "key": "sql_execute",
        "label": "SQL 执行 Skill",
        "stage": "advanced.skill.sql_execute",
        "toolType": "sql",
        "enabled": True,
        "order": 70,
        "description": "复用现有数据源路由执行 SQL，不重复造连接层。",
    },
    {
        "key": "sql_quality",
        "label": "SQL 质量门 Skill",
        "stage": "advanced.skill.sql_quality",
        "toolType": "sql",
        "enabled": True,
        "order": 75,
        "description": "检查 SQL 只读安全、字段映射、表映射、复核结论和首次结果质量。",
    },
    {
        "key": "template_policy",
        "label": "模板策略 Skill",
        "stage": "advanced.skill.template_policy",
        "toolType": "report",
        "enabled": True,
        "order": 78,
        "description": "检查排名/TopN 是否跟随报告模板和本轮 queryIntent，避免固定 Top3。",
    },
    {
        "key": "pandas_analyze",
        "label": "Pandas 加工 Skill",
        "stage": "advanced.skill.pandas_analyze",
        "toolType": "python",
        "enabled": True,
        "order": 80,
        "description": "对 SQL 结果做排名、差异、TopN、缺口和组织路径加工。",
    },
    {
        "key": "self_check",
        "label": "结果自检 Skill",
        "stage": "advanced.skill.self_check",
        "toolType": "fact",
        "enabled": True,
        "order": 90,
        "description": "检查空结果、数据集不匹配、风险阈值和报告完整性。",
    },
    {
        "key": "answer_contract",
        "label": "答案契约 Skill",
        "stage": "advanced.skill.answer_contract",
        "toolType": "report",
        "enabled": True,
        "order": 95,
        "description": "检查核心结论是否优先直接回答用户问题，并提示关键证据与风险。",
    },
    {
        "key": "conclusion_advice",
        "label": "结论建议 Skill",
        "stage": "advanced.skill.conclusion_advice",
        "toolType": "report",
        "enabled": True,
        "order": 97,
        "description": "基于结果证据生成核心结论重写建议，不改写现有报告。",
    },
    {
        "key": "evidence_vote",
        "label": "多信号择优 Skill",
        "stage": "advanced.skill.evidence_vote",
        "toolType": "fact",
        "enabled": True,
        "order": 98,
        "description": "汇总路由、SQL、Pandas、答案契约和自检信号，给出采信建议。",
    },
    {
        "key": "report_compose",
        "label": "报告组装 Skill",
        "stage": "advanced.skill.report_compose",
        "toolType": "report",
        "enabled": True,
        "order": 100,
        "description": "保持现有 report_spec/dataset_results 契约，组装最终报告。",
    },
]
DEFAULT_SKILL_KEYS = {item["key"] for item in DEFAULT_SKILLS}


DEFAULT_ADVANCED_CAPABILITIES: Dict[str, Any] = {
    "version": 1,
    "enabled": True,
    "description": "进阶问数能力中心配置。最终报告契约保持不变，升级执行过程和工具链路。",
    "execution": {
        "emitSkillTrace": True,
        "preserveFinalReportContract": True,
        "assetPreviewLimit": 3,
        "fallbackToBasicEngine": True,
    },
    "skills": DEFAULT_SKILLS,
    "mcp": {
        "enabled": False,
        "servers": [],
        "notes": "第一阶段只做配置和诊断占位，稳定后再接真实 MCP 工具调用。",
    },
    "sqlServer": {
        "enabled": False,
        "reuseDataSources": True,
        "driver": "ODBC Driver 18 for SQL Server",
        "notes": "优先复用数据连接管理里的 SQL Server 数据源；驱动和镜像依赖在第二阶段校验。",
    },
}


def _clean_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return fallback


def _clean_int(value: Any, fallback: int, minimum: int = 1, maximum: int = 20) -> int:
    try:
        current = int(value)
    except Exception:
        return fallback
    return min(max(current, minimum), maximum)


def _clean_skill_key(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9_:-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_:-")
    if not text:
        text = fallback
    return text[:80]


def _normalize_stage(key: str, value: Any) -> str:
    text = str(value or "").strip()
    if text.startswith("advanced."):
        return text[:160]
    return f"advanced.skill.custom.{key}"


def _normalize_tool_type(value: Any, fallback: str = "default") -> str:
    text = str(value or fallback or "default").strip().lower()
    return text if text in ALLOWED_TOOL_TYPES else fallback


def _normalize_skill(item: Any, fallback_order: int = 500) -> Dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    label = str(item.get("label") or item.get("name") or item.get("title") or "").strip()
    key = _clean_skill_key(item.get("key") or item.get("id") or item.get("name"), fallback=_clean_skill_key(label))
    if not key:
        return None
    is_builtin = key in DEFAULT_SKILL_KEYS
    skill = {
        "key": key,
        "label": label or key,
        "stage": _normalize_stage(key, item.get("stage")),
        "toolType": _normalize_tool_type(item.get("toolType") or item.get("tool_type"), "default"),
        "enabled": _clean_bool(item.get("enabled"), True),
        "order": _clean_int(item.get("order"), fallback_order, 1, 999),
        "description": str(item.get("description") or item.get("summary") or "").strip(),
        "custom": not is_builtin,
        "source": str(item.get("source") or item.get("url") or item.get("origin") or "").strip(),
    }
    for optional_key in ("prompt", "instructions", "inputs", "outputs", "config", "safety", "tags"):
        if optional_key in item:
            skill[optional_key] = item.get(optional_key)
    return skill


def _merge_skills(value: Any) -> List[Dict[str, Any]]:
    incoming = {}
    if isinstance(value, list):
        incoming = {
            str(item.get("key") or "").strip(): item
            for item in value
            if isinstance(item, dict) and str(item.get("key") or "").strip()
        }

    result: List[Dict[str, Any]] = []
    for default in DEFAULT_SKILLS:
        item = deepcopy(default)
        current = incoming.get(item["key"])
        if isinstance(current, dict):
            item["enabled"] = _clean_bool(current.get("enabled"), bool(item.get("enabled")))
            item["description"] = str(current.get("description") or item.get("description") or "")
            item["label"] = str(current.get("label") or item.get("label") or item["key"])
            for optional_key in ("prompt", "instructions", "inputs", "outputs", "config", "safety", "tags", "source"):
                if optional_key in current:
                    item[optional_key] = current.get(optional_key)
        result.append(item)
    next_order = max([int(item.get("order") or 0) for item in result] or [100]) + 10
    for key, current in incoming.items():
        if key in DEFAULT_SKILL_KEYS:
            continue
        skill = _normalize_skill(current, fallback_order=next_order)
        if not skill:
            continue
        result.append(skill)
        next_order += 10
    return sorted(result, key=lambda item: int(item.get("order") or 999))


def normalize_config(payload: Any) -> Dict[str, Any]:
    raw = payload if isinstance(payload, dict) else {}
    result = deepcopy(DEFAULT_ADVANCED_CAPABILITIES)
    result["enabled"] = _clean_bool(raw.get("enabled"), bool(result.get("enabled")))
    result["description"] = str(raw.get("description") or result.get("description") or "")

    execution = raw.get("execution") if isinstance(raw.get("execution"), dict) else {}
    result["execution"]["emitSkillTrace"] = _clean_bool(
        execution.get("emitSkillTrace"),
        bool(result["execution"].get("emitSkillTrace")),
    )
    result["execution"]["preserveFinalReportContract"] = True
    result["execution"]["assetPreviewLimit"] = _clean_int(
        execution.get("assetPreviewLimit"),
        int(result["execution"].get("assetPreviewLimit") or 3),
        1,
        10,
    )
    result["execution"]["fallbackToBasicEngine"] = True

    result["skills"] = _merge_skills(raw.get("skills"))

    mcp = raw.get("mcp") if isinstance(raw.get("mcp"), dict) else {}
    result["mcp"]["enabled"] = _clean_bool(mcp.get("enabled"), bool(result["mcp"].get("enabled")))
    result["mcp"]["servers"] = mcp.get("servers") if isinstance(mcp.get("servers"), list) else []
    result["mcp"]["notes"] = str(mcp.get("notes") or result["mcp"].get("notes") or "")

    sql_server = raw.get("sqlServer") if isinstance(raw.get("sqlServer"), dict) else {}
    result["sqlServer"]["enabled"] = _clean_bool(sql_server.get("enabled"), bool(result["sqlServer"].get("enabled")))
    result["sqlServer"]["reuseDataSources"] = _clean_bool(
        sql_server.get("reuseDataSources"),
        bool(result["sqlServer"].get("reuseDataSources")),
    )
    result["sqlServer"]["driver"] = str(sql_server.get("driver") or result["sqlServer"].get("driver") or "")
    result["sqlServer"]["notes"] = str(sql_server.get("notes") or result["sqlServer"].get("notes") or "")
    return result


def load_config() -> Dict[str, Any]:
    return normalize_config(read_json(ADVANCED_CAPABILITIES_FILE))


def save_config(payload: Any) -> Dict[str, Any]:
    config = normalize_config(payload)
    write_json(ADVANCED_CAPABILITIES_FILE, config)
    return config


def _extract_skill_payload(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("skills"), list):
        return [item for item in payload.get("skills") if isinstance(item, dict)]
    if isinstance(payload.get("skill"), dict):
        return [payload.get("skill")]
    manifest = payload.get("manifest")
    if isinstance(manifest, dict) and isinstance(manifest.get("skills"), list):
        return [item for item in manifest.get("skills") if isinstance(item, dict)]
    return [payload] if payload.get("key") or payload.get("name") or payload.get("label") else []


def import_skills(payload: Any) -> Dict[str, Any]:
    current = load_config()
    incoming = _extract_skill_payload(payload)
    existing_by_key = {str(item.get("key")): item for item in current.get("skills", []) if item.get("key")}
    imported = []
    skipped = []
    next_order = max([int(item.get("order") or 0) for item in existing_by_key.values()] or [100]) + 10

    for raw in incoming:
        normalized = _normalize_skill(raw, fallback_order=next_order)
        if not normalized:
            skipped.append({"label": str(raw.get("label") or raw.get("name") or ""), "reason": "缺少有效 key/label"})
            continue
        if normalized["key"] in DEFAULT_SKILL_KEYS:
            skipped.append({"key": normalized["key"], "reason": "内置 Skill 不允许通过导入覆盖"})
            continue
        existing_by_key[normalized["key"]] = normalized
        imported.append({"key": normalized["key"], "label": normalized["label"]})
        next_order += 10

    if not imported:
        return {"config": current, "imported": imported, "skipped": skipped}

    current["skills"] = sorted(existing_by_key.values(), key=lambda item: int(item.get("order") or 999))
    saved = save_config(current)
    return {"config": saved, "imported": imported, "skipped": skipped}


def reset_config() -> Dict[str, Any]:
    config = deepcopy(DEFAULT_ADVANCED_CAPABILITIES)
    write_json(ADVANCED_CAPABILITIES_FILE, config)
    return config


def enabled_skills(config: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    current = config or load_config()
    return [item for item in current.get("skills", []) if item.get("enabled")]
