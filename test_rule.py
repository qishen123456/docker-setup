import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc

orig = svc._build_rule_based_sql
def debug(self, question, context):
    res = orig(self, question, context)
    print(f'=== _build_rule_based_sql("{question[:30]}...")')
    ds = context.get('dataset') or {}
    print(f'  dataset={ds.get("dataset_name")} code={ds.get("dataset_code")}')
    print(f'  result len={len(res) if res else 0}, preview={res[:150] if res else ""}')
    return res
svc._build_rule_based_sql = debug

USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}
import sys; sys.stdout = sys.stderr
print('===== 消费者整体 =====', flush=True)
with contextlib.redirect_stdout(io.StringIO()):
    r = svc.ask(question='消费者事业部整体业绩', session_id='dbg-r', current_user=USER)
sys.stdout = sys.__stdout__
for d in (r.get('dataset_results') or []):
    rows=d.get('rows') or []
    print(f'  -> rows={len(rows)}', flush=True)
