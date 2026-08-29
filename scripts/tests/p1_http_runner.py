# -*- coding: utf-8 -*-
"""P1 HTTP 真实链路执行器（仓库版）：走 /api/smart-chat（前端同款路径，含 controller 全部理解层）。

用法（容器内）：
    python /app/backend/_p1_http_runner.py <cases.json> <out.jsonl> [起始] [数量]

cases 字段（四字段标签，门禁机器执行的依据）：
    question           问题原文（必填）
    category           分类标签
    expected_verdict   pass / rewrite / soft_hint / clarify（四态枚举）
    reasonable_clarify true=合理澄清豁免（弹卡但属语义真歧义，不算误拦）
    expect_correction  纠正目标串（rewrite 类应含此实体；测候选精度）
    deterministic      true=硬题必须恒答对 / false=软题允许多数决

token 自愈（优先级）：--token 参数 > 环境变量 P1_TOKEN > 自动读 /app/config/auth_tokens.json
    取未过期 super_admin 中最新签发的一个（多 AI 并发登录会挤掉旧 token，自动换新）。

宿主侧请用 scripts/tests/p1_run.sh 包装（自动 docker cp runner+cases 进容器）。
"""
import json
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

API = "http://localhost:5002/api/smart-chat"
TOKENS_FILE = "/app/config/auth_tokens.json"

_lock = threading.Lock()
_results = []
OUT_PATH = ""


def resolve_token(cli_token=None):
    if cli_token:
        return cli_token
    env = os.environ.get("P1_TOKEN")
    if env:
        return env
    try:
        data = json.load(open(TOKENS_FILE, encoding="utf-8"))
        now = datetime.now(timezone.utc)
        best = None
        for tok, info in (data.get("tokens") or {}).items():
            if not isinstance(info, dict):
                continue
            if (info.get("user") or {}).get("role") != "super_admin":
                continue
            try:
                exp = datetime.fromisoformat(str(info.get("expires_at")))
            except Exception:
                continue
            if exp <= now:
                continue
            if best is None or exp > best[1]:
                best = (tok, exp)
        if best:
            print(f"[token] 自动选用 super_admin token（{best[1].isoformat()} 过期）", flush=True)
            return best[0]
    except Exception as exc:
        print(f"[token] 自动选取失败: {exc}", flush=True)
    raise SystemExit("无可用 token：传 --token 或设 P1_TOKEN，或检查 config/auth_tokens.json")


