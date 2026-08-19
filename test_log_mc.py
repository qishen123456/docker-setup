import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}
SID = 'log-mc'

# 看 short_term_memory 内容
print('=== short_term_memory 状态 ===')
for k, v in svc.short_term_memory._items.items():
    print(f'  {k}: {str(v)[:200]}')
print()

svc.short_term_memory._items.pop(SID, None)
print(f'=== 第一轮：消费者业绩 (session={SID}) ===')
with contextlib.redirect_stdout(io.StringIO()):
    r1 = svc.ask(question='消费者业绩', session_id=SID, current_user=USER)
for d in (r1.get('dataset_results') or []):
    print(f'  ds_id={d.get("dataset_id")} rows={len(d.get("rows") or [])}')

print(f'\n--- short_term_memory AFTER 第一轮 ---')
for k, v in svc.short_term_memory._items.items():
    print(f'  {k}: {str(v)[:300]}')

print(f'\n=== 第二轮：东部分公司业绩 (session={SID}) ===')
with contextlib.redirect_stdout(io.StringIO()):
    r2 = svc.ask(question='东部分公司业绩', session_id=SID, current_user=USER)
print(f'  requires_confirmation: {r2.get("requires_confirmation")}')
print(f'  options: {[(o.get("label"), o.get("dataset_ids")) for o in (r2.get("confirmation_options") or [])]}')
for d in (r2.get('dataset_results') or []):
    print(f'  ds_id={d.get("dataset_id")} ds_name={d.get("dataset_name")} rows={len(d.get("rows") or [])}')
    qi = d.get('query_intent',{})
    print(f'  intent={qi.get("intent")} target_level={qi.get("target_level")}')
    print(f'  resolved_entities={qi.get("resolved_entities") or qi.get("entity_names")}')
    if d.get('rows'):
        for x in d['rows'][:3]:
            print(f'    {x.get("层级")}: {x.get("节点名称")} 上级={x.get("上级名称")}')

print(f'\n--- short_term_memory AFTER 第二轮 ---')
for k, v in svc.short_term_memory._items.items():
    print(f'  {k}: {str(v)[:300]}')
