"""Pure helpers for the SmartAsk engine."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


def _normalize_entity_key(value: Any) -> str:
    return re.sub(r"[\s,，、/\\|()（）【】\[\]{}<>《》“”\"'：:；;.!！?？-]+", "", str(value or "")).lower()


def _has_specific_node(context: Dict[str, Any]) -> bool:
    resolved = context.get("resolved_entities") or {}
    flag = resolved.get("has_specific_node")
    if isinstance(flag, bool):
        return flag
    return True


def _clean_org_subject_candidate(value: str) -> str:
    text = str(value or "").strip("，。！？、 ")
    text = re.sub(
        r"^(?:请|麻烦|帮我|帮忙|我想看|我想查|我想问|我想知道|我想了解|想看|想查|想问|看下|看一下|查下|查一下|查询|查询下|查询一下|帮我看看|麻烦帮我查下|麻烦帮我看下|问下|问一下|分析下|分析一下|了解下|了解一下|再看|再看下|再看一下|继续看|继续看下|继续看一下|继续查|继续查下|继续查一下)+",
        "",
        text,
    ).strip()
    # 去掉口语方位/指代词，避免 "上海那边"、"东部那个" 这类干扰
    text = re.sub(r"那边|那个|这块|那块|这边|这个|这位|那位", "", text).strip()
    # 去掉前缀数量词，避免 "三个业务部"、"前3分公司" 被当成主体名称。
    # 计数词必须跟量词（个/位/名...）才剥，避免吃掉 "三明"、"四川" 这种首字是数字的人名/地名。
    text = re.sub(r"^(?:前|第)?\s*(?:一|二|三|四|五|六|七|八|九|十|两|几|\d+)\s*(?:个|大|家|者|位|名)", "", text).strip("，。！？、 ")
    # 去掉尾部通用业务词与口语后缀
    text = re.sub(
        r"(?:的)?(?:业绩.*|表现.*|情况.*|完成情况.*|完成的怎么样.*|完成得怎么样.*|完成咋样.*|啥情况.*|啥.*)$",
        "",
        text,
    )
    text = re.sub(
        r"(?:的)?(?:怎么样了|怎么样|如何了|如何|咋样|怎样)$",
        "",
        text,
    ).strip("，。！？、 ")
    return text


def _node_index_match_key(item: Dict[str, Any]) -> Tuple[int, str, str, str, str]:
    return (
        int(item.get("dataset_id") or 0),
        str(item.get("node_name") or "").strip(),
        str(item.get("node_level") or "").strip(),
        str(item.get("parent_name") or "").strip(),
        str(item.get("track") or "").strip(),
    )


def _extract_subject_from_confirmation_label(label: str) -> str:
    text = str(label or "").strip()
    if not text:
        return ""
    text = re.sub(r"^系统推荐[:：]\s*", "", text)
    for sep in [" - ", " · ", "-", "·"]:
        if sep in text:
            text = text.split(sep, 1)[-1].strip()
            break
    text = re.sub(r"(的)?(业绩|情况|表现|完成情况|完成率|达成率|数据)$", "", text).strip()
    return text


def _looks_like_org_subject_question(question: str) -> bool:
    text = str(question or "").strip()
    if not text:
        return False
    # 纯层级词（如"城市分公司"）+ 业绩/情况，不应走主体追问，应直接按层级 Overview 处理
    level_only_terms = {"分公司", "代表处", "业务部", "城市分公司", "城市公司", "事业部", "业务代表", "业务员"}
    stripped = re.sub(r"^(?:看下|看一下|查下|查一下|查询|看看|请看下|请查下)", "", text)
    stripped = re.sub(r"(?:的)?(?:业绩|表现|情况|咋样|怎样|如何|咋样了|怎样了|如何了)$", "", stripped).strip("，,、 的")
    if stripped in level_only_terms:
        return False
    # 排名/TopN 类问题不应被当作组织主体追问处理，否则数量词（前3、前三等）
    # 会在重写时被丢掉，导致 SQL 不限制行数、标题也失真。
    # 裸中文基数词/阿拉伯数字 + 量词（四大/三个/五家/三家公司/4个事业部）同样属于
    # 排名/限定计数，必须排除，否则"四大分公司..."会被改写成"分公司的业绩"丢掉"四"。
    # 量词表与 _clean_org_subject_candidate 的前缀剥离正则保持一致，避免词表漂移。
    if re.search(r"(?:前|后|倒数)\s*(?:\d+|[一二两三四五六七八九十]+)|排名|排行|top\s*\d*|最高|最低|最好|最差|最大|最小|(?:[一二两三四五六七八九十]+|\d+)\s*(?:个|大|家|者|位|名|项)", text, flags=re.I):
        return False
    # 带数值阈值/单位（如小于500万、超过80%）的筛选问题，应走 filter 路径，
    # 不要当成组织主体追问处理，避免过滤条件被 refined_query 覆盖掉。
    has_numeric_threshold = bool(
        re.search(
            r"(?:大于等于|小于等于|不少于|不超过|大于|小于|高于|低于|超过|不足|等于|>=|<=|>|<)\s*(?:\d+(?:\.\d+)?)\s*(?:万|亿|%)?",
            text,
        )
    )
    if has_numeric_threshold:
        return False
    # aggregate 类问题不应被当作组织主体追问处理，
    # 否则"每个/各/平均/总和/总额"等聚合信号会被重写时丢掉。
    aggregate_tokens = ["每个", "各", "分别", "平均", "总和", "总额", "总量", "总数",
                       "数量", "个数", "合计", "统计", "总计", "总计值"]
    has_aggregate = bool(any(token in text for token in aggregate_tokens))
    if has_aggregate:
        return False
    # comparison 类问题不应被当作组织主体追问处理，
    # 否则"对比/比较/相比/差异"等比较信号会被重写时丢掉。
    comparison_tokens = ["对比", "比较", "相比", "vs", "哪个更好", "哪个更差",
                        "差异", "差距", "优劣", "胜出"]
    has_comparison = bool(any(token in text for token in comparison_tokens))
    if has_comparison:
        return False
    # overview 类问题（整体/总体/总览/汇总/全部/全局）不应被重写为"XX的业绩"，
    # 否则会丢失总览语义，导致返回全量数据而非聚合结果。
    overview_tokens = ["整体", "总体", "全部", "汇总", "总览", "全局", "整体情况",
                      "总体情况", "全部数据"]
    has_overview = bool(any(token in text for token in overview_tokens))
    if has_overview:
        return False
    # 具体节点 + 目标子层级（如"江浙沪分公司的城市分公司"）应直接走 drilldown 规则，
    # 不要经过 Agent1 改写，避免子层级信息被丢失。
    level_like_values = {"事业部", "分公司", "业务部", "代表处", "业务代表", "城市分公司", "城市公司", "区域条线", "行业条线"}
    level_pattern = "|".join(re.escape(level) for level in sorted(level_like_values, key=len, reverse=True))
    if re.search(rf"[\u4e00-\u9fa5A-Za-z0-9（）()]{{2,}}(?:的|之下|下面|下属)?\s*({level_pattern})\s*$", text):
        return False
    has_org_level = bool(re.search(r"代表处|分公司|业务部|城市分公司|城市公司|事业部|业务代表|业务员", text))
    has_spoken_style = bool(
        re.search(
            r"继续|再看|再查|看下|看一下|查下|查一下|查询下|问下|分析下|了解下|如何了|怎么样了|情况如何|啥情况了|啥情况|情况咋样|情况怎样|表现如何|那边|这边|那个|这块|那块|想看|帮我看|麻烦看|咋样|怎样",
            text,
        )
    )
    # 兜底：地名/组织简称 + 业绩/表现/情况等通用词，也视为可能的主体问法
    has_generic_org_metric = bool(
        re.search(r"^[\u4e00-\u9fa5]{2,}(?:业绩|表现|情况|咋样|怎样)", text)
    )
    return has_org_level or has_spoken_style or has_generic_org_metric


def _infer_subject_level_from_name(subject_name: str) -> str:
    text = str(subject_name or "").strip()
    if not text:
        return ""
    for suffix, level in (
        ("城市分公司", "城市分公司"),
        ("城市公司", "城市公司"),
        ("代表处", "代表处"),
        ("业务部", "业务部"),
        ("分公司", "分公司"),
        ("事业部", "事业部"),
        ("业务代表", "业务代表"),
        ("业务员", "业务代表"),
    ):
        if text.endswith(suffix):
            return level
    return ""
