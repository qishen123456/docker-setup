"""Pure helpers for the SmartAsk engine."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from ask_engine_profile import _is_dataset_root_name, _resolved_entity_names


def _build_trace_snapshot(trace: Dict[str, Any], include_result: bool = False) -> Dict[str, Any]:
    snapshot = {
        key: value
        for key, value in trace.items()
        if not str(key).startswith("_") and (include_result or key != "result")
    }
    if not include_result:
        snapshot.pop("result", None)
    return snapshot


def _build_confirmation_option(
    option_id: str,
    label: str,
    description: str = "",
    dataset_ids: Optional[List[int]] = None,
    option_type: str = "dataset_scope",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    option = {
        "id": option_id,
        "label": label,
        "description": description,
        "dataset_ids": [int(item) for item in (dataset_ids or []) if item is not None],
        "option_type": option_type,
    }
    if isinstance(extra, dict):
        for key, value in extra.items():
            if key in option or value is None:
                continue
            option[key] = value
    return option


def _format_metric(
    value: Optional[float],
    suffix: str = "",
    metric: Optional[Dict[str, Any]] = None,
) -> str:
    if value is None:
        return "-"
    if suffix:
        if value == int(value):
            return f"{int(value):,}{suffix}"
        return f"{value:.2f}{suffix}"

    def _fmt(num: float) -> str:
        if num == int(num):
            return str(int(num))
        return f"{num:.2f}".rstrip("0").rstrip(".")

    if isinstance(metric, dict) and metric.get("format") in ("amount", "currency"):
        unit = str(metric.get("unit") or "").strip()
        scale = float(metric.get("scale") or 0) or 1.0
        column = str(metric.get("column") or "").strip()
        if not unit:
            if "_万元" in column or column.endswith("万元"):
                unit = "万元"
            else:
                unit = "元"
        display = value / scale
        abs_display = abs(display)
        if unit == "万元":
            if abs_display < 10000:
                return _fmt(display) + "万"
            return _fmt(display / 10000) + "亿"
        # unit == "元"：与商用数据集保持一致的自动缩放展示
        if abs_display < 10000:
            return _fmt(display)
        if abs_display < 1000000:
            return f"{display / 10000:.1f}".rstrip("0").rstrip(".") + "万"
        if abs_display < 100000000:
            return f"{round(display / 10000)}万"
        return f"{display / 100000000:.2f}".rstrip("0").rstrip(".") + "亿"

    # 兼容旧调用：未传入 metric 时默认按元口径处理
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


def _build_display_title(question: str, dataset_result: Dict[str, Any]) -> str:
    """基于 query_intent 和数据集名称生成一句简洁的展示标题。"""
    from collections import Counter

    query_intent = dataset_result.get("query_intent") or {}
    dataset_name = str(dataset_result.get("dataset_name") or "").strip()

    # 数据集简称：去掉“飞书/安吉”等前缀后优先保留“…事业部”，否则保留有意义的部分
    cleaned_name = re.sub(r"^(飞书|安吉|cloud|公共)\s*", "", dataset_name, flags=re.I)
    domain_match = re.search(r".*?事业部", cleaned_name)
    if domain_match:
        domain = domain_match.group(0)
    else:
        # 去掉“测试数据集/数据集/数据/业绩/报告”等无意义后缀
        domain = re.sub(r"(测试数据集|数据集|数据|业绩|报告|分析|预算)$", "", cleaned_name, flags=re.I).strip() or cleaned_name
        # 如果剩下来的是“消费者/商用”等事业部简称，补上“事业部”
        if domain and not domain.endswith("事业部") and re.match(r"^(消费者|商用|电商|飞书).*$", domain):
            domain = domain + "事业部"

    intent = str(query_intent.get("intent") or "").strip()
    rows = dataset_result.get("rows") or []
    target_level = str(query_intent.get("target_level") or "").strip()
    # 标题层级优先使用 query_intent.target_level；只有为空时才按返回行中最多层级兜底
    if not target_level and rows:
        levels = [str(r.get("层级") or "").strip() for r in rows if r.get("层级")]
        if levels:
            target_level = Counter(levels).most_common(1)[0][0]

    # 指标标签支持业务线口径展示
    metric_label_map = {
        "年度开单金额": "开单金额",
        "线下业务开单金额": "线下业务开单金额",
        "新零售业务开单金额": "新零售业务开单金额",
        "燃气定制业务开单金额": "燃气定制业务开单金额",
        "地产业务开单金额": "地产业务开单金额",
        "总任务金额": "任务金额",
        "剩余任务金额": "剩余任务金额",
        "达成率": "达成率",
    }
    metric_key_map = {"actual": "开单金额", "task": "任务金额", "remain": "剩余任务金额", "rate": "达成率"}

    def metric_label(metric_key: str, metric_column: str) -> str:
        if metric_column in metric_label_map:
            return metric_label_map[metric_column]
        if metric_key in metric_label_map:
            return metric_label_map[metric_key]
        return metric_key_map.get(metric_key) or metric_key or "指标"

    op_text_map = {">": "大于", ">=": "大于等于", "<": "小于", "<=": "小于等于", "=": "等于", "between": "在"}

    def _level_filter_title(names: List[str], level: str) -> str:
        if not names:
            suffix = f"{level}筛选结果" if level else "筛选结果"
            return f"{domain}{suffix}" if domain else suffix
        shown = names[:3]
        joined = "、".join(shown)
        if len(names) > 3:
            joined = f"{joined}等"
        return f"{domain}{joined}的筛选结果" if domain else f"{joined}的筛选结果"

    if intent == "filter":
        metric_key = str(query_intent.get("filter_metric_key") or "")
        # 纯层级/点名 filter，没有附带数值阈值
        if metric_key == "level_only":
            resolved_names = _resolved_entity_names(dataset_result)
            if query_intent.get("_multi_parent"):
                dataset_hint = {"dataset_name": dataset_result.get("dataset_name") or ""}
                parent_names = [
                    n for n in (query_intent.get("_multi_parent_names") or resolved_names)
                    if not _is_dataset_root_name(n, dataset_hint)
                ]
                shown = parent_names[:3]
                joined = "、".join(shown)
                if len(parent_names) > 3:
                    joined = f"{joined}等"
                return f"{domain}{joined}的业绩" if domain else f"{joined}的业绩"
            return _level_filter_title(resolved_names, target_level)
        metric_column = str(query_intent.get("filter_metric_column") or "")
        operator = str(query_intent.get("filter_operator") or "")
        value = query_intent.get("filter_value")
        value2 = query_intent.get("filter_value2")
        label = metric_label(metric_key, metric_column)
        is_rate = label == "达成率"
        suffix = "%" if is_rate else ""

        if operator == "between" and value is not None and value2 is not None:
            value_text = f"{_format_metric(value, suffix)}到{_format_metric(value2, suffix)}之间"
            op_text = ""
        else:
            value_text = _format_metric(value, suffix) if value is not None else ""
            # 金额类阈值优先按题干单位显示
            if not is_rate and value is not None:
                if "亿" in question and float(value) < 10000:
                    value_text = f"{int(value)}亿" if float(value) == int(value) else f"{value}亿"
                elif "万" in question and float(value) < 10000:
                    value_text = f"{int(value)}万" if float(value) == int(value) else f"{value}万"
            op_text = op_text_map.get(operator, "超过") if operator else "超过"

        parts = [domain, label]
        if op_text:
            parts.append(op_text)
        if value_text:
            parts.append(value_text)
        title = "".join(parts)
        if target_level:
            title = f"{title}的{target_level}"
        return title

    if intent == "ranking":
        metric_key = str(query_intent.get("sort_metric_key") or "")
        metric_column = str(query_intent.get("sort_metric_column") or "")
        label = metric_label(metric_key, metric_column)
        top_n = query_intent.get("top_n")
        direction = str(query_intent.get("direction") or "desc")
        rank_word = "排名后" if direction == "asc" else "排名前"
        if target_level and top_n:
            return f"{rank_word}{top_n}的{target_level}"
        # 单点“哪个最高/最低”问法，标题直接表达为“最高的分公司”
        if top_n == 1 and (
            re.search(r"哪个|哪一家", question or "")
            or re.search(r"最高|最低|最好|最差", question or "")
        ):
            extrema_word = "最低" if direction == "asc" else "最高"
            if target_level:
                title = f"{domain}{label}{extrema_word}的{target_level}"
            else:
                title = f"{domain}{extrema_word}的对象"
            return title
        # 排名类标题：数据集 + 层级 + 指标 + 排名（+ TopN），避免“达成率的分公司”这种倒装
        if target_level:
            title = f"{domain}{target_level}{label}排名"
        else:
            title = f"{domain}{label}排名"
        if top_n:
            title = f"{title}{rank_word}{top_n}"
        return title

    # 兜底：去掉口语前缀后返回
    return re.sub(
        r"^(?:我说的是|我说的是|我说|我的问题是|我想问|我想知道|请问|问一下|看一下|查一下|看下|查下|请|麻烦|帮我|给我|告诉我|咨询一下|了解一下|看看)(?:[，,：:\s]+)?",
        "",
        str(question or ""),
    ).strip()
