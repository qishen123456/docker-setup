#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""baseline_survey.py — SmartAsk 基线拓展全量实测（纯测试，不改代码）

依据 config/confirmed_behaviors_baseline.md 的已确认行为，用真实节点名
（来自 config/dataset_node_index.json 的实测提取）拓展出 200+ 道问数题，
在容器内直调 svc.ask / confirm_by_boss 实测，输出每题的答案与判定。

用法（容器内）：
    python /app/backend/baseline_survey.py --smoke            # 冒烟 5 题
    python /app/backend/baseline_survey.py --batch 0 --of 5 \
        --out /app/backend/probe_out/batch_0.json             # 分片跑

结果 JSON：每题 {id, cat, q, verdict(PASS/FAIL/INFO/EXC), reasons[],
answer:{route, intent, row_count, rows 样本, kpis, sql_keys, analysis 摘要,
confirm_options, 每轮/每分支明细}}。
"""
import sys
import io
import os
import re
import json
import time
import argparse
import contextlib
import datetime

sys.path.insert(0, "/app/backend")

USER = {"role": "super_admin", "id": 99999, "username": "survey",
        "organization_codes": ["*"], "organization_node_ids": ["*"]}

# ============================================================ 真实节点（2026-08-19 从 dataset_node_index.json 提取）
DS3_BRANCHES = ["东部分公司", "南部分公司", "北部分公司", "西部分公司"]
DS3_DEPTS = ["公共办公业务部", "工业医疗业务部", "餐饮业务部"]
DS3_OFFICES = ["山东代表处", "河南代表处", "上海代表处", "北京代表处",
               "湖南代表处", "陕西代表处", "江苏代表处", "四川代表处"]
DS3_REPS = ["靳锋", "赵标", "李文强", "迟昊", "丁杰"]
DS2_BRANCHES = ["豫晋分公司", "河北分公司", "山东分公司", "江浙沪分公司",
                "湖南分公司", "西北分公司", "云贵渝分公司", "京津分公司"]
DS2_CITIES = ["万州城市公司", "昆明城市公司", "重庆城市公司", "北京城市公司",
              "济南城市公司", "淄博城市公司", "成都城市公司", "上海城市公司",
              "长沙城市公司", "广州城市公司"]
DS62_DEPTS = ["国内业务部", "直营零售部", "跨境业务部"]
DS62_CJR = ["黄超", "李金良", "胡根", "曾庆凌"]  # 避开刘志伟（ds3/ds62 都有）


# ============================================================ 题单生成
CASES = []


def add(cat, q, expect=None, src="", turns=None):
    cid = "%s%02d" % (cat, sum(1 for c in CASES if c["cat"] == cat) + 1)
    case = {"id": cid, "cat": cat, "q": q, "src": src, "expect": expect or {}}
    if turns:
        case["turns"] = turns
    CASES.append(case)


# ---- A 单对象下钻带一层下级（§1.1）
for n in DS3_BRANCHES:
    for t in ("%s的业绩怎么样了", "%s业绩如何", "看下%s的业绩"):
        add("A", t % n, {"no_confirm": True, "ds_eq": [3], "contains_node": n,
                         "has_child": n, "rows_gte": 2}, "§1.1")
for n in DS3_DEPTS:
    for t in ("%s的业绩怎么样了", "%s业绩如何"):
        add("A", t % n, {"no_confirm": True, "ds_eq": [3], "contains_node": n,
                         "has_child": n, "rows_gte": 2}, "§1.1")
for n in DS3_OFFICES:
    for t in ("%s的业绩怎么样了", "%s表现怎么样", "看下%s的业绩"):
        add("A", t % n, {"no_confirm": True, "ds_eq": [3], "contains_node": n,
                         "rows_gte": 1}, "§1.1")
for n in DS2_BRANCHES:
    for t in ("%s的业绩怎么样了", "%s业绩如何"):
        add("A", t % n, {"no_confirm": True, "ds_eq": [2], "contains_node": n,
                         "has_child": n, "rows_gte": 2}, "§1.1")
for n in DS2_CITIES:  # 城市公司是 ds2 末端节点：只返回本人
    for t in ("%s的业绩怎么样了", "%s业绩咋样"):
        add("A", t % n, {"no_confirm": True, "ds_eq": [2], "contains_node": n,
                         "rows_lte": 2}, "§1.1末端")
for n in DS62_DEPTS:
    add("A", "%s的业绩怎么样了" % n,
        {"no_confirm": True, "ds_eq": [62], "contains_node": n, "rows_gte": 1}, "§1.1")

# ---- B 末端个人只返回本人（§1.1末端例外）
for n in DS3_REPS:
    for t in ("商用事业部业务代表%s的业绩", "%s的业绩怎么样"):
        add("B", t % n, {"no_confirm": True, "ds_eq": [3], "contains_node": n,
                         "rows_lte": 3}, "§1.1末端")
for n in DS62_CJR:
    for t in ("电商承接人%s的业绩", "%s的业绩怎么样"):
        add("B", t % n, {"no_confirm": True, "ds_eq": [62], "contains_node": n,
                         "rows_lte": 3}, "§1.1末端")

# ---- C 双对象对比不误走下钻（§1.2）
for a, b, ds in (("东部分公司", "南部分公司", 3), ("北部分公司", "西部分公司", 3),
                 ("公共办公业务部", "工业医疗业务部", 3),
                 ("山东代表处", "河南代表处", 3), ("豫晋分公司", "河北分公司", 2)):
    for t in ("%s和%s的业绩对比", "%s与%s对比怎么样"):
        add("C", t % (a, b), {"no_confirm": True, "ds_eq": [ds],
                              "contains_nodes": [a, b], "rows_gte": 2}, "§1.2")

# ---- D 跨数据集对比（§1.2.1/§1.2.2）
for q in ("消费者和商用的对比", "商用和消费者的业绩对比", "商用和电商的对比",
          "电商和商用的业绩对比", "消费者和电商的对比"):
    add("D", q, {"no_confirm": True, "route_intent": "comparison",
                 "ds_count_gte": 2, "all_ds_rows_gte": 1}, "§1.2.1/1.2.2")

# ---- E 具体节点+目标子层级走 drilldown（§1.3）
for a, child, ds in (("江浙沪分公司", "城市分公司", 2), ("山东分公司", "城市分公司", 2),
                     ("豫晋分公司", "城市分公司", 2), ("东部分公司", "代表处", 3),
                     ("南部分公司", "业务代表", 3), ("国内业务部", "承接人", 62)):
    for t in ("%s的%s", "%s下面%s的业绩"):
        add("E", t % (a, child), {"no_confirm": True, "ds_eq": [ds],
                                  "levels_include": [child], "rows_gte": 1}, "§1.3")

# ---- F 电商根节点默认展示直接下级（§1.4）
for q in ("电商事业部的业绩", "电商事业部业绩如何", "看下电商事业部的业绩"):
    add("F", q, {"no_confirm": True, "ds_eq": [62],
                 "contains_nodes": ["国内业务部", "直营零售部", "跨境业务部"],
                 "rows_between": [2, 5]}, "§1.4")

# ---- G 层级 Overview 走 ranking top_n=0（§2.1/§2.4）
for q in ("城市分公司的业绩", "城市分公司的业绩咋样", "各城市分公司的业绩"):
    add("G", q, {"no_confirm": True, "ds_eq": [2], "intent": "ranking",
                 "top_n": 0, "rows_between": [60, 75]}, "§2.4")
for q in ("各代表处的业绩", "代表处的业绩咋样", "各代表处业绩如何"):
    add("G", q, {"no_confirm": True, "ds_eq": [3], "intent": "ranking",
                 "top_n": 0, "rows_between": [20, 30]}, "§2.4")
for q in ("业务代表的业绩", "各业务代表的业绩情况"):
    add("G", q, {"no_confirm": True, "ds_eq": [3], "intent": "ranking",
                 "top_n": 0, "rows_gte": 70}, "§2.4")
# 分公司/业务部为跨数据集通用层级 → 必须弹确认并走完每个分支（§3.3）
for q, walks in (
    ("各分公司的业绩", [([2], {"rows_between": [10, 16], "intent": "ranking"}),
                        ([3], {"rows_eq": 4, "intent": "ranking"})]),
    ("业务部的业绩情况", [([3], {"rows_gte": 2}), ([62], {"rows_gte": 2})]),
):
    add("G", q, {"must_confirm": True,
                 "confirm_walk": [{"ds": d, "expect": e} for d, e in walks]}, "§2.4/§3.3")

# ---- H TopN 前N/后N/垫底N（§2.5/§2.6）
add("H", "看下前三的城市分公司", {"no_confirm": True, "ds_eq": [2], "intent": "ranking",
                                "top_n": 3, "rows_eq": 3, "desc": True}, "§2.5")
add("H", "前5的业务代表", {"no_confirm": True, "ds_eq": [3], "intent": "ranking",
                          "top_n": 5, "rows_eq": 5, "desc": True}, "§2.5")
add("H", "前3的代表处", {"no_confirm": True, "ds_eq": [3], "intent": "ranking",
                        "top_n": 3, "rows_eq": 3, "desc": True}, "§2.5")
add("H", "消费者事业部垫底的5个城市分公司",
    {"no_confirm": True, "ds_eq": [2], "intent": "ranking", "top_n": 5,
     "rows_eq": 5, "asc": True}, "§2.6")
add("H", "消费者城市分公司排名前10", {"no_confirm": True, "ds_eq": [2], "intent": "ranking",
                                    "top_n": 10, "rows_eq": 10, "desc": True}, "§2.6")
add("H", "消费者事业部，业绩排名垫底的 3 家分公司",
    {"no_confirm": True, "ds_eq": [2], "intent": "ranking", "top_n": 3,
     "rows_eq": 3, "asc": True}, "§2.6")
add("H", "前2的业务部业绩", {"probe": True}, "§2.5-通用层级观察")  # 分公司/业务部歧义，观察路由
add("H", "业绩前3的承接人", {"no_confirm": True, "ds_eq": [62], "intent": "ranking",
                            "top_n": 3, "rows_eq": 3}, "§2.3/2.5")
add("H", "后3的业务代表", {"no_confirm": True, "ds_eq": [3], "intent": "ranking",
                          "top_n": 3, "rows_eq": 3, "asc": True}, "§2.5/2.6")
add("H", "倒数前二的代表处", {"probe": True}, "§2.6-口语数量观察")
add("H", "排名前5的城市分公司", {"no_confirm": True, "ds_eq": [2], "intent": "ranking",
                                "top_n": 5, "rows_eq": 5}, "§2.5")
add("H", "商用事业部垫底的2个代表处", {"no_confirm": True, "ds_eq": [3], "intent": "ranking",
                                      "top_n": 2, "rows_eq": 2, "asc": True}, "§2.6")

# ---- I 最X 无数量默认 top_n=1（§2.7）
add("I", "业绩最差的业务代表", {"no_confirm": True, "ds_eq": [3], "intent": "ranking",
                              "top_n": 1, "rows_gte": 1}, "§2.7")
add("I", "达成率最高的代表处", {"no_confirm": True, "ds_eq": [3], "intent": "ranking",
                              "top_n": 1, "rows_gte": 1}, "§2.7")
add("I", "业绩最好的承接人", {"no_confirm": True, "ds_eq": [62], "intent": "ranking",
                            "top_n": 1, "rows_gte": 1}, "§2.7")
add("I", "业绩最差的城市分公司", {"no_confirm": True, "ds_eq": [2], "intent": "ranking",
                                "top_n": 1, "rows_gte": 1}, "§2.7")
add("I", "开单金额最高的业务部", {"probe": True}, "§2.7-通用层级观察")
# 通用层级"最X" → 弹确认并走完（已知 bug#14/#17/#18 区域）
add("I", "业绩最好的分公司",
    {"must_confirm": True,
     "confirm_walk": [
         ([2], {"intent": "ranking", "top_n": 1, "rows_gte": 1,
                "row0_node": "豫晋分公司"}),
         ([3], {"intent": "ranking", "top_n": 1, "rows_gte": 1})]}, "§2.7/§3.3")
add("I", "垫底的分公司",
    {"must_confirm": True,
     "confirm_walk": [([2], {"intent": "ranking", "top_n": 1, "rows_gte": 1}),
                      ([3], {"intent": "ranking", "top_n": 1, "rows_gte": 1})]}, "§2.7/§3.3")
add("I", "业绩最差的分公司",
    {"must_confirm": True,
     "confirm_walk": [([2], {"intent": "ranking", "top_n": 1, "rows_gte": 1}),
                      ([3], {"intent": "ranking", "top_n": 1, "rows_gte": 1})]}, "§2.7/§3.3")

# ---- J 电商承接人排名（§2.3）
add("J", "看下前三的业务承接人", {"no_confirm": True, "ds_eq": [62], "intent": "ranking",
                                 "top_n": 3, "rows_eq": 3, "levels_include": ["承接人"]}, "§2.3")
add("J", "电商事业部业务承接人业绩排名", {"no_confirm": True, "ds_eq": [62],
                                        "intent": "ranking", "top_n": 0,
                                        "levels_include": ["承接人"]}, "§2.3")
add("J", "前5的承接人", {"no_confirm": True, "ds_eq": [62], "intent": "ranking",
                        "top_n": 5, "rows_eq": 5, "levels_include": ["承接人"]}, "§2.3")
add("J", "承接人排名", {"no_confirm": True, "ds_eq": [62], "intent": "ranking",
                       "levels_include": ["承接人"]}, "§2.3")
add("J", "垫底的2个承接人", {"no_confirm": True, "ds_eq": [62], "intent": "ranking",
                            "top_n": 2, "rows_eq": 2, "asc": True}, "§2.3/2.6")
add("J", "业绩最好的业务承接人", {"no_confirm": True, "ds_eq": [62], "intent": "ranking",
                                "top_n": 1, "levels_include": ["承接人"]}, "§2.3/2.7")

# ---- K 通用层级歧义确认走完（§3.1/§3.3）
add("K", "各分公司业绩排名",
    {"must_confirm": True,
     "confirm_walk": [
         ([2], {"intent": "ranking", "rows_between": [10, 16]}),
         ([3], {"intent": "ranking", "rows_eq": 4})]}, "§3.3")
add("K", "垫底的三个分公司",
    {"must_confirm": True,
     "confirm_walk": [
         ([2], {"intent": "ranking", "top_n": 3, "rows_eq": 3, "asc": True}),
         ([3], {"intent": "ranking", "top_n": 3, "rows_eq": 3, "asc": True})]}, "§2.6/§3.3")
add("K", "前3的分公司",
    {"must_confirm": True,
     "confirm_walk": [
         ([2], {"intent": "ranking", "top_n": 3, "rows_eq": 3, "desc": True}),
         ([3], {"intent": "ranking", "top_n": 3, "rows_eq": 3, "desc": True})]}, "§3.3")
add("K", "分公司的业绩排名",
    {"must_confirm": True,
     "confirm_walk": [([2], {"intent": "ranking", "rows_gte": 10}),
                      ([3], {"intent": "ranking", "rows_eq": 4})]}, "§3.3")

# ---- L 裸节点（§3.4-3.7）
add("L", "上海那边业绩如何了",
    {"must_confirm": True, "confirm_nodes": ["上海城市公司", "上海代表处"],
     "confirm_walk": [([2], {"contains_node": "上海城市公司"}),
                      ([3], {"contains_node": "上海代表处"})]}, "§3.4/§3.5")
add("L", "上海的业绩如何",
    {"must_confirm": True, "confirm_nodes": ["上海城市公司", "上海代表处"],
     "confirm_walk": [([2], {"contains_node": "上海城市公司"}),
                      ([3], {"contains_node": "上海代表处"})]}, "§3.5/§3.7")
add("L", "东部那个分公司怎么样",
    {"no_confirm": True, "ds_eq": [3], "contains_node": "东部分公司"}, "§3.6")
add("L", "河北业绩怎么样",
    {"no_confirm": True, "ds_eq": [2], "contains_node": "河北分公司"}, "§3.6")
add("L", "看下上海代表处的业绩咋样了",
    {"no_confirm": True, "ds_eq": [3], "contains_node": "上海代表处"}, "§3.6")
add("L", "继续看河南代表处的业绩如何了",
    {"no_confirm": True, "ds_eq": [3], "contains_node": "河南代表处"}, "§3.6")
add("L", "山东的业绩",
    {"must_confirm": True, "confirm_nodes": ["山东分公司", "山东代表处"],
     "confirm_walk": [([2], {"contains_node": "山东分公司"}),
                      ([3], {"contains_node": "山东代表处"})]}, "§3.5")
add("L", "北京的业绩",
    {"must_confirm": True, "confirm_nodes": ["北京城市公司", "北京代表处"],
     "confirm_walk": [([2], {"contains_node": "北京城市公司"}),
                      ([3], {"contains_node": "北京代表处"})]}, "§3.5")
add("L", "深圳的业绩怎么样",
    {"no_confirm": True, "ds_eq": [2], "contains_node": "深圳城市公司"}, "§3.6")
add("L", "湖南业绩如何", {"probe": True}, "§3.4-多命中观察")  # ds2 湖南分公司 + ds3 湖南代表处
add("L", "重庆的业绩", {"probe": True}, "§3.4-多命中观察")  # ds2 重庆城市公司 + ds3 重庆代表处
add("L", "天津业绩咋样", {"probe": True}, "§3.4-观察")  # ds2 天津城市公司唯一命中？
add("L", "成都那边的业绩", {"probe": True}, "§3.4-观察")  # ds2 成都城市公司唯一命中？

# ---- M 阈值筛选
add("M", "低于10%的业务代表", {"no_confirm": True, "ds_eq": [3],
                              "intent_in": ["filter", "ranking"], "rows_gte": 0}, "filter")
add("M", "达成率超过50%的代表处", {"no_confirm": True, "ds_eq": [3],
                                 "intent_in": ["filter", "ranking"], "rows_gte": 0}, "filter")
add("M", "开单金额大于5000万的代表处", {"no_confirm": True, "ds_eq": [3],
                                     "intent_in": ["filter", "ranking"], "rows_gte": 0}, "filter")
add("M", "达成率低于30%的城市分公司", {"no_confirm": True, "ds_eq": [2],
                                   "intent_in": ["filter", "ranking"], "rows_gte": 0}, "filter")
add("M", "开单金额超过一个亿的代表处", {"no_confirm": True, "ds_eq": [3],
                                    "intent_in": ["filter", "ranking"], "rows_gte": 0}, "filter")
add("M", "达成率低于20%的承接人", {"no_confirm": True, "ds_eq": [62],
                                "intent_in": ["filter", "ranking"], "rows_gte": 0}, "filter")
add("M", "任务金额超过5000万的分公司", {"probe": True}, "filter-通用层级观察")
add("M", "开单金额大于1000万的城市分公司", {"no_confirm": True, "ds_eq": [2],
                                       "intent_in": ["filter", "ranking"], "rows_gte": 0}, "filter")
add("M", "达成率超过60%的城市分公司", {"no_confirm": True, "ds_eq": [2],
                                   "intent_in": ["filter", "ranking"], "rows_gte": 0}, "filter")
add("M", "开单金额低于100万的业务代表", {"no_confirm": True, "ds_eq": [3],
                                     "intent_in": ["filter", "ranking"], "rows_gte": 0}, "filter")

# ---- N 多轮追问
add("N", "(多轮)阈值追问", src="多轮-filter继承",
    turns=[
        {"q": "开单金额超过一个亿的代表处",
         "expect": {"no_confirm": True, "ds_eq": [3], "rows_gte": 0}},
        {"q": "大于5000万的呢",
         "expect": {"no_confirm": True, "ds_eq": [3], "rows_gte": 0}},
    ])
add("N", "(多轮)跨数据集切换", src="多轮-切换",
    turns=[
        {"q": "城市分公司的业绩", "expect": {"no_confirm": True, "ds_eq": [2]}},
        {"q": "低于10%的业务代表", "expect": {"probe": True}},  # 切换商用，路由观察
    ])
add("N", "(多轮)跨数据集实体冲突1", src="§8.3",
    turns=[
        {"q": "商用事业部业绩如何", "expect": {"no_confirm": True, "ds_eq": [3]}},
        {"q": "东部分公司业绩", "expect": {"no_confirm": True, "ds_eq": [3],
                                         "contains_node": "东部分公司"}},
    ])
add("N", "(多轮)跨数据集实体冲突2", src="§8.3",
    turns=[
        {"q": "消费者事业部业绩", "expect": {"no_confirm": True, "ds_eq": [2]}},
        {"q": "东部分公司业绩", "expect": {"no_confirm": True, "ds_eq": [3],
                                         "contains_node": "东部分公司"}},
    ])
add("N", "(多轮)确认后同集追问不重复确认", src="§3.3",
    turns=[
        {"q": "前3的分公司", "expect": {"must_confirm": True},
         "select_ds": [2],
         "confirm_expect": {"intent": "ranking", "top_n": 3, "rows_eq": 3}},
        {"q": "看下河北分公司的业绩",
         "expect": {"no_confirm": True, "ds_eq": [2], "contains_node": "河北分公司"}},
    ])
add("N", "(多轮)确认后收敛真实节点", src="§3.7",
    turns=[
        {"q": "上海的业绩如何", "expect": {"must_confirm": True},
         "select_ds": [2],
         "confirm_expect": {"contains_node": "上海城市公司"}},
        {"q": "它的任务金额是多少",
         "expect": {"probe": True}},
    ])

# ---- O 空态/异常
add("O", "火星分公司的业绩", {"empty_or_notfound": True}, "空态")
add("O", "张三丰的业绩", {"empty_or_notfound": True}, "空态")
add("O", "南极代表处的业绩怎么样", {"empty_or_notfound": True}, "空态")
add("O", "去年的业绩", {"probe": True}, "时间词观察")
add("O", "2020年的销售额", {"probe": True}, "时间词观察")
add("O", "今年上半年的业绩", {"probe": True}, "时间词观察")


# ============================================================ 执行 harness
def _ask(svc, q, sid, user):
    with contextlib.redirect_stdout(io.StringIO()):
        return svc.ask(question=q, session_id=sid, conversation_history=None,
                       current_user=user)


def _confirm(svc, r, sel_ds, user):
    opts = r.get("confirmation_options") or []
    opt = None
    for o in opts:
        if set(o.get("dataset_ids") or []) == set(sel_ds):
            opt = o
            break
    if opt is None:
        return None, None
    with contextlib.redirect_stdout(io.StringIO()):
        r2 = svc.confirm_by_boss(
            session_id=r.get("session_id"),
            selected_option=opt.get("label") or "",
            selected_dataset_ids=sel_ds,
            option_id=opt.get("id") or "",
            current_user=user,
        )
    return opt, r2


def _num(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"-?\d+(?:\.\d+)?", str(v).replace(",", "").replace("%", ""))
    return float(m.group(0)) if m else None


# ============================================================ 断言评估
def eval_expect(r, expect, reasons):
    """把不符合项追加进 reasons。r 为 ask 或 confirm 的结果 dict。"""
    if expect.get("probe"):
        return
    if not isinstance(r, dict):
        reasons.append("结果不是 dict: %r" % (r,))
        return
    if r.get("error"):
        reasons.append("error: %s" % str(r["error"])[:120])
        return
    rc = bool(r.get("requires_confirmation"))
    if expect.get("no_confirm") and rc:
        reasons.append("不应弹确认但弹了确认")
    if expect.get("must_confirm") and not rc:
        reasons.append("应弹确认但没弹")
    if rc and expect.get("confirm_nodes"):
        labels = " ".join(str(o.get("label") or "")
                          for o in r.get("confirmation_options") or [])
        for n in expect["confirm_nodes"]:
            if n not in labels:
                reasons.append("确认选项缺真实节点 %s（选项: %s）" % (n, labels[:80]))
    if rc:
        return  # 弹确认时结果断言在 confirm_walk 分支里做

    drs = r.get("dataset_results") or []
    dr = drs[0] if drs else {}
    qi = dr.get("query_intent") or {}
    rows = dr.get("rows") or []
    route = r.get("route") or {}

    if "ds_eq" in expect and route.get("dataset_ids") != expect["ds_eq"]:
        reasons.append("route.dataset_ids=%s 期望 %s"
                       % (route.get("dataset_ids"), expect["ds_eq"]))
    if "route_intent" in expect and route.get("intent") != expect["route_intent"]:
        reasons.append("route.intent=%s 期望 %s" % (route.get("intent"), expect["route_intent"]))
    if "intent" in expect and qi.get("intent") != expect["intent"]:
        reasons.append("intent=%s 期望 %s" % (qi.get("intent"), expect["intent"]))
    if "intent_in" in expect and qi.get("intent") not in expect["intent_in"]:
        reasons.append("intent=%s 不在 %s" % (qi.get("intent"), expect["intent_in"]))
    if "top_n" in expect and qi.get("top_n") != expect["top_n"]:
        reasons.append("top_n=%s 期望 %s" % (qi.get("top_n"), expect["top_n"]))
    n = len(rows)
    if "rows_eq" in expect and n != expect["rows_eq"]:
        reasons.append("row_count=%d 期望=%d" % (n, expect["rows_eq"]))
    if "rows_gte" in expect and n < expect["rows_gte"]:
        reasons.append("row_count=%d 期望>=%d" % (n, expect["rows_gte"]))
    if "rows_lte" in expect and n > expect["rows_lte"]:
        reasons.append("row_count=%d 期望<=%d" % (n, expect["rows_lte"]))
    if "rows_between" in expect and not (expect["rows_between"][0] <= n <= expect["rows_between"][1]):
        reasons.append("row_count=%d 期望在 %s" % (n, expect["rows_between"]))
    if "ds_count_gte" in expect and len(drs) < expect["ds_count_gte"]:
        reasons.append("dataset_results 数=%d 期望>=%d" % (len(drs), expect["ds_count_gte"]))
    if "all_ds_rows_gte" in expect:
        for d in drs:
            if len(d.get("rows") or []) < expect["all_ds_rows_gte"]:
                reasons.append("ds=%s 返回 %d 行（期望>=%d）"
                               % (d.get("dataset_id"), len(d.get("rows") or []),
                                  expect["all_ds_rows_gte"]))
    names = [str(row.get("节点名称") or "") for row in rows if isinstance(row, dict)]
    if "contains_node" in expect:
        if not any(expect["contains_node"] in x for x in names):
            reasons.append("结果缺节点 %s（实到: %s）" % (expect["contains_node"], names[:5]))
    for node in expect.get("contains_nodes") or []:
        if not any(node in x for x in names):
            reasons.append("结果缺节点 %s（实到: %s）" % (node, names[:5]))
    if "has_child" in expect:
        parents = [str(row.get("上级名称") or "") for row in rows if isinstance(row, dict)]
        if not any(expect["has_child"] in p for p in parents):
            reasons.append("没有 %s 的下级行（上级列: %s）" % (expect["has_child"], parents[:5]))
    levels = set(str(row.get("层级") or "") for row in rows if isinstance(row, dict)) - {""}
    if "levels_include" in expect:
        for lv in expect["levels_include"]:
            if lv not in levels:
                reasons.append("层级缺 %s（实到: %s）" % (lv, sorted(levels)))
    if "levels_eq" in expect and levels != set(expect["levels_eq"]):
        reasons.append("层级=%s 期望 %s" % (sorted(levels), expect["levels_eq"]))
    if "row0_node" in expect:
        first = names[0] if names else ""
        if first != expect["row0_node"]:
            reasons.append("首行=%s 期望 %s" % (first, expect["row0_node"]))
    if "metric_col_gt0" in expect and rows:
        v = _num(rows[0].get(expect["metric_col_gt0"]))
        if not v or v <= 0:
            reasons.append("首行 %s=%s 期望>0" % (expect["metric_col_gt0"], rows[0].get(expect["metric_col_gt0"])))
    if expect.get("kpi_nonempty"):
        kpis = (dr.get("report_spec") or {}).get("kpis") or []
        if not any(_num(k.get("value") if isinstance(k, dict) else None) is not None for k in kpis):
            reasons.append("report_spec.kpis 空或无数值")
    sql = str(dr.get("sql") or "")
    if "sql_has" in expect and expect["sql_has"] not in sql:
        reasons.append("SQL 缺 %s" % expect["sql_has"])
    if "sql_not" in expect and expect["sql_not"] in sql:
        reasons.append("SQL 不应含 %s" % expect["sql_not"])
    if ("asc" in expect or "desc" in expect) and len(rows) >= 2:
        rates = [_num(row.get("达成率")) for row in rows]
        rates = [x for x in rates if x is not None]
        if len(rates) >= 2:
            if expect.get("asc") and rates[0] > rates[-1]:
                reasons.append("方向应为升序(垫底在前)，实到首=%s 尾=%s" % (rates[0], rates[-1]))
            if expect.get("desc") and rates[0] < rates[-1]:
                reasons.append("方向应为降序(最好在前)，实到首=%s 尾=%s" % (rates[0], rates[-1]))
    if expect.get("empty_or_notfound"):
        analyses = "".join(str(d.get("analysis") or "") for d in drs)
        if rows or "未找到" not in analyses:
            reasons.append("期望空态/未找到，实到 %d 行" % n)


# ============================================================ 答案采集
def _strip_think(text):
    return re.sub(r"<think>.*?(</think>|$)", "[think]", str(text or ""), flags=re.S).strip()


def _sql_keys(sql):
    keys = []
    for line in str(sql or "").splitlines():
        s = line.strip()
        if any(k in s.upper() for k in ("WHERE", "ORDER BY", "LIMIT", "层级")):
            keys.append(s[:100])
    return keys[:6]


def capture(r, elapsed):
    if not isinstance(r, dict):
        return {"raw": repr(r)[:200], "elapsed_s": elapsed}
    out = {"elapsed_s": elapsed}
    if r.get("error"):
        out["error"] = str(r["error"])[:200]
        return out
    out["requires_confirmation"] = bool(r.get("requires_confirmation"))
    if out["requires_confirmation"]:
        out["confirm_options"] = [
            {"label": o.get("label"), "dataset_ids": o.get("dataset_ids")}
            for o in r.get("confirmation_options") or []]
    route = r.get("route") or {}
    out["route"] = {"intent": route.get("intent"), "dataset_ids": route.get("dataset_ids")}
    ds_out = []
    for dr in r.get("dataset_results") or []:
        qi = dr.get("query_intent") or {}
        rows = dr.get("rows") or []
        head = []
        for row in rows[:6]:
            if not isinstance(row, dict):
                continue
            head.append({k: row.get(k) for k in
                         ("节点名称", "层级", "上级名称", "总任务金额", "任务金额",
                          "年度开单金额", "开单金额", "达成率", "剩余任务金额")
                         if row.get(k) is not None})
        kpis = []
        for k in ((dr.get("report_spec") or {}).get("kpis") or [])[:8]:
            if isinstance(k, dict):
                kpis.append({"label": k.get("label") or k.get("name") or k.get("key"),
                             "value": k.get("value")})
        ds_out.append({
            "dataset_id": dr.get("dataset_id"),
            "intent": qi.get("intent"), "top_n": qi.get("top_n"),
            "target_level": qi.get("target_level"),
            "row_count": len(rows),
            "levels": sorted(set(str(x.get("层级") or "") for x in rows
                                 if isinstance(x, dict)) - {""}),
            "head_rows": head,
            "kpis": kpis,
            "sql_keys": _sql_keys(dr.get("sql")),
            "analysis": _strip_think(dr.get("analysis"))[:240],
        })
    out["datasets"] = ds_out
    return out


# ============================================================ 用例执行
def run_case(case, svc):
    cid, q = case["id"], case["q"]
    sid = "survey-" + cid
    entry = {"id": cid, "cat": case["cat"], "q": q, "src": case.get("src", ""),
             "verdict": "PASS", "reasons": [], "turns": []}

    def run_one(question, expect, tag, session, select_ds=None, confirm_expect=None):
        t0 = time.time()
        try:
            r = _ask(svc, question, session, USER)
        except Exception as e:
            entry["turns"].append({"tag": tag, "q": question, "verdict": "EXC",
                                   "reasons": ["ask 异常: %r" % e], "answer": {}})
            entry["verdict"] = "EXC"
            return None
        el = round(time.time() - t0, 1)
        reasons = []
        eval_expect(r, expect, reasons)
        ans = capture(r, el)
        verdict = "PASS"
        if expect.get("probe"):
            verdict = "INFO"
        elif reasons:
            verdict = "FAIL"
        entry["turns"].append({"tag": tag, "q": question, "verdict": verdict,
                               "reasons": reasons, "answer": ans})
        if verdict == "FAIL":
            entry["verdict"] = "FAIL"
            entry["reasons"].extend("%s: %s" % (tag, x) for x in reasons)
        elif verdict == "EXC":
            entry["verdict"] = "EXC"
        elif verdict == "INFO" and entry["verdict"] == "PASS":
            entry["verdict"] = "INFO"
        # 多轮确认：选中数据集走完
        if select_ds and isinstance(r, dict) and r.get("requires_confirmation"):
            t1 = time.time()
            try:
                opt, r2 = _confirm(svc, r, select_ds, USER)
            except Exception as e:
                entry["turns"].append({"tag": tag + "-confirm", "q": question,
                                       "verdict": "EXC",
                                       "reasons": ["confirm 异常: %r" % e], "answer": {}})
                entry["verdict"] = "EXC"
                return r
            if r2 is None:
                opts = [o.get("dataset_ids") for o in r.get("confirmation_options") or []]
                entry["turns"].append({"tag": tag + "-confirm", "q": question,
                                       "verdict": "FAIL",
                                       "reasons": ["找不到选项 ds=%s（实到 %s）" % (select_ds, opts)],
                                       "answer": {}})
                entry["verdict"] = "FAIL"
                return r
            creasons = []
            eval_expect(r2, confirm_expect or {}, creasons)
            cans = capture(r2, round(time.time() - t1, 1))
            cverdict = "PASS" if not creasons else "FAIL"
            if (confirm_expect or {}).get("probe"):
                cverdict = "INFO"
            entry["turns"].append({"tag": tag + "-confirm选%s" % select_ds, "q": question,
                                   "verdict": cverdict, "reasons": creasons, "answer": cans})
            if cverdict == "FAIL":
                entry["verdict"] = "FAIL"
                entry["reasons"].extend("%s-confirm: %s" % (tag, x) for x in creasons)
        return r

    # 多轮
    if case.get("turns"):
        for i, turn in enumerate(case["turns"]):
            run_one(turn["q"], turn.get("expect") or {}, "turn%d" % (i + 1), sid,
                    select_ds=turn.get("select_ds"),
                    confirm_expect=turn.get("confirm_expect"))
        return entry

    r = run_one(q, case["expect"], "ask", sid)

    # 确认走完：每个候选数据集分支
    walks = (case["expect"] or {}).get("confirm_walk") or []
    for i, w in enumerate(walks):
        if isinstance(w, (list, tuple)):  # 兼容元组写法 (ds, expect)
            w = {"ds": w[0], "expect": w[1]}
        t0 = time.time()
        try:
            r_ask = _ask(svc, q, sid + "-w%d" % i, USER)
        except Exception as e:
            entry["turns"].append({"tag": "walk%d-ask" % i, "q": q, "verdict": "EXC",
                                   "reasons": ["ask 异常: %r" % e], "answer": {}})
            entry["verdict"] = "EXC"
            continue
        if not isinstance(r_ask, dict) or not r_ask.get("requires_confirmation"):
            entry["turns"].append({"tag": "walk%d-ask" % i, "q": q, "verdict": "FAIL",
                                   "reasons": ["应弹确认但没弹"],
                                   "answer": capture(r_ask, round(time.time() - t0, 1))})
            entry["verdict"] = "FAIL"
            continue
        t1 = time.time()
        try:
            opt, r2 = _confirm(svc, r_ask, w["ds"], USER)
        except Exception as e:
            entry["turns"].append({"tag": "walk选%s" % w["ds"], "q": q, "verdict": "EXC",
                                   "reasons": ["confirm 异常: %r" % e], "answer": {}})
            entry["verdict"] = "EXC"
            continue
        if r2 is None:
            opts = [o.get("dataset_ids") for o in r_ask.get("confirmation_options") or []]
            entry["turns"].append({"tag": "walk选%s" % w["ds"], "q": q, "verdict": "FAIL",
                                   "reasons": ["找不到选项 ds=%s（实到 %s）" % (w["ds"], opts)],
                                   "answer": {}})
            entry["verdict"] = "FAIL"
            continue
        wreasons = []
        eval_expect(r2, w.get("expect") or {}, wreasons)
        wans = capture(r2, round(time.time() - t1, 1))
        wverdict = "PASS" if not wreasons else "FAIL"
        if (w.get("expect") or {}).get("probe"):
            wverdict = "INFO"
        entry["turns"].append({"tag": "walk选%s" % w["ds"], "q": q,
                               "verdict": wverdict, "reasons": wreasons, "answer": wans})
        if wverdict == "FAIL":
            entry["verdict"] = "FAIL"
            entry["reasons"].extend("选%s: %s" % (w["ds"], x) for x in wreasons)

    return entry


# ============================================================ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=0)
    ap.add_argument("--of", type=int, default=1)
    ap.add_argument("--out", default="")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--ids", default="", help="只跑这些 id（逗号分隔）")
    args = ap.parse_args()

    if args.list:
        print("总题数: %d" % len(CASES))
        from collections import Counter
        print(dict(Counter(c["cat"] for c in CASES)))
        return

    cases = CASES[:5] if args.smoke else [c for i, c in enumerate(CASES) if i % args.of == args.batch]
    if args.ids:
        wanted = set(args.ids.split(","))
        cases = [c for c in CASES if c["id"] in wanted]
    print("本批 %d 题（batch %d/%d）" % (len(cases), args.batch, args.of), flush=True)

    from four_agent_ask import four_agent_ask_service as svc

    results = []
    for i, case in enumerate(cases):
        t0 = time.time()
        try:
            entry = run_case(case, svc)
        except Exception as e:
            entry = {"id": case["id"], "cat": case["cat"], "q": case["q"],
                     "verdict": "EXC", "reasons": ["run_case 异常: %r" % e], "turns": []}
        results.append(entry)
        print("[%d/%d] %s %s -> %s (%.0fs) %s" % (
            i + 1, len(cases), entry["id"], entry["q"][:24], entry["verdict"],
            time.time() - t0, "; ".join(entry["reasons"][:2])[:100]), flush=True)

    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"batch": args.batch, "of": args.of,
                       "ts": datetime.datetime.now().isoformat(timespec="seconds"),
                       "cases": results}, f, ensure_ascii=False, indent=1)
        print("已写出 %s" % args.out, flush=True)

    from collections import Counter
    stat = Counter(e["verdict"] for e in results)
    print("本批合计: %s" % dict(stat), flush=True)


if __name__ == "__main__":
    main()
