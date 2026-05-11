import re
from typing import Any, Dict, List, Optional

from dataset_dimension_profiles import get_dataset_profile, resolve_member_mentions
from report_contract_health import validate_report_contract
from report_scene_registry import detect_report_scene, layout_for_scene


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
    if metric.get("format") == "amount":
        return _format_amount(numeric)
    if numeric == int(numeric):
        return f"{int(numeric):,}"
    return f"{numeric:.2f}"


def _format_amount(value: float) -> str:
    abs_value = abs(value)
    if abs_value < 10000:
        if value == int(value):
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".")
    if abs_value < 1000000:
        return f"{value / 10000:.1f}万"
    if abs_value < 100000000:
        return f"{round(value / 10000)}万"
    return f"{value / 100000000:.2f}亿"


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


def _drill_children(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    children = [item for item in (node.get("children") or []) if item.get("name")]
    if children:
        return children
    return [item for item in _descendants(node) if item.get("name")]


def _level_label(nodes: List[Dict[str, Any]], fallback: str) -> str:
    values = []
    for node in nodes:
        value = node.get("levelValue") or node.get("levelName")
        if value and value not in values:
            values.append(value)
    return " / ".join(values) if values else fallback


def _detect_mode(question: str, focus_node: Optional[Dict[str, Any]], selected_count: int) -> str:
    return detect_report_scene(question, focus_node, selected_count).get("key", "detail")


def _layout_template(mode: str) -> str:
    return layout_for_scene(mode)


def _effective_thresholds(config: Dict[str, Any]) -> Dict[str, float]:
    return {
        "officeRisk": _to_float(config.get("officeRiskThreshold")) or 10,
        "officeBenchmark": _to_float(config.get("officeBenchmarkThreshold")) or 15,
        "personRisk": _to_float(config.get("personRiskThreshold")) or 10,
        "personBenchmark": _to_float(config.get("personBenchmarkThreshold")) or 20,
    }


def _rate_tone(rate: Optional[float], risk: float, benchmark: float) -> str:
    if rate is None:
        return "neutral"
    if rate < risk:
        return "danger"
    if rate >= benchmark:
        return "good"
    return "warn"


def _rate_tag(rate: Optional[float], risk: float, benchmark: float, good_label: str = "标杆") -> str:
    tone = _rate_tone(rate, risk, benchmark)
    if tone == "good":
        return f"✅ {good_label}"
    if tone == "warn":
        return "🟡 中等"
    if tone == "danger":
        return "⚠️ 风险"
    return "未分级"


def _rate_rank_label(rank: int) -> str:
    if rank <= 0:
        return ""
    return f"区域第{rank}"


def _question_mentions_node(question: str, name: str) -> bool:
    text = question or ""
    node_name = name or ""
    if node_name and node_name in text:
        return True
    return False


def _resolved_member_names(resolved_entities: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(resolved_entities, dict):
        return []
    names: List[str] = []
    for name in resolved_entities.get("all_members") or []:
        value = str(name or "").strip()
        if value and value not in names:
            names.append(value)
    for entity in resolved_entities.get("entities") or []:
        if not isinstance(entity, dict):
            continue
        for name in entity.get("members") or []:
            value = str(name or "").strip()
            if value and value not in names:
                names.append(value)
    return names


def _question_node_order(question: str, name: str, resolved_order: Optional[Dict[str, int]] = None) -> int:
    if resolved_order and name in resolved_order:
        return resolved_order[name]
    text = question or ""
    node_name = name or ""
    exact_index = text.find(node_name) if node_name else -1
    return exact_index if exact_index >= 0 else 9999


def build_report_spec(
    question: str,
    dataset: Dict[str, Any],
    rows: List[Dict[str, Any]],
    columns: List[str],
    report_config: Dict[str, Any],
    sql: str = "",
    review: Optional[Dict[str, Any]] = None,
    resolved_entities: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    config = report_config or {}
    rows = rows if isinstance(rows, list) else []
    tree = _build_tree(rows, config)
    nodes = tree["nodes"]

    metrics = [item for item in config.get("metrics") or [] if isinstance(item, dict)]
    task_metric = _metric_by_key(config, "task", ["任务", "目标"])
    actual_metric = _metric_by_key(config, "actual", ["开单", "成交", "营收", "收入", "完成", "实际", "销售"])
    rate_metric = _metric_by_key(config, "rate", ["率", "percent", "rate"])
    remain_metric = _metric_by_key(config, "remain", ["剩余", "待完成", "缺口", "差额"])

    resolved_names = _resolved_member_names(resolved_entities)
    if not resolved_names:
        profile = get_dataset_profile(dataset.get("dataset_code") or dataset.get("code"), dataset.get("dataset_name") or dataset.get("name"))
        if profile:
            resolved_names = _resolved_member_names(resolve_member_mentions(question or "", profile))
    resolved_order = {name: index for index, name in enumerate(resolved_names)}
    if resolved_names:
        matched_nodes = [
            node for node in sorted(nodes, key=lambda item: resolved_order.get(item.get("name") or "", 9999))
            if node.get("name") in resolved_order
        ]
    else:
        matched_nodes = [
            node for node in sorted(nodes, key=lambda item: len(item.get("name") or ""), reverse=True)
            if node.get("name") and _question_mentions_node(question or "", node["name"])
        ]
    explicit_comparative = len(matched_nodes) > 1 or bool(re.search(r"对比|比较|哪个|谁更|差异|分别|各自|和.+比|跟.+比|与.+比|\bvs\b", question or "", re.I))
    focus_node = next((node for node in matched_nodes if node.get("children")), None)
    if explicit_comparative and len(matched_nodes) > 1:
        comparison_nodes = sorted(
            matched_nodes,
            key=lambda item: _question_node_order(question or "", item.get("name") or "", resolved_order),
        )
    else:
        comparison_nodes = focus_node.get("children", []) if focus_node else []
    if not comparison_nodes and len(tree["roots"]) == 1:
        comparison_nodes = tree["roots"][0].get("children", [])
    if not comparison_nodes:
        parent_nodes = [node for node in nodes if node.get("children")]
        max_depth = max([node.get("depth", 0) for node in parent_nodes] or [0])
        comparison_nodes = [node for node in parent_nodes if node.get("depth", 0) == max_depth]
    comparison_nodes = [node for node in comparison_nodes if node.get("name")]

    scene = detect_report_scene(question, focus_node if not explicit_comparative else None, len(matched_nodes))
    mode = scene.get("key", "detail")
    contract_health = validate_report_contract(config, columns, scene)
    compare_label = _level_label(comparison_nodes, "下一层级")
    detail_nodes = [item for node in comparison_nodes for item in _drill_children(node)]
    detail_label = _level_label(detail_nodes, "明细层级")

    chart_metrics = [metric for metric in [actual_metric, task_metric, remain_metric, rate_metric] if metric]

    def chart_row(node: Dict[str, Any]) -> Dict[str, Any]:
        row = {"名称": node["name"]}
        for metric in chart_metrics:
            row[metric.get("label") or metric.get("column") or metric.get("key")] = _row_value(node["raw"], metric) or 0
        return row

    compare_rows = sorted(
        [chart_row(node) for node in comparison_nodes],
        key=lambda item: item.get(rate_metric.get("label") or rate_metric.get("column") or "达成率", 0) if rate_metric else 0,
        reverse=True,
    )
    compare_columns = ["名称"] + [metric.get("label") or metric.get("column") or metric.get("key") for metric in chart_metrics]

    kpis = []
    root_source = focus_node or (tree["roots"][0] if tree["roots"] else (nodes[0] if nodes else None))

    def metric_label(metric: Optional[Dict[str, Any]], fallback: str) -> str:
        return (metric or {}).get("label") or (metric or {}).get("column") or (metric or {}).get("key") or fallback

    def add_kpi(
        key: str,
        label: str,
        value: Any = None,
        metric: Optional[Dict[str, Any]] = None,
        display_value: Optional[str] = None,
    ) -> None:
        if value is None and display_value is None:
            return
        kpis.append({
            "key": key,
            "label": label,
            "value": value,
            "displayValue": display_value if display_value is not None else _format_value(value, metric or {}),
            "format": (metric or {}).get("format"),
        })

    def sum_metric(metric: Optional[Dict[str, Any]]) -> Optional[float]:
        if not metric:
            return None
        values = [_row_value(node["raw"], metric) for node in comparison_nodes]
        numeric_values = [value for value in values if value is not None]
        if not numeric_values:
            return None
        return sum(numeric_values)

    def overall_rate_value() -> Optional[float]:
        actual_total = sum_metric(actual_metric)
        task_total = sum_metric(task_metric)
        if actual_total is not None and task_total:
            return actual_total / task_total * 100
        if not rate_metric:
            return None
        rate_values = [_row_value(node["raw"], rate_metric) for node in comparison_nodes]
        numeric_rates = [value for value in rate_values if value is not None]
        if not numeric_rates:
            return None
        return sum(numeric_rates) / len(numeric_rates)

    if mode == "comparative" and comparison_nodes:
        compare_count = len(comparison_nodes)
        if compare_count <= 2:
            for node in comparison_nodes:
                for metric in [task_metric, actual_metric, rate_metric, remain_metric]:
                    if not metric:
                        continue
                    value = _row_value(node["raw"], metric)
                    if value is None:
                        continue
                    item_label = metric_label(metric, "指标")
                    add_kpi(
                        f"{node.get('name')}-{metric.get('key') or item_label}",
                        f"{node.get('name')}{item_label}",
                        value,
                        metric,
                    )
        elif compare_count <= 4:
            add_kpi("compare-total-task", f"累计{metric_label(task_metric, '总任务金额')}", sum_metric(task_metric), task_metric)
            add_kpi("compare-total-actual", f"累计{metric_label(actual_metric, '年度开单金额')}", sum_metric(actual_metric), actual_metric)
            add_kpi("compare-overall-rate", "整体达成率", overall_rate_value(), rate_metric)
            for node in comparison_nodes:
                value = _row_value(node["raw"], rate_metric)
                if value is None:
                    continue
                add_kpi(
                    f"{node.get('name')}-rate",
                    f"{node.get('name')}{metric_label(rate_metric, '达成率')}",
                    value,
                    rate_metric,
                )
        else:
            rate_ranked = sorted(
                [node for node in comparison_nodes if _row_value(node["raw"], rate_metric) is not None],
                key=lambda item: _row_value(item["raw"], rate_metric) or 0,
                reverse=True,
            )
            top_node = rate_ranked[0] if rate_ranked else None
            bottom_node = rate_ranked[-1] if rate_ranked else None
            top_rate = _row_value(top_node["raw"], rate_metric) if top_node else None
            bottom_rate = _row_value(bottom_node["raw"], rate_metric) if bottom_node else None
            add_kpi("compare-count", f"{compare_label}数量", compare_count, None, str(compare_count))
            add_kpi("compare-total-task", f"累计{metric_label(task_metric, '总任务金额')}", sum_metric(task_metric), task_metric)
            add_kpi("compare-total-actual", f"累计{metric_label(actual_metric, '年度开单金额')}", sum_metric(actual_metric), actual_metric)
            add_kpi("compare-overall-rate", "整体达成率", overall_rate_value(), rate_metric)
            if top_node and top_rate is not None:
                add_kpi("compare-best-rate", f"最高：{top_node.get('name')}", top_rate, rate_metric)
            if bottom_node and bottom_rate is not None:
                add_kpi("compare-worst-rate", f"最低：{bottom_node.get('name')}", bottom_rate, rate_metric)
            if top_rate is not None and bottom_rate is not None:
                add_kpi("compare-rate-gap", "首尾差距", abs(top_rate - bottom_rate), rate_metric)
    elif root_source:
        for metric in metrics[:6]:
            value = _row_value(root_source["raw"], metric)
            if value is not None:
                add_kpi(metric.get("key"), metric_label(metric, "指标"), value, metric)

    accordions = []
    thresholds = _effective_thresholds(config)
    ranked_comparison_nodes = sorted(
        comparison_nodes,
        key=lambda item: _row_value(item["raw"], rate_metric) if rate_metric else 0,
        reverse=True,
    )
    node_rank = {node.get("id"): index + 1 for index, node in enumerate(ranked_comparison_nodes)}
    for node in ranked_comparison_nodes:
        drill_children = _drill_children(node)
        node_detail_label = _level_label(drill_children, detail_label)
        sorted_children = sorted(drill_children, key=lambda item: _row_value(item["raw"], rate_metric) if rate_metric else 0)
        sorted_children_desc = sorted(sorted_children, key=lambda item: _row_value(item["raw"], rate_metric) if rate_metric else 0, reverse=True)
        worst = sorted_children[0] if sorted_children else None
        best = sorted_children_desc[0] if sorted_children_desc else None
        rate = _row_value(node["raw"], rate_metric) if rate_metric else None
        first_drill_has_next_level = any(child.get("children") for child in sorted_children_desc)
        direct_risk_threshold = thresholds["officeRisk"] if first_drill_has_next_level else thresholds["personRisk"]
        direct_benchmark_threshold = thresholds["officeBenchmark"] if first_drill_has_next_level else thresholds["personBenchmark"]
        child_chart_rows = []
        for child in sorted_children_desc:
            row = chart_row(child)
            child_rate = _row_value(child["raw"], rate_metric) if rate_metric else None
            row["标签"] = _rate_tag(
                child_rate,
                direct_risk_threshold,
                direct_benchmark_threshold,
            )
            child_chart_rows.append(row)
        risk_children = [
            child for child in sorted_children
            if rate_metric and (_row_value(child["raw"], rate_metric) or 0) < direct_risk_threshold
        ]

        def build_drill_group(child: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            grandchildren = _drill_children(child)
            if not grandchildren:
                return None
            group_detail_label = _level_label(grandchildren, "下一层级")
            sorted_grandchildren = sorted(
                grandchildren,
                key=lambda item: _row_value(item["raw"], rate_metric) if rate_metric else 0,
                reverse=True,
            )
            child_rate = _row_value(child["raw"], rate_metric) if rate_metric else None
            child_actual = _format_value(_row_value(child["raw"], actual_metric), actual_metric) if actual_metric else "-"
            child_task = _format_value(_row_value(child["raw"], task_metric), task_metric) if task_metric else "-"
            child_remain = _format_value(_row_value(child["raw"], remain_metric), remain_metric) if remain_metric else "-"
            group_rows = []
            for grandchild in sorted_grandchildren:
                row = chart_row(grandchild)
                grandchild_rate = _row_value(grandchild["raw"], rate_metric) if rate_metric else None
                row["标签"] = _rate_tag(
                    grandchild_rate,
                    thresholds["personRisk"],
                    thresholds["personBenchmark"],
                )
                group_rows.append(row)
            risk_grandchildren = [
                item for item in sorted_grandchildren
                if rate_metric and (_row_value(item["raw"], rate_metric) or 0) < thresholds["personRisk"]
            ]
            return {
                "id": child.get("id"),
                "title": child.get("name"),
                "parentName": child.get("parentName"),
                "levelLabel": child.get("levelValue") or child.get("levelName") or node_detail_label,
                "detailLevelLabel": group_detail_label,
                "tone": _rate_tone(child_rate, thresholds["officeRisk"], thresholds["officeBenchmark"]),
                "tag": _rate_tag(child_rate, thresholds["officeRisk"], thresholds["officeBenchmark"], "代表处标杆"),
                "kpis": [
                    {
                        "label": metric.get("label") or metric.get("column") or metric.get("key"),
                        "value": _format_value(_row_value(child["raw"], metric), metric),
                    }
                    for metric in [task_metric, actual_metric, rate_metric, remain_metric]
                    if metric
                ],
                "narrative": f"【{child.get('name')}】达成率{_format_value(child_rate, rate_metric) if rate_metric else '-'}，"
                             f"任务{child_task} / 已完成{child_actual}"
                             f"{f' / 缺口{child_remain}' if remain_metric else ''}；"
                             f"{len(risk_grandchildren)} 个{group_detail_label}低于{thresholds['personRisk']:.0f}%风险线。",
                "detailNarrative": f"{child.get('name')}继续下钻到{group_detail_label}，用于定位个人执行差异。",
                "chart": {
                    "chartType": "horizontalDrill",
                    "title": f"{child.get('name')}{group_detail_label}达成率与缺口",
                    "columns": compare_columns,
                    "rows": group_rows,
                },
            }

        def describe_detail(item: Optional[Dict[str, Any]]) -> str:
            if not item:
                return f"暂无{node_detail_label}明细"
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
        node_tag = _rate_tag(rate, thresholds["officeRisk"], thresholds["officeBenchmark"], "区域标杆")
        highlight = (
            f"亮点：{best['name']}达成率{_format_value(_row_value(best['raw'], rate_metric), rate_metric)}"
            if best and rate_metric else f"暂无{node_detail_label}明细"
        )
        risk_text = (
            f"{len(risk_children)} 个{node_detail_label}低于{direct_risk_threshold:.0f}%风险线"
            if risk_children else f"暂无低于{direct_risk_threshold:.0f}%的风险{node_detail_label}"
        )
        accordions.append({
            "id": node["id"],
            "title": node["name"],
            "parentName": node.get("parentName"),
            "levelLabel": node.get("levelValue") or node.get("levelName") or compare_label,
            "detailLevelLabel": node_detail_label,
            "rankLabel": _rate_rank_label(node_rank.get(node.get("id"), 0)),
            "tag": node_tag,
            "highlight": highlight,
            "riskSummary": risk_text,
            "tone": _rate_tone(rate, thresholds["officeRisk"], thresholds["officeBenchmark"]),
            "kpis": [
                {
                    "label": metric.get("label") or metric.get("column") or metric.get("key"),
                    "value": _format_value(_row_value(node["raw"], metric), metric),
                }
                for metric in [task_metric, actual_metric, rate_metric, remain_metric]
                if metric
            ],
            "narrative": f"【{node['name']}】 {node_tag} 达成率 {node_rate}"
                         f"{f'（{_rate_rank_label(node_rank.get(node.get('id'), 0))}）' if node_rank.get(node.get('id')) else ''}\n"
                         f"任务{node_task} / 已完成{node_actual}"
                         f"{f' / 缺口{node_remain}' if remain_metric else ''}\n"
                         f"{highlight}；{risk_text}\n"
                         f"点击展开{len(sorted_children_desc)}个{node_detail_label}明细。",
            "detailNarrative": f"{node['name']}下钻到{node_detail_label}层：最高为{describe_detail(best)}；最低为{describe_detail(worst)}。",
            "chart": {
                "chartType": "horizontalDrill",
                "title": f"{node['name']}{node_detail_label}达成率与缺口",
                "columns": compare_columns,
                "rows": child_chart_rows,
            },
            "drillGroups": [item for item in (build_drill_group(child) for child in sorted_children_desc) if item],
        })

    rate_sorted_nodes = sorted(comparison_nodes, key=lambda item: _row_value(item["raw"], rate_metric) if rate_metric else 0)
    best_node = rate_sorted_nodes[-1] if rate_sorted_nodes else None
    worst_node = rate_sorted_nodes[0] if rate_sorted_nodes else None

    def describe_comparison_node(node: Dict[str, Any]) -> str:
        actual_text = _format_value(_row_value(node["raw"], actual_metric), actual_metric) if actual_metric else "-"
        task_text = _format_value(_row_value(node["raw"], task_metric), task_metric) if task_metric else "-"
        rate_text = _format_value(_row_value(node["raw"], rate_metric), rate_metric) if rate_metric else "-"
        remain_text = _format_value(_row_value(node["raw"], remain_metric), remain_metric) if remain_metric else ""
        remain_part = f"，剩余缺口{remain_text}" if remain_metric else ""
        return f"{node['name']}：开单{actual_text} / 任务{task_text}，达成率{rate_text}{remain_part}"

    comparison_metric_parts = [describe_comparison_node(node) for node in comparison_nodes[:4]]
    summary_parts = []
    if comparison_nodes:
        summary_parts.append(f"本次结果覆盖 {len(comparison_nodes)} 个{compare_label}")
    if mode == "comparative" and comparison_metric_parts:
        if len(comparison_nodes) <= 4:
            summary_parts.append("对比对象：" + "；".join(comparison_metric_parts))
        else:
            summary_parts.append(f"对比对象较多，关键指标区聚焦整体、最高和最低，完整 {len(comparison_nodes)} 个{compare_label}在下方对比表展开。")
    if mode == "comparative" and len(comparison_nodes) >= 2 and rate_metric:
        if len(comparison_nodes) == 2:
            left, right = comparison_nodes[0], comparison_nodes[1]
            left_rate = _row_value(left["raw"], rate_metric)
            right_rate = _row_value(right["raw"], rate_metric)
            if left_rate is not None and right_rate is not None:
                winner, loser = (left, right) if left_rate >= right_rate else (right, left)
                diff = abs(left_rate - right_rate)
                summary_parts.append(
                    f"差异：{winner['name']}达成率比{loser['name']}高{diff:.2f}个百分点"
                )
        else:
            best_rate = _row_value(best_node["raw"], rate_metric) if best_node else None
            worst_rate = _row_value(worst_node["raw"], rate_metric) if worst_node else None
            if best_node and worst_node and best_rate is not None and worst_rate is not None:
                summary_parts.append(
                    f"首尾差异：{best_node['name']}达成率比{worst_node['name']}高{abs(best_rate - worst_rate):.2f}个百分点"
                )
    if best_node and rate_metric:
        summary_parts.append(f"{best_node['name']}达成率最高，为{_format_value(_row_value(best_node['raw'], rate_metric), rate_metric)}")
    if worst_node and rate_metric:
        summary_parts.append(f"{worst_node['name']}压力最大，为{_format_value(_row_value(worst_node['raw'], rate_metric), rate_metric)}")

    overview_chart = {
        "chartType": "horizontalRateBar",
        "title": f"各{compare_label}达成率排序",
        "columns": compare_columns,
        "rows": compare_rows,
    } if compare_rows else None

    provenance_id = "p_sql_result_001"
    return {
        "version": "2.0",
        "reportTitle": "业绩分析报告",
        "question": question,
        "analysisMode": mode,
        "layoutTemplate": _layout_template(mode),
        "debug": {
            "scene": scene,
            "contract": contract_health,
            "report_config_used": bool(config),
            "standard_columns": {
                "name": config.get("nameColumn"),
                "parent": config.get("parentColumn"),
                "level": config.get("levelColumn"),
                "track": config.get("trackColumn"),
            },
        },
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
            {"key": "drill", "title": f"{compare_label}下钻分析", "narrative": f"先横向比较{compare_label}，再纵向展开直接下级{detail_label}；业务员明细作为下一层证据，不直接替代管理层级判断。"},
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
                "resolvedEntities": resolved_entities or {},
            }
        ],
    }
