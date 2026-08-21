import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

# 看后端实际给前端的 report_spec 完整结构
with contextlib.redirect_stdout(io.StringIO()):
    r = svc.ask(question='电商事业部业绩', session_id='chart-real', current_user=USER)
for d in (r.get('dataset_results') or []):
    if d.get('dataset_id') != 62:
        continue
    rs = d.get('report_spec') or {}
    print('--- 关键指标 KPI ---')
    for kpi in (rs.get('kpis') or []):
        print(f'  {kpi.get("label")}: {kpi.get("value")} ({kpi.get("valueText")})')
    print('--- sections ---')
    for sec in (rs.get('sections') or []):
        print(f'  title: {sec.get("title")} | mode: {sec.get("mode")} | rows: {len(sec.get("rows") or [])}')
    print('--- accordions ---')
    for acc in (rs.get('accordions') or []):
        rows = acc.get('rows') or []
        print(f'  title: {acc.get("title")} | rows: {len(rows)}')
    print('--- answerSummary ---')
    sm = rs.get('answerSummary') or {}
    print(f'  mode={sm.get("mode")} title={sm.get("title")}')
    print(f'  text={sm.get("text")[:100]}')
    print('--- scope ---')
    scope = rs.get('scope') or {}
    print(f'  focusNodeIsLeaf: {scope.get("focusNodeIsLeaf")}')
    print(f'  focusNodeName: {scope.get("focusNodeName")}')
    print(f'  targetLevel: {scope.get("targetLevel")}')
    print(f'  summaryNodes: {scope.get("summaryNodes") or scope.get("comparisonNodes")}')