import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc

# Monkey-patch _assemble_generic_sql 来截获
orig = svc._assemble_generic_sql
def debug(self, *a, **kw):
    context = a[0] if a else kw.get('context', {})
    query_intent = a[1] if len(a) > 1 else kw.get('query_intent', {})
    # 在 _assemble_generic_sql 入口打印关键参数
    import json
    print('--- _assemble_generic_sql ---')
    print('entity_names:', json.dumps((query_intent.get('entity_names') or []), ensure_ascii=False))
    print('intent:', query_intent.get('intent'))
    print('target_level:', query_intent.get('target_level'))
    print('subject_name:', query_intent.get('subject_name'))
    return orig(self, *a, **kw)
svc._assemble_generic_sql = debug

USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}
print('===== 消费者整体 =====')
with contextlib.redirect_stdout(io.StringIO()):
    r = svc.ask(question='消费者事业部整体业绩', session_id='dbg-c', current_user=USER)
for d in (r.get('dataset_results') or []):
    rows=d.get('rows') or []
    print(f'rows={len(rows)}')
