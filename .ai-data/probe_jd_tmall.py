# -*- coding: utf-8 -*-
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
from four_agent_ask import four_agent_ask_service as svc

USER = {"role": "super_admin", "id": 1, "username": "qa", "organization_codes": [], "organization_node_ids": []}
q = "京东直营和天猫直营对比"
r = svc.ask(question=q, session_id="probe-jd-tmall", conversation_history=None, current_user=USER)
keys = ["error", "requires_confirmation", "route"]
out = {}
for k in keys:
    if k in r:
        out[k] = r[k]
drs = r.get("dataset_results") or []
out["n_dataset_results"] = len(drs)
for i, d in enumerate(drs[:3]):
    out[f"dr{i}"] = {
        "dataset_id": d.get("dataset_id"),
        "row_count": d.get("row_count"),
        "error": d.get("error"),
        "query_intent": d.get("query_intent"),
        "sql": (d.get("sql") or "")[:800],
        "rows_head": (d.get("rows") or [])[:5],
        "analysis": (d.get("analysis") or "")[:300],
    }
if r.get("confirmation_options"):
    out["confirmation_options"] = [
        {"dataset_ids": o.get("dataset_ids"), "label": o.get("label") or o.get("dataset_name")}
        for o in r["confirmation_options"]
    ]
print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
