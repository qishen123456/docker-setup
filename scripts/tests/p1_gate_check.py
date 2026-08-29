# -*- coding: utf-8 -*-
"""P1 门禁判定器：从多轮跑题结果 + 标签化用例集计算修订版门禁指标。

用法（容器内）：
    python /app/backend/_p1_gate_check.py <cases.json> <runs.jsonl> [runs2.jsonl ...]

runs.jsonl 每行带 run 标签（同一题多轮结果）；或用多个文件各自算一轮。

门禁指标（开工计划 v2 修订版）：
  1. verdict 级一致率：deterministic=true 硬题要求全轮一致；软题看多数决占比
  2. 真误拦率：expected_verdict=pass 且非 reasonable_clarify 的题被弹纠正卡的比例
  3. 不合理澄清率：应 pass 题被弹确认卡/纠正卡（扣除 reasonable_clarify 豁免）的比例
  4. rewrite 精度：expect_correction 命中率（拦截类题）
"""
import json
import sys
from collections import Counter, defaultdict


def load_jsonl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def main():
    cases_path = sys.argv[1]
    run_paths = sys.argv[2:]
    cases = {c["question"]: c for c in json.load(open(cases_path, encoding="utf-8"))}

    # by_question[q] = [verdict per run]
    by_q = defaultdict(list)
    for i, p in enumerate(run_paths):
        for rec in load_jsonl(p):
            by_q[rec["question"]].append(rec)

    hard_ok = hard_total = 0
    soft_consistency = []
    false_block = block_base = 0          # 真误拦
    unfair_clarify = clarify_base = 0     # 不合理澄清
    rewrite_hit = rewrite_total = 0       # 候选精度
    failures = []

    for q, recs in sorted(by_q.items()):
        case = cases.get(q)
        if case is None:
            continue
        if case.get("known_defect"):
            continue  # 已知他层缺陷（如 SQL 字段映射），不计入门禁分子分母
        verdicts = [r["verdict"] for r in recs]
        det = case.get("deterministic", False)
        exp_v = case.get("expected_verdict")
        n = len(verdicts)
        top, top_n = Counter(verdicts).most_common(1)[0]

        # 1. 一致率
        if det:
            hard_total += 1
            if len(set(verdicts)) == 1:
                hard_ok += 1
            else:
                failures.append(f"[硬题抖动] {q}: {verdicts}")
        else:
            soft_consistency.append(top_n / n)

        # 2/3. 误拦与不合理澄清（按单轮计）
        if exp_v == "pass":
            exempt = case.get("reasonable_clarify", False)
            for v in verdicts:
                block_base += 1
                clarify_base += 1
                if v in ("CARD", "CARD_MISS"):
                    if not exempt or v == "CARD_MISS":
                        false_block += 1
                        failures.append(f"[真误拦] {q}: {v}")
                if v in ("CARD", "CARD_MISS", "CONFIRM") and not exempt:
                    unfair_clarify += 1

        # 4. rewrite 精度
        if exp_v in ("rewrite", "soft_hint", "clarify") and case.get("expect_correction"):
            for r in recs:
                if r["verdict"] in ("CARD_HIT", "CARD_MISS"):
                    rewrite_total += 1
                    if r["verdict"] == "CARD_HIT":
                        rewrite_hit += 1
                    else:
                        failures.append(f"[候选错] {q}: {r.get('detail','')[:60]}")

    print("===== P1 门禁指标 =====")
    if hard_total:
        print(f"1a. 硬题全轮一致: {hard_ok}/{hard_total}"
              f"（{'PASS' if hard_ok == hard_total else 'FAIL'}，要求 100%）")
    if soft_consistency:
        avg = sum(soft_consistency) / len(soft_consistency)
        print(f"1b. 软题多数决一致率: {avg:.1%}（目标 ≥85%）{'PASS' if avg >= 0.85 else 'FAIL'}")
    if block_base:
        rate = false_block / block_base
        print(f"2. 真误拦率: {false_block}/{block_base} = {rate:.1%}（目标 <2%）{'PASS' if rate < 0.02 else 'FAIL'}")
    if clarify_base:
        rate = unfair_clarify / clarify_base
        print(f"3. 不合理澄清率: {unfair_clarify}/{clarify_base} = {rate:.1%}（目标 ≤5%）{'PASS' if rate <= 0.05 else 'FAIL'}")
    if rewrite_total:
        rate = rewrite_hit / rewrite_total
        print(f"4. 拦截候选精度: {rewrite_hit}/{rewrite_total} = {rate:.1%}（目标 ≥95%）{'PASS' if rate >= 0.95 else 'FAIL'}")
    if failures:
        print("\n===== 失败明细 =====")
        for f in failures:
            print(f)


if __name__ == "__main__":
    main()
