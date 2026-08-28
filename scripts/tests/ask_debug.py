import json, sys
sys.path.insert(0, "/app/backend")
from four_agent_ask import four_agent_ask_service as svc

USER = {"role": "super_admin", "id": 99999, "username": "qa", "organization_codes": ["*"], "organization_node_ids": ["*"]}


def run(q):
    r = svc.ask(question=q, session_id="qa-" + str(abs(hash(q))), conversation_history=None, current_user=USER)
    route = r.get("route") or {}
    print("Q:", q)
    print("  route.dataset_ids:", route.get("dataset_ids"))
    print("  route.decision:", route.get("decision"))
    print("  route.refined_query:", route.get("refined_query"))
    print("  route.original_question:", route.get("original_question"))
    print("  route.resolved_subject_name:", route.get("resolved_subject_name"))
    print("  requires_confirmation:", r.get("requires_confirmation"))
    drs = r.get("dataset_results") or []
    for i, d in enumerate(drs):
        qi = d.get("query_intent") or {}
        print("  [%d] dataset_id=%s row_count=%s intent=%s top_n=%s rank_sides=%s direction=%s target_level=%s sort_metric_key=%s" % (
            i, d.get("dataset_id"), d.get("row_count"), qi.get("intent"), qi.get("top_n"),
            qi.get("rank_sides"), qi.get("direction"), qi.get("target_level"), qi.get("sort_metric_key"),
        ))
        sql = d.get("sql") or ""
        print("      sql_has_LIMIT:", "LIMIT" in sql, "| sql_has_ORDER:", "ORDER BY" in sql)
        for line in sql.splitlines():
            ls = line.strip()
            if ls.startswith("LIMIT") or ls.startswith("ORDER BY"):
                print("      >", ls)
        rows = d.get("rows") or []
        print("      rows_count=%d" % len(rows))
        for row in rows[:10]:
            lv = row.get("层级") or row.get("level") or ""
            nm = row.get("节点名称") or row.get("name") or ""
            parent = row.get("上级名称") or row.get("parent") or ""
            print("        - 层级=%s 名称=%s 上级=%s" % (lv, nm, parent))
    return r


if __name__ == "__main__":
    for q in sys.argv[1:]:
        try:
            run(q)
        except Exception as e:
            print("Q:", q, "ERROR:", repr(e))
        print("=" * 70)
