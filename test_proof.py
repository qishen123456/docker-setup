import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

scenarios = [
    ('S1', '消费者业绩', '东部分公司业绩'),
    ('S2', '消费者业绩', '东部分公司的业绩咋样'),
    ('S3', '消费者业绩', '东部分公司的业绩'),
    ('S4', '消费者事业部业绩', '东部分公司业绩'),
    ('S5', '电商业绩', '东部分公司业绩'),
    ('S6', '商用业绩', '东部分公司业绩'),
]
for sid, q1, q2 in scenarios:
    svc.short_term_memory._items.pop(sid, None)
    with contextlib.redirect_stdout(io.StringIO()):
        svc.ask(question=q1, session_id=sid, current_user=USER)
    with contextlib.redirect_stdout(io.StringIO()):
        r2 = svc.ask(question=q2, session_id=sid, current_user=USER)
    for d in (r2.get('dataset_results') or []):
        rows = d.get('rows') or []
        lv = {}
        for x in rows: lv[x.get('层级') or '?'] = lv.get(x.get('层级') or '?', 0) + 1
        names = [x.get('节点名称') for x in rows[:6]]
        qi = d.get('query_intent',{})
        print(f'  [{sid}] 第一轮={q1!r} → 第二轮={q2!r}')
        print(f'    -> ds_id={d.get("dataset_id")} ds_name={d.get("dataset_name")} intent={qi.get("intent")} target_level={qi.get("target_level")}')
        print(f'    -> rows={len(rows)} 层级分布={lv} 节点前6={names}')
