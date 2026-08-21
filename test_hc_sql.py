import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

with contextlib.redirect_stdout(io.StringIO()):
    r = svc.ask(question='黄超的业绩', session_id='hc-sql', current_user=USER)
sql = r.get('sql') or ''
print('=== SQL（关键行）===')
for line in sql.split('\n'):
    s = line.strip()
    if not s: continue
    if any(k in s for k in ['WITH', 'SELECT', 'FROM', 'WHERE', 'COALESCE', 'GROUP', 'ORDER', 'LIMIT', 'UNION', 'ON ', 'END AS']):
        print(s[:160])

# 直接查 ds=62 数据库黄超的数据
print('\n=== 数据库直接查 ===')
from four_agent_ask import four_agent_ask_service
ds62 = svc.repository.get_dataset_by_id(62) if hasattr(svc.repository, 'get_dataset_by_id') else None
print('ds62 keys:', list((ds62 or {}).keys())[:10])

# 看 ds=62 节点索引里"黄超"所在层级
print('\n=== ds=62 节点层级 ===')
idx = svc._load_dataset_node_index()
for ds in idx.get('datasets') or []:
    if ds.get('dataset_id') == 62:
        for n in ds.get('nodes') or []:
            nm = n.get('node_name') or ''
            if '黄' in nm or nm in ['黄超','黄俊','黄蓉']:
                print(f'  {nm} aliases={n.get("aliases")}')
        # 看"业务代表"层级有几个节点
        rep_nodes = [n.get('node_name') for n in ds.get('nodes') or [] if isinstance(n,dict) and n.get('node_name','').strip() == n.get('node_name','').strip()]
        print(f'  ds=62 总节点数: {len(ds.get("nodes") or [])}')
