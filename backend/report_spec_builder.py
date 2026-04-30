import re
from typing import Any, Dict, List, Optional


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value == value else None
    text = str(value).strip()
    if not text:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", text)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _format_value(value: Any, metric: Dict[str, Any]) -> str:
    numeric = _to_float(value)
    if numeric is None:
        return "-"
    if metric.get("format") == "percent":
        return f"{numeric:.2f}%"
    if metric.get("format") == "amount" and abs(numeric) >= 10000:
        return f"{numeric / 10000:.2f}万"
    if numeric == int(numeric):
        return f"{int(numeric):,}"
    return f"{numeric:.2f}"


def _metric_by_key(config: Dict[str, Any], key: str, fallback_tokens: List[str]) -> Optional[Dict[str, Any]]:
    metrics = [item for item in config.get("metrics") or [] if isinstance(item, dict)]
    direct = next((item for item in metrics if item.get("key") == key), None)
    if direct:
        return direct
    for item in metrics:
        text = f"{item.get('label', '')}{item.get('column', '')}{item.get('format', '')}"
        if any(token in text for token in fallback_tokens):
            return item
    return None


def _row_value(row: Dict[str, Any], metric: Optional[Dict[str, Any]]) -> Optional[float]:
    if not metric:
        return None
    return _to_float(row.get(metric.get("column")))


def _infer_level(row: Dict[str, Any], config: Dict[str, Any], level_col: str) -> Dict[str, str]:
    level_value = str(row.get(level_col) or "").strip()
    for level in config.get("levels") or []:
        if level_value in (level.get("values") or []):
            return {"levelName": str(level.get("name") or level_value), "levelValue": level_value}
    return {"levelName": level_value or "未分层", "levelValue": level_value}


def _build_tree(rows: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    name_col = str(config.get("nameColumn") or "节点名称")
    parent_col = str(config.get("parentColumn") or "上级名称")
    level_col = str(config.get("levelColumn") or "层级")
    track_col = str(config.get("trackColumn") or "条线")
    nodes: List[Dict[str, Any]] = []
    by_name: Dict[str, Dict[str, Any]] = {}
    seen = set()

    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get(name_col) or "").strip()
        if not name:
            continue
        parent_name = str(row.get(parent_col) or "").strip()
        level = _infer_level(row, config, level_col)
        key = (name, parent_name, level["levelValue"])
        if key in seen:
            continue
        seen.add(key)
        node = {
            "id": "::".join(key),
            "name": name,
            "parentName": parent_name,
            "levelName": level["levelName"],
            "levelValue": level["levelValue"],
            "trackName": str(row.get(track_col) or "").strip(),
            "depth": 0,
            "children": [],
            "raw": row,
        }
        nodes.append(node)
        by_name[name] = node

    for node in nodes:
        parent = by_name.get(node["parentName"])
        if parent and parent is not node:
            parent["children"].append(node)

    roots = [node for node in nodes if not node["parentName"] or node["parentName"] not in by_name]
    visited = set()

    def walk(item: Dict[str, Any], depth: int) -> None:
        if item["id"] in visited:
            return
        visited.add(item["id"])
        item["depth"] = depth
        for child in item["children"]:
            walk(child, depth + 1)

    for root in roots:
        walk(root, 0)
    for node in nodes:
        if node["id"] not in visited:
            walk(node, 0)

    return {"roots": roots, "nodes": nodes}


