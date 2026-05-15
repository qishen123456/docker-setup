from __future__ import annotations

import time
from typing import Any, Dict, List
from uuid import uuid4
import csv
import io
import re

from config_manager import read_json, write_json


ORG_TREE_FILE = "organization_trees.json"


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _as_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _dedupe_key(value: Any) -> str:
    return _as_text(value).lower()


def _default_data() -> Dict[str, Any]:
    return {
        "version": 1,
        "tree_types": [],
        "nodes": [],
        "updated_at": _now(),
        "updated_by": "",
    }


def _clean_tree_type(item: Dict[str, Any]) -> Dict[str, Any]:
    tree_id = _as_text(item.get("id")) or _new_id("tree")
    code = _as_text(item.get("code")) or tree_id
    return {
        "id": tree_id,
        "name": _as_text(item.get("name")) or "未命名组织树",
        "code": code,
        "description": _as_text(item.get("description")),
        "enabled": bool(item.get("enabled", True)),
        "sort_order": _as_int(item.get("sort_order"), 100),
        "created_at": _as_text(item.get("created_at")) or _now(),
        "updated_at": _as_text(item.get("updated_at")) or _now(),
    }


def _clean_node(item: Dict[str, Any]) -> Dict[str, Any]:
    node_id = _as_text(item.get("id")) or _new_id("node")
    return {
        "id": node_id,
        "tree_type_id": _as_text(item.get("tree_type_id")),
        "parent_id": _as_text(item.get("parent_id")),
        "name": _as_text(item.get("name")) or "未命名节点",
        "code": _as_text(item.get("code")) or node_id,
        "description": _as_text(item.get("description")),
        "enabled": bool(item.get("enabled", True)),
        "sort_order": _as_int(item.get("sort_order"), 100),
        "created_at": _as_text(item.get("created_at")) or _now(),
        "updated_at": _as_text(item.get("updated_at")) or _now(),
        "path_ids": [],
        "path_names": [],
        "level": 1,
    }


