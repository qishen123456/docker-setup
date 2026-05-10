import json
import os
import re
from functools import lru_cache
from itertools import permutations
from typing import Any, Dict, List, Optional

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_PATH = os.path.join(CURRENT_DIR, "data", "dataset_dimension_profiles.json")


def _normalize(text: Any) -> str:
    return re.sub(r"[\s,，、/\\|()（）【】\[\]{}<>《》“”\"'：:；;.!！?？-]+", "", str(text or "")).lower()


def _ordered_unique(items: List[str]) -> List[str]:
    output: List[str] = []
    seen = set()
    for item in items:
        value = str(item or "").strip()
        key = _normalize(value)
        if not value or key in seen:
            continue
        seen.add(key)
        output.append(value)
    return output


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

    normalized_code = _normalize(dataset_code)
    for code, raw_profile in profiles.items():
        base_code = _normalize(code)
        if normalized_code and normalized_code.startswith(f"{base_code}_"):
            profile = dict(raw_profile)
            profile.setdefault("dataset_code", code)
            profile.setdefault("matched_dataset_code", dataset_code)
            return profile

    normalized_name = _normalize(dataset_name)
    for code, raw_profile in profiles.items():
        aliases = [raw_profile.get("dataset_name", ""), *(raw_profile.get("dataset_aliases") or [])]
        alias_keys = {_normalize(item) for item in aliases if item}
        if normalized_name and (
            normalized_name in alias_keys
            or any(alias and alias in normalized_name for alias in alias_keys)
        ):
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


def _member_alias_items(level: Dict[str, Any]) -> List[Dict[str, Any]]:
    dimension_name = str(level.get("dimension_name") or "").strip()
    suffixes = _ordered_unique([dimension_name, *(level.get("aliases") or [])])
    items: List[Dict[str, Any]] = []

    for member in _ordered_unique([str(item) for item in (level.get("members") or [])]):
        aliases = [{"alias": member, "exact": True}]
        for suffix in sorted(suffixes, key=len, reverse=True):
            if not suffix or not member.endswith(suffix) or len(member) <= len(suffix):
                continue
            short = member[: -len(suffix)].strip()
            if short:
                aliases.append({"alias": short, "exact": len(short) >= 2})
                if len(short) >= 2:
                    unit = short[-1]
                    root = short[:-1]
                    if root:
                        aliases.append({"alias": root, "exact": False, "root": root, "unit": unit})
        for alias in aliases:
            alias_text = str(alias.get("alias") or "").strip()
            alias_norm = _normalize(alias_text)
            if not alias_text or not alias_norm:
                continue
            items.append(
                {
                    "member": member,
                    "dimension_name": dimension_name,
                    "alias": alias_text,
                    "alias_norm": alias_norm,
                    "exact": bool(alias.get("exact")),
                    "root": str(alias.get("root") or "").strip(),
                    "unit": str(alias.get("unit") or "").strip(),
                }
            )
    return items


def _add_match(
    matches: List[Dict[str, Any]],
    member: str,
    dimension_name: str,
    matched_alias: str,
    position: int,
    source: str,
) -> None:
    if not member:
        return
    matches.append(
        {
            "member": member,
            "dimension_name": dimension_name,
            "matched_alias": matched_alias,
            "position": max(position, 0),
            "source": source,
        }
    )


