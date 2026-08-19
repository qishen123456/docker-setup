import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

# 模拟前端传 selected_dataset_ids=[2] 强行沿用消费者
print('=== 测试：preferred_dataset_ids=[2]（前端沿用消费者），问"东部分公司业绩" ===')
with contextlib.redirect_stdout(io.StringIO()):
    r = svc.ask(question='东部分公司业绩', session_id='pref-1',
                preferred_dataset_ids=[2], current_user=USER)
print(f'  requires_confirmation: {r.get("requires_confirmation")}')
for d in (r.get('dataset_results') or []):
    rows=d.get('rows') or []
    print(f'  ds_id={d.get("dataset_id")} ds_name={d.get("dataset_name")} rows={len(rows)}')
    for x in rows[:3]:
        print(f'    {x.get("层级")}: {x.get("节点名称")}')

# 反向：ds=3 沿用，问消费者节点
print('\n=== 测试：preferred_dataset_ids=[3]（前端沿用商用），问"豫晋分公司业绩" ===')
with contextlib.redirect_stdout(io.StringIO()):
    r2 = svc.ask(question='豫晋分公司业绩', session_id='pref-2',
                 preferred_dataset_ids=[3], current_user=USER)
print(f'  requires_confirmation: {r2.get("requires_confirmation")}')
for d in (r2.get('dataset_results') or []):
    rows=d.get('rows') or []
    print(f'  ds_id={d.get("dataset_id")} ds_name={d.get("dataset_name")} rows={len(rows)}')
    for x in rows[:3]:
        print(f'    {x.get("层级")}: {x.get("节点名称")}')

# 兼容：ds=2 沿用，问 ds=2 内的节点（应保留）
print('\n=== 测试：preferred_dataset_ids=[2]（沿用消费者），问"豫晋分公司业绩"（ds=2 内的节点）===')
with contextlib.redirect_stdout(io.StringIO()):
    r3 = svc.ask(question='豫晋分公司业绩', session_id='pref-3',
                 preferred_dataset_ids=[2], current_user=USER)
print(f'  requires_confirmation: {r3.get("requires_confirmation")}')
for d in (r3.get('dataset_results') or []):
    rows=d.get('rows') or []
    print(f'  ds_id={d.get("dataset_id")} ds_name={d.get("dataset_name")} rows={len(rows)}')
    for x in rows[:3]:
        print(f'    {x.get("层级")}: {x.get("节点名称")}')

# 问 西部/南部/北部分公司（ds=3 内的节点），看是否正确沿用 ds=3
print('\n=== 测试：preferred_dataset_ids=[3]（沿用商用），问"西部分公司业绩"（ds=3 内的节点）===')
with contextlib.redirect_stdout(io.StringIO()):
    r4 = svc.ask(question='西部分公司业绩', session_id='pref-4',
                 preferred_dataset_ids=[3], current_user=USER)
for d in (r4.get('dataset_results') or []):
    rows=d.get('rows') or []
    print(f'  ds_id={d.get("dataset_id")} ds_name={d.get("dataset_name")} rows={len(rows)}')
    for x in rows[:3]:
        print(f'    {x.get("层级")}: {x.get("节点名称")}')
