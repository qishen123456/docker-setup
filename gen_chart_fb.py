"""模拟前端 getDatasetChartSpecs 行为"""
import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

# 直接调用四个数据集的"普通业绩"问法，看前端推断会怎么生成
test_cases = [
    ('电商', '电商事业部业绩'),
    ('商用', '商用的四个分公司'),
    ('商用', '商用事业部业绩'),
    ('消费', '消费者事业部整体业绩'),
    ('消费', '消费者城市分公司排名'),
]
for tag, q in test_cases:
    print(f'=== [{tag}] {q} ===')
    with contextlib.redirect_stdout(io.StringIO()):
        r = svc.ask(question=q, session_id=f'chart-fb-{tag}', current_user=USER)
    for d in (r.get('dataset_results') or []):
        ds_id = d.get('dataset_id')
        rows = d.get('rows') or []
        rs = d.get('report_spec') or {}
        backend_charts = rs.get('charts') or []
        scope = rs.get('scope') or {}
        print(f'  ds={ds_id} rows={len(rows)} focusNodeName={scope.get("focusNodeName")} targetLevel={scope.get("targetLevel")}')
        print(f'  后端 charts 数={len(backend_charts)}')
        for c in backend_charts:
            print(f'    - {c.get("chartType")} "{c.get("title")}" rows={len(c.get("rows") or [])}')
        # 模拟前端 fallback：rows=3 时，inferChartSpec 走到 numericColumns.length > 0 分支
        # rows=1 → metric；rows>6 → bar；否则 bar with columns
        # 业务部行有 4-5 个数值列：总任务/年度开单/达成率/剩余任务
        if not backend_charts:
            # 前端 fallback 会走 inferChartSpec
            print(f'  前端 fallback 推断路径：')
            print(f'    - rows.length > 6? {len(rows) > 6}')
            print(f'    - rows.length === 1? {len(rows) == 1}')
            # 看 columns
            cols = d.get('columns') or list((rows[0] if rows else {}).keys())
            num_cols = [c for c in cols if isinstance((rows[0] if rows else {}).get(c), (int, float))]
            print(f'    - 数值列数={len(num_cols)}: {num_cols[:4]}')