import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}
SID = 'real-mc-1'
# 清空 session
svc.short_term_memory._items.pop(SID, None)
svc.short_term_memory._items.pop(SID+'-2', None)
svc.short_term_memory._items.pop('mc-1', None)
svc.short_term_memory._items.pop('mc-2', None)

print('=== 第一轮：消费者业绩 ===')
with contextlib.redirect_stdout(io.StringIO()):
    r1 = svc.ask(question='消费者业绩', session_id=SID, current_user=USER)
for d in (r1.get('dataset_results') or []):
    print(f'  ds_id={d.get("dataset_id")} ds_name={d.get("dataset_name")} rows={len(d.get("rows") or [])}')

print('\n=== 第二轮：东部分公司业绩（同 session，复用 session 记忆）===')
with contextlib.redirect_stdout(io.StringIO()):
    r2 = svc.ask(question='东部分公司业绩', session_id=SID, current_user=USER)
print('  requires_confirmation:', r2.get('requires_confirmation'))
for d in (r2.get('dataset_results') or []):
    print(f'  ds_id={d.get("dataset_id")} ds_name={d.get("dataset_name")} rows={len(d.get("rows") or [])}')
    print(f'  intent={d.get("query_intent",{}).get("intent")} target_level={d.get("query_intent",{}).get("target_level")}')
    if d.get('rows'):
        for x in d['rows'][:3]:
            print(f'    {x.get("层级")}: {x.get("节点名称")} 上级={x.get("上级名称")}')
print('  route.dataset_ids:', r2.get('route',{}).get('dataset_ids') if isinstance(r2.get('route'),dict) else '?')
