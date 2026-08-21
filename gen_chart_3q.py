import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

for q in ['电商事业部业绩', '电商事业部总体业绩', '电商事业部整体业绩']:
    print(f'=== {q} ===')
    with contextlib.redirect_stdout(io.StringIO()):
        r = svc.ask(question=q, session_id=f'ds-{q}', current_user=USER)
    for d in (r.get('dataset_results') or []):
        if d.get('dataset_id') != 62:
            continue
        rows = d.get('rows') or []
        print(f'rows={len(rows)}')
        for row in rows:
            print(f'  层级={row.get("层级")} 节点={row.get("节点名称")} 上级={row.get("上级名称")}')
        # 看 SQL WHERE
        sql = d.get('sql') or ''
        for line in sql.split('\n'):
            s = line.strip()
            if 'WHERE' in s.upper() or 'LIMIT' in s.upper() or '层级' in s:
                print(f'  SQL: {s}')