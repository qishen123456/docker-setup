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
    if metric.get("format") in ("amount", "currency"):
        return _format_amount(numeric, metric)
    if numeric == int(numeric):
        return f"{int(numeric):,}"
    return f"{numeric:.2f}"


def _metric_unit_hint(metric: Optional[Dict[str, Any]]) -> str:
    if not metric:
        return ""
    return f"{metric.get('label', '')}{metric.get('column', '')}{metric.get('unit', '')}"


def _column_uses_wan_unit(column: str) -> bool:
    """判断列名是否明确表示数值单位为万元。"""
    text = str(column or "")
    return "_万元" in text or "转换万" in text or text.endswith("万")


def _format_amount(value: float, metric: Optional[Dict[str, Any]] = None) -> str:
    unit = ""
    scale = 1.0
    if isinstance(metric, dict):
        unit = str(metric.get("unit") or "").strip()
        scale = float(metric.get("scale") or 0) or 1.0
    if not unit:
        hint = _metric_unit_hint(metric)
        if "万元" in hint or "_万元" in hint or _column_uses_wan_unit(metric.get("column") if isinstance(metric, dict) else ""):
            unit = "万元"
        else:
            unit = "元"

    display = value / scale
    abs_display = abs(display)

    def fmt(num: float) -> str:
        if num == int(num):
            return str(int(num))
        return f"{num:.2f}".rstrip("0").rstrip(".")

    if unit == "万元":
        if abs_display < 10000:
            return fmt(display) + "万"
        return fmt(display / 10000) + "亿"

    # 默认按 "元" 口径缩放展示
    if abs_display < 10000:
        return fmt(display)
    if abs_display < 1000000:
        return f"{display / 10000:.1f}".rstrip("0").rstrip(".") + "万"
    if abs_display < 100000000:
        return f"{round(display / 10000)}万"
    return f"{display / 100000000:.2f}".rstrip("0").rstrip(".") + "亿"


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


def _extract_amount_unit_from_config(config: Dict[str, Any]) -> str:
    if not isinstance(config, dict):
        return ""

    direct_candidates = [
        config.get("amountUnit"),
        config.get("amountUnitConvention"),
        (config.get("display") or {}).get("amountUnit") if isinstance(config.get("display"), dict) else "",
        (config.get("sqlOutputContract") or {}).get("amountUnit") if isinstance(config.get("sqlOutputContract"), dict) else "",
    ]
    for candidate in direct_candidates:
        text = str(candidate or "").strip()
        if text in {"元", "万元", "亿"}:
            return text

    return ""


def _dataset_amount_unit(
    dataset: Dict[str, Any],
    config: Dict[str, Any],
    columns: Optional[List[str]] = None,
    profile: Optional[Dict[str, Any]] = None,
) -> str:
    configured_unit = _extract_amount_unit_from_config(config)
    if configured_unit:
        return configured_unit

    for column in columns or []:
        if _column_uses_wan_unit(column):
            return "万元"

    return ""


