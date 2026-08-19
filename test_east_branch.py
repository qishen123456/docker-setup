import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}
SID='sct-mc'
svc.short_term_memory._items.pop(SID, None)

print('=== 第一轮：消费者业绩 ===')
with contextlib.redirect_stdout(io.StringIO()):
    r1 = svc.ask(question='消费者业绩', session_id=SID, current_user=USER)
for d in (r1.get('dataset_results') or []):
    print(f'  ds_id={d.get("dataset_id")}')

print('\n=== 第二轮：东部分公司业绩 ===')
with contextlib.redirect_stdout(io.StringIO()):
    r2 = svc.ask(question='东部分公司业绩', session_id=SID, current_user=USER)
for d in (r2.get('dataset_results') or []):
    print(f'  ds_id={d.get("dataset_id")} ds_name={d.get("dataset_name")} rows={len(d.get("rows") or [])}')
    qi = d.get('query_intent',{})
    print(f'  intent={qi.get("intent")} target_level={qi.get("target_level")}')
    print(f'  resolved_entities={qi.get("resolved_entities")} subject_name={qi.get("subject_name")}')
    print(f'  entity_names={qi.get("entity_names")} matched_nodes={qi.get("matched_nodes")}')

# 抓SQL
sql = r2.get('sql') or ''
print(f'\n--- SQL WHERE/层级/节点名称/上级名称 ---')
for line in sql.split('\n'):
    s = line.strip()
    if any(k in s for k in ['WHERE', '节点名称', '上级名称', '层级', 'ORDER BY', 'LIMIT']) and 'CASE' not in s and 'END AS' not in s:
        print(s[:160])
print(f'\n--- rows 前 3 ---')
for d in (r2.get('dataset_results') or []):
    for x in (d.get('rows') or [])[:3]:
        print(f'  {x.get("层级")}: {x.get("节点名称")} 上级={x.get("上级名称")}')

# 第二轮问法换成"东部分公司的业绩咋样"（与截图一致）
print('\n=== 第二轮（截图问法）：东部分公司的业绩咋样 ===')
SID2='sct-mc2'
svc.short_term_memory._items.pop(SID2, None)
with contextlib.redirect_stdout(io.StringIO()):
    r1b = svc.ask(question='消费者业绩', session_id=SID2, current_user=USER)
with contextlib.redirect_stdout(io.StringIO()):
    r2b = svc.ask(question='东部分公司的业绩咋样', session_id=SID2, current_user=USER)
for d in (r2b.get('dataset_results') or []):
    print(f'  ds_id={d.get("dataset_id")} ds_name={d.get("dataset_name")} rows={len(d.get("rows") or [])}')
    qi = d.get('query_intent',{})
    print(f'  intent={qi.get("intent")} target_level={qi.get("target_level")} subject_name={qi.get("subject_name")}')
    print(f'  resolved_entities={qi.get("resolved_entities")} entity_names={qi.get("entity_names")}')
    for x in (d.get('rows') or [])[:5]:
        print(f'    {x.get("层级")}: {x.get("节点名称")} 上级={x.get("上级名称")}')
