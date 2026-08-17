import sys
sys.path.insert(0, "/app/backend")
from four_agent_ask import four_agent_ask_service as svc
import dataset_report_config as report_config_store

q = sys.argv[1]
print("Q:", q)
print("looks_like_org_subject:", svc._looks_like_org_subject_question(q))
cfg = report_config_store.get_default_config()
ctx = {"report_config": cfg, "dataset": {"dataset_code": "syyb_standard_v1", "dataset_name": "商用事业部", "id": 3}}
print("_has_specific_node(ctx):", svc._has_specific_node(ctx))
names = svc._question_subject_names(q, ctx, include_resolved=False)
print("question_subject_names(include_resolved=False):", names)
res = svc._agent1_resolve_org_subject(q, conversation_context=None, trace=None)
print("agent1 result keys:", list(res.keys()) if isinstance(res, dict) else type(res))
if isinstance(res, dict):
    for k in ("rewritten_question", "subject_name", "subject_level", "resolved_subject_name"):
        print("  agent1.%s =" % k, res.get(k))
