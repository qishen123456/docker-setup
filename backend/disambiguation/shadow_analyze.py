# -*- coding: utf-8 -*-
"""影子守门员离线分析（澄清方案 v4 / 9.1-B3 门槛评估）。

用法（容器内）：
  python /app/backend/disambiguation/shadow_analyze.py [log_path]

输入：config/shadow_gatekeeper_log.jsonl（P-1 在线采集）
输出：B3 五项指标的可评估部分 + 分桶校准表 + 需人工标注的抽样清单。

B3 门槛：
  误拦率 ≤2%（需人工标注 should_block 后计算）
  高置信桶(≥0.8)正确率 ≥95%（需标注）
  ECE ≤0.1 且分桶正确率单调（需标注）
  真歧义捕获率 ≥80%（需标注）
  在线样本 ≥500（本脚本直接可算）

未标注时只输出分布与代理信号：
  - user_reasked_within_30s：同 session 30s 内换问题重问（纠正信号的弱代理）
  - pass 占比 / suggest / block 分布、gk_status 健康度、延迟分布
"""
import json
import os
import sys
from collections import Counter, defaultdict

DEFAULT_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config", "shadow_gatekeeper_log.jsonl")

CONFIDENCE_BUCKETS = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01)]


def load_records(path):
    records = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue
    return records


def mark_reask(records):
    """同 session 30s 内再次提问 → 上一条标记 reask 代理信号。"""
    by_session = defaultdict(list)
    for r in records:
        sid = r.get("session_id") or ""
        if sid:
            by_session[sid].append(r)
    for sid, items in by_session.items():
        items.sort(key=lambda x: x.get("timestamp") or 0)
        for prev, cur in zip(items, items[1:]):
            if 0 < (cur.get("timestamp") or 0) - (prev.get("timestamp") or 0) <= 30:
                prev["user_reasked_within_30s"] = True
    return records


def bucket_of(conf):
    if conf is None:
        return None
    try:
        conf = float(conf)
    except Exception:
        return None
    for lo, hi in CONFIDENCE_BUCKETS:
        if lo <= conf < hi:
            return f"[{lo},{hi})"
    return None


def main(path):
    records = mark_reask(load_records(path))
    total = len(records)
    print(f"样本总量: {total}  (B3 门槛 ≥500: {'达标' if total >= 500 else '未达标'})")
    if not total:
        return

    status = Counter(r.get("gk_status") for r in records)
    print(f"\ngk_status: {dict(status)}")
    ok = [r for r in records if r.get("gk_status") == "ok"]
    if records:
        err_rate = (total - len(ok)) / total * 100
        print(f"调用失败率: {err_rate:.1f}%  (超时/非JSON——P0 换模型或压 max_tokens 的依据)")

    actions = Counter(r.get("gk_action") for r in ok)
    print(f"\naction 分布（仅 gk_status=ok 的 {len(ok)} 条）:")
    for a, n in actions.most_common():
        print(f"  {a}: {n}  ({n/len(ok)*100:.1f}%)")
    would_block = sum(1 for r in ok if r.get("would_block"))
    print(f"would_block 占比: {would_block}/{len(ok)} = {would_block/len(ok)*100:.1f}%  (澄清频次上限估计)")

    lat = sorted(r.get("gk_latency_ms") or 0 for r in ok)
    if lat:
        print(f"\n延迟 ms: p50={lat[len(lat)//2]} p90={lat[int(len(lat)*0.9)]} max={lat[-1]}")

    reask = sum(1 for r in ok if r.get("user_reasked_within_30s"))
    print(f"\n30s 内重问（纠正弱代理）: {reask}/{len(ok)} = {reask/len(ok)*100:.1f}%")

    print("\n置信度分桶（action 分布 | 重问率）:")
    buckets = defaultdict(list)
    for r in ok:
        b = bucket_of(r.get("self_confidence"))
        if b:
            buckets[b].append(r)
    for lo, hi in CONFIDENCE_BUCKETS:
        b = f"[{lo},{hi})"
        items = buckets.get(b) or []
        if not items:
            continue
        acts = Counter(r.get("gk_action") for r in items)
        rr = sum(1 for r in items if r.get("user_reasked_within_30s")) / len(items) * 100
        print(f"  {b}: n={len(items)}  actions={dict(acts)}  重问率={rr:.0f}%")

    labeled = [r for r in records if r.get("should_block") is not None]
    print(f"\n人工标注: {len(labeled)} 条")
    if labeled:
        tp = sum(1 for r in labeled if r["should_block"] and r.get("would_block"))
        fp = sum(1 for r in labeled if not r["should_block"] and r.get("would_block"))
        fn = sum(1 for r in labeled if r["should_block"] and not r.get("would_block"))
        print(f"  误拦率 FP={fp}/{len(labeled)} = {fp/len(labeled)*100:.1f}%  (门槛 ≤2%)")
        print(f"  捕获率 TP/(TP+FN) = {tp}/{tp+fn} = {tp/(tp+fn)*100:.1f}%" if tp + fn else "  捕获率: 标注集中无真歧义样本")

    sample = [r for r in ok if r.get("would_block") and r.get("should_block") is None][:100]
    if sample:
        out = os.path.join(os.path.dirname(path), "shadow_label_sample.jsonl")
        with open(out, "w", encoding="utf-8") as fh:
            for r in sample:
                fh.write(json.dumps({
                    "question": r.get("question"),
                    "gk_action": r.get("gk_action"),
                    "block_reason": r.get("block_reason"),
                    "candidates": r.get("candidate_options_topN"),
                    "should_block": None,
                }, ensure_ascii=False) + "\n")
        print(f"\n已导出待标注样本 {len(sample)} 条 → {out}")
        print("标注方式：把 should_block 填 true/false 后回填日志重跑本脚本即可出 B3 全量指标。")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LOG)
