from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from bookshelf_repository import BookshelfRepository
from datasource_router import DataSourceRouter
from four_agent_ask import FourAgentAskService


OUTPUT_PATH = Path(__file__).resolve().parent.parent / "config" / "dataset_node_index.json"
TARGET_DATASET_IDS = (2, 3, 62)

LEVEL_SUFFIXES = [
    "城市分公司",
    "城市公司",
    "业务承接角色",
    "业务经理",
    "业务代表",
    "业务员",
    "代表处",
    "分公司",
    "业务部",
    "事业部",
]


def _extract_jsonb_text(field_name: str) -> str:
    return (
        "TRIM(COALESCE("
        f"CASE WHEN jsonb_typeof(fields->'{field_name}') = 'array' "
        f"THEN fields->'{field_name}'->0->>'text' ELSE fields->>'{field_name}' END, "
        "'')"
        ")"
    )


def _consumer_nodes_sql() -> str:
    year_expr = _extract_jsonb_text("当前年")
    division_expr = _extract_jsonb_text("事业部")
    branch_expr = _extract_jsonb_text("分公司")
    city_expr = _extract_jsonb_text("城市分公司")
    return f"""
WITH base AS (
    SELECT
        {division_expr} AS 事业部,
        {branch_expr} AS 分公司,
        {city_expr} AS 城市分公司
    FROM feishu_tbl_xioafeizhe
    WHERE COALESCE(NULLIF({year_expr}, ''), '2026') = '2026'
),
nodes AS (
    SELECT DISTINCT
        '事业部' AS node_level,
        COALESCE(NULLIF(事业部, ''), '消费者事业部') AS node_name,
        NULL::TEXT AS parent_name,
        '消费者经营链路' AS track
    FROM base
    UNION ALL
    SELECT DISTINCT
        '分公司' AS node_level,
        分公司 AS node_name,
        COALESCE(NULLIF(事业部, ''), '消费者事业部') AS parent_name,
        '消费者经营链路' AS track
    FROM base
    WHERE 分公司 <> ''
    UNION ALL
    SELECT DISTINCT
        '城市分公司' AS node_level,
        城市分公司 AS node_name,
        分公司 AS parent_name,
        '消费者经营链路' AS track
    FROM base
    WHERE 城市分公司 <> ''
)
SELECT node_level, node_name, parent_name, track
FROM (
    SELECT DISTINCT node_level, node_name, parent_name, track
    FROM nodes
    WHERE node_name <> ''
) dedup
ORDER BY
    CASE node_level
        WHEN '事业部' THEN 0
        WHEN '分公司' THEN 1
        WHEN '城市分公司' THEN 2
        ELSE 9
    END,
    parent_name NULLS FIRST,
    node_name;
""".strip()


def _ecommerce_nodes_sql() -> str:
    return """
WITH nodes AS (
    SELECT DISTINCT
        '事业部' AS node_level,
        COALESCE(NULLIF(TRIM(事业部), ''), '电商事业部') AS node_name,
        NULL::TEXT AS parent_name,
        '电商业务' AS track
    FROM v_feishu_tbldianshang
    UNION ALL
    SELECT DISTINCT
        '业务部' AS node_level,
        TRIM(业务部) AS node_name,
        COALESCE(NULLIF(TRIM(事业部), ''), '电商事业部') AS parent_name,
        '电商业务' AS track
    FROM v_feishu_tbldianshang
    WHERE COALESCE(TRIM(业务部), '') <> ''
    UNION ALL
    SELECT DISTINCT
        '业务承接角色' AS node_level,
        TRIM(细分业务) AS node_name,
        TRIM(业务部) AS parent_name,
        '电商业务' AS track
    FROM v_feishu_tbldianshang
    WHERE COALESCE(TRIM(细分业务), '') <> ''
    UNION ALL
    SELECT DISTINCT
        '承接人' AS node_level,
        TRIM(负责人) AS node_name,
        COALESCE(NULLIF(TRIM(细分业务), ''), NULLIF(TRIM(业务部), ''), COALESCE(NULLIF(TRIM(事业部), ''), '电商事业部')) AS parent_name,
        '电商业务' AS track
    FROM v_feishu_tbldianshang
    WHERE COALESCE(TRIM(负责人), '') <> ''
)
SELECT node_level, node_name, parent_name, track
FROM (
    SELECT DISTINCT node_level, node_name, parent_name, track
    FROM nodes
    WHERE node_name <> ''
) dedup
ORDER BY
    CASE node_level
        WHEN '事业部' THEN 0
        WHEN '业务部' THEN 1
        WHEN '业务承接角色' THEN 2
        WHEN '承接人' THEN 3
        ELSE 9
    END,
    parent_name NULLS FIRST,
    node_name;
""".strip()


def _commercial_nodes_sql(service: FourAgentAskService, context: Dict[str, Any]) -> str:
    base_sql = service._build_syyb_base_sql(context)
    return f"""
WITH summary AS (
{base_sql}
)
SELECT node_level, node_name, parent_name, track
FROM (
    SELECT DISTINCT
        层级 AS node_level,
        节点名称 AS node_name,
        上级名称 AS parent_name,
        条线 AS track
    FROM summary
    WHERE COALESCE(节点名称, '') <> ''
) dedup
ORDER BY
    CASE node_level
        WHEN '事业部' THEN 0
        WHEN '分公司' THEN 1
        WHEN '业务部' THEN 1
        WHEN '代表处' THEN 2
        WHEN '业务代表' THEN 3
        WHEN '业务员' THEN 3
        ELSE 9
    END,
    parent_name NULLS FIRST,
    node_name;
""".strip()


