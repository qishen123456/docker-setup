import sys, contextlib, io
sys.path.insert(0, '/app/backend')
for n in ['werkzeug','urllib3','requests','neo4j']:
    import logging; logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

q1 = '开单金额低于500万的业务员有哪些'
print('#' * 60)
print('# Q1 正确 confirm 流（用返回的 session_id）')
print('#' * 60)
with contextlib.redirect_stdout(io.StringIO()):
    r = svc.ask(question=q1, session_id='probe-q1-v2', current_user=USER)
print('ask: requires_confirmation =', r.get('requires_confirmation'))
print('ask: session_id(token) =', r.get('session_id'))
token = r.get('session_id') or ''
options = (r.get('route') or {}).get('confirmation_options') or []
target = ''
for o in options:
    if o.get('dataset_ids') == [3]:
        target = o.get('id') or o.get('option_id') or ''
        print('option:', target, '|', o.get('label'))
if token and target:
    with contextlib.redirect_stdout(io.StringIO()):
        r2 = svc.confirm_by_boss(
            session_id=token,
            selected_option='商用事业部',
            selected_dataset_ids=[3],
            option_id=target,
            current_user=USER,
        )
    ds = (r2.get('dataset_results') or [])
    rows_total = sum(len(d.get('rows') or []) for d in ds)
    print('confirm 后 rows_total =', rows_total)
    print('error =', str(r2.get('error') or '')[:150])
    for d in ds[:1]:
        rows = d.get('rows') or []
        qi = d.get('query_intent') or {}
        print('  intent =', qi.get('intent'), '| target_level =', qi.get('target_level'))
        print('  filter =', qi.get('filter_metric_column'), qi.get('filter_operator'), qi.get('filter_value'), qi.get('filter_unit'))
        sql = str(d.get('sql') or '')
        print('  sql_len =', len(sql))
        # 外层 WHERE
        import re as _re
        m = _re.search(r'WHERE[^\n]*$', sql)
        tail = sql[-500:]
        print('  sql tail:', ' '.join(tail.split())[:350])
        for row in rows[:6]:
            print('   ', row.get('层级'), '|', row.get('节点名称'), '| 开单 =', row.get('年度开单金额'), '| 任务 =', row.get('总任务金额'))
    print('  analysis:', str(r2.get('analysis') or '')[:250])
else:
    print('token/target missing, cannot confirm')