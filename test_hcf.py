import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

for q in ['黄超的业绩', '黄超业绩', '黄超业绩如何', '黄超业绩咋样', '黄超的业绩如何']:
    with contextlib.redirect_stdout(io.StringIO()):
        r = svc.ask(question=q, session_id=f'hcf-{q}', current_user=USER)
    print(f'\n=== {q} ===')
    for d in (r.get('dataset_results') or []):
        rows=d.get('rows') or []
        print(f'  ds_id={d.get("dataset_id")} rows={len(rows)}')
        for x in rows[:3]:
            print(f'    {x.get("层级")}: {x.get("节点名称")} 上级={x.get("上级名称")} 负责人={x.get("负责人")}')
            print(f'    总任务={x.get("总任务金额")} 实际={x.get("年度开单金额")} 达成率={x.get("达成率")}')
