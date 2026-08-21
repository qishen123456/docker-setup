"""消费者全问法图表实测"""
import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

cases = [
    ('消费整体业绩', '消费者事业部整体业绩'),
    ('消费业绩', '消费者业绩'),
    ('消费事业部业绩', '消费者事业部业绩'),
    ('消费城市分公司业绩', '消费者城市分公司的业绩'),
    ('消费城市分公司排名', '消费者城市分公司排名'),
    ('消费分公司业绩', '消费者分公司的业绩'),
    ('消费分公司业绩排名', '消费者分公司业绩排名'),
    ('消费业务部业绩', '消费者业务部业绩'),
    ('消费业务部业绩排名', '消费者业务部业绩排名'),
    ('消费每个分公司业绩', '消费每个分公司的业绩'),
    ('豫晋分公司业绩', '豫晋分公司业绩'),
    ('河北分公司业绩', '河北分公司业绩'),
    ('低于10%的城市分公司', '低于10%的城市分公司'),
    ('消费前3分公司', '消费者前3的分公司'),
]
for tag, question in cases:
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            r = svc.ask(question=question, session_id=f'c-{tag}', current_user=USER)
    except Exception as e:
        print(f'\n=== {question} === EXC {e}')
        continue
    print(f'\n=== {question} ===')
    for d in (r.get('dataset_results') or []):
        if d.get('dataset_id') != 2:
            continue
        try:
            rs = d.get('report_spec') or {}
            backend_charts = rs.get('charts') or []
            rows = d.get('rows') or []
            scope = rs.get('scope') or {}
            sm = rs.get('answerSummary') or {}
            print(f'  rows={len(rows)} focusNode={scope.get("focusNodeName")} mode={sm.get("mode")}', flush=True)
            print(f'  后端 charts={len(backend_charts)}', end='')
            if backend_charts:
                for c in backend_charts:
                    print(f' [{c.get("chartType")} "{c.get("title")}" rows={len(c.get("rows") or [])}]', end='')
            print(flush=True)
            if not backend_charts and rows:
                cols = d.get('columns') or list(rows[0].keys() if rows else [])
                num = [c for c in cols if isinstance(rows[0].get(c), (int, float))]
                print(f'  fallback：rows={len(rows)} 数值列数={len(num)}', flush=True)
        except Exception as e:
            print(f'  EXC: {e}', flush=True)