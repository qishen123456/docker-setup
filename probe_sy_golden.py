import sys, contextlib, io, json
sys.path.insert(0, '/app/backend')
for n in ['werkzeug','urllib3','requests','neo4j']:
    import logging; logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

q = '商用事业部整体达成率是多少'
with contextlib.redirect_stdout(io.StringIO()):
    r = svc.ask(question=q, session_id='probe-sy-golden', current_user=USER)

print('=== route ===')
print(json.dumps(r.get('route') or {}, ensure_ascii=False, indent=2)[:2500])

print('\n=== report_debug keys ===')
rd = r.get('report_debug') or {}
print('keys:', list(rd.keys()) if isinstance(rd, dict) else type(rd))

print('\n=== sql ===')
sql = r.get('sql') or ''
print('len=', len(sql))
print(sql[:3000])

print('\n=== row_count ===')
print('row_count=', r.get('row_count'))

print('\n=== steps (sample strategy trace) ===')
steps = r.get('steps') or []
for s in steps:
    if isinstance(s, dict):
        title = s.get('title') or s.get('step') or ''
        if any(t in str(title) for t in ['golden','sample','模板','样本','rule']):
            print('-- step --', title)
            print(json.dumps(s, ensure_ascii=False, indent=2)[:1200])