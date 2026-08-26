import sys, contextlib, io
sys.path.insert(0, '/app/backend')
for n in ['werkzeug','urllib3','requests','neo4j']:
    import logging; logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

q = '消费者事业部哪个分公司完成率最低'
with contextlib.redirect_stdout(io.StringIO()):
    r = svc.ask(question=q, session_id='probe-rlowest', current_user=USER)
for d in (r.get('dataset_results') or [])[:1]:
    rows = d.get('rows') or []
    print('row_count =', len(rows))
    for row in rows:
        print(' 层级=', row.get('层级'), '| 节点=', row.get('节点名称'), '| 上级=', row.get('上级名称'), '| 达成率=', row.get('达成率'))