def _descendants(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []

    def walk(item: Dict[str, Any]) -> None:
        for child in item.get("children") or []:
            output.append(child)
            walk(child)

    walk(node)
    return output


def _level_label(nodes: List[Dict[str, Any]], fallback: str) -> str:
    values = []
    for node in nodes:
        value = node.get("levelValue") or node.get("levelName")
        if value and value not in values:
            values.append(value)
    return " / ".join(values) if values else fallback


def _detect_mode(question: str, focus_node: Optional[Dict[str, Any]], selected_count: int) -> str:
    text = question or ""
    if re.search(r"为什么|原因|归因|下滑|异常|差距", text):
        return "diagnostic"
    if selected_count > 1 or re.search(r"对比|比较|哪个|谁更|差异| vs |VS", text):
        return "comparative"
    if focus_node:
        return "drill_down"
    if re.search(r"最差|最好|最高|最低|风险|缺口", text):
        return "bottom_up"
    return "top_down"


def build_report_spec(
    question: str,
    dataset: Dict[str, Any],
    rows: List[Dict[str, Any]],
    columns: List[str],
    report_config: Dict[str, Any],
    sql: str = "",
    review: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    config = report_config or {}
    rows = rows if isinstance(rows, list) else []
    tree = _build_tree(rows, config)
    nodes = tree["nodes"]

    metrics = [item for item in config.get("metrics") or [] if isinstance(item, dict)]
    task_metric = _metric_by_key(config, "task", ["任务", "目标"])
    actual_metric = _metric_by_key(config, "actual", ["开单", "完成", "实际", "销售"])
    rate_metric = _metric_by_key(config, "rate", ["率", "percent", "rate"])
    remain_metric = _metric_by_key(config, "remain", ["剩余", "缺口", "差额"])

    matched_nodes = [
        node for node in sorted(nodes, key=lambda item: len(item.get("name") or ""), reverse=True)
        if node.get("name") and node["name"] in (question or "")
    ]
    explicit_comparative = len(matched_nodes) > 1 or bool(re.search(r"对比|比较|哪个|谁更|差异| vs |VS", question or ""))
    focus_node = next((node for node in matched_nodes if node.get("children")), None)
    if explicit_comparative and len(matched_nodes) > 1:
        comparison_nodes = matched_nodes
    else:
        comparison_nodes = focus_node.get("children", []) if focus_node else []
    if not comparison_nodes and len(tree["roots"]) == 1:
        comparison_nodes = tree["roots"][0].get("children", [])
    if not comparison_nodes:
        parent_nodes = [node for node in nodes if node.get("children")]
        max_depth = max([node.get("depth", 0) for node in parent_nodes] or [0])
        comparison_nodes = [node for node in parent_nodes if node.get("depth", 0) == max_depth]
    comparison_nodes = [node for node in comparison_nodes if node.get("name")]

    mode = _detect_mode(question, focus_node if not explicit_comparative else None, len(matched_nodes))
    compare_label = _level_label(comparison_nodes, "下一层级")
    detail_nodes = [item for node in comparison_nodes for item in (_descendants(node) or node.get("children") or [])]
    leaf_nodes = [node for node in detail_nodes if not node.get("children")]
    detail_label = _level_label(leaf_nodes or detail_nodes, "明细层级")

    def chart_row(node: Dict[str, Any]) -> Dict[str, Any]:
        row = {"名称": node["name"]}
        for metric in [actual_metric, task_metric, remain_metric, rate_metric]:
            if metric:
                row[metric.get("label") or metric.get("column") or metric.get("key")] = _row_value(node["raw"], metric) or 0
        return row

    compare_rows = sorted(
        [chart_row(node) for node in comparison_nodes],
        key=lambda item: item.get(rate_metric.get("label") or rate_metric.get("column") or "达成率", 0) if rate_metric else 0,
        reverse=True,
    )
    compare_columns = ["名称"] + [
        metric.get("label") or metric.get("column") or metric.get("key")
        for metric in [actual_metric, task_metric, remain_metric, rate_metric]
        if metric
    ]

    kpis = []
    root_source = focus_node or (tree["roots"][0] if tree["roots"] else (nodes[0] if nodes else None))
    if root_source:
        for metric in metrics[:6]:
            value = _row_value(root_source["raw"], metric)
            if value is not None:
                kpis.append({
                    "key": metric.get("key"),
                    "label": metric.get("label") or metric.get("column") or metric.get("key"),
                    "value": value,
                    "displayValue": _format_value(value, metric),
                    "format": metric.get("format"),
                })

    accordions = []
    threshold = _to_float(config.get("riskThreshold")) or 80
    for node in comparison_nodes:
        descendants = _descendants(node)
        leaf_children = [item for item in descendants if not item.get("children")] or descendants or node.get("children") or []
        sorted_children = sorted(leaf_children, key=lambda item: _row_value(item["raw"], rate_metric) if rate_metric else 0)
        worst = sorted_children[0] if sorted_children else None
        best = sorted(sorted_children, key=lambda item: _row_value(item["raw"], rate_metric) if rate_metric else 0, reverse=True)[0] if sorted_children else None
        rate = _row_value(node["raw"], rate_metric) if rate_metric else None
        child_chart_rows = [chart_row(child) for child in sorted_children]
        risk_children = [
            child for child in sorted_children
            if rate_metric and (_row_value(child["raw"], rate_metric) or 0) < threshold
        ]

        def describe_detail(item: Optional[Dict[str, Any]]) -> str:
            if not item:
                return f"暂无{detail_label}明细"
            actual_text = _format_value(_row_value(item["raw"], actual_metric), actual_metric) if actual_metric else "-"
            task_text = _format_value(_row_value(item["raw"], task_metric), task_metric) if task_metric else "-"
            rate_text = _format_value(_row_value(item["raw"], rate_metric), rate_metric) if rate_metric else "-"
            remain_text = _format_value(_row_value(item["raw"], remain_metric), remain_metric) if remain_metric else "-"
            gap_text = f"，剩余缺口{remain_text}" if remain_metric else ""
            return f"{item['name']}开单{actual_text} / 任务{task_text}，达成率{rate_text}{gap_text}"

        node_actual = _format_value(_row_value(node["raw"], actual_metric), actual_metric) if actual_metric else "-"
        node_task = _format_value(_row_value(node["raw"], task_metric), task_metric) if task_metric else "-"
        node_rate = _format_value(rate, rate_metric) if rate_metric else "-"
        node_remain = _format_value(_row_value(node["raw"], remain_metric), remain_metric) if remain_metric else "-"
        risk_text = f"其中 {len(risk_children)} 个{detail_label}低于风险线，需要优先跟进金额缺口和项目转化。" if risk_children else f"当前暂无明显低达成风险{detail_label}。"
        accordions.append({
            "id": node["id"],
            "title": node["name"],
            "parentName": node.get("parentName"),
            "levelLabel": node.get("levelValue") or node.get("levelName") or compare_label,
            "detailLevelLabel": detail_label,
            "tone": "danger" if rate is not None and rate < threshold else "good" if rate is not None and rate >= 100 else "warn",
            "kpis": [
                {
                    "label": metric.get("label") or metric.get("column") or metric.get("key"),
                    "value": _format_value(_row_value(node["raw"], metric), metric),
                }
                for metric in [task_metric, actual_metric, rate_metric, remain_metric]
                if metric
            ],
            "narrative": f"{node['name']}当前开单{node_actual}，任务{node_task}，达成率{node_rate}"
                         f"{f'，剩余缺口{node_remain}' if remain_metric else ''}。{risk_text}"
                         f"下钻到{detail_label}层：最高为{describe_detail(best)}；最低为{describe_detail(worst)}。",
            "chart": {
                "chartType": "combo",
                "title": f"{node['name']}{detail_label}达成情况",
                "columns": compare_columns,
                "rows": child_chart_rows,
            },
        })

    rate_sorted_nodes = sorted(comparison_nodes, key=lambda item: _row_value(item["raw"], rate_metric) if rate_metric else 0)
    best_node = rate_sorted_nodes[-1] if rate_sorted_nodes else None
    worst_node = rate_sorted_nodes[0] if rate_sorted_nodes else None
    summary_parts = []
    if comparison_nodes:
        summary_parts.append(f"本次结果覆盖 {len(comparison_nodes)} 个{compare_label}")
    if best_node and rate_metric:
        summary_parts.append(f"{best_node['name']}达成率最高，为{_format_value(_row_value(best_node['raw'], rate_metric), rate_metric)}")
    if worst_node and rate_metric:
        summary_parts.append(f"{worst_node['name']}压力最大，为{_format_value(_row_value(worst_node['raw'], rate_metric), rate_metric)}")

    overview_chart = {
        "chartType": "combo",
        "title": f"各{compare_label}任务、完成与达成率对比",
        "columns": compare_columns,
        "rows": compare_rows,
    } if compare_rows else None

    provenance_id = "p_sql_result_001"
    return {
        "version": "2.0",
        "question": question,
        "analysisMode": mode,
        "dataset": {
            "id": dataset.get("id") or dataset.get("dataset_id"),
            "code": dataset.get("dataset_code"),
            "name": dataset.get("dataset_name"),
        },
        "scope": {
            "focusNode": focus_node.get("name") if focus_node else None,
            "compareLevelLabel": compare_label,
            "detailLevelLabel": detail_label,
        },
        "kpis": kpis,
        "sections": [
            {"key": "overview", "title": "总体判断", "narrative": "；".join(summary_parts)},
            {"key": "drill", "title": f"{compare_label}下钻分析", "narrative": "按当前问题命中节点展开下一层级。"},
        ],
        "charts": [overview_chart] if overview_chart else [],
        "accordions": accordions,
        "narrative": summary_parts,
        "provenance": [
            {
                "provenanceId": provenance_id,
                "type": "sql_result",
                "sql": sql,
                "columns": columns,
                "rowCount": len(rows),
                "configColumns": {
                    "nameColumn": config.get("nameColumn"),
                    "parentColumn": config.get("parentColumn"),
                    "levelColumn": config.get("levelColumn"),
                    "trackColumn": config.get("trackColumn"),
                },
                "reviewSummary": (review or {}).get("review_summary"),
            }
        ],
    }