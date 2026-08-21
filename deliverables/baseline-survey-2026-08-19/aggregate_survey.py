#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""aggregate_survey.py — 聚合 baseline_survey 分片结果，输出 markdown 报告。

容器内用法：
    python /app/backend/aggregate_survey.py --indir /app/backend/probe_out \
        --out /app/backend/probe_out/report.md
"""
import argparse
import glob
import json
import os
from collections import Counter, defaultdict


def fmt_rows(head):
    parts = []
    for r in head or []:
        name = r.get("节点名称") or "?"
        lv = r.get("层级") or ""
        rate = r.get("达成率")
        kd = r.get("年度开单金额") or r.get("开单金额")
        seg = str(name)
        if lv:
            seg += "(%s)" % lv
        if kd is not None:
            seg += " 开单=%s" % kd
        if rate is not None:
            seg += " 率=%s" % rate
        parts.append(seg)
    return "；".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", default="/app/backend/probe_out")
    ap.add_argument("--out", default="/app/backend/probe_out/report.md")
    args = ap.parse_args()

    cases = []
    for path in sorted(glob.glob(os.path.join(args.indir, "batch_*.json"))):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        cases.extend(data.get("cases") or [])
    # 按 id 去重：后写的文件（重跑）覆盖先写的
    dedup = {}
    for c in cases:
        dedup[c.get("id", "")] = c
    cases = sorted(dedup.values(), key=lambda c: c.get("id", ""))

    verdicts = Counter(c.get("verdict") for c in cases)
    # 作答题数 = 用例的 turn 数（含 confirm 分支与多轮追问）
    turns_total = sum(len(c.get("turns") or []) for c in cases)
    turn_verdicts = Counter()
    for c in cases:
        for t in c.get("turns") or []:
            turn_verdicts[t.get("verdict")] += 1

    by_cat = defaultdict(Counter)
    for c in cases:
        by_cat[c.get("cat")][c.get("verdict")] += 1

    fails = [c for c in cases if c.get("verdict") in ("FAIL", "EXC")]

    lines = []
    lines.append("# SmartAsk 基线拓展全量实测报告（2026-08-19）")
    lines.append("")
    lines.append("- 用例数：%d；实际作答轮次（含 confirm 分支与多轮追问）：%d"
                 % (len(cases), turns_total))
    lines.append("- 用例判定：%s" % dict(verdicts))
    lines.append("- 轮次判定：%s" % dict(turn_verdicts))
    lines.append("")
    lines.append("## 分类汇总")
    lines.append("")
    lines.append("| 类目 | 题数 | PASS | FAIL | INFO | EXC |")
    lines.append("|---|---|---|---|---|---|")
    cat_names = {
        "A": "单对象下钻带一层下级", "B": "末端个人只返回本人", "C": "双对象对比",
        "D": "跨数据集对比", "E": "节点+子层级drilldown", "F": "电商根节点",
        "G": "层级Overview", "H": "TopN", "I": "最X无数量", "J": "电商承接人排名",
        "K": "通用层级歧义确认", "L": "裸节点", "M": "阈值筛选", "N": "多轮追问",
        "O": "空态/时间词",
    }
    for cat in sorted(by_cat):
        v = by_cat[cat]
        lines.append("| %s %s | %d | %d | %d | %d | %d |" % (
            cat, cat_names.get(cat, ""), sum(v.values()),
            v.get("PASS", 0), v.get("FAIL", 0), v.get("INFO", 0), v.get("EXC", 0)))
    lines.append("")

    lines.append("## FAIL/EXC 清单（%d 题）" % len(fails))
    lines.append("")
    for c in fails:
        lines.append("### %s [%s] %s" % (c["id"], c["verdict"], c["q"]))
        lines.append("- 基线锚点：%s" % c.get("src", ""))
        for reason in c.get("reasons") or []:
            lines.append("- ❌ %s" % reason)
        for t in c.get("turns") or []:
            a = t.get("answer") or {}
            ds = (a.get("datasets") or [{}])[0]
            lines.append("- 轮次 %s [%s]：route=%s intent=%s top_n=%s 行数=%s 层级=%s" % (
                t.get("tag"), t.get("verdict"),
                (a.get("route") or {}).get("dataset_ids"),
                ds.get("intent"), ds.get("top_n"), ds.get("row_count"),
                ds.get("levels")))
            if a.get("requires_confirmation"):
                opts = [o.get("label") for o in a.get("confirm_options") or []]
                lines.append("  - 确认选项：%s" % opts)
            if ds.get("head_rows"):
                lines.append("  - 样本行：%s" % fmt_rows(ds.get("head_rows"))[:400])
            if ds.get("sql_keys"):
                lines.append("  - SQL：%s" % " | ".join(ds.get("sql_keys"))[:300])
        lines.append("")

    lines.append("## 全部题目答案明细")
    lines.append("")
    for c in cases:
        lines.append("### %s [%s] %s" % (c["id"], c.get("verdict"), c["q"]))
        if c.get("reasons"):
            for reason in c["reasons"]:
                lines.append("- ❌ %s" % reason)
        for t in c.get("turns") or []:
            a = t.get("answer") or {}
            lines.append("- **%s** [%s]" % (t.get("tag"), t.get("verdict")))
            if a.get("error"):
                lines.append("  - error: %s" % a["error"])
                continue
            if a.get("requires_confirmation"):
                opts = ["%s ds=%s" % (o.get("label"), o.get("dataset_ids"))
                        for o in a.get("confirm_options") or []]
                lines.append("  - 弹确认，选项：%s" % opts)
            for ds in a.get("datasets") or []:
                lines.append("  - ds=%s intent=%s top_n=%s 行数=%s 层级=%s" % (
                    ds.get("dataset_id"), ds.get("intent"), ds.get("top_n"),
                    ds.get("row_count"), ds.get("levels")))
                if ds.get("kpis"):
                    ktxt = "；".join("%s=%s" % (k.get("label"), k.get("value"))
                                     for k in ds["kpis"] if k.get("label"))
                    lines.append("  - KPI：%s" % ktxt[:300])
                if ds.get("head_rows"):
                    lines.append("  - 样本行：%s" % fmt_rows(ds.get("head_rows"))[:500])
                if ds.get("analysis"):
                    lines.append("  - 解读：%s" % ds["analysis"][:200])
        lines.append("")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("报告已写出 %s（%d 用例 / %d 轮次）" % (args.out, len(cases), turns_total))
    print("用例判定: %s" % dict(verdicts))
    print("轮次判定: %s" % dict(turn_verdicts))


if __name__ == "__main__":
    main()
