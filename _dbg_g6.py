# -*- coding: utf-8 -*-
import sys, io, json, contextlib
sys.path.insert(0, "/app/backend")
from four_agent_ask import four_agent_ask_service as svc

USER = {"role": "super_admin", "id": 99999, "username": "qa",
        "organization_codes": ["*"], "organization_node_ids": ["*"]}

# monkey-patch 打印 _build_consumer_business_sql 的入参
_orig = svc._build_consumer_business_sql


def patched(nq, context):
    qi = context.get("query_intent") or {}
    print("[HOOK] normalized_question=%r" % nq)
    print("[HOOK] query_intent=", json.dumps(qi, ensure_ascii=False))
    print("[HOOK] entity_names(resolved)=", svc._resolved_entity_names(context))
    return _orig(nq, context)


svc._build_consumer_business_sql = patched


def ask(q, sid):
    with contextlib.redirect_stdout(io.StringIO()):
        return svc.ask(question=q, session_id=sid, conversation_history=None, current_user=USER)


def confirm(r, sel_ds):
    opts = r.get("confirmation_options") or []
    opt = None
    for o in opts:
        if set(o.get("dataset_ids") or []) == set(sel_ds):
            opt = o
            break
    if opt is None:
        return None
    with contextlib.redirect_stdout(io.StringIO()):
        return svc.confirm_by_boss(session_id=r.get("session_id"), selected_option=opt.get("label") or "",
                                   selected_dataset_ids=sel_ds, option_id=opt.get("id") or "", current_user=USER)


r = ask("谁业绩最好", "dbg-n6b")
r2 = confirm(r, [2])
for d in (r2.get("dataset_results") or []):
    print("[RESULT] keys=", list(d.keys()))
    print("[RESULT] row_count=", d.get("row_count"))
    print("[RESULT] question=", d.get("question"))
    print("[RESULT] refined_query=", d.get("refined_query"))
    print("[RESULT] raw_question=", d.get("raw_question"))
