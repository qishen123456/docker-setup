from __future__ import annotations

from typing import Any, Dict, List

from .config_store import enabled_skills, load_config


def build_skill_plan(config: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    """Return the enabled advanced capability chain in deterministic order."""

    current = config or load_config()
    return enabled_skills(current)


def capability_summary(config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    current = config or load_config()
    skills = build_skill_plan(current)
    return {
        "enabled": bool(current.get("enabled")),
        "skill_count": len(skills),
        "skills": [{"key": item.get("key"), "label": item.get("label")} for item in skills],
        "mcp_enabled": bool((current.get("mcp") or {}).get("enabled")),
        "sql_server_enabled": bool((current.get("sqlServer") or {}).get("enabled")),
        "preserve_final_report_contract": bool((current.get("execution") or {}).get("preserveFinalReportContract", True)),
    }
