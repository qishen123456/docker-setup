#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SmartAsk 问数准确率快速诊断工具

用法（容器内执行）：
    # 批量诊断（跑全部用例）
    docker exec smartask-backend python /app/scripts/tests/quick_accuracy_check.py

    # 单个问题诊断（显示每一步中间结果）
    docker exec smartask-backend python /app/scripts/tests/quick_accuracy_check.py "商用事业部丁杰的业绩"

    # 只跑某一类
    docker exec smartask-backend python /app/scripts/tests/quick_accuracy_check.py --category subject

输出：
    - 控制台实时表格（红绿标注每一步对错）
    - Markdown 报告：/app/config/diagnostics/accuracy_report_YYYYMMDD_HHMMSS.md
"""
import json
import os
import re
import sys
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
os.chdir(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from four_agent_ask import FourAgentAskService

FAKE_USER = {"id": 1, "username": "diag", "role": "super_admin", "source": "diag"}

# 懒初始化的 svc（_canonicalize_subject 用到 _node_index_matches）
_SVC_SINGLETON = None


def _get_svc():
    global _SVC_SINGLETON
    if _SVC_SINGLETON is None:
        _SVC_SINGLETON = FourAgentAskService()
    return _SVC_SINGLETON


def _canonicalize_subject(subject: str, svc=None) -> str:
    """用节点索引把口语化主体（如"东部那个分公司"）标准化为真实节点（如"东部分公司"）。"""
    if not subject or len(subject) > 20:
        return subject
    if svc is None:
        svc = _get_svc()
    matches = svc._node_index_matches(subject)
    if len(matches) == 1:
        return matches[0]["node_name"]
    if len(matches) >= 2:
        # 多命中：按 node_name 与 subject 的接近度挑最像的
        for m in matches:
            if m["node_name"] in subject or subject in m["node_name"]:
                return m["node_name"]
    return subject

# ─── 测试用例 ────────────────────────────────────────────────────────────────
# 每个用例：question + category + expect(dict) + note
# expect 可用字段：
#   subject: str          期望主体名
#   dataset_ids: [int]    期望路由到的数据集（包含即可）
#   intent: str           期望 intent 类型
#   target_level: str     期望目标层级
#   top_n: int|None       期望 top_n
#   sql_contains: [str]   SQL 中必须包含的关键词
#   requires_confirmation: bool  期望是否需要确认
#   no_error: bool        期望无报错
#   preferred: [int]      传入 preferred_dataset_ids 跳过路由确认

TEST_CASES = [
    # ── 主体提取（subject）──
    {"q": "丁杰的业绩", "cat": "subject", "note": "单人名",
     "expect": {"subject": "丁杰", "dataset_ids": [3], "no_error": True}},
    {"q": "三明的业绩", "cat": "subject", "note": "数字开头人名(节点索引=三明城市公司)",
     "expect": {"subject": "三明城市公司", "no_error": True}},
    {"q": "迟昊看下这个人的业绩", "cat": "subject", "note": "口语前缀+指代",
     "expect": {"subject": "迟昊", "no_error": True}},
    {"q": "商用事业部丁杰的业绩", "cat": "subject", "note": "事业部+人名取人名",
     "expect": {"subject": "丁杰", "dataset_ids": [3], "no_error": True}},
    {"q": "这个人的业绩丁杰", "cat": "subject", "note": "倒桩人名在尾部",
     "expect": {"subject": "丁杰", "no_error": True}},
    {"q": "查询丁杰", "cat": "subject", "note": "查询前缀(裸节点索引命中直出)",
     "expect": {"subject": "丁杰", "dataset_ids": [3], "no_error": True}},
    {"q": "看下靳锋", "cat": "subject", "note": "看下前缀(裸节点直出)",
     "expect": {"subject": "靳锋", "dataset_ids": [3], "no_error": True}},
    {"q": "我想知道丁杰的业绩", "cat": "subject", "note": "我想知道前缀",
     "expect": {"subject": "丁杰", "no_error": True}},
    {"q": "万州城市公司咋样了", "cat": "subject", "note": "城市公司不被吃",
     "expect": {"subject": "万州城市公司", "no_error": True}},
    {"q": "消费者事业部万州的业绩", "cat": "subject", "note": "事业部+城市公司(节点索引=万州城市公司)",
     "expect": {"subject": "万州城市公司", "no_error": True}},
    {"q": "四川代表处的业绩", "cat": "subject", "note": "数字开头代表处",
     "expect": {"subject": "四川代表处", "no_error": True}},

    # ── 排名/TopN（ranking）──
    {"q": "看下前三的业务承接人", "cat": "ranking", "note": "电商承接人Top3",
     "expect": {"intent": "ranking", "top_n": 3, "target_level": "承接人", "preferred": [62], "no_error": True}},
    {"q": "看下前三的城市分公司", "cat": "ranking", "note": "Top3不误走drilldown",
     "expect": {"intent": "ranking", "top_n": 3, "preferred": [3], "no_error": True}},
    {"q": "前5的业务代表", "cat": "ranking", "note": "Top5",
     "expect": {"intent": "ranking", "top_n": 5, "preferred": [3], "no_error": True}},
    {"q": "垫底的三个分公司", "cat": "ranking", "note": "通用层级需确认(baseline 3.3)",
     "expect": {"requires_confirmation": True, "no_error": True}},
    {"q": "业绩最差的业务代表", "cat": "ranking", "note": "最差默认1",
     "expect": {"intent": "ranking", "top_n": 1, "preferred": [3], "no_error": True}},
    {"q": "城市分公司的业绩", "cat": "ranking", "note": "层级Overview走ranking",
     "expect": {"intent": "ranking", "top_n": 0, "preferred": [3], "no_error": True}},
    {"q": "消费者城市分公司排名", "cat": "ranking", "note": "无数量返回全量",
     "expect": {"intent": "ranking", "top_n": 0, "preferred": [2], "no_error": True}},
    {"q": "看下销售金额前三的代表处", "cat": "ranking", "note": "销售金额+Top3",
     "expect": {"intent": "ranking", "top_n": 3, "preferred": [3], "no_error": True}},

    # ── 下钻（drilldown）──
    {"q": "江浙沪分公司的城市分公司", "cat": "drilldown", "note": "节点+目标子层级",
     "expect": {"intent": "drilldown", "no_error": True}},
    {"q": "电商事业部的业绩", "cat": "drilldown", "note": "电商根节点展示下级",
     "expect": {"no_error": True}},

    # ── 过滤（filter）──
    {"q": "没有开张的业务代表", "cat": "filter", "note": "零开单口语",
     "expect": {"intent": "filter", "preferred": [3], "no_error": True}},
    {"q": "达成率在20%到40%之间的分公司", "cat": "filter", "note": "达成率区间",
     "expect": {"intent": "filter", "preferred": [3], "no_error": True}},
    {"q": "低于10%的业务代表", "cat": "filter", "note": "低于阈值",
     "expect": {"intent": "filter", "preferred": [3], "no_error": True}},

    # ── 路由/确认（routing）──
    {"q": "看下上海代表处的业绩咋样了", "cat": "routing", "note": "唯一命中直出",
     "expect": {"subject": "上海代表处", "no_error": True}},
    {"q": "东部那个分公司怎么样", "cat": "routing", "note": "口语化唯一命中",
     "expect": {"subject": "东部分公司", "preferred": [3], "no_error": True}},

    # ── 对比（comparison）──
    {"q": "东部分公司和南部分公司的业绩对比", "cat": "comparison", "note": "对比带preferred走detail路径",
     "expect": {"subject": "东部分公司", "preferred": [3], "no_error": True}},
]

# ─── 诊断逻辑 ────────────────────────────────────────────────────────────────

def _extract(resp):
    """从 ask() 响应中提取关键诊断字段"""
    dr = (resp.get("dataset_results") or [{}])[0]
    qi = dr.get("query_intent") or {}
    route = resp.get("route") or {}
    sql = dr.get("sql") or resp.get("sql") or ""

    # subject 的五层来源（按优先级）：
    # 1. query_intent.subject_name — Agent1 主体解析路径
    # 2. route.resolved_subject_name — 路由层解析
    # 3. refined_query 中"组织树标准名称：XXX" — 路由层已标准化
    # 4. effective_question 去掉"的业绩"后缀 — 兜底
    # 5. display_title 去掉"的业绩"后缀 — 最后兜底
    subject = qi.get("subject_name") or route.get("resolved_subject_name") or ""
    if not subject:
        refined = route.get("refined_query") or ""
        m = re.search(r"组织树标准名称[：:]([^。\n]+)", refined)
        if m:
            subject = m.group(1).strip()
    if not subject:
        for src in [resp.get("effective_question") or "", resp.get("display_title") or ""]:
            # 通用正则：剥 "的XXX" 后缀（XXX 是任意业务词），保留主体
            m = re.match(r"^(.+?)的(?:业绩|表现|指标|情况|综合情况|完成情况|怎么样|如何|咋样|业务|业绩如何|的业绩)$", src)
            if m:
                subject = m.group(1).strip()
                break
    # subject 标准化：如果剥出来的还是口语化（如"东部那个分公司"），用节点索引查真实节点
    if subject:
        subject = _canonicalize_subject(subject)

    return {
        "subject": subject,
        "dataset_ids": route.get("dataset_ids") or [],
        "intent": qi.get("intent") or "",
        "target_level": qi.get("target_level") or "",
        "top_n": qi.get("top_n"),
        "rank_sides": qi.get("rank_sides") or "",
        "sql": sql,
        "row_count": dr.get("row_count", 0),
        "error": resp.get("error") or dr.get("error"),
        "requires_confirmation": bool(resp.get("requires_confirmation")),
        "display_title": resp.get("display_title") or "",
    }


def _check(info, expect):
    """逐项检查，返回 (all_pass, details_list)"""
    details = []
    all_pass = True

    if "subject" in expect:
        ok = info["subject"] == expect["subject"]
        mark = "✅" if ok else "❌"
        details.append(f"subject={mark}{info['subject']!r}(期望{expect['subject']!r})")
        if not ok:
            all_pass = False

    if "dataset_ids" in expect:
        ok = any(d in info["dataset_ids"] for d in expect["dataset_ids"])
        mark = "✅" if ok else "❌"
        details.append(f"ds={mark}{info['dataset_ids']}(期望含{expect['dataset_ids']})")
        if not ok:
            all_pass = False

    if "intent" in expect:
        ok = info["intent"] == expect["intent"]
        mark = "✅" if ok else "❌"
        details.append(f"intent={mark}{info['intent']!r}(期望{expect['intent']!r})")
        if not ok:
            all_pass = False

    if "target_level" in expect:
        ok = info["target_level"] == expect["target_level"]
        mark = "✅" if ok else "❌"
        details.append(f"level={mark}{info['target_level']!r}(期望{expect['target_level']!r})")
        if not ok:
            all_pass = False

    if "top_n" in expect:
        ok = info["top_n"] == expect["top_n"]
        mark = "✅" if ok else "❌"
        details.append(f"top_n={mark}{info['top_n']}(期望{expect['top_n']})")
        if not ok:
            all_pass = False

    if "sql_contains" in expect:
        for kw in expect["sql_contains"]:
            ok = kw in info["sql"]
            mark = "✅" if ok else "❌"
            details.append(f"sql含'{kw}'={mark}")
            if not ok:
                all_pass = False

    if "requires_confirmation" in expect:
        ok = info["requires_confirmation"] == expect["requires_confirmation"]
        mark = "✅" if ok else "❌"
        details.append(f"confirm={mark}{info['requires_confirmation']}")
        if not ok:
            all_pass = False

    if expect.get("no_error"):
        ok = info["error"] is None
        mark = "✅" if ok else "❌"
        details.append(f"err={mark}{info['error']}")
        if not ok:
            all_pass = False

    return all_pass, details


def diagnose_single(svc, question):
    """单个问题诊断：显示每一步中间结果"""
    print(f"\n{'='*60}")
    print(f"诊断: {question}")
    print(f"{'='*60}")
    start = time.time()
    resp = svc.ask(question=question, current_user=FAKE_USER, session_id="diag")
    elapsed = round(time.time() - start, 2)
    info = _extract(resp)

    print(f"\n[1] 主体提取")
    print(f"    subject: {info['subject']!r}")
    print(f"    route.resolved_subject_name: {(resp.get('route') or {}).get('resolved_subject_name')!r}")

    print(f"\n[2] 重写问题")
    print(f"    effective_question: {resp.get('effective_question')!r}")
    print(f"    refined_query: {(resp.get('route') or {}).get('refined_query')!r}")

    print(f"\n[3] 路由")
    print(f"    dataset_ids: {info['dataset_ids']}")
    print(f"    requires_confirmation: {info['requires_confirmation']}")
    print(f"    arbiter_reason: {(resp.get('route') or {}).get('arbiter_reason')!r}")

    print(f"\n[4] 意图解析")
    print(f"    intent: {info['intent']!r}")
    print(f"    target_level: {info['target_level']!r}")
    print(f"    top_n: {info['top_n']}")
    print(f"    rank_sides: {info['rank_sides']!r}")

    print(f"\n[5] SQL (前200字)")
    sql_preview = info["sql"][:200].replace("\n", " ")
    print(f"    {sql_preview}...")

    print(f"\n[6] 结果")
    print(f"    rows: {info['row_count']}")
    print(f"    error: {info['error']}")
    print(f"    display_title: {info['display_title']!r}")
    print(f"    耗时: {elapsed}s")
    print()

    # steps trace
    steps = resp.get("steps") or []
    if steps:
        print(f"[7] 执行步骤")
        for s in steps:
            status = "✅" if s.get("status") == "success" else "❌"
            print(f"    {status} {s.get('title','?')} ({s.get('duration',0):.0f}ms)")
    print()


def run_batch(svc, cases, category_filter=None):
    """批量跑测试用例"""
    filtered = [c for c in cases if not category_filter or c["cat"] == category_filter]
    print(f"\n{'='*80}")
    print(f"SmartAsk 问数准确率诊断 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"用例数: {len(filtered)} | 分类: {category_filter or '全部'}")
    print(f"{'='*80}\n")

    results = []
    for i, case in enumerate(filtered, 1):
        q = case["q"]
        expect = case["expect"]
        note = case.get("note", "")
        cat = case["cat"]

        try:
            preferred = expect.get("preferred")
            resp = svc.ask(
                question=q, current_user=FAKE_USER, session_id=f"diag-{i}",
                preferred_dataset_ids=preferred,
            )
            info = _extract(resp)
        except Exception as e:
            info = {"subject": "", "dataset_ids": [], "intent": "", "target_level": "",
                    "top_n": None, "rank_sides": "", "sql": "", "row_count": 0,
                    "error": str(e), "requires_confirmation": False, "display_title": ""}

        all_pass, details = _check(info, expect)
        status = "✅" if all_pass else "❌"

        results.append({
            "no": i, "question": q, "category": cat, "note": note,
            "pass": all_pass, "details": details, "info": {
                "subject": info["subject"], "dataset_ids": info["dataset_ids"],
                "intent": info["intent"], "target_level": info["target_level"],
                "top_n": info["top_n"], "error": info["error"],
                "row_count": info["row_count"],
            },
        })

        # 控制台输出
        print(f"{status} [{i:2d}] {q}")
        print(f"    分类: {cat} | {note}")
        if not all_pass:
            for d in details:
                if "❌" in d:
                    print(f"    {d}")
        print()

    # 汇总
    passed = sum(1 for r in results if r["pass"])
    failed = sum(1 for r in results if not r["pass"])
    print(f"{'='*80}")
    print(f"结果: {passed}/{len(filtered)} 通过, {failed} 失败")
    print(f"{'='*80}\n")

    if failed:
        print("失败明细:")
        for r in results:
            if not r["pass"]:
                print(f"  ❌ [{r['no']}] {r['question']}")
                for d in r["details"]:
                    if "❌" in d:
                        print(f"      {d}")
        print()

    return results


def save_report(results, category_filter=None):
    """保存 Markdown 报告"""
    output_dir = os.path.join(PROJECT_ROOT, "config", "diagnostics")
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output_dir, f"accuracy_report_{ts}.md")

    passed = sum(1 for r in results if r["pass"])
    failed = sum(1 for r in results if not r["pass"])

    lines = [
        f"# SmartAsk 问数准确率诊断报告",
        f"",
        f"- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 用例: {len(results)} 个",
        f"- 通过: {passed}",
        f"- 失败: {failed}",
        f"- 分类: {category_filter or '全部'}",
        f"",
        f"## 结果总览",
        f"",
        f"| # | 问题 | 分类 | 主体 | 路由 | intent | top_n | 结果 |",
        f"|---|------|------|------|------|--------|-------|------|",
    ]

    for r in results:
        mark = "✅" if r["pass"] else "❌"
        info = r["info"]
        ds = ",".join(str(d) for d in info["dataset_ids"]) or "-"
        lines.append(
            f"| {r['no']} | {r['question']} | {r['category']} "
            f"| {info['subject'] or '-'} | {ds} | {info['intent'] or '-'} "
            f"| {info['top_n']} | {mark} |"
        )

    if failed:
        lines += [
            f"",
            f"## 失败明细",
            f"",
        ]
        for r in results:
            if not r["pass"]:
                lines.append(f"### ❌ [{r['no']}] {r['question']}")
                lines.append(f"- 分类: {r['category']}")
                lines.append(f"- 说明: {r['note']}")
                lines.append(f"- 实际: subject={r['info']['subject']}, ds={r['info']['dataset_ids']}, "
                             f"intent={r['info']['intent']}, top_n={r['info']['top_n']}")
                for d in r["details"]:
                    if "❌" in d:
                        lines.append(f"- **{d}**")
                lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a.split("=")[0]: a.split("=")[1] if "=" in a else True for a in sys.argv[1:] if a.startswith("--")}

    svc = FourAgentAskService()

    if args:
        # 单问题诊断
        question = args[0]
        diagnose_single(svc, question)
    else:
        # 批量诊断
        category = flags.get("--category")
        results = run_batch(svc, TEST_CASES, category)
        report_path = save_report(results, category)
        print(f"报告已保存: {report_path}")


if __name__ == "__main__":
    main()
