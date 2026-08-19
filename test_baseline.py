import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}
for q in ['消费者事业部整体业绩','消费者事业部业绩','商用事业部整体业绩','商用事业部业绩']:
    with contextlib.redirect_stdout(io.StringIO()):
        r = svc.ask(question=q, session_id='bl-'+q, current_user=USER)
    print(f'=== {q} ===')
    for d in (r.get('dataset_results') or []):
        rows=d.get('rows') or []
        lv={}
        for x in rows: lv[x.get('层级') or '?']=lv.get(x.get('层级') or '?',0)+1
        qi=d.get('query_intent',{})
        print(f'rows={len(rows)} intent={qi.get("intent")} _level_overview={qi.get("_level_overview")} target_level={qi.get("target_level")} 层级={lv}')
