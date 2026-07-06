import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from four_agent_ask import FourAgentAskService
import dataset_report_config as report_config_store

service = object.__new__(FourAgentAskService)
ctx = {
    "dataset": {"dataset_code": "angel_business_2026_phase1", "dataset_name": "商用事业部（阶段一升级版）"},
    "report_config": report_config_store.get_default_config(),
    "resolved_entities": {},
    "data_dictionary": [{"jsonb_key": "业务部"}],
}

for q in ["看下靳锋、赵标的业绩情况", "靳锋和赵标的业绩"]:
    intent = service._resolve_query_intent(q, ctx)
    ctx["query_intent"] = intent
    sql = service._build_rule_based_sql(q, intent, ctx)
    print(f"Q: {q}")
    print(f"  intent: {intent.get('intent')}")
    print("  赵标:", "赵标" in sql)
    print("  靳锋:", "靳锋" in sql)
    for line in sql.splitlines():
        if "IN (" in line and ("赵标" in line or "靳锋" in line):
            print("  filter:", line.strip())
    print()
