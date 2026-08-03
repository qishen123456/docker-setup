from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Set


def resolve_target_level(
    text: str,
    config: Dict[str, Any],
    ranking_policy: Dict[str, Any],
    *,
    safe_dict: Callable[[Any], Dict[str, Any]],
) -> str:
    root_values: Set[str] = {
        str(dimension.get("path")[0]).strip()
        for dimension in (config.get("analysisDimensions") or [])
        if isinstance(dimension.get("path") or [], list) and (dimension.get("path") or [])
    }
    level_values = {
        "事业部", "分公司", "业务部", "代表处", "业务代表",
        "城市分公司", "城市公司", "区域条线", "行业条线",
    }
    level_pattern = "|".join(re.escape(level) for level in sorted(level_values, key=len, reverse=True))
    child_match = re.search(rf"(?:的|之下|下面|下属)\s*({level_pattern})\b", text)
    if child_match:
        return child_match.group(1)

    aliases = safe_dict(ranking_policy.get("targetLevelAliases"))
    matches: List[Dict[str, Any]] = []
    for level, level_aliases in aliases.items():
        candidates = [str(level)] + [str(item) for item in (level_aliases or [])]
        if str(level) == "城市分公司":
            candidates.append("城市分公司")
        for candidate in candidates:
            if not candidate:
                continue
            pos = text.rfind(candidate)
            if pos != -1:
                matches.append({"candidate": candidate, "level": str(level), "pos": pos, "is_root": str(level) in root_values})
    if "城市分公司" in text and "城市分公司" not in {item["candidate"] for item in matches}:
        matches.append({"candidate": "城市分公司", "level": "城市分公司", "pos": text.rfind("城市分公司"), "is_root": False})
    for dimension in config.get("analysisDimensions") or []:
        for level in dimension.get("path") or []:
            if level and str(level) in text:
                matches.append({"candidate": str(level), "level": str(level), "pos": text.rfind(str(level)), "is_root": str(level) in root_values})
    if not matches:
        return ""
    non_root = [item for item in matches if not item["is_root"]]
    pool = non_root if non_root else matches
    exact = []
    for item in pool:
        candidate = item["candidate"]
        contained = any(
            other["candidate"] != candidate
            and candidate in other["candidate"]
            and abs(other["pos"] - item["pos"]) < len(other["candidate"])
            for other in pool
        )
        if not contained:
            exact.append(item)
    if exact:
        pool = exact
    return max(pool, key=lambda item: (item["pos"], len(item["candidate"])))["level"]
