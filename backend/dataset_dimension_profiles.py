import json
import os
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_PATH = os.path.join(CURRENT_DIR, "data", "dataset_dimension_profiles.json")


def _normalize(text: Any) -> str:
    return re.sub(r"\s+", "", str(text or "")).lower()


@lru_cache(maxsize=1)
def load_dataset_profiles() -> Dict[str, Dict[str, Any]]:
    if not os.path.exists(PROFILE_PATH):
        return {}
    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def get_dataset_profile(dataset_code: str = "", dataset_name: str = "") -> Optional[Dict[str, Any]]:
    profiles = load_dataset_profiles()
    if dataset_code and dataset_code in profiles:
        profile = dict(profiles[dataset_code])
        profile.setdefault("dataset_code", dataset_code)
        return profile

    normalized_name = _normalize(dataset_name)
    for code, raw_profile in profiles.items():
        aliases = [raw_profile.get("dataset_name", ""), *(raw_profile.get("dataset_aliases") or [])]
        if normalized_name and normalized_name in {_normalize(item) for item in aliases if item}:
            profile = dict(raw_profile)
            profile.setdefault("dataset_code", code)
            return profile
    return None


def find_group_matches(question: str, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    text = str(question or "")
    normalized_text = _normalize(text)
    matches: List[Dict[str, Any]] = []
    for level in profile.get("levels") or []:
        dimension_name = str(level.get("dimension_name") or "").strip()
        for group in level.get("groups") or []:
            aliases = [group.get("group_name", ""), *(group.get("aliases") or [])]
            matched_alias = next(
                (
                    str(alias).strip()
                    for alias in aliases
                    if alias and _normalize(alias) and _normalize(alias) in normalized_text
                ),
                "",
            )
            if not matched_alias:
                continue
            members = [str(item).strip() for item in (group.get("members") or []) if str(item).strip()]
            matches.append(
                {
                    "group_name": str(group.get("group_name") or matched_alias).strip(),
                    "group_key": _normalize(group.get("group_name") or matched_alias),
                    "matched_alias": matched_alias,
                    "dimension_name": dimension_name,
                    "members": members,
                    "description": str(group.get("description") or "").strip(),
                }
            )
    return matches
