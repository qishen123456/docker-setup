import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc

orig = svc._build_consumer_business_sql
def debug(self, nq, ctx):
    print(f'_build_consumer_business_sql: nq={nq!r} target_level={ctx.get("query_intent",{}).get("target_level")} _level_overview={ctx.get("query_intent",{}).get("_level_overview")}', flush=True)
    return orig(self, nq, ctx)
svc._build_consumer_business_sql = debug

USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}
with contextlib.redirect_stdout(io.StringIO()):
    r = svc.ask(question='消费者事业部整体业绩', session_id='trace-c', current_user=USER)
for d in (r.get('dataset_results') or []):
    print(f'  rows={len(d.get("rows") or [])}', flush=True)