def _normalize(data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    raw = data if isinstance(data, dict) else read_json(ORG_TREE_FILE)
    if not isinstance(raw, dict):
        raw = {}

    tree_types: List[Dict[str, Any]] = []
    tree_ids = set()
    tree_codes = set()
    for item in raw.get("tree_types") or []:
        if not isinstance(item, dict):
            continue
        tree = _clean_tree_type(item)
        if tree["id"] in tree_ids:
            continue
        if tree["code"] in tree_codes:
            tree["code"] = f"{tree['code']}_{len(tree_codes) + 1}"
        tree_ids.add(tree["id"])
        tree_codes.add(tree["code"])
        tree_types.append(tree)

    nodes: List[Dict[str, Any]] = []
    node_ids = set()
    node_code_keys = set()
    for item in raw.get("nodes") or []:
        if not isinstance(item, dict):
            continue
        node = _clean_node(item)
        if node["tree_type_id"] not in tree_ids or node["id"] in node_ids:
            continue
        key = (node["tree_type_id"], node["code"])
        if key in node_code_keys:
            node["code"] = f"{node['code']}_{len(node_code_keys) + 1}"
            key = (node["tree_type_id"], node["code"])
        node_ids.add(node["id"])
        node_code_keys.add(key)
        nodes.append(node)

    node_map = {node["id"]: node for node in nodes}
    for node in nodes:
        parent_id = node.get("parent_id") or ""
        parent = node_map.get(parent_id)
        if not parent or parent.get("tree_type_id") != node.get("tree_type_id"):
            node["parent_id"] = ""

    def resolve_path(node: Dict[str, Any], seen: set[str] | None = None) -> tuple[List[str], List[str]]:
        seen = seen or set()
        node_id = node["id"]
        if node_id in seen:
            node["parent_id"] = ""
            return [node_id], [node["name"]]
        parent = node_map.get(node.get("parent_id") or "")
        if not parent:
            return [node_id], [node["name"]]
        parent_ids, parent_names = resolve_path(parent, seen | {node_id})
        return [*parent_ids, node_id], [*parent_names, node["name"]]

    for node in nodes:
        path_ids, path_names = resolve_path(node)
        node["path_ids"] = path_ids
        node["path_names"] = path_names
        node["level"] = len(path_ids)

    return {
        "version": 1,
        "tree_types": sorted(tree_types, key=lambda item: (item["sort_order"], item["created_at"], item["id"])),
        "nodes": sorted(nodes, key=lambda item: (item["tree_type_id"], item["level"], item["sort_order"], item["created_at"], item["id"])),
        "updated_at": _as_text(raw.get("updated_at")) or _now(),
        "updated_by": _as_text(raw.get("updated_by")),
    }


def load_organization_trees() -> Dict[str, Any]:
    return _normalize()


def save_organization_trees(data: Dict[str, Any], operator: str = "") -> Dict[str, Any]:
    normalized = _normalize(data)
    normalized["updated_at"] = _now()
    normalized["updated_by"] = operator
    write_json(ORG_TREE_FILE, normalized)
    return normalized


def tree_nodes(nodes: List[Dict[str, Any]], tree_type_id: str) -> List[Dict[str, Any]]:
    scoped = [dict(node) for node in nodes if node.get("tree_type_id") == tree_type_id]
    by_parent: Dict[str, List[Dict[str, Any]]] = {}
    for node in scoped:
        node["children"] = []
        by_parent.setdefault(node.get("parent_id") or "", []).append(node)
    for children in by_parent.values():
        children.sort(key=lambda item: (item.get("sort_order", 100), item.get("name", "")))
    for node in scoped:
        node["children"] = by_parent.get(node["id"], [])
    return by_parent.get("", [])


def overview() -> Dict[str, Any]:
    data = load_organization_trees()
    types = []
    for tree in data.get("tree_types", []):
        nodes = [node for node in data.get("nodes", []) if node.get("tree_type_id") == tree["id"]]
        types.append({
            **tree,
            "node_count": len(nodes),
            "root_count": sum(1 for node in nodes if not node.get("parent_id")),
            "max_depth": max([int(node.get("level") or 1) for node in nodes] or [0]),
        })
    return {
        **data,
        "tree_types": types,
        "trees": {
            tree["id"]: tree_nodes(data.get("nodes", []), tree["id"])
            for tree in data.get("tree_types", [])
        },
    }


def create_tree_type(payload: Dict[str, Any], operator: str = "") -> Dict[str, Any]:
    data = load_organization_trees()
    tree = _clean_tree_type({**(payload or {}), "id": _as_text((payload or {}).get("id")) or _new_id("tree")})
    if any(item["code"] == tree["code"] for item in data.get("tree_types", [])):
        raise ValueError("组织树编码已存在")
    data["tree_types"].append(tree)
    save_organization_trees(data, operator)
    return tree


def update_tree_type(tree_id: str, payload: Dict[str, Any], operator: str = "") -> Dict[str, Any]:
    data = load_organization_trees()
    for tree in data.get("tree_types", []):
        if tree["id"] != tree_id:
            continue
        next_code = _as_text((payload or {}).get("code")) or tree["code"]
        if any(item["id"] != tree_id and item["code"] == next_code for item in data.get("tree_types", [])):
            raise ValueError("组织树编码已存在")
        tree.update({
            "name": _as_text((payload or {}).get("name")) or tree["name"],
            "code": next_code,
            "description": _as_text((payload or {}).get("description")),
            "enabled": bool((payload or {}).get("enabled", tree.get("enabled", True))),
            "sort_order": _as_int((payload or {}).get("sort_order"), tree.get("sort_order", 100)),
            "updated_at": _now(),
        })
        save_organization_trees(data, operator)
        return tree
    raise ValueError("组织树不存在")


def delete_tree_type(tree_id: str, operator: str = "") -> None:
    data = load_organization_trees()
    if any(node.get("tree_type_id") == tree_id for node in data.get("nodes", [])):
        raise ValueError("该组织树下仍有节点，请先删除节点")
    data["tree_types"] = [tree for tree in data.get("tree_types", []) if tree.get("id") != tree_id]
    save_organization_trees(data, operator)


def create_node(payload: Dict[str, Any], operator: str = "") -> Dict[str, Any]:
    data = load_organization_trees()
    tree_id = _as_text((payload or {}).get("tree_type_id"))
    if not any(tree["id"] == tree_id for tree in data.get("tree_types", [])):
        raise ValueError("组织树不存在")
    node = _clean_node({**(payload or {}), "id": _as_text((payload or {}).get("id")) or _new_id("node")})
    if any(item["tree_type_id"] == tree_id and item["code"] == node["code"] for item in data.get("nodes", [])):
        raise ValueError("同一组织树下节点编码已存在")
    if node.get("parent_id"):
        parent = next((item for item in data.get("nodes", []) if item["id"] == node["parent_id"]), None)
        if not parent or parent.get("tree_type_id") != tree_id:
            raise ValueError("上级节点不属于当前组织树")
    data["nodes"].append(node)
    save_organization_trees(data, operator)
    return next(item for item in load_organization_trees()["nodes"] if item["id"] == node["id"])


def update_node(node_id: str, payload: Dict[str, Any], operator: str = "") -> Dict[str, Any]:
    data = load_organization_trees()
    nodes = data.get("nodes", [])
    node = next((item for item in nodes if item["id"] == node_id), None)
    if not node:
        raise ValueError("组织节点不存在")
    tree_id = node["tree_type_id"]
    next_code = _as_text((payload or {}).get("code")) or node["code"]
    if any(item["id"] != node_id and item["tree_type_id"] == tree_id and item["code"] == next_code for item in nodes):
        raise ValueError("同一组织树下节点编码已存在")
    next_parent_id = _as_text((payload or {}).get("parent_id"))
    if next_parent_id == node_id:
        raise ValueError("上级节点不能是自己")
    if next_parent_id:
        parent = next((item for item in nodes if item["id"] == next_parent_id), None)
        if not parent or parent.get("tree_type_id") != tree_id:
            raise ValueError("上级节点不属于当前组织树")
        if node_id in (parent.get("path_ids") or []):
            raise ValueError("不能把节点移动到自己的下级")
    node.update({
        "parent_id": next_parent_id,
        "name": _as_text((payload or {}).get("name")) or node["name"],
        "code": next_code,
        "description": _as_text((payload or {}).get("description")),
        "enabled": bool((payload or {}).get("enabled", node.get("enabled", True))),
        "sort_order": _as_int((payload or {}).get("sort_order"), node.get("sort_order", 100)),
        "updated_at": _now(),
    })
    save_organization_trees(data, operator)
    return next(item for item in load_organization_trees()["nodes"] if item["id"] == node_id)


def delete_node(node_id: str, operator: str = "") -> None:
    data = load_organization_trees()
    if any(node.get("parent_id") == node_id for node in data.get("nodes", [])):
        raise ValueError("该节点下仍有子节点，请先删除子节点")
    data["nodes"] = [node for node in data.get("nodes", []) if node.get("id") != node_id]
    save_organization_trees(data, operator)


def _parse_import_table(text: str) -> tuple[List[Dict[str, Any]], List[str], Dict[str, int]]:
    raw = _as_text(text).replace("\ufeff", "")
    if not raw:
        return [], ["请粘贴从 Excel 复制出来的组织树表格内容"], {"duplicate_rows": 0, "conflict_rows": 0, "row_count": 0}
    lines = [line for line in raw.splitlines() if line.strip()]
    if not lines:
        return [], ["导入内容为空"], {"duplicate_rows": 0, "conflict_rows": 0, "row_count": 0}
    delimiter = "\t" if "\t" in lines[0] else ","
    reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=delimiter)
    headers = [str(item or "").strip() for item in (reader.fieldnames or [])]
    if not headers:
        return [], ["未识别到表头"], {"duplicate_rows": 0, "conflict_rows": 0, "row_count": 0}

    level_columns: Dict[int, Dict[str, str]] = {}
    for header in headers:
        clean = header.replace(" ", "")
        level_match = re.search(r"(\d+)\s*级", clean)
        if not level_match:
            continue
        level = int(level_match.group(1))
        entry = level_columns.setdefault(level, {})
        lowered = clean.lower()
        if "名称" in clean or "name" in lowered:
            entry["name"] = header
        elif "id" in lowered or "编码" in clean or "code" in lowered:
            entry["code"] = header

    if not level_columns:
        return [], ["未识别到层级列，请使用类似「公司ID（0级）/公司名称（0级）/1级ID/1级名称」的表头"], {"duplicate_rows": 0, "conflict_rows": 0, "row_count": 0}

    errors: List[str] = []
    imported: Dict[str, Dict[str, Any]] = {}
    duplicate_rows = 0
    conflict_rows = 0
    row_count = 0

    for row_index, row in enumerate(reader, start=2):
        row_count += 1
        parent_code = ""
        for level in sorted(level_columns):
            columns = level_columns[level]
            code = _as_text(row.get(columns.get("code", "")))
            name = _as_text(row.get(columns.get("name", "")))
            if not code and not name:
                continue
            if not code or not name:
                errors.append(f"第 {row_index} 行 {level}级缺少{'ID/编码' if not code else '名称'}")
                continue
            key = _dedupe_key(code)
            item = {
                "code": code,
                "name": name,
                "level": level + 1,
                "parent_code": parent_code,
                "sort_order": len(imported) + 1,
            }
            existing = imported.get(key)
            if existing:
                if existing["name"] != item["name"] or existing.get("parent_code") != item.get("parent_code"):
                    conflict_rows += 1
                    errors.append(f"第 {row_index} 行节点编码 {code} 重复但名称或上级不一致")
                else:
                    duplicate_rows += 1
            else:
                imported[key] = item
            parent_code = code

    nodes = sorted(imported.values(), key=lambda item: (item["level"], item["sort_order"], item["code"]))
    return nodes, [
        *errors,
        *([] if nodes else ["未解析到任何组织节点"]),
        *([] if row_count else ["表格没有数据行"]),
    ], {"duplicate_rows": duplicate_rows, "conflict_rows": conflict_rows, "row_count": row_count}


