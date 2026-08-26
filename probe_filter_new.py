import sys, contextlib, io, json
sys.path.insert(0, '/app/backend')
for n in ['werkzeug','urllib3','requests','neo4j']:
    import logging; logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

QUESTIONS = [
    '开单金额低于500万的业务员有哪些',
    '没有业绩的业务代表有哪些（开单金额=0）',
]

for q in QUESTIONS:
    print('=' * 70)
    print('Q:', q)
    print('=' * 70)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            r = svc.ask(question=q, session_id='probe-filter-'+q[:8], current_user=USER)
    except Exception as e:
        print('EXCEPTION:', repr(e))
        continue

    route = r.get('route') or {}
    print('route.dataset_ids =', route.get('dataset_ids'))
    print('route.decision =', route.get('decision'), '| arbiter_reason =', route.get('arbiter_reason'))
    print('requires_confirmation =', r.get('requires_confirmation'))
    if r.get('requires_confirmation'):
        opts = route.get('confirmation_options') or []
        for i, o in enumerate(opts[:5]):
            print(f'  option[{i}]:', o.get('label'), '| dataset_ids =', o.get('dataset_ids'))
        print('  (走 confirm 流，需选择后重测)')
        continue

    ds = (r.get('dataset_results') or [])
    print('dataset_results count =', len(ds))
    for d in ds[:2]:
        rows = d.get('rows') or []
        print(f'--- dataset id={d.get("id")} name={d.get("name")} rows={len(rows)}')
        cols = d.get('columns') or []
        print('    columns =', cols[:10])
        qi = d.get('query_intent') or {}
        print('    intent =', qi.get('intent'), '| target_level =', qi.get('target_level'))
        print('    filter_metric =', qi.get('filter_metric_key'), qi.get('filter_metric_column'),
              '| op =', qi.get('filter_operator'), '| value =', qi.get('filter_value'))
        sql = str(d.get('sql') or '')
        # 抽取 WHERE 部分
        import re as _re
        wh = _re.findall(r'WHERE.*?(?:ORDER|GROUP|LIMIT|$)', sql, _re.S)
        if wh:
            print('    WHERE (first 400 chars):', ' '.join(wh[0].split())[:400])
        if rows:
            for row in rows[:3]:
                print('    row sample:', {k: row.get(k) for k in list(cols)[:8] if k in row})
    print()