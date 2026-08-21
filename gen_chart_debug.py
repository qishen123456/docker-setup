import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

with contextlib.redirect_stdout(io.StringIO()):
    r = svc.ask(question='电商事业部业绩', session_id='ds-debug', current_user=USER)
for d in (r.get('dataset_results') or []):
    if d.get('dataset_id') != 62:
        continue
    print(f'dataset_id={d.get("dataset_id")} dataset_name={d.get("dataset_name")}')
    print(f'rows={len(d.get("rows") or [])}')
    qi = d.get('query_intent', {})
    print(f'query_intent.intent={qi.get("intent")}')
    print(f'query_intent._level_overview={qi.get("_level_overview")}')
    print(f'query_intent.target_level={qi.get("target_level")}')
    rs = d.get('report_spec') or {}
    print(f'report_spec.charts count={len(rs.get("charts") or [])}')
    print(f'---')
    print(f'report_spec keys: {list(rs.keys())}')
    if rs.get('charts'):
        for c in rs['charts']:
            print(f'  chart: {c.get("chartType")} "{c.get("title")}" rows={len(c.get("rows") or [])}')
    # 看 raw row 字段
    rows = d.get('rows') or []
    if rows:
        print(f'first row keys: {list(rows[0].keys())[:20]}')
        print(f'first row: {rows[0]}')