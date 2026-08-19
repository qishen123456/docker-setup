import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

print('===== 消费者 =====')
with contextlib.redirect_stdout(io.StringIO()):
    r = svc.ask(question='消费者事业部整体业绩', session_id='sql-c', current_user=USER)
sql = r.get('sql') or ''
# 找所有包含 层级 / 节点名称 / 上级名称 / WHERE / UNION 的行
for line in sql.split('\n'):
    s = line.strip()
    if not s: continue
    if any(k in s for k in ['层级','节点名称','上级名称','WHERE','UNION','WITH','SELECT']) :
        print(s[:140])

print('\n===== 商用 =====')
with contextlib.redirect_stdout(io.StringIO()):
    r = svc.ask(question='商用事业部整体业绩', session_id='sql-s', current_user=USER)
sql = r.get('sql') or ''
for line in sql.split('\n'):
    s = line.strip()
    if not s: continue
    if any(k in s for k in ['层级','节点名称','上级名称','WHERE','UNION','WITH','SELECT']) :
        print(s[:140])
