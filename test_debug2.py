import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc

# Monkey-patch _build_consumer_business_sql to inspect entity_names and where the scope_filter comes from
orig = svc._build_consumer_business_sql
def debug(self, normalized_question, context):
    # 看上游状态
    qi = context.get('query_intent') or {}
    resolved = list(self._resolved_entity_names(context) or [])
    print('--- _build_consumer_business_sql ---', normalized_question)
    print('  resolved_entity_names:', resolved)
    print('  query_intent.target_level:', qi.get('target_level'))
    print('  query_intent.intent:', qi.get('intent'))
    print('  query_intent._level_overview:', qi.get('_level_overview'))
    print('  query_intent.subject_name:', qi.get('subject_name'))
    return orig(self, normalized_question, context)
svc._build_consumer_business_sql = debug

USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}
with contextlib.redirect_stdout(io.StringIO()):
    r = svc.ask(question='消费者事业部整体业绩', session_id='dbg-c2', current_user=USER)
for d in (r.get('dataset_results') or []):
    rows=d.get('rows') or []
    print(f'  -> rows={len(rows)}')
