# -*- coding: utf-8 -*-
import json, re, sys, time

from four_agent_ask import four_agent_ask_service

USER = {"role": "super_admin", "id": 99999, "username": "qa",
        "organization_codes": ["*"], "organization_node_ids": ["*"]}

def last_limit(sql):
    if not sql:
        return None
    m = re.findall(r"LIMIT\s+\d+", sql, flags=re.I)
    return m[-1] if m else None

def summarize(r):
    route = r.get("route") or {}
    out = {
        "route_dataset_ids": route.get("dataset_ids"),
        "route_decision": route.get("decision"),
        "route_intent": route.get("intent"),
        "requires_confirmation": bool(r.get("requires_confirmation")),
        "confirmation_question": route.get("confirmation_question"),
    }
    drs = r.get("dataset_results") or []
    out["dataset_results"] = []
    for dr in drs:
        qi = dr.get("query_intent") or {}
        rows = dr.get("rows") or []
        item = {
            "dataset_id": dr.get("dataset_id"),
            "dataset_name": dr.get("dataset_name"),
            "qi_intent": qi.get("intent"),
            "qi_top_n": qi.get("top_n"),
            "qi_target_level": qi.get("target_level"),
            "qi_matched_triggers": qi.get("matched_triggers"),
            "row_count": dr.get("row_count"),
            "last_limit": last_limit(dr.get("sql")),
            "columns": dr.get("columns"),
            "rows_head": rows[:8],
        }
        out["dataset_results"].append(item)
    return out

def run(case_no, question, session_id):
    t0 = time.time()
    r = four_agent_ask_service.ask(
        question=question,
        session_id=session_id,
        conversation_history=None,
        current_user=USER,
    )
    dur = round(time.time() - t0, 2)
    print(f"\n===== CASE {case_no} | {question} | {dur}s =====", flush=True)
    print(json.dumps(summarize(r), ensure_ascii=False, default=str), flush=True)
    return r

if __name__ == "__main__":
    # A. P1 改动目标
    run(1, "商用事业部整体业绩", "qa_reg_1")
    run(2, "消费者事业部哪个分公司完成率最高", "qa_reg_2")
    # B. 排名类回归
    run(3, "看下前三的商用分公司", "qa_reg_3")
    run(4, "看下前三的业务承接人", "qa_reg_4")
    run(5, "业绩最好的分公司", "qa_reg_5")
    run(6, "各分公司业绩排名", "qa_reg_6")
    run(7, "城市分公司的业绩咋样", "qa_reg_7")
    # C. P4 改动目标（多轮）
    run("8a", "丁杰的业绩", "qa_reg_8")
    run("8b", "达成率咋样", "qa_reg_8")
    # D. P4 回归
    run(9, "各分公司业绩咋样", "qa_reg_9")
    # E. 核心基线
    run(10, "东部分公司的业绩怎么样了", "qa_reg_10")
    run(11, "东部分公司和南部分公司的业绩对比", "qa_reg_11")
    run(12, "电商事业部的业绩", "qa_reg_12")
    run(13, "低于10%的业务代表", "qa_reg_13")
    run(14, "江浙沪分公司的城市分公司", "qa_reg_14")
    # E15 多轮跨数据集
    run("15a", "消费者事业部业绩", "qa_reg_15")
    run("15b", "东部分公司业绩", "qa_reg_15")
    print("\n===== DONE =====", flush=True)
