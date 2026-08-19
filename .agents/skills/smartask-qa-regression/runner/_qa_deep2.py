# -*- coding: utf-8 -*-
import json, uuid
from four_agent_ask import four_agent_ask_service as svc
USER = {"role": "super_admin", "id": 1, "username": "qa", "organization_codes": [], "organization_node_ids": []}
DEEP = [
    ("CY-D1", "河南代表处业绩"),
    ("CY-D2", "工业医疗业务部业绩"),
    ("CY-M1", "赵标和靳锋的业绩"),
    ("CY-C1", "河南代表处和上海代表处对比"),
    ("CY-C2", "工业医疗业务部和餐饮业务部对比"),
    ("XF-D1", "河北分公司业绩"),
    ("XF-C1", "云贵渝分公司和山东分公司对比"),
    ("XF-C2", "上海城市公司和郑州城市公司对比"),
    ("DS-D1", "国内业务部业绩"),
    ("DS-S2", "刘志伟的业绩"),
    ("DS-L1", "业务承接人的业绩"),
    ("CY-S3", "丁杰的业绩"),
]
for cid, q in DEEP:
    sid = str(uuid.uuid4())
    res = svc.ask(question=q, session_id=sid, conversation_history=None, current_user=USER)
    print(f"\n=== {cid} | {q} ===")
    if "error" in res:
        print(" ERROR:", res["error"]); continue
    dr = (res.get("dataset_results") or [{}])[0]
    rows = dr.get("rows") or []
    print(f"  row_count={dr.get('row_count')}")
    from collections import Counter
    lvls = Counter(r.get("层级","?") for r in rows if isinstance(r,dict))
    print(f"  层级分布: {dict(lvls)}")
    print(f"  节点: {[r.get('节点名称','') for r in rows[:15] if isinstance(r,dict)]}")