def _target_tree(data: Dict[str, Any], payload: Dict[str, Any]) -> tuple[Dict[str, Any] | None, str]:
    tree_id = _as_text(payload.get("tree_type_id"))
    tree = next((item for item in data.get("tree_types", []) if item.get("id") == tree_id), None)
    if tree:
        return tree, "existing"
    name = _as_text(payload.get("tree_type_name")) or _as_text(payload.get("name"))
    code = _as_text(payload.get("tree_type_code")) or _as_text(payload.get("code"))
    if not name or not code:
        return None, "missing"
    existing_by_code = next((item for item in data.get("tree_types", []) if item.get("code") == code), None)
    if existing_by_code:
        return existing_by_code, "existing_by_code"
    return _clean_tree_type({"name": name, "code": code, "description": _as_text(payload.get("description"))}), "create"


def preview_import(payload: Dict[str, Any]) -> Dict[str, Any]:
    mode = _as_text(payload.get("mode") or "merge")
    if mode not in {"merge", "replace"}:
        mode = "merge"
    data = load_organization_trees()
    tree, tree_action = _target_tree(data, payload)
    parsed = _parse_import_table(_as_text(payload.get("text")))
    imported_nodes, errors, parse_stats = parsed
    if not tree:
        errors.append("请选择已有组织树，或填写新组织树名称和编码")
        tree_id = ""
    else:
        tree_id = tree["id"]

    current_nodes = [node for node in data.get("nodes", []) if tree_id and node.get("tree_type_id") == tree_id]
    current_by_code = {_dedupe_key(node.get("code")): node for node in current_nodes}
    imported_by_code = {_dedupe_key(node.get("code")): node for node in imported_nodes}
    changes: List[Dict[str, Any]] = []
    stats = {
        "create": 0,
        "update": 0,
        "unchanged": 0,
        "delete": 0,
        "duplicates": parse_stats.get("duplicate_rows", 0),
        "conflicts": parse_stats.get("conflict_rows", 0),
        "rows": parse_stats.get("row_count", 0),
        "parsed_nodes": len(imported_nodes),
    }

    for item in imported_nodes:
        existing = current_by_code.get(_dedupe_key(item["code"]))
        parent = imported_by_code.get(_dedupe_key(item.get("parent_code")))
        next_parent_code = parent.get("code") if parent else ""
        if not existing:
            stats["create"] += 1
            changes.append({"action": "create", "code": item["code"], "name": item["name"], "parent_code": next_parent_code})
            continue
        current_parent = next((node for node in current_nodes if node.get("id") == existing.get("parent_id")), None)
        current_parent_code = current_parent.get("code") if current_parent else ""
        diffs = []
        if existing.get("name") != item["name"]:
            diffs.append(f"名称：{existing.get('name')} -> {item['name']}")
        if current_parent_code != next_parent_code:
            diffs.append(f"上级：{current_parent_code or '根节点'} -> {next_parent_code or '根节点'}")
        if diffs:
            stats["update"] += 1
            changes.append({"action": "update", "code": item["code"], "name": item["name"], "parent_code": next_parent_code, "diffs": diffs})
        else:
            stats["unchanged"] += 1

    if mode == "replace":
        for node in current_nodes:
            if _dedupe_key(node.get("code")) not in imported_by_code:
                stats["delete"] += 1
                changes.append({"action": "delete", "code": node.get("code"), "name": node.get("name"), "parent_code": ""})

    return {
        "mode": mode,
        "tree_type": tree,
        "tree_action": tree_action,
        "stats": stats,
        "changes": changes[:500],
        "change_count": len(changes),
        "errors": errors,
        "can_apply": bool(tree and imported_nodes and not errors),
    }


