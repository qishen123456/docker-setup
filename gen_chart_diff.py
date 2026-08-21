import sys, contextlib, io, json
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

for q in [
    ('电商', '电商的业绩'),
    ('电商', '电商事业部业绩'),
    ('电商', '看下电商业务部业绩'),
    ('商用', '商用的四个分公司'),
    ('商用', '商用事业部业绩'),
    ('商用', '西部分公司业绩'),
    ('消费', '消费者事业部整体业绩'),
    ('消费', '消费者城市分公司排名'),
    ('消费', '豫晋分公司业绩'),
]:
    tag, question = q
    with contextlib.redirect_stdout(io.StringIO()):
        r = svc.ask(question=question, session_id=f'chart-test-{tag}', current_user=USER)
    print(f'=== [{tag}] {question} ===')
    print(f'  requires_confirmation: {r.get("requires_confirmation")}')
    print(f'  route.dataset_ids: {r.get("route", {}).get("dataset_ids")}')
    for d in (r.get('dataset_results') or []):
        rs = d.get('report_spec') or {}
        charts = rs.get('charts') or []
        print(f'  ds={d.get("dataset_id")} name={d.get("dataset_name")} rows={len(d.get("rows") or [])}')
        print(f'    charts count={len(charts)}')
        for c in charts[:3]:
            ct = c.get('chartType')
            title = c.get('title','')[:40]
            rows = c.get('rows') or []
            print(f'      - {ct} "{title}" rows={len(rows)}')
        # 看 scope
        scope = rs.get('scope') or {}
        print(f'    scope.focusNodeIsLeaf={scope.get("focusNodeIsLeaf")}')
        print(f'    answerSummary.mode={rs.get("answerSummary",{}).get("mode")}')