from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from bookshelf_repository import BookshelfRepository
from datasource_router import DataSourceRouter
from dataset_copilot.syyb_rule_generator import BASE_SQL as SYYB_BASE_SQL


OUTPUT_PATH = Path(__file__).resolve().parent.parent / "config" / "dataset_node_index.json"
SUPPORTED_DATASET_CODES = (
    "consumer_business_standard_v1",
    "angel_business_2026_phase1",
    "feishu_tbldianshang",
    "feishu_tblyongfukaidan",
)
SOURCE_TABLE_TO_DATASET_CODES = {
    "feishu_tbl_xioafeizhe": ["consumer_business_standard_v1"],
    "angel_group_data": ["angel_business_2026_phase1"],
    "feishu_tbldianshang": ["feishu_tbldianshang"],
    "feishu_tblyongfukaidan": ["feishu_tblyongfukaidan"],
}

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

# 节点索引自动别名只按后缀剥离生成，业务惯用简称需在此显式补充
# key: (dataset_code, node_name) → 额外别名
EXTRA_NODE_ALIASES = {
    ("feishu_tblyongfukaidan", "用户服务与运营事业部"): ["用服事业部", "用服"],
    # 用服视图分公司列已去除"用户服务与运营"后缀（如"粤桂琼分公司"），与其他数据集同名，
    # 同名时进入多数据集消歧确认；补"X用服"别名供口语指向用服
    ("feishu_tblyongfukaidan", "粤桂琼分公司"): ["粤桂琼用服"],
    ("feishu_tblyongfukaidan", "豫晋分公司"): ["豫晋用服"],
    ("feishu_tblyongfukaidan", "鄂皖分公司"): ["鄂皖用服"],
    ("feishu_tblyongfukaidan", "湖南分公司"): ["湖南用服"],
    ("feishu_tblyongfukaidan", "河北分公司"): ["河北用服"],
    ("feishu_tblyongfukaidan", "赣闽分公司"): ["赣闽用服"],
    ("feishu_tblyongfukaidan", "云贵渝分公司"): ["云贵渝用服"],
    ("feishu_tblyongfukaidan", "西北分公司"): ["西北用服"],
    ("feishu_tblyongfukaidan", "江浙沪分公司"): ["江浙沪用服"],
    ("feishu_tblyongfukaidan", "黑吉辽分公司"): ["黑吉辽用服"],
    ("feishu_tblyongfukaidan", "京津分公司"): ["京津用服"],
    ("feishu_tblyongfukaidan", "川藏分公司"): ["川藏用服"],
    ("feishu_tblyongfukaidan", "山东分公司"): ["山东用服"],
}


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


def _yongfu_nodes_sql() -> str:
    return """
WITH nodes AS (
    SELECT DISTINCT
        '事业部' AS node_level,
        COALESCE(NULLIF(TRIM(事业部), ''), '用户服务与运营事业部') AS node_name,
        NULL::TEXT AS parent_name,
        '用服经营链路' AS track
    FROM v_feishu_tblyongfukaidan
    WHERE 层级级别 = '事业部'
    UNION ALL
    SELECT DISTINCT
        '分公司' AS node_level,
        TRIM(分公司) AS node_name,
        COALESCE(NULLIF(TRIM(事业部), ''), '用户服务与运营事业部') AS parent_name,
        '用服经营链路' AS track
    FROM v_feishu_tblyongfukaidan
    WHERE 层级级别 = '分公司' AND COALESCE(TRIM(分公司), '') <> ''
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
        ELSE 9
    END,
    parent_name NULLS FIRST,
    node_name;
""".strip()


def _build_syyb_base_sql(context: Dict[str, Any]) -> str:
    dictionary_keys = {
        str(item.get("jsonb_key") or "").strip()
        for item in context.get("data_dictionary", []) or []
        if str(item.get("jsonb_key") or "").strip()
    }
    if "业务部" in dictionary_keys:
        return SYYB_BASE_SQL
    return SYYB_BASE_SQL.replace(
        "TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务部') = 'array' THEN fields->'业务部'->0->>'text' ELSE fields->>'业务部' END, '')) AS 业务部,",
        "'' AS 业务部,",
    )