def _build_aliases(node_name: str) -> List[str]:
    aliases: List[str] = []

    def add_alias(value: str) -> None:
        normalized = str(value or "").strip()
        if normalized and normalized not in aliases:
            aliases.append(normalized)

    add_alias(node_name)
    base = str(node_name or "").strip()
    for suffix in LEVEL_SUFFIXES:
        if base.endswith(suffix) and len(base) > len(suffix):
            add_alias(base[: -len(suffix)].strip())
    return aliases


def _normalize_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip() if value is not None else ""
    if text.lower() == "nan":
        return None
    return text or None


def _build_dataset_nodes(
    dataset_id: int,
    dataset_name: str,
    source_id: int,
    sql: str,
    router: DataSourceRouter,
) -> Dict[str, Any]:
    dataframe = router.execute_sql_for_source(source_id, sql)
    nodes: List[Dict[str, Any]] = []
    alias_index: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    seen_keys = set()

    for row in dataframe.to_dict(orient="records"):
        node_level = _normalize_value(row.get("node_level")) or ""
        node_name = _normalize_value(row.get("node_name")) or ""
        parent_name = _normalize_value(row.get("parent_name"))
        track = _normalize_value(row.get("track"))
        if not node_name:
            continue
        node_key = (node_level, node_name, parent_name, track)
        if node_key in seen_keys:
            continue
        seen_keys.add(node_key)
        aliases = _build_aliases(node_name)
        node = {
            "node_name": node_name,
            "node_level": node_level,
            "parent_name": parent_name,
            "track": track,
            "aliases": aliases,
            "match_key": node_name,
        }
        nodes.append(node)
        for alias in aliases:
            alias_index[alias].append(
                {
                    "node_name": node_name,
                    "node_level": node_level,
                    "parent_name": parent_name,
                    "track": track,
                }
            )

    sorted_alias_index = [
        {
            "alias": alias,
            "matches": sorted(
                matches,
                key=lambda item: (
                    str(item.get("node_level") or ""),
                    str(item.get("parent_name") or ""),
                    str(item.get("node_name") or ""),
                ),
            ),
        }
        for alias, matches in sorted(alias_index.items(), key=lambda item: item[0])
    ]

    return {
        "dataset_id": dataset_id,
        "dataset_name": dataset_name,
        "source_id": source_id,
        "node_count": len(nodes),
        "alias_count": len(sorted_alias_index),
        "nodes": nodes,
        "alias_index": sorted_alias_index,
    }


def _dataset_sql_map(service: FourAgentAskService, contexts: Dict[int, Dict[str, Any]]) -> Dict[int, str]:
    return {
        2: _consumer_nodes_sql(),
        3: _commercial_nodes_sql(service, contexts[3]),
        62: _ecommerce_nodes_sql(),
    }


def _flatten_alias_index(datasets: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    seen = set()
    for dataset in datasets:
        dataset_id = dataset["dataset_id"]
        dataset_name = dataset["dataset_name"]
        for alias_item in dataset["alias_index"]:
            alias = alias_item["alias"]
            for match in alias_item["matches"]:
                payload = {
                    "dataset_id": dataset_id,
                    "dataset_name": dataset_name,
                    "node_name": match.get("node_name"),
                    "node_level": match.get("node_level"),
                    "parent_name": match.get("parent_name"),
                    "track": match.get("track"),
                }
                key = (
                    alias,
                    payload["dataset_id"],
                    payload["node_name"],
                    payload["node_level"],
                    payload["parent_name"],
                    payload["track"],
                )
                if key in seen:
                    continue
                seen.add(key)
                merged[alias].append(payload)

    return [
        {
            "alias": alias,
            "matches": sorted(
                matches,
                key=lambda item: (
                    int(item.get("dataset_id") or 0),
                    str(item.get("node_level") or ""),
                    str(item.get("parent_name") or ""),
                    str(item.get("node_name") or ""),
                ),
            ),
        }
        for alias, matches in sorted(merged.items(), key=lambda item: item[0])
    ]


def main() -> None:
    repository = BookshelfRepository()
    router = DataSourceRouter()
    service = FourAgentAskService()

    contexts = {
        dataset_id: repository.get_dataset_context(dataset_id, "节点索引构建")
        for dataset_id in TARGET_DATASET_IDS
    }
    sql_map = _dataset_sql_map(service, contexts)

    datasets: List[Dict[str, Any]] = []
    for dataset_id in TARGET_DATASET_IDS:
        context = contexts[dataset_id]
        dataset_meta = context.get("dataset") or {}
        datasets.append(
            _build_dataset_nodes(
                dataset_id=dataset_id,
                dataset_name=str(dataset_meta.get("dataset_name") or ""),
                source_id=int(dataset_meta.get("source_id") or 0),
                sql=sql_map[dataset_id],
                router=router,
            )
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_ids": list(TARGET_DATASET_IDS),
        "datasets": datasets,
        "flat_alias_index": _flatten_alias_index(datasets),
    }

    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUTPUT_PATH}")
    for dataset in datasets:
        print(
            f"dataset={dataset['dataset_id']} "
            f"nodes={dataset['node_count']} aliases={dataset['alias_count']}"
        )


if __name__ == "__main__":
    main()
