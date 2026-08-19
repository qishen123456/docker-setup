import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

# 场景 A：第一轮商用，第二轮东部分公司
for sid, q1 in [('A1', '商用业绩'), ('A2', '商用事业部业绩'), ('A3', '电商业绩')]:
    svc.short_term_memory._items.pop(sid, None)
    print(f'\n========== session {sid}: 第一轮={q1} ==========')
    with contextlib.redirect_stdout(io.StringIO()):
        r1 = svc.ask(question=q1, session_id=sid, current_user=USER)
    for d in (r1.get('dataset_results') or []):
        print(f'  第一轮: ds_id={d.get("dataset_id")} ds_name={d.get("dataset_name")}')

    print(f'  --- 第二轮: 东部分公司业绩 ---')
    with contextlib.redirect_stdout(io.StringIO()):
        r2 = svc.ask(question='东部分公司业绩', session_id=sid, current_user=USER)
    print(f'  requires_confirmation: {r2.get("requires_confirmation")}')
    print(f'  options: {[(o.get("label"), o.get("dataset_ids")) for o in (r2.get("confirmation_options") or [])]}')
    for d in (r2.get('dataset_results') or []):
        print(f'  第二轮: ds_id={d.get("dataset_id")} ds_name={d.get("dataset_name")} rows={len(d.get("rows") or [])}')