def _commercial_nodes_sql(context: Dict[str, Any]) -> str:
    base_sql = _build_syyb_base_sql(context)
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


def _normalize_table_name(table_name: str) -> str:
    return str(table_name or "").strip().lower()


def affected_dataset_codes_for_source_table(source_table: str) -> List[str]:
    return list(SOURCE_TABLE_TO_DATASET_CODES.get(_normalize_table_name(source_table), []))


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
    dataset_code: str,
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
        for extra in EXTRA_NODE_ALIASES.get((dataset_code, node_name), []):
            if extra not in aliases:
                aliases.append(extra)
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
        "dataset_code": dataset_code,
        "dataset_name": dataset_name,
        "source_id": source_id,
        "node_count": len(nodes),
        "alias_count": len(sorted_alias_index),
        "nodes": nodes,
        "alias_index": sorted_alias_index,
    }


def _flatten_alias_index(datasets: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    seen = set()
    for dataset in datasets:
        dataset_id = dataset["dataset_id"]
        dataset_name = dataset["dataset_name"]
        dataset_code = dataset.get("dataset_code")
        for alias_item in dataset["alias_index"]:
            alias = alias_item["alias"]
            for match in alias_item["matches"]:
                payload = {
                    "dataset_id": dataset_id,
                    "dataset_code": dataset_code,
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


def _load_existing_datasets() -> List[Dict[str, Any]]:
    if not OUTPUT_PATH.exists():
        return []
    try:
        payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    datasets = payload.get("datasets")
    return [item for item in datasets if isinstance(item, dict)] if isinstance(datasets, list) else []


def _sort_datasets(datasets: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        datasets,
        key=lambda item: (
            int(item.get("dataset_id") or 0),
            str(item.get("dataset_code") or ""),
            str(item.get("dataset_name") or ""),
        ),
    )


def merge_dataset_entries(
    existing_datasets: Iterable[Dict[str, Any]],
    rebuilt_datasets: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rebuilt_list = [dict(item) for item in rebuilt_datasets if isinstance(item, dict)]
    rebuilt_codes = {str(item.get("dataset_code") or "").strip() for item in rebuilt_list if str(item.get("dataset_code") or "").strip()}
    rebuilt_ids = {int(item.get("dataset_id") or 0) for item in rebuilt_list if int(item.get("dataset_id") or 0)}

    preserved: List[Dict[str, Any]] = []
    for item in existing_datasets:
        if not isinstance(item, dict):
            continue
        dataset_code = str(item.get("dataset_code") or "").strip()
        dataset_id = int(item.get("dataset_id") or 0)
        if (dataset_code and dataset_code in rebuilt_codes) or (dataset_id and dataset_id in rebuilt_ids):
            continue
        preserved.append(dict(item))

    return _sort_datasets([*preserved, *rebuilt_list])


def _resolve_active_dataset_rows(
    repository: BookshelfRepository,
    dataset_codes: Iterable[str],
) -> Dict[str, Dict[str, Any]]:
    target_codes = {str(code).strip() for code in dataset_codes if str(code).strip()}
    rows_by_code: Dict[str, Dict[str, Any]] = {}
    for row in repository.get_agent1_catalog():
        dataset_code = str(row.get("dataset_code") or "").strip()
        if dataset_code and dataset_code in target_codes:
            rows_by_code[dataset_code] = row
    return rows_by_code


def _build_sql_for_dataset(
    dataset_code: str,
    context: Dict[str, Any],
) -> str:
    if dataset_code == "consumer_business_standard_v1":
        return _consumer_nodes_sql()
    if dataset_code == "angel_business_2026_phase1":
        return _commercial_nodes_sql(context)
    if dataset_code == "feishu_tbldianshang":
        return _ecommerce_nodes_sql()
    if dataset_code == "feishu_tblyongfukaidan":
        return _yongfu_nodes_sql()
    raise ValueError(f"Unsupported dataset for node index build: {dataset_code}")


def build_dataset_node_index(
    dataset_codes: Iterable[str] | None = None,
    merge_existing: bool = False,
) -> Dict[str, Any]:
    repository = BookshelfRepository()
    router = DataSourceRouter()

    # 自动获取默认数据源ID，用于source_id无效时的fallback
    default_source_id = None
    try:
        for ds_id, ds_config in router.data_sources.items():
            if ds_config.get("config", {}).get("is_default"):
                default_source_id = ds_id
                break
    except Exception:
        # 获取失败时fallback到5（PostgreSQL默认ID）
        default_source_id = 5
    valid_source_ids = set(router.data_sources.keys())

    target_codes = list(dict.fromkeys([
        code for code in (dataset_codes or SUPPORTED_DATASET_CODES)
        if str(code).strip() in SUPPORTED_DATASET_CODES
    ]))
    active_rows = _resolve_active_dataset_rows(repository, target_codes)

    rebuilt_datasets: List[Dict[str, Any]] = []
    for dataset_code in target_codes:
        row = active_rows.get(dataset_code)
        if not row:
            continue
        dataset_id = int(row.get("id") or 0)
        if not dataset_id:
            continue
        context = repository.get_dataset_context(dataset_id, "节点索引构建")
        dataset_meta = context.get("dataset") or {}
        
        # 解析source_id，无效时自动fallback到默认数据源
        source_id = int(dataset_meta.get("source_id") or row.get("source_id") or 0)
        if source_id not in valid_source_ids:
            source_id = default_source_id
            
        rebuilt_datasets.append(
            _build_dataset_nodes(
                dataset_id=dataset_id,
                dataset_code=dataset_code,
                dataset_name=str(dataset_meta.get("dataset_name") or row.get("dataset_name") or ""),
                source_id=source_id,
                sql=_build_sql_for_dataset(dataset_code, context),
                router=router,
            )
        )

    datasets = _sort_datasets(rebuilt_datasets)
    if merge_existing:
        datasets = merge_dataset_entries(_load_existing_datasets(), datasets)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_ids": [int(item.get("dataset_id") or 0) for item in datasets],
        "dataset_codes": [str(item.get("dataset_code") or "") for item in datasets],
        "datasets": datasets,
        "flat_alias_index": _flatten_alias_index(datasets),
    }


def write_dataset_node_index(payload: Dict[str, Any]) -> Path:
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return OUTPUT_PATH


def rebuild_dataset_node_index_for_source_table(source_table: str) -> Dict[str, Any]:
    dataset_codes = affected_dataset_codes_for_source_table(source_table)
    if not dataset_codes:
        return {
            "rebuilt": False,
            "source_table": _normalize_table_name(source_table),
            "dataset_codes": [],
            "dataset_ids": [],
            "path": str(OUTPUT_PATH),
            "reason": "no_matching_dataset",
        }

    payload = build_dataset_node_index(dataset_codes=dataset_codes, merge_existing=True)
    write_dataset_node_index(payload)
    rebuilt_entries = [
        item for item in payload.get("datasets", [])
        if str(item.get("dataset_code") or "") in dataset_codes
    ]
    return {
        "rebuilt": bool(rebuilt_entries),
        "source_table": _normalize_table_name(source_table),
        "dataset_codes": dataset_codes,
        "dataset_ids": [int(item.get("dataset_id") or 0) for item in rebuilt_entries],
        "path": str(OUTPUT_PATH),
        "dataset_count": len(rebuilt_entries),
        "alias_count": sum(int(item.get("alias_count") or 0) for item in rebuilt_entries),
    }


def main() -> None:
    payload = build_dataset_node_index()
    write_dataset_node_index(payload)
    print(f"wrote {OUTPUT_PATH}")
    for dataset in payload["datasets"]:
        print(
            f"dataset={dataset['dataset_id']} "
            f"code={dataset.get('dataset_code', '')} "
            f"nodes={dataset['node_count']} aliases={dataset['alias_count']}"
        )


if __name__ == "__main__":
    main()