def load_cases(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def classify(case, r):
    """返回 (verdict, detail, observed_state)。observed_state 用于四态门禁判定。"""
    if r.get("error"):
        return "ERROR", str(r.get("error"))[:120], "error"
    expect = case.get("expect_correction") or case.get("expect")
    cs = r.get("clarify_suggestion") or {}
    cands = cs.get("candidates") or []
    if r.get("early_clarify") or cands:
        src = cs.get("source") or "?"
        detail = f"{src}: {json.dumps(cands, ensure_ascii=False)[:110]}"
        if expect is None:
            return "CARD", detail, "card"
        hit = any(expect in str(c) for c in cands)
        return ("CARD_HIT" if hit else "CARD_MISS"), detail, "card"
    if r.get("requires_confirmation"):
        opts = [str(o.get("label") or "") for o in (r.get("confirmation_options") or [])]
        return "CONFIRM", json.dumps(opts, ensure_ascii=False)[:120], "confirm"
    if (r.get("row_count") or 0) > 0:
        expect_ds = case.get("dataset_id")
        if expect_ds is None:
            return "DIRECT_OK", f"rows={r.get('row_count')}", "pass"
        ds_ids = (r.get("route") or {}).get("dataset_ids") or []
        ok = expect_ds in [int(d) for d in ds_ids]
        state = "pass" if ok else "wrongds"
        return ("DIRECT_OK" if ok else "DIRECT_WRONGDS"), f"rows={r.get('row_count')} ds={ds_ids}", state
    analysis = str(r.get("analysis") or "")
    if "没有查到" in analysis or "未找到" in analysis:
        return "ZERO_LEAK", analysis[:80], "zero"
    return "OTHER", analysis[:80], "other"


def judge(case, verdict):
    """对照四字段标签判定本题 OK/ FAIL（门禁机器执行口径）。"""
    if case.get("known_defect"):
        return f"SKIP(known_defect={case['known_defect']})"  # 他层已知缺陷，不计入判定
    exp_v = case.get("expected_verdict")
    if not exp_v:
        return None  # 无标签，只记录不判定
    if verdict == "ERROR":
        return "FAIL(error)"
    if exp_v == "pass":
        if verdict == "DIRECT_OK":
            return "OK"
        if verdict in ("CARD", "CARD_HIT") and case.get("reasonable_clarify"):
            return "OK(reasonable_clarify)"
        if verdict == "CONFIRM" and case.get("reasonable_clarify"):
            return "OK(reasonable_clarify)"
        return f"FAIL(expect pass, got {verdict})"
    # 期望拦截类（rewrite/soft_hint/clarify）
    if verdict in ("CARD", "CARD_HIT", "CONFIRM"):
        target = case.get("expect_correction")
        if target and verdict != "CONFIRM":
            return "OK" if verdict == "CARD_HIT" else "FAIL(correction miss)"
        return "OK"
    return f"FAIL(expect {exp_v}, got {verdict})"


def run_one(case, headers):
    q = case["question"]
    for attempt in range(4):
        try:
            resp = requests.post(API, headers=headers, timeout=300,
                                 data=json.dumps(
                                     {"question": q,
                                      "session_id": f"p1h-{abs(hash(q))}"
                                      }).encode("utf-8"))
            r = resp.json()
            verdict, detail, state = classify(case, r)
            rec = {"question": q, "category": case.get("category"),
                   "expect": case.get("expect_correction") or case.get("expect"),
                   "verdict": verdict, "observed_state": state, "detail": detail,
                   "duration": r.get("total_duration")}
            break
        except Exception as exc:
            msg = str(exc)
            if ("429" in msg or "timed out" in msg or "Connection" in msg) and attempt < 3:
                time.sleep(20 * (attempt + 1) + random.random() * 10)
                continue
            rec = {"question": q, "category": case.get("category"),
                   "expect": case.get("expect_correction") or case.get("expect"),
                   "verdict": "ERROR", "observed_state": "error", "detail": msg[:150]}
            break
    j = judge(case, verdict)
    if j:
        rec["judge"] = j
    with _lock:
        _results.append(rec)
        with open(OUT_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tag = f" [{j}]" if j else ""
    print(f"[{rec['verdict']:<14}] {q[:38]} -> {rec['detail'][:55]}{tag}", flush=True)


def main():
    global OUT_PATH
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cli_token = None
    for a in sys.argv[1:]:
        if a.startswith("--token="):
            cli_token = a.split("=", 1)[1]
    token = resolve_token(cli_token)
    headers = {"Content-Type": "application/json; charset=utf-8",
               "Authorization": f"Bearer {token}"}
    cases_path, OUT_PATH = args[0], args[1]
    start = int(args[2]) if len(args) > 2 else 0
    count = int(args[3]) if len(args) > 3 else 9999
    if os.path.exists(OUT_PATH):
        os.remove(OUT_PATH)
    cases = load_cases(cases_path)[start:start + count]
    print(f"HTTP 真实链路执行 {len(cases)} 题（{cases_path} [{start}:{start+count}]）-> {OUT_PATH}")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda c: run_one(c, headers), cases))
    from collections import Counter
    by_cat = {}
    for rec in _results:
        by_cat.setdefault(rec["category"] or "?", []).append(rec["verdict"])
    print("\n===== 汇总 =====")
    for cat, verdicts in by_cat.items():
        print(f"{cat}: {dict(Counter(verdicts))}")
    print(f"TOTAL {len(_results)}: {dict(Counter(r['verdict'] for r in _results))}")
    judged = [r for r in _results if r.get("judge") and not r["judge"].startswith("SKIP")]
    skipped = sum(1 for r in _results if str(r.get("judge", "")).startswith("SKIP"))
    if judged:
        ok = sum(1 for r in judged if r["judge"].startswith("OK"))
        print(f"JUDGE {len(judged)}: OK {ok} / FAIL {len(judged)-ok}（另 SKIP {skipped} 道 known_defect）")
    print(f"耗时 {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