def apply_import(payload: Dict[str, Any], operator: str = "") -> Dict[str, Any]:
    preview = preview_import(payload)
    if not preview.get("can_apply"):
        raise ValueError("预检未通过，不能导入")

    mode = preview["mode"]
    data = load_organization_trees()
    tree, tree_action = _target_tree(data, payload)
    if not tree:
        raise ValueError("组织树不存在")
    if tree_action == "create":
        data["tree_types"].append(tree)
    tree_id = tree["id"]

    imported_nodes, _, _ = _parse_import_table(_as_text(payload.get("text")))
    imported_by_code = {_dedupe_key(item.get("code")): item for item in imported_nodes}
    other_nodes = [node for node in data.get("nodes", []) if node.get("tree_type_id") != tree_id]
    current_nodes = [node for node in data.get("nodes", []) if node.get("tree_type_id") == tree_id]
    current_by_code = {_dedupe_key(node.get("code")): node for node in current_nodes}

    result_nodes: List[Dict[str, Any]] = []
    id_by_code: Dict[str, str] = {}
    for item in imported_nodes:
        existing = current_by_code.get(_dedupe_key(item["code"]))
        node_id = existing.get("id") if existing else _new_id("node")
        id_by_code[_dedupe_key(item["code"])] = node_id

    for item in imported_nodes:
        existing = current_by_code.get(_dedupe_key(item["code"])) or {}
        parent_id = id_by_code.get(_dedupe_key(item.get("parent_code")))
        result_nodes.append({
            **existing,
            "id": id_by_code[_dedupe_key(item["code"])],
            "tree_type_id": tree_id,
            "parent_id": parent_id or "",
            "name": item["name"],
            "code": item["code"],
            "description": existing.get("description", ""),
            "enabled": existing.get("enabled", True),
            "sort_order": item.get("sort_order") or existing.get("sort_order") or 100,
            "created_at": existing.get("created_at") or _now(),
            "updated_at": _now(),
        })

    if mode == "merge":
        imported_keys = set(imported_by_code.keys())
        preserved = [node for node in current_nodes if _dedupe_key(node.get("code")) not in imported_keys]
        result_nodes = [*preserved, *result_nodes]

    data["nodes"] = [*other_nodes, *result_nodes]
    saved = save_organization_trees(data, operator)
    return {"preview": preview, **overview()}
