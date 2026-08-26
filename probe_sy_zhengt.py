import sys, contextlib, io, json
sys.path.insert(0, '/app/backend')
for n in ['werkzeug','urllib3','requests','neo4j']:
    import logging; logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

q = '商用事业部整体达成率是多少'
with contextlib.redirect_stdout(io.StringIO()):
    r = svc.ask(question=q, session_id='probe-sy-zhengt', current_user=USER)
print('=== Q ===', q)
print('=== top-level keys ===', list(r.keys()))
for d in (r.get('dataset_results') or []):
    print('\n--- dataset ---')
    print('id=', d.get('id'), 'name=', d.get('name'), 'rows=', len(d.get('rows') or []))
    cols = d.get('columns') or []
    print('columns=', cols)
    rows = d.get('rows') or []
    for row in rows[:8]:
        print('  row:', {k: row.get(k) for k in cols if k in row})
    qi = d.get('query_intent') or {}
    print('intent=', qi.get('intent'), 'target_level=', qi.get('target_level'), '_level_overview=', qi.get('_level_overview'))
    print('_multi_parent=', qi.get('_multi_parent'), 'top_n=', qi.get('top_n'), 'sort_metric=', qi.get('sort_metric_key') or qi.get('sort_metric_column'))
    rs = d.get('report_spec') or {}
    print('report_spec.scope=', rs.get('scope'))
    print('report_spec.answerMode=', rs.get('answerMode'), 'answerSummary=', rs.get('answerSummary'))
    print('report_spec.kpis (count=', len(rs.get('kpis') or []), '):')
    for kpi in (rs.get('kpis') or [])[:8]:
        print('  kpi:', kpi)
    print('report_spec.charts (count=', len(rs.get('charts') or []), '):')
    for ch in (rs.get('charts') or [])[:3]:
        print('  chart:', {k: ch.get(k) for k in ['chartType','title','columns','sortColumn']})
        print('    rows=', (ch.get('rows') or [])[:5])