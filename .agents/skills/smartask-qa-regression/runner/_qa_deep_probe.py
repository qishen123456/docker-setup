# -*- coding: utf-8 -*-
"""深挖：DS-C1/C2 报错原因 + 关键用例的行级节点分布"""
import json, uuid
from four_agent_ask import four_agent_ask_service as svc

USER = {"role": "super_admin", "id": 1, "username": "qa", "organization_codes": [], "organization_node_ids": []}

DEEP = [
    ("DS-C1", "国内业务部和直营零售部对比"),
    ("DS-C2", "黄超和刘志伟对比"),
    ("CY-D1", "河南代表处业绩"),
    ("CY-D2", "工业医疗业务部业绩"),
    ("CY-M1", "赵标和靳锋的业绩"),
    ("CY-C1", "河南代表处和上海代表处对比"),
    ("XF-D1", "河北分公司业绩"),
    ("XF-C1", "云贵渝分公司和山东分公司对比"),
    ("DS-D1", "国内业务部业绩"),
    ("DS-L1", "业务承接人的业绩"),
    ("DS-L2", "承接人的业绩"),
    ("CY-S3", "丁杰的业绩"),
]

for cid, q in DEEP:
    sid = str(uuid.uuid4())
    try:
        res = svc.ask(question=q, session_id=sid, conversation_history=None, current_user=USER)
        print(f"\n=== {cid} | {q} ===")
        if "error" in res:
            print("  ERROR:", json.dumps(res.get("error"), ensure_ascii=False)[:500])
            continue
        drs = res.get("dataset_results") or []
        if not drs:
            print("  no dataset_results; keys=", list(res.keys()))
            if "confirmation" in res:
                print("  conf:", json.dumps(res["confirmation"], ensure_ascii=False)[:300])
            continue
        dr = drs[0]
        rows = dr.get("rows") or []
        print(f"  row_count={dr.get('row_count')} sql={(dr.get('sql') or '')[:200]}")
        # 打印前 30 行的节点名/层级
        for i, r in enumerate(rows[:30]):
            if isinstance(r, dict):
                keys = list(r.keys())
                nm = r.get("node_name") or r.get("name") or r.get("节点") or ""
                lvl = r.get("node_level") or r.get("level") or ""
                print(f"   row{i}: name={nm} level={lvl} keys={keys[:6]}")
    except Exception as e:
        print(f"\n=== {cid} | {q} === EXCEPTION: {e}")
