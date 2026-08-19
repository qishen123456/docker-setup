import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

# 第一轮：消费者业绩
print('=== 第一轮：消费者业绩 ===')
with contextlib.redirect_stdout(io.StringIO()):
    r1 = svc.ask(question='消费者业绩', session_id='mc-1', current_user=USER)
for d in (r1.get('dataset_results') or []):
    print(f'  ds_id={d.get("dataset_id")} ds_name={d.get("dataset_name")} rows={len(d.get("rows") or [])}')
    qi = d.get('query_intent',{})
    print(f'  intent={qi.get("intent")} target_level={qi.get("target_level")}')
    print(f'  route_dataset_ids={r1.get("route",{}).get("dataset_ids") if isinstance(r1.get("route"),dict) else "?"}')

# 第二轮：东部分公司业绩（应该继续消费者）
print('\n=== 第二轮：东部分公司业绩 ===')
with contextlib.redirect_stdout(io.StringIO()):
    r2 = svc.ask(question='东部分公司业绩', session_id='mc-1', current_user=USER,
                  conversation_history=[
                    {'role':'user','content':'消费者业绩'},
                    {'role':'assistant','content':f'已查询 {len(r1.get("dataset_results") or [])} 个数据集', 'metadata':{'dataset_id': (r1.get('dataset_results') or [{}])[0].get('dataset_id') if r1.get('dataset_results') else None}},
                  ])
print('  requires_confirmation:', r2.get('requires_confirmation'))
print('  error:', r2.get('error'))
for d in (r2.get('dataset_results') or []):
    print(f'  ds_id={d.get("dataset_id")} ds_name={d.get("dataset_name")} rows={len(d.get("rows") or [])}')
    qi = d.get('query_intent',{})
    print(f'  intent={qi.get("intent")} target_level={qi.get("target_level")} matched_nodes={qi.get("matched_nodes")}')

# 同时测：直接问「东部分公司业绩」（无上下文）
print('\n=== 直接问（无上下文）：东部分公司业绩 ===')
with contextlib.redirect_stdout(io.StringIO()):
    r3 = svc.ask(question='东部分公司业绩', session_id='mc-2', current_user=USER)
print('  requires_confirmation:', r3.get('requires_confirmation'))
opts = r3.get('confirmation_options') or []
print('  options:', [(o.get('label'), o.get('dataset_ids')) for o in opts])
for d in (r3.get('dataset_results') or []):
    print(f'  ds_id={d.get("dataset_id")} ds_name={d.get("dataset_name")} rows={len(d.get("rows") or [])}')
