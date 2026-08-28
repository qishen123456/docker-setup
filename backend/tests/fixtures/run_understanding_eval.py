# -*- coding: utf-8 -*-
"""输入理解层评估 runner（P0 专用，非 qa_runner——设计文档 §9）。

跑 understanding_eval.json，验证拼音索引的证据召回质量：
  - typo 集（分母只含 expect_correction 非空的实体错字题）：
    expect_correction 是否进入召回证据候选（锚定召回率，达标线 ≥80%）
  - 歧义题（expect_correction=None）：单列统计，不进召回率分母
    （它们归方向歧义层管，不是拼音索引的职责）
  - clear 集：召回噪音率（候选实体未逐字出现在问题中的才算噪音；
    最终误拦率 0 的判定在 LLM 主判层，本层只量噪音）

用法（容器内）：
    python /app/backend/tests/fixtures/run_understanding_eval.py [eval.json 路径]
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, "/app/backend")

from disambiguation.pinyin_index import recall_in_question, _PYPINYIN_OK  # noqa: E402

DEFAULT_EVAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "understanding_eval.json")


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EVAL
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    if not _PYPINYIN_OK:
        print("ENV-FAIL: pypinyin 不可用，拼音索引整模块失效")
        return 1

    typo_cases = data["sets"]["typo"]["cases"]
    clear_cases = data["sets"]["clear"]["cases"]
    entity_cases = [c for c in typo_cases if c.get("expect_correction")]
    amb_cases = [c for c in typo_cases if not c.get("expect_correction")]

    # --- 实体错字题：锚定召回率 ---
    hit, miss = 0, []
    for c in entity_cases:
        q = c["question"]
        expect = c["expect_correction"]
        evidence = recall_in_question(q, [c["dataset_id"]] if c.get("dataset_id") else None)
        recalled = {cand["node_name"] for e in evidence for cand in e["candidates"]}
        recalled |= {cand["text"] for e in evidence for cand in e["candidates"]}
        if expect in recalled:
            hit += 1
        else:
            miss.append((q, expect, [e["fragment"] for e in evidence][:3]))
    total = len(entity_cases)
    recall_rate = hit / total if total else 0.0
    print(f"[typo] 锚定召回率: {hit}/{total} = {recall_rate:.1%}（达标线 ≥80%）")
    for q, expect, frags in miss[:15]:
        print(f"  MISS: {q}  期望={expect}  召回片段={frags}")

    # --- 歧义题：单列（归方向歧义层，不进分母） ---
    print(f"[ambiguity] 歧义题 {len(amb_cases)} 道（归方向歧义层管，不进召回率分母）")

    # --- clear 集：召回噪音 ---
    noisy, noise_detail = 0, []
    for c in clear_cases:
        q = c["question"]
        evidence = recall_in_question(q, [c["dataset_id"]] if c.get("dataset_id") else None)
        noise = [(e["fragment"], cand["text"]) for e in evidence for cand in e["candidates"]]
        if noise:
            noisy += 1
            noise_detail.append((q, noise[:3]))
    ctotal = len(clear_cases)
    print(f"[clear] 召回噪音: {noisy}/{ctotal}（仅供决策层参考，误拦判定在 LLM 主判层）")
    for q, noise in noise_detail[:15]:
        print(f"  NOISE: {q}  {noise}")

    ok = recall_rate >= 0.8
    print(f"RESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
