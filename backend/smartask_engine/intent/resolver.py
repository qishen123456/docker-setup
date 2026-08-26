from __future__ import annotations

import re
from typing import Any, Dict

from .output import IntentPorts


class IntentResolver:
    def __init__(self, ports: IntentPorts):
        self.ports = ports

    def resolve(self, question: str, context: Dict[str, Any]) -> Dict[str, Any]:
        config = self.ports.safe_dict(context.get("report_config")) or self.ports.default_report_config()
        policies = self.ports.safe_dict(config.get("intentPolicies"))
        ranking_policy = self.ports.safe_dict(policies.get("ranking"))
        text = str(question or "").replace("\n", " ").strip()
        text = self.ports.normalize_chinese_numbers(text)
        dataset = self.ports.safe_dict(context.get("dataset"))
        dataset_code = str(dataset.get("dataset_code") or "")
        dataset_name = str(dataset.get("dataset_name") or "")
        is_ecommerce_dataset = dataset_code == "feishu_tbldianshang" or "电商事业部" in dataset_name
        intent = {
            "intent": "unknown",
            "source": "report_config.intentPolicies",
            "target_level": "",
            "top_n": None,
            "sort_metric_key": "",
            "sort_metric_column": "",
            "direction": "",
            "rank_sides": "",
            "output_mode": "",
            "matched_triggers": [],
        }
        if not text:
            return intent

        # 根层级通常是 analysisDimensions 中每条 path 的第一个节点（如 电商事业部/消费者事业部）。
        # 识别 target_level 时，如果问题里同时提到根节点别名和更细层级别名，应优先取更细层级。
        root_level_values = {
            str(dimension.get("path")[0]).strip()
            for dimension in (config.get("analysisDimensions") or [])
            if isinstance(dimension.get("path") or [], list) and (dimension.get("path") or [])
        }

        def resolve_target_level_from_text() -> str:
            # 优先识别"节点 + 的 + 子层级"结构，避免"江浙沪分公司的城市分公司"被解析成 target_level="分公司"
            level_like_values = {"事业部", "分公司", "业务部", "代表处", "业务代表", "城市分公司", "城市公司", "区域条线", "行业条线"}
            level_pattern = "|".join(re.escape(level) for level in sorted(level_like_values, key=len, reverse=True))
            child_level_match = re.search(rf"(?:的|之下|下面|下属)\s*({level_pattern})\b", text)
            if child_level_match:
                return child_level_match.group(1)

            aliases = self.ports.safe_dict(ranking_policy.get("targetLevelAliases"))
            matches = []
            for level, level_aliases in aliases.items():
                candidates = [str(level)] + [str(item) for item in (level_aliases or [])]
                if str(level) == "城市分公司":
                    candidates.append("城市分公司")
                for candidate in candidates:
                    if not candidate:
                        continue
                    pos = text.rfind(candidate)
                    if pos != -1:
                        matches.append({"candidate": candidate, "level": str(level), "pos": pos, "is_root": str(level) in root_level_values})
            if "城市分公司" in text and "城市分公司" not in {m["candidate"] for m in matches}:
                matches.append({"candidate": "城市分公司", "level": "城市分公司", "pos": text.rfind("城市分公司"), "is_root": False})
            for dimension in config.get("analysisDimensions") or []:
                for level in dimension.get("path") or []:
                    if level and str(level) in text:
                        matches.append({"candidate": str(level), "level": str(level), "pos": text.rfind(str(level)), "is_root": str(level) in root_level_values})
            if not matches:
                return ""
            non_root = [m for m in matches if not m["is_root"]]
            pool = non_root if non_root else matches
            # 精确匹配优先：如果用户原话中某个候选词是独立出现的（不被更长的候选词包含），优先选它
            # 例如：用户说"分公司前3"而不是"城市分公司前3"，应选"分公司"
            exact_matches = []
            for m in pool:
                candidate = m["candidate"]
                is_substring_of_longer = any(
                    other["candidate"] != candidate
                    and candidate in other["candidate"]
                    and other["pos"] is not None
                    and m["pos"] is not None
                    and abs(other["pos"] - m["pos"]) < len(other["candidate"])
                    for other in pool
                )
                if not is_substring_of_longer:
                    exact_matches.append(m)
            if exact_matches:
                pool = exact_matches
            best = max(pool, key=lambda m: (m["pos"], len(m["candidate"])))
            return best["level"]

        # 口语化：“开单金额完成超过500万” -> “开单金额超过500万”，便于模式匹配
        text = re.sub(
            r"(年度开单金额|开单金额|总任务金额|任务金额|剩余任务金额|完成金额|年度目标营收|目标营收)\s*完成\s*(超过|大于|高于|小于|低于|不少于|不超过|等于|>=|<=|>|<)",
            r"\1\2",
            text,
        )

        filter_operator = ""
        if re.search(r"低于|不足|小于|低过|少于", text):
            filter_operator = "<"
        elif re.search(r"高于|超过|不少于|不低于|达到|达成率高|大于等于", text):
            filter_operator = ">="
        elif re.search(r"大于", text):
            filter_operator = ">"
        filter_value_match = re.search(r"(\d+(?:\.\d+)?)\s*%?", text)
        filter_value = float(filter_value_match.group(1)) if filter_value_match else None
        level_only_filter = bool(
            re.search(r'''属于['""“”](?:业务部|代表处|分公司|城市分公司|业务代表|城市公司|区域条线|行业条线)['""“”](?:层级|层|节点|数据)?''', text)
            or re.search(r"(?:哪些|哪个|哪家|哪几个|找出|筛选出).*(?:区域条线|行业条线)", text)
        )
        explicit_filter_question = bool(
            re.search(r"(?:哪些|哪个|哪家|哪几个).*(?:低于|不足|小于|少于|高于|超过|大于).*\d+(?:\.\d+)?\s*%?", text)
            or level_only_filter
            or re.search(r"(?:筛选出|找出).*(?:大于|小于|高于|低于|超过|不少于|不超过|等于|大于等于|小于等于)\s*0(?:\D|$)", text)
            or re.search(r"(?:达成率|完成率).*在\s*\d+(?:\.\d+)?\s*%?\s*到\s*\d+(?:\.\d+)?\s*%?\s*之间", text)
        )
        threshold_filter_question = bool(
            re.search(r"(?:低于|不足|小于|低过|少于|高于|超过|大于)", text)
            and re.search(r"\d+(?:\.\d+)?\s*%?", text)
            and re.search(r"(?:城市分公司|城市公司|分公司|代表处|业务部|业务员|业务代表|业务经理|细分业务)", text)
        )

        # 解析可能的多个数值过滤条件
        filter_conditions = []
        _metric_op_map = {
            "大于": ">", "大于等于": ">=", "高于": ">", "超过": ">", "不少于": ">=",
            "小于": "<", "小于等于": "<=", "低于": "<", "不超过": "<=", "少于": "<",
            "等于": "=", ">=": ">=", "<=": "<=", ">": ">", "<": "<", "=": "=",
        }
        _metric_name_map = {
            "年度开单金额": "年度开单金额",
            "年度开单": "年度开单金额",
            "开单金额": "年度开单金额",
            "开单": "年度开单金额",
            "完成金额": "年度开单金额",
            "完成": "年度开单金额",
            "总任务金额": "总任务金额",
            "总任务": "总任务金额",
            "任务金额": "总任务金额",
            "任务": "总任务金额",
            "达成率": "达成率",
            "完成率": "达成率",
            "剩余任务金额": "剩余任务金额",
            "剩余任务": "剩余任务金额",
            "缺口": "剩余任务金额",
        }
        _metric_pattern = re.compile(
            r"(年度开单金额|年度开单|开单金额|开单|完成金额|完成|总任务金额|总任务|任务金额|任务|达成率|完成率|剩余任务金额|剩余任务|缺口)"
            r"\s*(大于等于|小于等于|不少于|不超过|大于|小于|高于|低于|超过|等于|>=|<=|>|<|=)"
            r"\s*(\d+(?:\.\d+)?)\s*(万|亿)?\s*%?"
        )
        for m in _metric_pattern.finditer(text):
            col = _metric_name_map.get(m.group(1), "")
            op = _metric_op_map.get(m.group(2), ">=" if any(t in m.group(2) for t in ["大", "高", "超"]) else "<=")
            if col:
                # intent 层保留用户输入的原始数值，单位换算推迟到 SQL 构建阶段，
                # 保持 intent 测试与 SQL 测试的数值口径一致。
                raw_value = float(m.group(3))
                unit = m.group(4) or ""
                filter_conditions.append({"column": col, "operator": op, "value": raw_value, "unit": unit})
        # 达成率范围也作为 between 条件加入
        for m in re.finditer(r"(?:达成率|完成率).*?(\d+(?:\.\d+)?)\s*%?\s*到\s*(\d+(?:\.\d+)?)\s*%?\s*之间", text):
            filter_conditions.append({"column": "达成率", "operator": "between", "value": float(m.group(1)), "value2": float(m.group(2))})

        explicit_metric_filter = bool(filter_conditions)
        filter_problem = (
            explicit_filter_question
            or threshold_filter_question
            or explicit_metric_filter
            or (any(token in text for token in ["哪些", "哪个", "哪家", "哪几个"]) and bool(filter_operator))
            or bool(re.search(r"完成得不好|完成不好|承压|风险节点|风险|落后|不达标", text))
            # 零业绩口语也属过滤语义（bug 2026-08-25）：堵住后续 ranking/level_overview/drilldown 抽签路径
            or any(token in text for token in ["没有业绩", "没有开单", "没业绩", "无业绩", "零业绩", "没开单", "无开单", "零开单"])
        )
        target_level = resolve_target_level_from_text()
        # 电商数据集中，口语“业务承接人/负责人”统一收敛到标准层级“承接人”。
        # 优先级高于 resolve_target_level_from_text 对中间层级（如业务部）的命中，
        # 避免 confirm_by_boss 重写 refined_query 后引入“业务部”把承接人层级覆盖掉。
        if is_ecommerce_dataset and any(t in text for t in ["业务承接人", "承接人", "负责人", "任务承接人"]):
            target_level = "承接人"
        elif not target_level and "人" in text and not any(token in text for token in ["城市分公司", "城市公司", "分公司", "代表处", "业务部"]):
            target_level = "业务代表"

        drilldown_problem = bool(re.search(r"下面|下属|下级|展开看看|展开|明细|往下看|继续下钻|下钻|下有哪些|有哪些下属|下都", text))
        # “国内业务部的业务经理有哪些”这类“有哪些”列表问法，如果没有数值过滤，也视为下钻取子节点
        list_children_question = bool(
            target_level
            and not explicit_filter_question
            and not threshold_filter_question
            # 指标阈值过滤（如"开单金额=0"/"低于500万"）成立时不得劫持（bug 2026-08-25）
            and not explicit_metric_filter
            and re.search(r"(?:有哪些|有什么|包含哪些|名单|列表)", text)
            and re.search(r"(?:业务经理|负责人|细分业务|业务线|业务部)", text)
        )
        # filter 语义已成立时抑制 drilldown 劫持（bug 2026-08-25：
        # Agent1 refined 注入"明细/下属"曾把"低于500万的业务员"劫持到 drilldown 断裂 SQL）
        if (drilldown_problem and not filter_problem) or list_children_question:
            intent.update({
                "intent": "drilldown",
                "target_level": target_level,
                "output_mode": "children_first",
                "matched_triggers": ["drilldown"],
            })
            return intent

        # "A 比 B 重/大/高" 应优先于聚合意图
        bi_compare = re.search(r"(.+?)比(.+?)(重|大|高|多|低|小|少)$", text)
        if bi_compare and not re.search(r"\d+(?:\.\d+)?\s*%?", text):
            intent.update({
                "intent": "comparison",
                "target_level": target_level,
                "comparison_left": bi_compare.group(1).strip(),
                "comparison_right": bi_compare.group(2).strip(),
                "comparison_operator": "<" if bi_compare.group(3) in {"低", "小", "少"} else ">",
                "output_mode": "matched_nodes_first",
                "matched_triggers": ["comparison_bi"],
            })
            return intent

        # Aggregate intent: grouping + aggregation keywords without numeric threshold
        aggregate_tokens = ["每个", "各", "分别", "按.*汇总", "按.*统计", "按.*分组", "汇总", "统计每个", "统计各", "按.*算", "按.*计算"]
        aggregate_metric_tokens = ["平均", "总和", "总额", "总量", "总数", "数量", "个数", "合计", "统计"]
        has_aggregate_structure = any(re.search(token, text) for token in aggregate_tokens)
        has_aggregate_metric = any(token in text for token in aggregate_metric_tokens)
        asks_count = any(token in text for token in ["多少", "几个", "数量", "个数", "一共有", "总共有"])
        asks_total = (
            any(token in text for token in ["总和", "一共", "总共", "总计", "合计"])
            or bool(re.search(r"总[^的\s]*(?:金额|业绩|任务|开单|指标).*?(?:是多少|多少|怎么样|如何)", text))
        )
        asks_aggregate = has_aggregate_structure or has_aggregate_metric or asks_count or asks_total
        if asks_aggregate and not re.search(r"\d+(?:\.\d+)?\s*%?", text):
            resolved_names = self.ports.resolved_entity_names(context)
            level_like_values = {"事业部", "分公司", "业务部", "代表处", "业务代表", "城市分公司", "城市公司", "区域条线", "行业条线"}
            org_suffixes = ["分公司", "代表处", "业务部", "事业部", "城市分公司", "城市公司", "业务代表"]
            # 仅当 resolved 的是具体组织/人名实体时才跳过聚合；指标、动作类 token 仍走聚合
            non_level_resolved = [
                n for n in resolved_names
                if n and n not in level_like_values
                and any(n.endswith(suffix) for suffix in org_suffixes)
            ]
            if non_level_resolved:
                pass
            else:
                intent.update({
                    "intent": "aggregate",
                    "target_level": target_level,
                    "output_mode": "aggregation",
                    "matched_triggers": ["aggregate"],
                })
                return intent

        # 多具体对象 + 层级 Overview 词，按 filter/list 返回，避免误走末端个人 KPI
        level_like_values = {"事业部", "分公司", "业务部", "代表处", "业务代表", "城市分公司", "城市公司", "区域条线", "行业条线"}
        org_suffixes = ["分公司", "代表处", "业务部", "事业部", "城市分公司", "城市公司"]
        resolved_names = self.ports.resolved_entity_names(context)
        if not resolved_names:
            resolved_names = self.ports.question_subject_names(text, context, include_resolved=False)
        specific_names = [n for n in resolved_names if n and n not in level_like_values]
        # 没命中层级词，但提取到多个看起来像人名的对象时，兜底到业务代表层级
        if (
            not target_level
            and len(specific_names) >= 2
            and all(len(n) <= 4 and not any(n.endswith(s) for s in org_suffixes) for n in specific_names)
        ):
            target_level = "业务代表"
        overview_tokens = ["业绩", "表现", "情况", "咋样", "怎样", "如何"]
        has_ranking_token = bool(re.search(r"(?:前|后|倒数)\s*(?:\d+|[一二两三四五六七八九十]+)|排名|排行|top\s*\d*|最高|最低|最好|最差|最大|最小", text, flags=re.I))
        has_comparison_token = any(token in text for token in ("对比", "比较", "相比", "谁更", "哪个更"))
        # 过滤掉数据集根节点别名，避免把“商用事业部”本身也当成查询对象
        dataset = self.ports.safe_dict(context.get("dataset"))
        filtered_specific_names = [
            n for n in specific_names
            if n and not self.ports.is_dataset_root_name(n, dataset)
        ]
        if (
            len(filtered_specific_names) >= 2
            and target_level
            and not filter_problem
            and not drilldown_problem
            and not asks_aggregate
            and not has_ranking_token
            and any(token in text for token in overview_tokens)
            and not has_comparison_token
            and intent.get("intent") == "unknown"
        ):
            person_levels = {"业务代表", "业务员", "承接人", "负责人", "个人"}
            is_person_overview = target_level in person_levels
            if is_person_overview:
                intent.update({
                    "intent": "filter",
                    "target_level": target_level,
                    "filter_metric_key": "level_only",
                    "filter_metric_column": "",
                    "filter_operator": "",
                    "filter_value": None,
                    "_multi_parent_names": filtered_specific_names,
                    "direction": "desc",
                    "output_mode": "matched_nodes_first",
                    "matched_triggers": ["multi_entity_level_overview"],
                })
            else:
                intent.update({
                    "intent": "filter",
                    "target_level": target_level,
                    "filter_metric_key": "level_only",
                    "filter_metric_column": "",
                    "filter_operator": "",
                    "filter_value": None,
                    "_multi_parent": True,
                    "_multi_parent_names": filtered_specific_names,
                    "direction": "desc",
                    "output_mode": "children_first",
                    "matched_triggers": ["multi_parent_level_overview"],
                })
            return intent

        # 具体节点 + 目标子层级（如"江浙沪分公司的城市分公司"）识别为下钻
        resolved_names = self.ports.resolved_entity_names(context)
        if (
            resolved_names
            and not filter_problem
            and not has_ranking_token
            and intent.get("intent") == "unknown"
        ):
            level_like_values = {"事业部", "分公司", "业务部", "代表处", "业务代表", "城市分公司", "城市公司", "区域条线", "行业条线"}
            aliases = self.ports.safe_dict(ranking_policy.get("targetLevelAliases"))
            target_aliases = {target_level} | set(str(item) for item in (aliases.get(target_level) or []) if item) if target_level else set()
            for name in resolved_names:
                if not name or name in level_like_values:
                    continue
                # 节点名本身已经是目标层级实例的（如"业务代表靳锋"中的"靳锋"若 endswith 业务代表），不应视为下钻
                if target_aliases and any(name.endswith(alias) for alias in target_aliases):
                    continue
                # 只有当问题文本中明确出现"节点名 + 目标子层级"结构时才下钻
                # 例："江浙沪分公司的城市分公司" -> 节点名"江浙沪分公司" + "城市分公司"
                # 直接从文本中匹配节点名后的层级词，不依赖 resolve_target_level_from_text 的结果
                level_pattern = "|".join(re.escape(level) for level in sorted(level_like_values, key=len, reverse=True))
                match = re.search(rf"{re.escape(name)}(?:的|之下|下面|下属)?\s*({level_pattern})", text)
                if match:
                    intent.update({
                        "intent": "drilldown",
                        "target_level": match.group(1),
                        "output_mode": "children_first",
                        "matched_triggers": ["entity_with_target_level"],
                    })
                    return intent

        # Comparison intent: A 超过/大于/小于/等于 B (B is not a pure number)
        # 如果整体满足 filter 条件（如“看下大于一个亿的分公司”），优先走 filter 逻辑，不要误判为对比
        if filter_problem:
            symbol_match = None
            comparison_match = None
            vs_match = None
        else:
            # 1) Symbol comparison (e.g. A > B, A >= B)
            symbol_match = re.search(r"(.+?)\s*([><=≥≤]+)\s*(.+)", text)
        if symbol_match:
            left_text = symbol_match.group(1).strip()
            right_text = symbol_match.group(3).strip()
            if not re.match(r"^\d+(?:\.\d+)?\s*%?", right_text):
                symbol_op_map = {">": ">", "<": "<", "=": "=", "≥": ">=", "<=": "<=", ">=": ">=", "<=": "<="}
                matched_op = symbol_match.group(2).strip()
                if matched_op in symbol_op_map:
                    intent.update({
                        "intent": "comparison",
                        "target_level": target_level,
                        "comparison_left": left_text,
                        "comparison_right": right_text,
                        "comparison_operator": symbol_op_map[matched_op],
                        "output_mode": "matched_nodes_first",
                        "matched_triggers": ["comparison_symbol"],
                    })
                    return intent

        # 2) Chinese comparison (e.g. A 大于 B)
        if not filter_problem:
            comparison_match = re.search(r"(.+?)(超过|大于|高于|多于|不小于|小于|低于|少于|等于)(.+)", text)
        else:
            comparison_match = None
        if comparison_match:
            left_text = comparison_match.group(1).strip()
            right_text = comparison_match.group(3).strip()
            # Exclude numeric comparisons handled by filter intent
            if not re.match(r"^\d+(?:\.\d+)?\s*%?", right_text):
                operator_map = {
                    "超过": ">", "大于": ">", "高于": ">", "多于": ">", "不小于": ">=",
                    "小于": "<", "低于": "<", "少于": "<",
                    "等于": "=",
                }
                matched_op = comparison_match.group(2)
                intent.update({
                    "intent": "comparison",
                    "target_level": target_level,
                    "comparison_left": left_text,
                    "comparison_right": right_text,
                    "comparison_operator": operator_map.get(matched_op, ">"),
                    "output_mode": "matched_nodes_first",
                    "matched_triggers": ["comparison_chinese"],
                })
                return intent

        # 3) "A 和 B 比/比较" structure
        vs_match = re.search(r"(.+?)(?:和|与|跟|同)(.+?)(?:相比|比较|比|哪个|谁更)", text)
        if vs_match:
            left_text = re.sub(r"[的对比]+$", "", vs_match.group(1)).strip()
            right_text = re.sub(r"[的对比]+$", "", vs_match.group(2)).strip()
            if left_text and right_text:
                intent.update({
                    "intent": "comparison",
                    "target_level": target_level,
                    "comparison_left": left_text,
                    "comparison_right": right_text,
                    "comparison_operator": ">",
                    "output_mode": "matched_nodes_first",
                    "matched_triggers": ["comparison_vs"],
                })
                return intent

        # 口语化意图映射
        # 零业绩词表（bug 2026-08-25：原词表缺"没有业绩/没有开单"，
        # "没有业绩的业务代表有哪些"无法命中本分支 → 被 ranking/drilldown 抽签劫持）
        zero_actual_tokens = ["没有开张", "未开张", "零开单", "没开单", "无开单", "未开单", "没业绩", "零业绩", "无业绩", "未业绩", "没有业绩", "没有开单"]
        if any(token in text for token in zero_actual_tokens):
            intent.update({
                "intent": "filter",
                "target_level": target_level,
                "filter_metric_key": "actual",
                "filter_metric_column": "年度开单金额",
                "filter_operator": "=",
                "filter_value": 0,
                "direction": "asc",
                "output_mode": "matched_nodes_first",
                "matched_triggers": ["spoken_zero_actual"],
            })
            return intent

        lagging_tokens = ["拖后腿", "严重落后", "完成不好", "完成得不好", "承压", "风险大"]
        if any(token in text for token in lagging_tokens):
            intent.update({
                "intent": "filter",
                "target_level": target_level,
                "filter_metric_key": "rate",
                "filter_metric_column": "达成率",
                "filter_operator": "<",
                "filter_value": 10.0,
                "direction": "asc",
                "output_mode": "matched_nodes_first",
                "matched_triggers": ["spoken_lagging"],
            })
            return intent

        # 提前/超额完成 → 达成率 >= 100%
        completion_tokens = ["提前完成", "超额完成", "完成全年", "完成指标", "已经超额", "已超额"]
        if any(token in text for token in completion_tokens):
            intent.update({
                "intent": "filter",
                "target_level": target_level,
                "filter_metric_key": "rate",
                "filter_metric_column": "达成率",
                "filter_operator": ">=",
                "filter_value": 100.0,
                "direction": "desc",
                "output_mode": "matched_nodes_first",
                "matched_triggers": ["spoken_completion"],
            })
            return intent

        # 达成率在 X% 到 Y% 之间
        rate_range_match = re.search(r"(?:达成率|完成率).*?(\d+(?:\.\d+)?)\s*%?\s*到\s*(\d+(?:\.\d+)?)\s*%?\s*之间", text)
        if rate_range_match:
            intent.update({
                "intent": "filter",
                "target_level": target_level,
                "filter_metric_key": "rate",
                "filter_metric_column": "达成率",
                "filter_operator": "between",
                "filter_value": float(rate_range_match.group(1)),
                "filter_value2": float(rate_range_match.group(2)),
                "direction": "asc",
                "output_mode": "matched_nodes_first",
                "matched_triggers": ["filter_range"],
            })
            return intent

        # 金额类指标在 X 到 Y 之间
        amount_range_match = re.search(
            r"(年度开单金额|开单金额|总任务金额|年度目标营收|任务金额|剩余任务金额).*?(\d+(?:\.\d+)?)\s*(万|亿)?\s*%?\s*到\s*(\d+(?:\.\d+)?)\s*(万|亿)?\s*%?\s*之间",
            text,
        )
        if amount_range_match:
            metric_name = amount_range_match.group(1)
            key_map = {
                "年度开单金额": "actual", "开单金额": "actual",
                "总任务金额": "task", "年度目标营收": "task", "任务金额": "task",
                "剩余任务金额": "remain",
            }
            # intent 层保留原始数值，单位换算推迟到 SQL 构建阶段
            intent.update({
                "intent": "filter",
                "target_level": target_level,
                "filter_metric_key": key_map.get(metric_name, "actual"),
                "filter_metric_column": metric_name,
                "filter_operator": "between",
                "filter_value": float(amount_range_match.group(2)),
                "filter_value2": float(amount_range_match.group(5)),
                "direction": "asc",
                "output_mode": "matched_nodes_first",
                "matched_triggers": ["filter_amount_range"],
            })
            return intent

        if filter_problem:
            if filter_conditions:
                primary = filter_conditions[0]
                intent.update({
                    "intent": "filter",
                    "target_level": target_level,
                    "filter_metric_key": primary["column"],
                    "filter_metric_column": primary["column"],
                    "filter_operator": primary["operator"],
                    "filter_value": primary["value"],
                    "filter_value2": primary.get("value2"),
                    "direction": "asc" if primary["operator"] in {"<", "<="} else "desc",
                    "output_mode": "matched_nodes_first",
                    "matched_triggers": ["filter"],
                })
                if len(filter_conditions) > 1:
                    intent["filter_conditions"] = filter_conditions
                return intent

            # 纯层级/条线过滤，没有附带数值阈值，不要把题干里的数字当成阈值
            if level_only_filter:
                intent.update({
                    "intent": "filter",
                    "target_level": target_level,
                    "filter_metric_key": "level_only",
                    "filter_metric_column": "",
                    "filter_operator": "",
                    "filter_value": None,
                    "output_mode": "matched_nodes_first",
                    "matched_triggers": ["level_only_filter"],
                })
                return intent

            metrics = [item for item in (config.get("metrics") or []) if isinstance(item, dict)]
            text_lower = text.lower()
            metric_scores = []
            for m in metrics:
                key = str(m.get("key") or "").lower()
                label = str(m.get("label") or "").lower()
                col = str(m.get("column") or "").lower()
                score = 0
                if label and label in text_lower:
                    score += 100
                if col and col in text_lower:
                    score += 100
                if key == "rate" and any(t in text_lower for t in ["达成率", "完成率"]):
                    score += 80
                if key == "actual" and (
                    any(t in text_lower for t in ["开单", "实际", "销售", "完成金额"])
                    or ("完成" in text_lower and "完成率" not in text_lower)
                ):
                    # 关键修复：如果问题中已经包含完成率、达成率，actual 就不加分，优先让 rate 胜出
                    if "完成率" not in text_lower and "达成率" not in text_lower:
                        score += 80
                if key == "task" and any(t in text_lower for t in ["任务", "目标"]):
                    score += 80
                if key == "remain" and any(t in text_lower for t in ["剩余", "缺口", "差额", "待完成"]):
                    score += 80
                if score > 0:
                    metric_scores.append((score, m))
            metric = max(metric_scores, key=lambda x: x[0])[1] if metric_scores else {}
            if not metric:
                # 未命中任何指标时，根据阈值单位/量级做兜底推断
                text_lower = text.lower()
                has_rate_keyword = any(t in text_lower for t in ["达成率", "完成率", "进度", "比例", "%"])
                has_amount_unit = "万" in text or "亿" in text
                amount_like = (
                    not has_rate_keyword
                    and (
                        has_amount_unit
                        or (filter_value is not None and filter_value >= 100)
                        or ("完成" in text_lower and "完成率" not in text_lower)
                        or any(t in text_lower for t in ["开单", "实际", "销售", "完成金额"])
                    )
                )
                if amount_like:
                    metric = next((m for m in metrics if str(m.get("key") or "") == "actual"), {})
                    if not metric:
                        metric = next((m for m in metrics if "年度开单" in str(m.get("label") or "")), {})
                if not metric:
                    metric = next((m for m in metrics if str(m.get("key") or "") == "rate"), {})
            if not filter_operator:
                filter_operator = "<"
            if filter_value is None and filter_operator == "<":
                filter_value = 60.0
            intent.update({
                "intent": "filter",
                "target_level": target_level,
                "filter_metric_key": metric.get("key") or "rate",
                "filter_metric_column": metric.get("column") or metric.get("label") or "达成率",
                "filter_operator": filter_operator,
                "filter_value": filter_value,
                "direction": "asc" if filter_operator == "<" else "desc",
                "output_mode": "matched_nodes_first",
                "matched_triggers": ["filter"],
            })
            return intent

        triggers = [str(item) for item in (ranking_policy.get("triggers") or []) if str(item).strip()]

        def metric_match_score(metric_item: Dict[str, Any]) -> int:
            score = 0
            metric_key = str(metric_item.get("key") or "")
            metric_label = str(metric_item.get("label") or "")
            metric_column = str(metric_item.get("column") or "")
            metric_text = " ".join([metric_key, metric_label, metric_column])
            amount_tokens = ["销售金额", "销售额", "开单金额", "开单额", "年度开单金额", "年度开单", "开单", "实际金额", "实际", "完成金额", "业绩金额", "金额", "销售"]
            task_tokens = ["任务金额", "任务额", "目标金额", "目标", "任务"]
            remain_tokens = ["剩余任务", "剩余金额", "缺口", "差额", "待完成"]
            rate_tokens = ["达成率", "完成率", "进度", "比例", "rate", "percent"]
            text_lower = text.lower()
            has_rate_keyword = any(token in text_lower for token in ["达成率", "完成率"])

            if not has_rate_keyword and any(token in text for token in amount_tokens):
                if metric_key == "actual":
                    score += 60
                if any(token in metric_text for token in ["年度开单", "开单金额", "开单", "实际", "销售"]):
                    score += 40
            if any(token in text for token in task_tokens):
                if metric_key == "task":
                    score += 60
                if any(token in metric_text for token in ["任务", "目标"]):
                    score += 40
            if any(token in text for token in remain_tokens):
                if metric_key == "remain":
                    score += 60
                if any(token in metric_text for token in ["剩余", "缺口", "差额", "待完成"]):
                    score += 40
            if has_rate_keyword:
                if metric_key == "rate":
                    score += 100  # 修复：优先让率胜出
                if any(token in metric_text.lower() for token in [item.lower() for item in rate_tokens]):
                    score += 60

            if metric_key and metric_key in text:
                score += 30
            if metric_label and metric_label in text:
                score += 30
            if metric_column and metric_column in text:
                score += 30
            return score

        def trigger_matched(item: str) -> bool:
            if item in {"前", "后"}:
                return bool(re.search(rf"{re.escape(item)}\s*(?:\d+|[一二两三四五六七八九十]+)", text))
            if item.lower() == "top":
                return bool(re.search(r"\btop\s*(?:\d+|[一二两三四五六七八九十]+)?", text, flags=re.I))
            return item.lower() in text.lower()

        matched_triggers = [item for item in triggers if item and trigger_matched(item)]
        extra_ranking_tokens = ["排序", "从高到低", "从低到高", "最多", "最少", "最大", "最小", "缺口最大", "最好", "最差", "最高", "最低", "垫底"]
        if any(token in text for token in extra_ranking_tokens):
            matched_triggers.append("extra_sort")
        if not matched_triggers:
            # 层级 Overview：X层级 + 业绩/情况，无数值/对比/排名/聚合关键词 → 按 ranking/top_n=0 返回全部
            is_level_overview = (
                target_level
                and re.search(r"(?:业绩|表现|情况|咋样|怎样|如何)", text)
                and not filter_problem
                and not drilldown_problem
                and not asks_aggregate
            )
            # 如果 resolved 了具体节点，且 target_level 只是该节点名的一部分（如"江浙沪分公司业绩"），
            # 则不把它当作纯层级 Overview，继续后续规则处理。
            if is_level_overview:
                resolved_names = self.ports.resolved_entity_names(context)
                if resolved_names:
                    level_like_values = {"事业部", "分公司", "业务部", "代表处", "业务代表", "城市分公司", "城市公司", "区域条线", "行业条线"}
                    target_aliases = {target_level} | set(str(item) for item in (ranking_policy.get("targetLevelAliases", {}).get(target_level) or []) if item)
                    # 根节点（事业部）问题：仅当用户明确带"整体/总体/总览/汇总/全部"时才走整体概览；
                    # 不带这些词（如"电商事业部的业绩"）应走 §1.4 根节点默认带下级，不能被 level_overview 拦截。
                    overview_markers = ("整体", "总体", "总览", "汇总", "全部", "全局")
                    has_explicit_overview = any(kw in text for kw in overview_markers)
                    # 关键修复：根节点别名（消费者事业部/商用事业部/电商事业部）作为 target_level 时，
                    # 即使没"整体"词也走 level_overview 路径，避免落到 entity scope_filter 全下级瀑布。
                    is_root_level_target = target_level in {"消费者事业部", "商用事业部", "电商事业部"}
                    if any(
                        name and name not in level_like_values
                        and any(name.endswith(alias) for alias in target_aliases)
                        for name in resolved_names
                    ) and not has_explicit_overview and not is_root_level_target:
                        is_level_overview = False
                    # 如果 resolved 的是具体业务员成员，也不按层级概览处理，而是按单点查询
                    if is_level_overview:
                        overview_profile = self.ports.dataset_profile(dataset_code, dataset_name)
                        if overview_profile:
                            overview_person_members: set = set()
                            for level in overview_profile.get("levels") or []:
                                if str(level.get("dimension_name") or "").strip() in {"业务员", "业务代表"}:
                                    overview_person_members.update(str(m).strip() for m in level.get("members") or [] if str(m).strip())
                            if any(name in overview_person_members for name in resolved_names):
                                is_level_overview = False

            if is_level_overview:
                config_metrics = [item for item in (config.get("metrics") or []) if isinstance(item, dict)]
                default_metric = next(
                    (item for item in config_metrics if str(item.get("key") or "") == "rate"),
                    None,
                ) or {}
                intent.update({
                    "intent": "ranking",
                    "target_level": target_level,
                    "top_n": 0,
                    "sort_metric_key": default_metric.get("key") or "rate",
                    "sort_metric_column": default_metric.get("column") or default_metric.get("label") or "达成率",
                    "direction": "desc",
                    "rank_sides": "",
                    "output_mode": ranking_policy.get("outputMode") or "topn_only",
                    "matched_triggers": ["level_overview"],
                    "_level_overview": True,
                })
                return intent
            if target_level:
                intent["target_level"] = target_level
            return intent

        max_top_n = self.ports.safe_int(ranking_policy.get("maxTopN"), 20)
        rank_spec = self.ports.rank_request_spec(text, default_limit=0, max_limit=max_top_n)
        top_n = rank_spec.get("limit") if rank_spec.get("limit") is not None else None
        if top_n is not None:
            top_n = max(0, min(max_top_n, top_n))

        # 规则未提取到数量时，尝试读取 Agent1.5/LLM 解析的 ranking_params 作为补充
        # 规则优先，LLM 仅补漏，避免影响现有明确问法
        llm_ranking_params = (context.get("resolved_entities") or {}).get("ranking_params") if isinstance(context, dict) else None
        llm_filled_top_n = False
        if (top_n == 0 or top_n is None) and isinstance(llm_ranking_params, dict):
            llm_top_n = llm_ranking_params.get("top_n")
            if isinstance(llm_top_n, int) and llm_top_n > 0:
                top_n = max(0, min(max_top_n, llm_top_n))
                intent["_llm_top_n_fallback"] = True
                llm_filled_top_n = True

        # 单点最高/最低问法（“哪个最高/最低”或“最低的分公司”）默认只取 1 个，避免和“排名前 N”混淆
        # 只要没有显式数量（如“最低的三个”），且不是“最高和最低”同时问，就按单点处理
        # "垫底"也视为明确的倒数第一方向；若 LLM 已补漏数量，则不再覆盖。
        if (
            (top_n == 0 or top_n is None)
            and not llm_filled_top_n
            and rank_spec.get("sides") != "both"
            and any(t in text for t in ["最高", "最低", "最好", "最差", "垫底"])
            and not self.ports.rank_limit_match(text)
        ):
            top_n = 1

        negative_triggers = [str(item) for item in (ranking_policy.get("negativeTriggers") or []) if str(item).strip()]
        for nt in ["最少", "最小"]:
            if nt not in negative_triggers:
                negative_triggers.append(nt)
        direction = (
            "desc"
            if rank_spec.get("sides") == "both"
            else "asc" if any(item in text for item in negative_triggers)
            else str(ranking_policy.get("defaultDirection") or "desc")
        )
        if direction not in {"asc", "desc"}:
            direction = "desc"

        metrics = [item for item in (config.get("metrics") or []) if isinstance(item, dict)]
        scored_metrics = sorted(
            (
                (metric_match_score(item), item)
                for item in metrics
            ),
            key=lambda pair: pair[0],
            reverse=True,
        )
        metric = scored_metrics[0][1] if scored_metrics and scored_metrics[0][0] > 0 else None
        if not metric:
            default_metric_key = str(ranking_policy.get("defaultMetricKey") or "")
            metric = next((item for item in metrics if str(item.get("key") or "") == default_metric_key), None)
        metric = metric or {}

        intent.update({
            "intent": "ranking",
            "target_level": target_level,
            "top_n": top_n,
            "top_limit": rank_spec.get("top_limit") or 0,
            "bottom_limit": rank_spec.get("bottom_limit") or 0,
            "sort_metric_key": metric.get("key") or "",
            "sort_metric_column": metric.get("column") or metric.get("label") or "",
            "direction": direction,
            "rank_sides": rank_spec.get("sides") or "",
            "output_mode": ranking_policy.get("outputMode") or "topn_only",
            "matched_triggers": matched_triggers,
        })
        return intent