def _normalize_amount_metrics(
    metrics: List[Dict[str, Any]],
    dataset: Dict[str, Any],
    config: Dict[str, Any],
    columns: Optional[List[str]] = None,
    profile: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    amount_unit = _dataset_amount_unit(dataset, config, columns, profile)
    if not amount_unit:
        return metrics

    normalized: List[Dict[str, Any]] = []
    for metric in metrics:
        if not isinstance(metric, dict):
            continue
        next_metric = dict(metric)
        if next_metric.get("format") in {"amount", "currency"}:
            next_metric["unit"] = amount_unit
            next_metric["scale"] = 1
        normalized.append(next_metric)
    return normalized


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
    column = scored[0][1]
    metric = {"key": key, "label": label, "column": column, "format": fmt}
    if fmt == "amount":
        # 列名显式带 "_万元"/"万元" 时按万元口径解析，否则统一按商用数据集元口径处理
        if _column_uses_wan_unit(column):
            metric["unit"] = "万元"
            metric["scale"] = 1
        else:
            metric["unit"] = "元"
            metric["scale"] = 1
    return metric


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
    common_values = ["城市分公司", "城市公司", "事业部", "业务部", "分公司", "代表处", "业务代表", "业务员", "部门", "条线"]
    alias_map = {"城市公司": "城市分公司"}
    for value in sorted([*configured_values, *common_values], key=len, reverse=True):
        canonical = alias_map.get(value, value)
        if value and value in text and canonical not in values:
            values.append(canonical)
    return values


def _canonical_level_value(value: Any) -> str:
    text = str(value or "").strip()
    alias_map = {
        "城市公司": "城市分公司",
    }
    return alias_map.get(text, text)


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


def _nodes_match_requested_levels(nodes: List[Dict[str, Any]], requested_level_set: set) -> bool:
    if not nodes or not requested_level_set:
        return False
    for node in nodes:
        level_value = _canonical_level_value(node.get("levelValue") or node.get("levelName"))
        if level_value not in requested_level_set:
            return False
    return True


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
    if text and node_name:
        normalized_question = text.replace("城市分公司", "城市公司")
        normalized_node = node_name.replace("城市分公司", "城市公司")
        if normalized_node and normalized_node in normalized_question:
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
    expanded = []
    for name in names:
        if name not in expanded:
            expanded.append(name)
        alias = name.replace("城市分分公司", "城市公司").replace("城市分公司", "城市公司")
        if alias and alias not in expanded:
            expanded.append(alias)
        reverse_alias = name.replace("城市公司", "城市分公司")
        if reverse_alias and reverse_alias not in expanded:
            expanded.append(reverse_alias)
    return expanded


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
    profile = get_dataset_profile(dataset.get("dataset_code") or dataset.get("code"), dataset.get("dataset_name") or dataset.get("name"))
    metrics = [
        metric for metric in [task_metric, actual_metric, rate_metric, remain_metric]
        if metric
    ] + [
        metric for metric in metrics
        if metric and metric not in [task_metric, actual_metric, rate_metric, remain_metric]
    ]
    metrics = _normalize_amount_metrics(metrics, dataset, config, available_columns, profile)
    task_metric = next((metric for metric in metrics if str(metric.get("key") or "") == "task"), task_metric)
    actual_metric = next((metric for metric in metrics if str(metric.get("key") or "") == "actual"), actual_metric)
    rate_metric = next((metric for metric in metrics if str(metric.get("key") or "") == "rate"), rate_metric)
    remain_metric = next((metric for metric in metrics if str(metric.get("key") or "") == "remain"), remain_metric)
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
    if ranking_sort_metric:
        sort_column_label = str(query_intent.get("sort_metric_column") or "").strip()
        if sort_column_label and sort_column_label not in {
            str(ranking_sort_metric.get("column") or ""),
            str(ranking_sort_metric.get("label") or ""),
            str(ranking_sort_metric.get("key") or ""),
        }:
            ranking_sort_metric = {
                **ranking_sort_metric,
                "label": sort_column_label,
            }
    sort_metric = ranking_sort_metric or rate_metric or actual_metric or task_metric or remain_metric or {}
    is_ranking_mode = query_intent.get("intent") == "ranking"

    resolved_names = _resolved_member_names(resolved_entities)
    if not resolved_names:
        if profile:
            resolved_names = _resolved_member_names(resolve_member_mentions(question or "", profile))
    explicit_single_focus_name = ""
    if len(resolved_names) == 1 and any((node.get("name") or "") == resolved_names[0] for node in nodes):
        explicit_single_focus_name = resolved_names[0]
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
    # 只有题干明确出现对比/比较类词汇时才视为显式对比；避免“各分公司排名”因错误解析出多个成员而被当成对比
    explicit_comparative = bool(re.search(r"对比|比较|谁更|差异|分别|各自|和.+比|跟.+比|与.+比|\bvs\b", question or "", re.I))
    requested_levels = _requested_level_values(question or "", config)
    query_target_level = _canonical_level_value(query_intent.get("target_level"))
    if query_target_level and query_target_level not in requested_levels:
        requested_levels.insert(0, query_target_level)
    requested_level_set = {_canonical_level_value(value) for value in requested_levels if str(value or "").strip()}
    focus_node = None
    if len(matched_nodes) == 1:
        focus_node = matched_nodes[0]
    else:
        focus_node = next(
            (
                node for node in matched_nodes
                if not requested_level_set or _canonical_level_value(node.get("levelValue") or node.get("levelName")) not in requested_level_set
            ),
            None,
        ) or next((node for node in matched_nodes if node.get("children")), None)
    if explicit_single_focus_name:
        focus_node = next((node for node in nodes if node.get("name") == explicit_single_focus_name), focus_node)
    is_single_focus_question = bool(focus_node) and not explicit_comparative and len(matched_nodes) == 1
    if explicit_comparative and len(matched_nodes) > 1:
        comparison_nodes = sorted(
            matched_nodes,
            key=lambda item: _question_node_order(question or "", item.get("name") or "", resolved_order),
        )
    else:
        comparison_nodes = focus_node.get("children", []) if focus_node else []
    if is_single_focus_question and not comparison_nodes and focus_node:
        comparison_nodes = [focus_node]
    elif not comparison_nodes and len(tree["roots"]) == 1:
        root = tree["roots"][0]
        root_level = _canonical_level_value(root.get("levelValue") or root.get("levelName"))
        if requested_levels and root_level in requested_level_set:
            comparison_nodes = [root]
        else:
            comparison_nodes = root.get("children", [])
    if not comparison_nodes and not is_single_focus_question:
        parent_nodes = [node for node in nodes if node.get("children")]
        max_depth = max([node.get("depth", 0) for node in parent_nodes] or [0])
        comparison_nodes = [node for node in parent_nodes if node.get("depth", 0) == max_depth]
    # 对于“筛选出...节点”这种没有指定层级的过滤问题，默认不要只取根节点的子节点，应该遍历全部节点
    if (
        query_intent.get("intent") == "filter"
        and not requested_levels
        and not focus_node
        and not matched_nodes
    ):
        comparison_nodes = [node for node in nodes if node.get("name")]
    # 排名类问题如果只返回同层节点（没有父节点在结果里），直接把这些节点作为比较对象
    if not comparison_nodes and query_intent.get("intent") == "ranking":
        comparison_nodes = [node for node in nodes if node.get("name")]
    comparison_nodes = [node for node in comparison_nodes if node.get("name")]
    if (
        query_intent.get("intent") == "filter"
        and requested_level_set
        and _nodes_match_requested_levels(nodes, requested_level_set)
    ):
        comparison_nodes = [node for node in nodes if node.get("name")]
        focus_node = None
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
                _canonical_level_value(node.get("levelValue")) in requested_level_set
                or _canonical_level_value(node.get("levelName")) in requested_level_set
                or any(value and value in str(node.get("name") or "") for value in requested_levels)
            )
        ]
        if level_nodes:
            comparison_nodes = level_nodes
            if len(level_nodes) == 1:
                focus_node = level_nodes[0]
            elif query_intent.get("intent") == "filter":
                focus_node = None
    low_first = (
        str(query_intent.get("direction") or "").lower() == "asc"
        if query_intent.get("intent") == "ranking"
        else _negative_ranking_requested(question or "")
    )

    scene = detect_report_scene(question, focus_node if not explicit_comparative else None, len(matched_nodes), query_intent)
    if query_intent.get("intent") == "ranking":
        scene = {
            "key": "ranking",
            "label": "排名分析",
            "layout": "ranking",
            "required_contract": ["nameColumn", "metrics"],
            "reasons": ["命中数据集意图策略：ranking"],
        }
    elif query_intent.get("intent") == "filter":
        scene = {
            "key": "filter",
            "label": "filter",
            "layout": "filter",
            "required_contract": ["nameColumn", "metrics"],
            "reasons": ["query_intent.intent=filter"],
        }
    elif query_intent.get("intent") == "drilldown":
        scene = {
            "key": "drilldown",
            "label": "drilldown",
            "layout": "detail",
            "required_contract": ["nameColumn", "metrics"],
            "reasons": ["query_intent.intent=drilldown"],
        }
    mode = scene.get("key", "detail")
    contract_health = validate_report_contract(config, columns, scene)
    compare_label = _level_label(comparison_nodes, "下一层级")
    detail_nodes = [item for node in comparison_nodes for item in _drill_children(node)]
    has_drill_detail = bool(detail_nodes)
    detail_label = _level_label(detail_nodes, "明细层级")
    # 未指定层级的全量节点过滤，层级标签用“全部”，避免前端默认卡到某一层
    if (
        query_intent.get("intent") == "filter"
        and not requested_levels
        and not focus_node
        and not matched_nodes
    ):
        compare_label = "全部"
        detail_label = "全部"

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

    def metric_value_text(node: Dict[str, Any], metric: Optional[Dict[str, Any]]) -> str:
        if not metric:
            return "-"
        return _format_value(_row_value(node.get("raw") or {}, metric), metric)

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

    def kpi_payload(metric: Dict[str, Any], raw: Dict[str, Any]) -> Dict[str, Any]:
        value = _row_value(raw, metric)
        return {
            "label": metric.get("label") or metric.get("column") or metric.get("key"),
            "value": value,
            "displayValue": _format_value(value, metric),
            "format": metric.get("format"),
        }

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
        key=lambda item: _row_sort_value(item.get("raw") or {}, sort_metric if sort_metric else rate_metric),
        reverse=not low_first,
    )
    high_ranked_comparison_nodes = sorted(
        comparison_nodes,
        key=lambda item: _row_sort_value(item.get("raw") or {}, sort_metric if sort_metric else rate_metric),
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
        sorted_children = sorted(
            drill_children,
            key=lambda item: _row_sort_value(item["raw"], sort_metric if sort_metric else rate_metric) if (sort_metric or rate_metric) else 0,
        )
        sorted_children_desc = sorted(
            sorted_children,
            key=lambda item: _row_sort_value(item["raw"], sort_metric if sort_metric else rate_metric) if (sort_metric or rate_metric) else 0,
            reverse=True,
        )
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
                    kpi_payload(metric, child["raw"])
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
        if is_leaf_level and child_chart_rows:
            child_chart_rows[0]["标签"] = node_tag
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
        node_rank_label = f"排序第{node_rank_value}" if is_ranking_mode and node_rank_value else _rate_rank_label(node_rank_value)
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
            "childCount": 0 if is_leaf_level else len(sorted_children_desc),
            "rankLabel": node_rank_label,
            "tag": node_tag,
            "highlight": highlight,
            "riskSummary": risk_text,
            "tone": _rate_tone(rate, thresholds["officeRisk"], thresholds["officeBenchmark"]),
            "kpis": [
                kpi_payload(metric, node["raw"])
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
        "chartType": "horizontalRateBar" if (sort_metric or {}).get("format") == "percent" else "bar",
        "title": f"各{compare_label}{sort_metric.get('label') or sort_metric.get('column') or '达成率'}排序",
        "columns": compare_columns,
        "rows": compare_rows,
        "sortColumn": sort_metric.get("label") or sort_metric.get("column") or sort_metric.get("key"),
        "lowFirst": low_first,
    } if compare_rows else None

    answer_mode = (
        "filter" if query_intent.get("intent") == "filter"
        else "ranking" if query_intent.get("intent") == "ranking"
        else "drilldown" if query_intent.get("intent") == "drilldown"
        else mode
    )
    matched_filter_nodes: List[Dict[str, Any]] = []
    answer_summary: Dict[str, Any] = {}
    if answer_mode == "filter":
        filter_metric_key = str(query_intent.get("filter_metric_key") or "")
        filter_metric_column = str(query_intent.get("filter_metric_column") or "")
        filter_metric = next(
            (
                metric for metric in metrics
                if (
                    filter_metric_key and str(metric.get("key") or "") == filter_metric_key
                ) or (
                    filter_metric_column and filter_metric_column in {
                        str(metric.get("column") or ""),
                        str(metric.get("label") or ""),
                        str(metric.get("key") or ""),
                    }
                )
            ),
            None,
        ) or rate_metric or sort_metric
        filter_operator = str(query_intent.get("filter_operator") or "<")
        try:
            filter_value = float(query_intent.get("filter_value"))
        except (TypeError, ValueError):
            filter_value = thresholds.get("officeRisk") if filter_operator in {"<", "<="} else None
        # intent 层保留原始数值，report spec 阶段根据问题中的单位换算，与 SQL 层口径一致
        is_rate_metric = (
            (filter_metric or {}).get("format") == "percent"
            or "率" in str((filter_metric or {}).get("label") or "")
        )
        if not is_rate_metric and filter_value is not None:
            if "亿" in question and filter_value < 10000:
                filter_value = filter_value * 100000000
            elif "万" in question and filter_value < 10000:
                filter_value = filter_value * 10000

        def filter_matches(node: Dict[str, Any]) -> bool:
            value = _row_value(node.get("raw") or {}, filter_metric)
            if value is None:
                return False
            if filter_value is None:
                return True
            if filter_operator in {"<", "<="}:
                return value <= filter_value if filter_operator == "<=" else value < filter_value
            if filter_operator in {">", ">="}:
                return value >= filter_value if filter_operator == ">=" else value > filter_value
            return value == filter_value

        matched_source_nodes = sorted(
            [node for node in comparison_nodes if filter_matches(node)],
            key=lambda item: _row_sort_value(item.get("raw") or {}, filter_metric),
            reverse=filter_operator in {">", ">="},
        )
        matched_filter_nodes = [
            {
                "id": node.get("id"),
                "name": node.get("name"),
                "parentName": node.get("parentName"),
                "levelLabel": node.get("levelValue") or node.get("levelName") or compare_label,
                "tag": comparison_tag_by_name.get(node.get("name")) or "",
                "kpis": [
                    kpi_payload(metric, node.get("raw") or {})
                    for metric in [task_metric, actual_metric, rate_metric, remain_metric]
                    if metric
                ],
                "metric": {
                    "label": filter_metric.get("label") or filter_metric.get("column") or filter_metric.get("key"),
                    "value": _format_value(_row_value(node.get("raw") or {}, filter_metric), filter_metric),
                    "rawValue": _row_value(node.get("raw") or {}, filter_metric),
                },
            }
            for node in matched_source_nodes
        ]
        answer_summary = {
            "mode": "filter",
            "title": "命中结果",
            "targetLevel": compare_label,
            "matchedCount": len(matched_filter_nodes),
            "metricLabel": filter_metric.get("label") or filter_metric.get("column") or filter_metric.get("key"),
            "operator": filter_operator,
            "value": filter_value,
            "text": (
                f"命中 {len(matched_filter_nodes)} 个{compare_label}"
                if matched_filter_nodes
                else f"未命中符合条件的{compare_label}"
            ),
        }

    if answer_mode == "ranking" and not answer_summary:
        rank_sides = str(query_intent.get("rank_sides") or "")
        raw_top_n = query_intent.get("top_n")
        if raw_top_n is None or raw_top_n == "":
            effective_limit = 10
        else:
            effective_limit = int(raw_top_n)
        # top_n=0 表示用户未指定数量，返回全部节点
        rank_limit = max(0, min(len(ranked_comparison_nodes), effective_limit)) if ranked_comparison_nodes else 0
        if rank_sides == "both" and rank_limit:
            bottom_nodes = list(reversed(ranked_comparison_nodes[-rank_limit:]))
            ranked_nodes = []
            seen_node_ids = set()
            for node in [*ranked_comparison_nodes[:rank_limit], *bottom_nodes]:
                node_id = node.get("id") or node.get("name")
                if node_id in seen_node_ids:
                    continue
                seen_node_ids.add(node_id)
                ranked_nodes.append(node)
        elif rank_limit > 0:
            ranked_nodes = ranked_comparison_nodes[:rank_limit]
        else:
            ranked_nodes = ranked_comparison_nodes
        top_nodes = ranked_comparison_nodes[:rank_limit] if rank_limit > 0 else ranked_comparison_nodes
        bottom_nodes = list(reversed(ranked_comparison_nodes[-rank_limit:])) if rank_sides == "both" and rank_limit > 0 else []
        is_single_extreme = rank_sides != "both" and rank_limit == 1
        if is_single_extreme and ranked_nodes:
            extreme_label = "最低" if low_first else "最高"
            answer_title = f"{extreme_label}结果"
            answer_text = f"{extreme_label}的{compare_label}是 {ranked_nodes[0].get('name')}"
        else:
            answer_title = "排名结果"
            sort_label = sort_metric.get('label') or sort_metric.get('column') or '指标'
            if rank_sides == "both" and ranked_nodes:
                answer_text = f"已按{sort_label}输出前{rank_limit}和后{rank_limit}个{compare_label}的排序结果"
            elif not ranked_nodes:
                answer_text = f"当前没有可排序的{compare_label}结果"
            elif query_intent.get("_level_overview"):
                order_phrase = "从低到高" if low_first else "从高到低"
                answer_text = f"共 {len(ranked_nodes)} 个{compare_label}，按{sort_label}{order_phrase}排序"
            else:
                answer_text = f"已按{sort_label}输出 {len(ranked_nodes)} 个{compare_label}的排序结果"
        answer_summary = {
            "mode": "ranking",
            "title": answer_title,
            "targetLevel": compare_label,
            "metricLabel": sort_metric.get("label") or sort_metric.get("column") or sort_metric.get("key"),
            "direction": "asc" if low_first else "desc",
            "rankSides": rank_sides,
            "topN": len(ranked_nodes),
            "leader": ranked_nodes[0].get("name") if ranked_nodes else "",
            "tail": ranked_nodes[-1].get("name") if len(ranked_nodes) > 1 else "",
            "text": answer_text,
            "topNames": [node.get("name") for node in top_nodes],
            "bottomNames": [node.get("name") for node in bottom_nodes],
        }
    elif answer_mode == "drilldown" and not answer_summary:
        focus_name = focus_node.get("name") if focus_node else ""
        child_count = len(comparison_nodes)
        is_leaf_focus = bool(focus_node) and not bool(focus_node.get("children"))
        if is_leaf_focus:
            answer_text = f"已定位到 {focus_name}，当前展示其个人业绩指标"
        elif focus_node and comparison_nodes:
            answer_text = f"已定位到 {focus_name}，当前展示其下一级 {child_count} 个{compare_label}"
        else:
            answer_text = f"当前展示 {child_count} 个{compare_label}下级节点"
        answer_summary = {
            "mode": "drilldown",
            "title": "下钻结果",
            "targetLevel": compare_label,
            "focusNode": focus_name,
            "childCount": child_count,
            "text": answer_text,
        }

    # 单点最高/最低问题，默认把答案节点作为聚焦节点，让前端展示其下级明细
    if (
        answer_mode == "ranking"
        and rank_sides != "both"
        and rank_limit == 1
        and ranked_nodes
        and not focus_node
    ):
        focus_node = ranked_nodes[0]

    provenance_id = "p_sql_result_001"
    sort_spec = {
        "metricKey": sort_metric.get("key") or "",
        "metricLabel": sort_metric.get("label") or sort_metric.get("column") or sort_metric.get("key") or "",
        "metricColumn": sort_metric.get("column") or sort_metric.get("label") or "",
        "direction": "asc" if low_first else "desc",
        "appliesTo": answer_mode if answer_mode in {"ranking", "filter"} else mode,
        "source": "query_intent" if query_intent.get("intent") == "ranking" else "default",
    }
    return {
        "version": "2.0",
        "reportTitle": str(config.get("reportTitle") or "业绩分析报告"),
        "amountUnit": _dataset_amount_unit(dataset, config, available_columns, profile),
        "question": question,
        "answerMode": answer_mode,
        "answerSummary": answer_summary,
        "sortSpec": sort_spec,
        "matchedNodes": matched_filter_nodes,
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
            "focusNodeIsLeaf": bool(focus_node) and not bool(focus_node.get("children")),
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
                    else f"当前结果已返回到{compare_label}层级；若已是最细层，则直接展示本层完成情况，不再继续下钻。"
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
