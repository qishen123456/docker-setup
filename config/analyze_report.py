#!/usr/bin/env python3
"""分析测试报告中的异常，输出原因分类与解决方案"""
import json
import re
from collections import defaultdict

RESULT_PATH = "/app/config/smartask_test_results_20260627_070408.json"
OUT_PATH = "/app/config/smartask_issue_analysis.md"


def load():
    with open(RESULT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["results"]


def has_flag(r, flag):
    return flag in r.get("flags", [])


def is_empty(r):
    res = r.get("result", {})
    return res.get("row_count") == 0 and res.get("kpis") == []


def dataset_id(r):
    ids = r.get("result", {}).get("dataset_ids", [])
    return ids[0] if ids else None


def display_title(r):
    return r.get("result", {}).get("display_title", "") or ""


def intent(r):
    return r.get("result", {}).get("intent", "")


def route_decision(r):
    return r.get("result", {}).get("decision", "")


def requires_confirmation(r):
    return r.get("result", {}).get("requires_confirmation", False)


def sql_sample(r):
    return r.get("result", {}).get("sql", "") or ""


def categorize(r):
    q = r["question"]
    target = r["target"]
    flags = r.get("flags", [])
    res = r.get("result", {})
    ds = dataset_id(r)
    title = display_title(r)
    sql = sql_sample(r)
    reasons = []

    # 1. 通用层级词被当实体
    generic_levels = {"事业部", "分公司", "代表处", "业务部", "业务代表", "城市分公司", "承接人"}
    if "节点名称 IN ('代表处')" in sql or "节点名称 IN ('分公司')" in sql or "节点名称 IN ('业务部')" in sql:
        reasons.append(("generic_level_as_entity", "SQL 把层级词（代表处/分公司/业务部）当作节点名称过滤"))

    # 2. 跨数据集对比未识别
    if target == "跨数据集":
        reasons.append(("cross_dataset_not_supported", "跨数据集对比未被识别，系统只选了一个数据集"))

    # 3. 应确认但未确认 / 不应确认却确认
    if has_flag(r, "未按预期弹确认"):
        reasons.append(("missing_confirmation", "多义集合词（事业部/业务部/代表处）未触发确认，直接锁定数据集"))
    if has_flag(r, "意外弹确认"):
        reasons.append(("unexpected_confirmation", "边界/不存在节点触发确认或路由守卫返回空"))

    # 4. 不存在的节点 / 时间维度 / 越界数量
    if any(w in q for w in ["华北分公司", "不存在的代表处", "2023 年", "前 0 名", "前 100", "最高 5 名"]):
        reasons.append(("boundary_unsupported", "问题涉及不存在节点、不支持的时间维度或非法数量"))

    # 5. 排序指标 / N 值理解错误
    if re.search(r"按.*(开单金额|金额|达成率|毛利率).*排", q) and not re.search(r"按.*排", title):
        reasons.append(("sort_metric_misunderstood", "未按问题指定指标排序"))
    if "排名" in q and title and not re.search(r"排名(前|后)\d+", title) and not re.search(r"前\s*\d+|后\s*\d+|第\s*\d+", q):
        reasons.append(("rank_default_limit", "排名问法未给 N，系统默认 top3 与预期可能不符"))

    # 6. 多条件筛选丢失
    if re.search(r"低于\s*\d+%?.*且|高于\s*\d+%?.*且|且.*超过", q):
        if "AND" not in sql.upper() or len(re.findall(r"达成率\s*[<>=]|年度开单金额\s*[<>=]|总任务金额\s*[<>=]", sql)) < 2:
            reasons.append(("multi_condition_lost", "多条件筛选只保留了一个条件"))

    # 7. 指标口径错误（毛利率/利润/目标营收完成率）
    if "毛利率" in q and "达成率" in title and "毛利率" not in title and "毛利" not in sql:
        reasons.append(("metric_mismatch", "问题问毛利率，SQL/标题用了达成率"))
    if "利润" in q and "达成率" in title:
        reasons.append(("metric_mismatch", "问题问利润，系统回退到达成率"))
    if "目标营收完成率" in q and "达成率" in title and "年度目标营收" not in sql:
        reasons.append(("metric_mismatch", "自定义完成率口径未正确生成"))

    # 8. 下钻层级过滤为空
    if "下属" in q or "下有哪些" in q or ("业绩" in q and any(w in q for w in ["代表处", "业务部", "城市分公司"])):
        if is_empty(r) and ds in (2, 3):
            reasons.append(("drill_filter_empty", "下钻/层级过滤后结果为空，可能是父节点名或层级映射错误"))

    # 9. 标题扩展化/模板化
    if has_flag(r, "卡片标题与问题关联度低"):
        if re.search(r"排名(前|后)\d+", title) and "排名" not in q and not re.search(r"前|后|最高|最低", q):
            reasons.append(("title_template_expansion", "系统将非排名问法扩展为排名前N标题"))
        elif title and not any(k in title for k in re.findall(r"[\u4e00-\u9fa5]+", q)):
            reasons.append(("title_unrelated", "标题与问题关键词基本无关"))

    # 10. 电商 vs 对比类空结果
    if ds == 62 and is_empty(r) and any(w in q for w in ["vs", "对比", "和", "与", "负责人"]):
        reasons.append(("ecommerce_special_case", "电商数据集特殊问法（对比/负责人）未命中数据或 SQL 口径未适配"))

    # 兜底
    if not reasons:
        if is_empty(r):
            reasons.append(("empty_unknown", "结果为空，需进一步查看 SQL"))
        elif has_flag(r, "卡片标题与问题关联度低"):
            reasons.append(("title_heuristic", "仅标题启发式标记，结论可能正常"))
        else:
            reasons.append(("other", "其他"))
    return reasons


def main():
    rows = load()
    groups = defaultdict(list)
    for r in rows:
        if not r.get("flags"):
            continue
        reasons = categorize(r)
        for code, desc in reasons:
            groups[code].append({
                "id": r["id"],
                "question": r["question"],
                "target": r["target"],
                "flags": r.get("flags", []),
                "reason_desc": desc,
                "dataset": dataset_id(r),
                "title": display_title(r),
            })

    lines = [
        "# SmartAsk 测试问题根因分析与解决方案",
        "",
        f"- 分析对象：`config/smartask_test_results_20260627_070408.json`（170 题）",
        f"- 异常/待确认题数：{sum(1 for r in rows if r.get('flags'))}",
        "- 当前阶段：只分析原因、给出方案，不修改代码",
        "",
        "## 一、问题分类汇总",
        "",
        "| 类别编码 | 类别说明 | 涉及题数 | 典型问题 |",
        "|---|---|---|---|",
    ]
    sorted_groups = sorted(groups.items(), key=lambda x: -len(x[1]))
    for code, items in sorted_groups:
        desc = items[0]["reason_desc"]
        examples = [i["question"] for i in items[:2]]
        lines.append(f"| {code} | {desc} | {len(items)} | {' / '.join(examples)} |")

    lines.append("")
    lines.append("## 二、每类问题详细原因与解决方案")
    lines.append("")

    solutions = {
        "generic_level_as_entity": {
            "cause": [
                "Agent1/Agent2 在解析层级词时，把『代表处/分公司/业务部/城市分公司』等通用层级标签和具体节点名称混在一起，作为 `resolved_entities` 传给 SQL 生成器。",
                "SQL 生成器在排名/筛选分支里，直接把这些标签放入 `节点名称 IN (...)` 或 `上级名称 IN (...)`，导致没有任何节点能匹配。"
            ],
            "solution": [
                "在 SQL 生成入口处维护一份 `LEVEL_LABELS = {'事业部','分公司','代表处','业务部','业务代表','城市分公司','承接人'}`。",
                "任何从 `resolved_entities` 或正则提取出的『实体』，如果是纯层级标签，且不等于某个具体节点名，就不加入节点过滤条件。",
                "只对包含业务前缀/区域前缀的具体节点（如『东部分公司』、『甘青宁代表处』）才生成 `节点名称 IN (...)`。",
                "在 `dataset_route.py` 或 `route_guard.py` 增加层级词识别：如果问题只包含层级词而没有具体节点，应标记为需要确认或强制按层级聚合。"
            ]
        },
        "cross_dataset_not_supported": {
            "cause": [
                "当前路由逻辑是单数据集模式。遇到『商用事业部和消费者事业部对比』时，Agent1 只返回一个最高分数据集，Agent2 也按单数据集生成 SQL。",
                "没有独立的 cross-dataset execution / union 阶段，也没有把问题拆成两个子查询再合并的模块。"
            ],
            "solution": [
                "在 Agent2 增加『跨数据集对比』意图分支。",
                "当检测到多个明确数据集名称/业务域时，分别对每个数据集生成 SQL，得到结果后按相同指标对齐。",
                "报告层用对比卡展示两个数据集的整体 KPI，而不是只展示一个。",
                "如果指标口径不一致（如金额单位、字段含义不同），系统应显式提示，而不是强行对比。"
            ]
        },
        "missing_confirmation": {
            "cause": [
                "`route_guard.py` 的 `exact_match_texts` 匹配只看数据集名称/业务域/同义词，而『事业部/业务部/代表处』在多个数据集里都可能成立。",
                "`DatasetRouteSkill.score` 给通用层级词的加分过低或没有区分，导致某个数据集因其他特征（如业务域）得分偏高，直接 auto_lock。"
            ],
            "solution": [
                "当问题只包含通用层级词（事业部/分公司/业务部/代表处/城市分公司）且不含具体节点名时，强制进入确认流程。",
                "在 `route_guard.py` 中增加 `generic_level_only` 判断：如果问题匹配 `LEVEL_LABELS` 且未命中任何具体节点，返回 `requires_confirmation`。",
                "把 `LEVEL_LABELS` 从 `DatasetRouteSkill` 的加分项中剔除，避免它们拉高某个数据集的分数。"
            ]
        },
        "unexpected_confirmation": {
            "cause": [
                "边界问题（如『华北分公司』不存在、『2023 年业绩』时间不支持、『前 0 名』非法数量）没有独立兜底。",
                "路由守卫无法判断节点是否存在，或无法识别不支持的时间维度，于是 fallback 到确认或返回空结果。"
            ],
            "solution": [
                "在 Agent1 增加『存在性校验』：用组织树/数据字典快速判断提到的节点名是否真实存在。",
                "不存在节点直接返回友好提示：『未找到名为“华北分公司”的节点，请检查名称或切换数据源』。",
                "时间维度问题单独识别：如果问题含年份/季度且数据集只有当前年，提示『当前数据集仅支持 2026 年』。",
                "非法 topN（如 0、负数、超大数）在 Agent2 前置校验，自动修正为合理值并提示用户。"
            ]
        },
        "boundary_unsupported": {
            "cause": [
                "同 unexpected_confirmation，主要是缺失前置语义校验。"
            ],
            "solution": [
                "建立『不支持语义清单』（时间、跨数据集、不存在节点、非法数量），在 Agent1/Agent2 入口拦截。",
                "对拦截场景返回结构化错误，而不是 0 行结果。"
            ]
        },
        "sort_metric_misunderstood": {
            "cause": [
                "`query_intent.sort_metric_column` 解析失败，fallback 到默认指标（通常是达成率）。",
                "问题里的『按年度开单金额排』被 NLU 忽略或识别为筛选条件而非排序指标。"
            ],
            "solution": [
                "增强排序指标识别：支持『按 X 排 / 按 X 排序 / X 最高的 N 个』。",
                "在 Agent2 中把排序指标传给 SQL 生成器，覆盖默认指标。",
                "如果排序指标与问题里的其他指标冲突，优先使用问题明确指定的指标。"
            ]
        },
        "rank_default_limit": {
            "cause": [
                "问题只问『排名』但没给 N，系统默认取 top3。",
                "用户预期可能是全部排名，或 top10。"
            ],
            "solution": [
                "默认 limit 可改为 10，或在报告里明确说明『展示前 10，其余可展开』。",
                "提供『查看全部』交互，或支持用户追加『前 20』等限定。"
            ]
        },
        "multi_condition_lost": {
            "cause": [
                "Agent2 的 SQL 生成模板只支持单条件过滤，多条件被截断。",
                "NLU 把『达成率低于 50% 且缺口超过 1000 万』只解析出一个条件。"
            ],
            "solution": [
                "在 Agent2 的过滤条件解析中支持 AND/OR 组合。",
                "把多个过滤条件作为列表传给 SQL builder，每个条件独立生成 where 片段后再用 AND 拼接。",
                "Agent3 SQL 复核增加多条件校验，确保没有丢失条件。"
            ]
        },
        "metric_mismatch": {
            "cause": [
                "数据集 62 有毛利率/利润字段，但 SQL 生成器只认识达成率/开单金额/任务金额/剩余任务。",
                "当问题问『毛利率』时，Agent2 找不到对应指标，fallback 到达成率。"
            ],
            "solution": [
                "在数据集配置/数据字典里补充毛利率、利润、目标营收完成率等指标定义和同义词。",
                "SQL 生成器读取数据字典，按需生成 `ROUND(毛利/收入,2)` 或读取已有字段。",
                "指标找不到时返回『当前数据集暂不支持“毛利率”口径』，而不是用错误指标替代。"
            ]
        },
        "drill_filter_empty": {
            "cause": [
                "下钻问法（如『东部分公司下属代表处』）的层级映射或父节点名匹配错误。",
                "有的数据集用『分公司→代表处→业务代表』，有的用『业务部→业务代表』，SQL 的 `上级名称` 映射和实际数据不完全一致。"
            ],
            "solution": [
                "统一层级映射配置：每个数据集声明层级字段和父子关系。",
                "下钻 SQL 使用 `组织路径 LIKE '父节点%'` 或递归 CTE，而不是仅依赖 `上级名称` 字符串匹配。",
                "对不存在的父节点先做存在性校验。"
            ]
        },
        "title_template_expansion": {
            "cause": [
                "报告生成器为了套用模板，把『哪个分公司最低』扩展成『达成率排名前3的分公司』，导致标题和原问题差异大。",
                "`display_title` 是 Agent4 根据 report_spec 生成的，倾向于使用『排名前N』这种固定句式。"
            ],
            "solution": [
                "Agent4 生成标题时，优先复用问题原句中的关键意图词（最低/最高/后N/低于X%）。",
                "如果问题本身没有排名词，标题不要强行加『排名前N』；可用『达成率最低的分公司』这类自然表达。",
                "为不同意图（极值、筛选、下钻、对比）配置专属标题模板。"
            ]
        },
        "title_unrelated": {
            "cause": [
                "Agent4 fallback 到默认标题（如『经营分析报告』），或 display_title 为空。"
            ],
            "solution": [
                "如果无法生成贴切标题，默认使用问题原文 + 数据集名称，而不是通用报告标题。",
                "对空标题增加校验和告警。"
            ]
        },
        "ecommerce_special_case": {
            "cause": [
                "数据集 62 的字段和数据结构与商用/消费者不同（承接人、细分业务、毛利率等），但 SQL 生成器仍按统一模板处理。",
                "『vs / 对比』类问题需要双指标，但当前模板只支持单指标。",
                "『负责人是谁』属于明细查询，不是聚合，被当作业绩查询处理。"
            ],
            "solution": [
                "为数据集 62 单独配置字段映射和指标口径（毛利率、目标营收、年度开单、承接人）。",
                "对比类问题支持双指标 SQL：同时 SELECT 指标 A 和指标 B，用条形图/表格对比展示。",
                "『负责人/承接人是谁』走明细查询分支，直接返回负责人字段，不做聚合。"
            ]
        },
        "empty_unknown": {
            "cause": [
                "需要逐条看 SQL 才能确认，可能是上述某一类或数据本身缺失。"
            ],
            "solution": [
                "对空结果统一增加诊断信息：SQL 实际过滤条件、命中层级、建议动作。",
                "在测试报告里附加每条空结果的 SQL 执行计划/采样数据，便于后续归类。"
            ]
        },
        "title_heuristic": {
            "cause": [
                "测试脚本的标题匹配启发式过于严格，把正常扩展标题误判为不相关。"
            ],
            "solution": [
                "优化测试脚本标题评分逻辑，允许同义词和句式扩展。",
                "这类标记不代表系统缺陷，只需人工复核。"
            ]
        },
        "other": {
            "cause": ["需逐条复核。"],
            "solution": ["人工查看具体 SQL 和返回结果。"]
        }
    }

    for code, items in sorted_groups:
        info = solutions.get(code, {"cause": ["待补充"], "solution": ["待补充"]})
        lines.append(f"### {code}（{items[0]['reason_desc']}）")
        lines.append("")
        lines.append("**涉及问题：**")
        for i in items[:15]:
            lines.append(f"- `{i['id']}` {i['question']}（数据集 {i['target']}，实际 {i['dataset']}）")
        if len(items) > 15:
            lines.append(f"- ... 等共 {len(items)} 题")
        lines.append("")
        lines.append("**根因：**")
        for c in info["cause"]:
            lines.append(f"- {c}")
        lines.append("")
        lines.append("**解决方案：**")
        for s in info["solution"]:
            lines.append(f"- {s}")
        lines.append("")

    lines.append("## 三、总体实施建议")
    lines.append("")
    lines.append("1. **先修路由/确认策略**：统一 `LEVEL_LABELS`，避免通用层级词直接锁定数据集；对只含层级词的问法强制确认。")
    lines.append("2. **再修 SQL 生成**：在排名、筛选、下钻分支里过滤掉纯层级标签，避免 `节点名称 IN ('代表处')` 这类错误过滤。")
    lines.append("3. **补齐指标口径**：把数据集 62 的毛利率、利润、目标营收完成率等加入数据字典和 SQL 模板。")
    lines.append("4. **增强边界兜底**：不存在节点、不支持时间、非法数量等给出结构化提示，而不是返回 0 行。")
    lines.append("5. **优化报告标题**：Agent4 按意图选择标题模板，减少模板化扩展。")
    lines.append("6. **跨数据集对比**：作为独立功能后续实现，当前可先拦截并提示用户分两次提问。")
    lines.append("7. **测试脚本优化**：标题匹配启发式放宽，减少误报。")
    lines.append("")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"分析完成，输出：{OUT_PATH}")


if __name__ == "__main__":
    main()
