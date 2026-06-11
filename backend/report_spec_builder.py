import math
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
        return _format_amount(numeric, _metric_unit_hint(metric))
    if numeric == int(numeric):
        return f"{int(numeric):,}"
    return f"{numeric:.2f}"


def _metric_unit_hint(metric: Optional[Dict[str, Any]]) -> str:
    if not metric:
        return ""
    return f"{metric.get('label', '')}{metric.get('column', '')}{metric.get('unit', '')}"


def _format_amount(value: float, unit_hint: str = "") -> str:
    abs_value = abs(value)
    if "万元" in unit_hint or "_万元" in unit_hint:
        if abs_value < 10000:
            if value == int(value):
                return f"{int(value)}万"
            return f"{value:.2f}".rstrip("0").rstrip(".") + "万"
        return f"{value / 10000:.2f}".rstrip("0").rstrip(".") + "亿"
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


def _infer_metric_from_columns(columns: List[str], key: str, label: str, tokens: List[str], fmt: str) -> Optional[Dict[str, Any]]:
    channel_tokens = ("线下", "新零售", "燃气", "地产", "定制")
    scored: List[tuple] = []
    for column in columns:
        text = str(column or "")
        if not text:
            continue
        score = 0
        if any(token in text for token in tokens):
            score += 20
        if "总" in text or "整体" in text:
            score += 12
        if "万元" in text:
            score += 4
        if key == "task" and any(token in text for token in ("实际", "开单", "完成", "达成")):
            score -= 30
        if key == "actual" and any(token in text for token in ("任务", "目标", "剩余", "缺口", "达成率")):
            score -= 30
        if key == "rate" and "率" not in text:
            score -= 30
        if key == "remain" and not any(token in text for token in ("剩余", "缺口", "差额", "待完成")):
            score -= 30
        if any(token in text for token in channel_tokens):
            score -= 8
        if score > 0:
            scored.append((score, text))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    return {"key": key, "label": label, "column": scored[0][1], "format": fmt}


def _row_value(row: Dict[str, Any], metric: Optional[Dict[str, Any]]) -> Optional[float]:
    if not metric:
        return None
    return _to_float(row.get(metric.get("column")))


def _row_sort_value(row: Dict[str, Any], metric: Optional[Dict[str, Any]]) -> float:
    value = _row_value(row, metric)
    return value if value is not None else 0.0


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


def _requested_level_values(question: str, config: Dict[str, Any]) -> List[str]:
    text = str(question or "")
    values: List[str] = []
    configured_values = [
        str(value)
        for level in (config.get("levels") or [])
        for value in (level.get("values") or [])
        if str(value or "").strip()
    ]
    common_values = ["事业部", "业务部", "分公司", "代表处", "业务代表", "业务员", "城市公司", "部门", "条线"]
    for value in [*configured_values, *common_values]:
        if value and value in text and value not in values:
            values.append(value)
    return values


def _negative_ranking_requested(question: str) -> bool:
    return bool(re.search(r"完成.*不好|不好|差|最差|最低|落后|承压|风险|低于|倒数|垫底|未完成|缺口", question or ""))


def _rate_sort_value(node: Dict[str, Any], rate_metric: Optional[Dict[str, Any]]) -> float:
    if not rate_metric:
        return 0.0
    return _row_sort_value(node.get("raw") or {}, rate_metric)


def _detect_mode(question: str, focus_node: Optional[Dict[str, Any]], selected_count: int) -> str:
    return detect_report_scene(question, focus_node, selected_count).get("key", "detail")


def _layout_template(mode: str) -> str:
    return layout_for_scene(mode)


