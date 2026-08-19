# -*- coding: utf-8 -*-
"""QA 补漏实测：一次性跑所有未覆盖组合，只读"""
import json, sys, uuid
from four_agent_ask import four_agent_ask_service as svc

USER = {"role": "super_admin", "id": 1, "username": "qa", "organization_codes": [], "organization_node_ids": []}

CASES = [
    # id, question, expect_dataset_ids(单)，expect_intent 关键词（软）, 备注
    # ===== 商用 id=3 =====
    ("CY-D1", "河南代表处业绩", [3], "drill_down", "代表处下钻→4业务代表"),
    ("CY-D2", "工业医疗业务部业绩", [3], "drill_down", "业务部下钻→3业务代表"),
    ("CY-S1", "靳锋的业绩", [3], "single", "业务代表单点"),
    ("CY-S2", "赵标的业绩", [3], "single", "业务代表单点"),
    ("CY-S3", "丁杰的业绩", [3], "single", "业务代表单点(不存在)"),
    ("CY-M1", "赵标和靳锋的业绩", [3], "multi", "并列多人名"),
    ("CY-M2", "靳锋和赵标的业绩", [3], "multi", "并列多人名(反序)"),
    ("CY-C1", "河南代表处和上海代表处对比", [3], "comparison", "代表处对比"),
    ("CY-C2", "工业医疗业务部和餐饮业务部对比", [3], "comparison", "业务部对比"),
    # ===== 消费者 id=2 =====
    ("XF-D1", "河北分公司业绩", [2], "drill_down", "分公司下钻→4城市公司"),
    ("XF-S1", "上海城市公司业绩", [2], "single", "城市分公司单点"),
    ("XF-C1", "云贵渝分公司和山东分公司对比", [2], "comparison", "分公司对比"),
    ("XF-C2", "上海城市公司和郑州城市公司对比", [2], "comparison", "城市分公司对比"),
    # ===== 电商 id=62 =====
    ("DS-D1", "国内业务部业绩", [62], "drill_down", "业务部下钻→承接人"),
    ("DS-S1", "黄超的业绩", [62], "single", "承接人单点"),
    ("DS-S2", "刘志伟的业绩", [62], "single", "承接人单点(重复多条)"),
    ("DS-C1", "国内业务部和直营零售部对比", [62], "comparison", "业务部对比"),
    ("DS-C2", "黄超和刘志伟对比", [62], "comparison", "承接人对比"),
    ("DS-L1", "业务承接人的业绩", [62], "level", "层级词-业务承接人"),
    ("DS-L2", "承接人的业绩", [62], "level", "层级词-承接人"),
    ("DS-L3", "任务承接人的业绩", [62], "level", "层级词-任务承接人"),
    ("DS-L4", "负责人的业绩", [62], "level", "层级词-负责人"),
]

def summarize(res):
    """提取关键信息"""
    out = {}
    try:
        route = res.get("route") or {}
        out["dataset_ids"] = route.get("dataset_ids")
        out["decision"] = route.get("decision") or route.get("decision_type")
        drs = res.get("dataset_results") or []
        if drs:
            dr = drs[0]
            qi = dr.get("query_intent") or {}
            out["intent"] = qi.get("intent")
            out["top_n"] = qi.get("top_n")
            out["direction"] = qi.get("direction")
            out["row_count"] = dr.get("row_count")
            rows = dr.get("rows") or []
            # 层级分布
            lv = {}
            names = []
            for r in rows[:20]:
                if isinstance(r, dict):
                    lvl = r.get("node_level") or r.get("level") or "?"
                    lv[lvl] = lv.get(lvl, 0) + 1
                    nm = r.get("node_name") or r.get("name")
                    if nm:
                        names.append(nm)
            out["levels"] = lv
            out["top_nodes"] = names[:6]
        else:
            # 弹确认场景
            conf = res.get("confirmation") or res.get("clarification")
            if conf:
                out["confirmation"] = str(conf)[:200]
            else:
                out["raw_keys"] = list(res.keys())[:10]
    except Exception as e:
        out["error"] = str(e)
    return out

for cid, q, exp_ds, exp_int, note in CASES:
    sid = str(uuid.uuid4())
    try:
        res = svc.ask(question=q, session_id=sid, conversation_history=None, current_user=USER)
        s = summarize(res)
        # 判定
        ds = s.get("dataset_ids") or []
        intent = (s.get("intent") or "").lower()
        ok_ds = (set(ds) == set(exp_ds))
        # 软判 intent
        print(f"\n=== {cid} | {q} ===")
        print(f"  期望: ds={exp_ds} intent~{exp_int} | {note}")
        print(f"  实测: {json.dumps(s, ensure_ascii=False, default=str)[:400]}")
        print(f"  判定: ds={'OK' if ok_ds else 'NG'}")
    except Exception as e:
        print(f"\n=== {cid} | {q} === EXCEPTION: {e}")