def _match_compound_aliases(normalized_text: str, level: Dict[str, Any], items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    dimension_name = str(level.get("dimension_name") or "").strip()
    compound_items = [
        item for item in items
        if item.get("root") and item.get("unit") and len(str(item.get("root"))) <= 2
    ]
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in compound_items:
        grouped.setdefault(str(item.get("unit")), []).append(item)

    matches: List[Dict[str, Any]] = []
    for unit, group in grouped.items():
        unique_group = []
        seen_members = set()
        for item in group:
            member_key = _normalize(item.get("member"))
            if member_key in seen_members:
                continue
            seen_members.add(member_key)
            unique_group.append(item)
        if len(unique_group) < 2 or len(unique_group) > 8:
            continue

        max_size = min(4, len(unique_group))
        suffixes = _ordered_unique([dimension_name, *(level.get("aliases") or [])])
        for size in range(2, max_size + 1):
            for ordered in permutations(unique_group, size):
                roots = "".join(str(item.get("root") or "") for item in ordered)
                aliases = "".join(str(item.get("alias") or "") for item in ordered)
                phrases = _ordered_unique(
                    [
                        f"{roots}{unit}",
                        *[f"{roots}{unit}{suffix}" for suffix in suffixes if suffix],
                        *[f"{roots}{suffix}" for suffix in suffixes if suffix],
                        aliases,
                        *[f"{aliases}{suffix}" for suffix in suffixes if suffix],
                    ]
                )
                phrase = next((item for item in phrases if _normalize(item) in normalized_text), "")
                if not phrase:
                    continue
                position = normalized_text.find(_normalize(phrase))
                for offset, item in enumerate(ordered):
                    _add_match(
                        matches,
                        str(item.get("member") or ""),
                        dimension_name,
                        phrase,
                        position * 10 + offset,
                        "profile_compound_alias",
                    )
                return matches
    return matches


def resolve_member_mentions(question: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    text = str(question or "")
    normalized_text = _normalize(text)
    matches: List[Dict[str, Any]] = []

    for group_match in find_group_matches(text, profile):
        members = [str(item).strip() for item in (group_match.get("members") or []) if str(item).strip()]
        if not members:
            continue
        position = normalized_text.find(_normalize(group_match.get("matched_alias")))
        for offset, member in enumerate(members):
            _add_match(
                matches,
                member,
                str(group_match.get("dimension_name") or ""),
                str(group_match.get("matched_alias") or group_match.get("group_name") or ""),
                (position if position >= 0 else 0) * 10 + offset,
                "profile_group_alias",
            )

    for level in profile.get("levels") or []:
        items = _member_alias_items(level)
        for item in items:
            if not item.get("exact"):
                continue
            alias_norm = str(item.get("alias_norm") or "")
            if alias_norm and alias_norm in normalized_text:
                _add_match(
                    matches,
                    str(item.get("member") or ""),
                    str(item.get("dimension_name") or ""),
                    str(item.get("alias") or ""),
                    normalized_text.find(alias_norm) * 10,
                    "profile_alias",
                )
        matches.extend(_match_compound_aliases(normalized_text, level, items))

    grouped: Dict[str, Dict[str, Any]] = {}
    for match in matches:
        member_key = _normalize(match.get("member"))
        existing = grouped.get(member_key)
        if not existing or int(match.get("position", 999999)) < int(existing.get("position", 999999)):
            grouped[member_key] = match

    ordered_matches = sorted(grouped.values(), key=lambda item: int(item.get("position", 999999)))
    members = [str(item.get("member") or "").strip() for item in ordered_matches if str(item.get("member") or "").strip()]
    dimensions = []
    for item in ordered_matches:
        dimension_name = str(item.get("dimension_name") or "").strip()
        if not dimension_name:
            continue
        bucket = next((entry for entry in dimensions if entry.get("dimension_name") == dimension_name), None)
        if not bucket:
            bucket = {
                "dimension_name": dimension_name,
                "members": [],
                "matched_aliases": [],
                "source": "profile_semantic",
            }
            dimensions.append(bucket)
        bucket["members"].append(str(item.get("member") or "").strip())
        bucket["matched_aliases"].append(str(item.get("matched_alias") or "").strip())

    comparative = len(members) > 1 or bool(re.search(r"对比|比较|分别|各自|哪个|谁更|差异|和.+比|跟.+比|与.+比|\bvs\b", text, re.I))
    return {
        "intent": "compare" if comparative and members else ("single" if members else "unknown"),
        "scope_mode": "compare" if comparative and len(members) > 1 else ("single" if len(members) == 1 else "unknown"),
        "entities": [
            {
                **entry,
                "members": _ordered_unique(entry.get("members") or []),
                "matched_aliases": _ordered_unique(entry.get("matched_aliases") or []),
            }
            for entry in dimensions
        ],
        "all_members": _ordered_unique(members),
        "confidence": 0.72 if members else 0,
        "source": "profile_semantic",
    }
