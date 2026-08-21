import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

for q in ['黄超的业绩', '黄超业绩', '黄超业绩如何', '黄超业绩咋样', '黄超的业绩如何']:
    with contextlib.redirect_stdout(io.StringIO()):
        r = svc.ask(question=q, session_id=f'hc-{q}', current_user=USER)
    print(f'\n=== {q} ===')
    print(f'  requires_confirmation: {r.get("requires_confirmation")}')
    print(f'  error: {r.get("error")}')
    print(f'  options: {[(o.get("label"), o.get("dataset_ids")) for o in (r.get("confirmation_options") or [])]}')
    for d in (r.get('dataset_results') or []):
        rows=d.get('rows') or []
        qi=d.get('query_intent',{})
        print(f'  ds_id={d.get("dataset_id")} ds_name={d.get("dataset_name")} rows={len(rows)}')
        print(f'  intent={qi.get("intent")} target_level={qi.get("target_level")} subject_name={qi.get("subject_name")}')
        print(f'  resolved_entities={qi.get("resolved_entities")} entity_names={qi.get("entity_names")}')
        for x in rows[:3]:
            print(f'    {x.get("层级")}: {x.get("节点名称")} 上级={x.get("上级名称")}')