def _effective_thresholds(config: Dict[str, Any]) -> Dict[str, float]:
    generic_benchmark = _to_float(config.get("benchmarkThreshold"))
    return {
        "officeRisk": _to_float(config.get("officeRiskThreshold")) or 10,
        "officeBenchmark": _to_float(config.get("officeBenchmarkThreshold")) or generic_benchmark or 15,
        "personRisk": _to_float(config.get("personRiskThreshold")) or 10,
        "personBenchmark": _to_float(config.get("personBenchmarkThreshold")) or generic_benchmark or 20,
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
        return "🟠 需推进"
    if tone == "danger":
        return "⚠️ 风险"
    return "未分级"


def _dynamic_group_limit(count: int) -> int:
    if count <= 1:
        return 0
    return max(1, min(3, count // 3))


def _item_identity(item: Dict[str, Any]) -> str:
    return str(item.get("id") or item.get("name") or id(item))


def _dynamic_performance_groups(
    items: List[Dict[str, Any]],
    rate_getter,
) -> Dict[str, Any]:
    valid_items = []
    seen = set()
    for item in items or []:
        rate = rate_getter(item)
        if rate is None:
            continue
        key = _item_identity(item)
        if key in seen:
            continue
        seen.add(key)
        valid_items.append(item)

    if len(valid_items) <= 1:
        return {
            "good": [],
            "middle": [],
            "weak": [],
            "ranked": valid_items,
            "canCompare": False,
            "mode": "single",
            "count": len(valid_items),
        }

    ranked = sorted(valid_items, key=lambda item: rate_getter(item) or 0, reverse=True)
    if len(ranked) == 2:
        return {
            "good": ranked[:1],
            "middle": [],
            "weak": ranked[1:],
            "ranked": ranked,
            "canCompare": True,
            "mode": "pair",
            "count": len(ranked),
        }

    top_count = max(1, math.ceil(len(ranked) / 3))
    weak_count = max(1, math.floor(len(ranked) / 3))
    middle_count = max(0, len(ranked) - top_count - weak_count)
    good = ranked[:top_count]
    middle = ranked[top_count:top_count + middle_count]
    weak = ranked[top_count + middle_count:]
    return {
        "good": good,
        "middle": middle,
        "weak": weak,
        "ranked": ranked,
        "canCompare": True,
        "mode": "tiers",
        "count": len(ranked),
    }


def _dynamic_performance_tag(item: Dict[str, Any], groups: Dict[str, Any]) -> str:
    if not groups.get("canCompare"):
        return "单体"
    key = _item_identity(item)
    if key in {_item_identity(row) for row in groups.get("good", [])}:
        return "✅ 领先主体" if groups.get("mode") == "pair" else "🔵 第一梯队"
    if key in {_item_identity(row) for row in groups.get("middle", [])}:
        return "🟡 第二梯队"
    if key in {_item_identity(row) for row in groups.get("weak", [])}:
        return "⚠️ 承压主体" if groups.get("mode") == "pair" else "🟠 第三梯队"
    return "— 未分层"


def _combined_performance_tag(
    item: Dict[str, Any],
    groups: Dict[str, Any],
    rate: Optional[float],
    risk: float,
    benchmark: float,
    good_label: str = "标杆",
) -> str:
    absolute_tone = _rate_tone(rate, risk, benchmark)
    relative_tag = _dynamic_performance_tag(item, groups)
    if groups.get("mode") == "single" or not groups.get("canCompare"):
        return _rate_tag(rate, risk, benchmark, good_label)
    if relative_tag.startswith("✅") or relative_tag.startswith("🔵"):
        return f"✅ {good_label}" if absolute_tone == "good" else "🔵 相对领先"
    if relative_tag.startswith("🟡"):
        if absolute_tone == "danger":
            return "⚠️ 中位风险"
        return "🟡 稳定推进"
    if relative_tag.startswith("⚠️") or relative_tag.startswith("🟠"):
        return "⚠️ 重点风险" if absolute_tone == "danger" else "🟠 相对承压"
    return _rate_tag(rate, risk, benchmark, good_label)


def _format_dynamic_group(
    items: List[Dict[str, Any]],
    rate_metric: Optional[Dict[str, Any]],
    empty_text: str,
) -> str:
    if not items:
        return empty_text
    return "、".join(
        f"{item.get('name')}{_format_value(_row_value(item.get('raw') or {}, rate_metric), rate_metric)}"
        for item in items
        if item.get("name")
    ) or empty_text


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
    query_intent = config.get("queryIntent") if isinstance(config.get("queryIntent"), dict) else {}
    rows = rows if isinstance(rows, list) else []
    available_columns = [str(item) for item in (columns or []) if str(item or "").strip()]
    if not available_columns:
        seen_columns = []
        for row in rows[:5]:
            if not isinstance(row, dict):
                continue
            for key in row.keys():
                text = str(key or "")
                if text and text not in seen_columns:
                    seen_columns.append(text)
        available_columns = seen_columns
    tree = _build_tree(rows, config)
    nodes = tree["nodes"]

    metrics = [item for item in config.get("metrics") or [] if isinstance(item, dict)]
    task_metric = _metric_by_key(config, "task", ["任务", "目标"])
    actual_metric = _metric_by_key(config, "actual", ["开单", "成交", "营收", "收入", "完成", "实际", "销售"])
    rate_metric = _metric_by_key(config, "rate", ["率", "percent", "rate"])
    remain_metric = _metric_by_key(config, "remain", ["剩余", "待完成", "缺口", "差额"])

    def metric_available(metric: Optional[Dict[str, Any]]) -> bool:
        if not metric:
            return False
        column = str(metric.get("column") or "")
        if not column:
            return False
        return column in available_columns or any(
            isinstance(row, dict) and _row_value(row, metric) is not None
            for row in rows[:20]
        )

    if not metric_available(task_metric):
        task_metric = _infer_metric_from_columns(available_columns, "task", "总任务", ["任务", "目标"], "amount")
    if not metric_available(actual_metric):
        actual_metric = _infer_metric_from_columns(available_columns, "actual", "总实际", ["实际", "开单", "完成", "营收", "收入", "销售"], "amount")
    if not metric_available(rate_metric):
        rate_metric = _infer_metric_from_columns(available_columns, "rate", "达成率", ["达成率", "完成率", "率"], "percent")
    if not metric_available(remain_metric):
        remain_metric = _infer_metric_from_columns(available_columns, "remain", "剩余缺口", ["剩余", "缺口", "差额", "待完成"], "amount")
    metrics = [
        metric for metric in [task_metric, actual_metric, rate_metric, remain_metric]
        if metric
    ] + [
        metric for metric in metrics
        if metric and metric not in [task_metric, actual_metric, rate_metric, remain_metric]
    ]
    ranking_sort_metric = None
    if query_intent.get("intent") == "ranking":
        sort_key = str(query_intent.get("sort_metric_key") or "")
        sort_column = str(query_intent.get("sort_metric_column") or "")
        ranking_sort_metric = next(
            (
                metric for metric in metrics
                if sort_key and str(metric.get("key") or "") == sort_key
            ),
            None,
        ) or next(
            (
                metric for metric in metrics
                if sort_column and sort_column in {
                    str(metric.get("column") or ""),
                    str(metric.get("label") or ""),
                    str(metric.get("key") or ""),
                }
            ),
            None,
        )
    sort_metric = ranking_sort_metric or rate_metric or actual_metric or task_metric or remain_metric or {}

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
    requested_levels = _requested_level_values(question or "", config)
    if requested_levels:
        if explicit_comparative and len(comparison_nodes) > 1:
            scoped_nodes = []
            seen_scoped_ids = set()
            for node in comparison_nodes:
                for child in _descendants(node):
                    child_id = child.get("id")
                    if child_id in seen_scoped_ids:
                        continue
                    seen_scoped_ids.add(child_id)
                    scoped_nodes.append(child)
        else:
            scoped_nodes = _descendants(focus_node) if focus_node else nodes
        level_nodes = [
            node for node in scoped_nodes
            if node.get("name")
            and (
                node.get("levelValue") in requested_levels
                or node.get("levelName") in requested_levels
                or any(value and value in str(node.get("name") or "") for value in requested_levels)
            )
        ]
        if level_nodes:
            comparison_nodes = level_nodes
    low_first = (
        str(query_intent.get("direction") or "").lower() == "asc"
        if query_intent.get("intent") == "ranking"
        else _negative_ranking_requested(question or "")
    )

    scene = detect_report_scene(question, focus_node if not explicit_comparative else None, len(matched_nodes))
    if query_intent.get("intent") == "ranking":
        scene = {
            "key": "ranking",
            "label": "排名分析",
            "layout": "ranking",
            "required_contract": ["nameColumn", "metrics"],
            "reasons": ["命中数据集意图策略：ranking"],
        }
    mode = scene.get("key", "detail")
    contract_health = validate_report_contract(config, columns, scene)
    compare_label = _level_label(comparison_nodes, "下一层级")
    detail_nodes = [item for node in comparison_nodes for item in _drill_children(node)]
    has_drill_detail = bool(detail_nodes)
    detail_label = _level_label(detail_nodes, "明细层级")

    chart_metrics = [metric for metric in [actual_metric, task_metric, remain_metric, rate_metric] if metric]

    def chart_row(node: Dict[str, Any]) -> Dict[str, Any]:
        row = {"名称": node["name"]}
        for metric in chart_metrics:
            row[metric.get("label") or metric.get("column") or metric.get("key")] = _row_value(node["raw"], metric) or 0
        return row

    compare_rows = sorted(
        [chart_row(node) for node in comparison_nodes],
        key=lambda item: item.get(sort_metric.get("label") or sort_metric.get("column") or "达成率", 0) if sort_metric else 0,
        reverse=not low_first,
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
        key=lambda item: _rate_sort_value(item, rate_metric),
        reverse=not low_first,
    )
    high_ranked_comparison_nodes = sorted(
        comparison_nodes,
        key=lambda item: _rate_sort_value(item, rate_metric),
        reverse=True,
    )
    high_node_rank = {node.get("id"): index + 1 for index, node in enumerate(high_ranked_comparison_nodes)}
    comparison_groups = _dynamic_performance_groups(
        comparison_nodes,
        lambda item: _row_value(item.get("raw") or {}, rate_metric) if rate_metric else None,
    )
    for node in ranked_comparison_nodes:
        raw_drill_children = _drill_children(node)
        is_leaf_level = not raw_drill_children
        drill_children = raw_drill_children or [node]
        node_detail_label = _level_label(drill_children, detail_label)
        if is_leaf_level:
            node_detail_label = node.get("levelValue") or node.get("levelName") or compare_label or "当前层级"
        sorted_children = sorted(drill_children, key=lambda item: _row_sort_value(item["raw"], rate_metric) if rate_metric else 0)
        sorted_children_desc = sorted(sorted_children, key=lambda item: _row_sort_value(item["raw"], rate_metric) if rate_metric else 0, reverse=True)
        child_groups = _dynamic_performance_groups(
            sorted_children_desc,
            lambda item: _row_value(item.get("raw") or {}, rate_metric) if rate_metric else None,
        )
        worst = child_groups["weak"][0] if child_groups.get("weak") else None
        best = child_groups["good"][0] if child_groups.get("good") else None
        rate = _row_value(node["raw"], rate_metric) if rate_metric else None
        child_chart_rows = []
        for child in sorted_children_desc:
            row = chart_row(child)
            child_rate = _row_value(child.get("raw") or {}, rate_metric) if rate_metric else None
            row["标签"] = _combined_performance_tag(
                child,
                child_groups,
                child_rate,
                thresholds["personRisk"],
                thresholds["personBenchmark"],
                "标杆",
            )
            child_chart_rows.append(row)
        risk_children = child_groups.get("weak", [])

        def build_drill_group(child: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            grandchildren = _drill_children(child)
            if not grandchildren:
                return None
            group_detail_label = _level_label(grandchildren, "下一层级")
            sorted_grandchildren = sorted(
                grandchildren,
                key=lambda item: _row_sort_value(item["raw"], rate_metric) if rate_metric else 0,
                reverse=True,
            )
            child_rate = _row_value(child["raw"], rate_metric) if rate_metric else None
            child_actual = _format_value(_row_value(child["raw"], actual_metric), actual_metric) if actual_metric else "-"
            child_task = _format_value(_row_value(child["raw"], task_metric), task_metric) if task_metric else "-"
            child_remain = _format_value(_row_value(child["raw"], remain_metric), remain_metric) if remain_metric else "-"
            group_rows = []
            grandchild_groups = _dynamic_performance_groups(
                sorted_grandchildren,
                lambda item: _row_value(item.get("raw") or {}, rate_metric) if rate_metric else None,
            )
            for grandchild in sorted_grandchildren:
                row = chart_row(grandchild)
                grandchild_rate = _row_value(grandchild.get("raw") or {}, rate_metric) if rate_metric else None
                row["标签"] = _combined_performance_tag(
                    grandchild,
                    grandchild_groups,
                    grandchild_rate,
                    thresholds["personRisk"],
                    thresholds["personBenchmark"],
                    "标杆",
                )
                group_rows.append(row)
            risk_grandchildren = grandchild_groups.get("weak", [])
            child_tag = _combined_performance_tag(
                child,
                child_groups,
                child_rate,
                thresholds["personRisk"],
                thresholds["personBenchmark"],
                "标杆",
            )
            return {
                "id": child.get("id"),
                "title": child.get("name"),
                "parentName": child.get("parentName"),
                "levelLabel": child.get("levelValue") or child.get("levelName") or node_detail_label,
                "detailLevelLabel": group_detail_label,
                "tone": _rate_tone(child_rate, thresholds["personRisk"], thresholds["personBenchmark"]),
                "tag": child_tag,
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
                             f"{len(risk_grandchildren)} 个{group_detail_label}相对承压。",
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
        node_tag = _combined_performance_tag(
            node,
            comparison_groups,
            rate,
            thresholds["officeRisk"],
            thresholds["officeBenchmark"],
            "区域标杆",
        )
        if child_groups.get("canCompare"):
            highlight = f"领先节点：{_format_dynamic_group(child_groups.get('good', []), rate_metric, '暂无明显领先节点')}"
            risk_text = f"相对承压：{_format_dynamic_group(risk_children, rate_metric, '暂无明显落后节点')}"
        elif len(sorted_children_desc) <= 1:
            highlight = f"仅 {len(sorted_children_desc)} 个{node_detail_label}，不做横向好坏对比"
            risk_text = "样本不足，不做相对承压标识"
        else:
            highlight = f"{node_detail_label}达成率接近，暂无明显领先节点"
            risk_text = "暂无明显落后节点"
        node_rank_value = high_node_rank.get(node.get("id"), 0)
        node_rank_label = _rate_rank_label(node_rank_value)
        node_rank_suffix = f"（{node_rank_label}）" if node_rank_value else ""
        detail_action_text = "当前最细层" if is_leaf_level else f"点击展开{len(sorted_children_desc)}个{node_detail_label}明细。"
        detail_narrative = (
            f"{node['name']}已是当前结果的最细层级，右侧展示该节点的任务、开单、缺口与达成率。"
            if is_leaf_level
            else (
                f"{node['name']}下钻到{node_detail_label}层：领先节点为{describe_detail(best)}；承压节点为{describe_detail(worst)}。"
                if child_groups.get("canCompare")
                else f"{node['name']}下钻到{node_detail_label}层：样本不足或差异不明显，不做首尾对比。"
            )
        )
        accordions.append({
            "id": node["id"],
            "title": node["name"],
            "parentName": node.get("parentName"),
            "levelLabel": node.get("levelValue") or node.get("levelName") or compare_label,
            "detailLevelLabel": node_detail_label,
            "isLeafLevel": is_leaf_level,
            "leafLabel": "当前最细层" if is_leaf_level else "",
            "rankLabel": node_rank_label,
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
                         f"{node_rank_suffix}\n"
                         f"任务{node_task} / 已完成{node_actual}"
                         f"{f' / 缺口{node_remain}' if remain_metric else ''}\n"
                         f"{highlight}；{risk_text}\n"
                         f"{detail_action_text}",
            "detailNarrative": detail_narrative,
            "chart": {
                "chartType": "horizontalDrill",
                "title": f"{node['name']}{node_detail_label}达成率与缺口",
                "columns": compare_columns,
                "rows": child_chart_rows,
            },
            "drillGroups": [item for item in (build_drill_group(child) for child in sorted_children_desc) if item],
        })

    comparison_groups = _dynamic_performance_groups(
        comparison_nodes,
        lambda item: _row_value(item.get("raw") or {}, rate_metric) if rate_metric else None,
    )
    comparison_tag_by_name = {
        node.get("name"): _combined_performance_tag(
            node,
            comparison_groups,
            _row_value(node.get("raw") or {}, rate_metric) if rate_metric else None,
            thresholds["officeRisk"],
            thresholds["officeBenchmark"],
            "区域标杆",
        )
        for node in comparison_nodes
        if node.get("name")
    }
    if compare_rows and comparison_tag_by_name:
        for row in compare_rows:
            row["标签"] = comparison_tag_by_name.get(row.get("名称"), "单体")
        if "标签" not in compare_columns:
            compare_columns.append("标签")
    best_node = comparison_groups["good"][0] if comparison_groups.get("good") else None
    worst_node = comparison_groups["weak"][0] if comparison_groups.get("weak") else None

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
    if mode == "comparative" and len(comparison_nodes) >= 2 and rate_metric and comparison_groups.get("canCompare"):
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
    if comparison_groups.get("canCompare") and rate_metric:
        leading_label = "领先主体" if comparison_groups.get("mode") == "pair" else "第一梯队"
        middle_label = "第二梯队"
        weak_label = "承压主体" if comparison_groups.get("mode") == "pair" else "第三梯队"
        summary_parts.append(
            f"{leading_label}："
            + _format_dynamic_group(comparison_groups.get("good", []), rate_metric, "暂无明显领先节点")
        )
        if comparison_groups.get("middle"):
            summary_parts.append(
                f"{middle_label}："
                + _format_dynamic_group(comparison_groups.get("middle", []), rate_metric, "暂无中位节点")
            )
        summary_parts.append(
            f"{weak_label}："
            + _format_dynamic_group(comparison_groups.get("weak", []), rate_metric, "暂无明显落后节点")
        )
    elif len(comparison_nodes) <= 1:
        summary_parts.append("当前可比对象不足 2 个，不做横向好坏对比。")

    overview_chart = {
        "chartType": "horizontalRateBar",
        "title": f"各{compare_label}{sort_metric.get('label') or sort_metric.get('column') or '达成率'}排序",
        "columns": compare_columns,
        "rows": compare_rows,
        "lowFirst": low_first,
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
            "query_intent": query_intent,
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
            {
                "key": "drill",
                "title": f"{compare_label}{'下钻' if has_drill_detail else '对比'}分析",
                "narrative": (
                    f"先横向比较{compare_label}，再纵向展开直接下级{detail_label}；业务员明细作为下一层证据，不直接替代管理层级判断。"
                    if has_drill_detail
                    else f"当前结果只返回到{compare_label}层级，先做横向对比；未返回下一层明细时不展示下钻卡片，避免误导。"
                ),
            },
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
