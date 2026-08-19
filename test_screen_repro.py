import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

# 模拟 session：和截图一样
SID='real-screen-1'
svc.short_term_memory._items.pop(SID, None)

print('=== 第一轮：消费者业绩 ===')
with contextlib.redirect_stdout(io.StringIO()):
    r1 = svc.ask(question='消费者业绩', session_id=SID, current_user=USER)
for d in (r1.get('dataset_results') or []):
    print(f'  ds_id={d.get("dataset_id")} refined_query={r1.get("route",{}).get("refined_query") if isinstance(r1.get("route"),dict) else "?"}')

# 看 session 缓存里到底是什么
import json
mem = svc.short_term_memory.get(SID) or []
print(f'\n--- session 缓存 ({len(mem)} items) ---')
for it in mem:
    print(json.dumps(it, ensure_ascii=False, default=str)[:400])

# 第二轮用截图问法
print('\n=== 第二轮（截图原问法）：东部分公司的业绩咋样了 ===')
with contextlib.redirect_stdout(io.StringIO()):
    r2 = svc.ask(question='东部分公司的业绩咋样了', session_id=SID, current_user=USER)
print(f'  requires_confirmation: {r2.get("requires_confirmation")}')
print(f'  error: {r2.get("error")}')
print(f'  options: {[(o.get("label"), o.get("dataset_ids")) for o in (r2.get("confirmation_options") or [])]}')
for d in (r2.get('dataset_results') or []):
    print(f'  ds_id={d.get("dataset_id")} ds_name={d.get("dataset_name")} rows={len(d.get("rows") or [])}')
    qi = d.get('query_intent',{})
    print(f'  intent={qi.get("intent")} target_level={qi.get("target_level")} subject_name={qi.get("subject_name")}')
    print(f'  resolved_entities={qi.get("resolved_entities")} entity_names={qi.get("entity_names")}')
    print(f'  row0={d.get("rows",[{}])[0] if d.get("rows") else "?"}')
print(f'  route.dataset_ids: {r2.get("route",{}).get("dataset_ids") if isinstance(r2.get("route"),dict) else "?"}')
