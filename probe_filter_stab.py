import sys, contextlib, io
sys.path.insert(0, '/app/backend')
for n in ['werkzeug','urllib3','requests','neo4j']:
    import logging; logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

# ============ Q2 稳定性: 连跑 4 次 ============
print('#' * 60)
print('# Q2 稳定性测试: 没有业绩的业务代表有哪些（开单金额=0）x4')
print('#' * 60)
q2 = '没有业绩的业务代表有哪些（开单金额=0）'
for i in range(4):
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            r = svc.ask(question=q2, session_id=f'probe-q2-stab-{i}', current_user=USER)
        rows_total = sum(len(d.get('rows') or []) for d in (r.get('dataset_results') or []))
        # 检查 SQL 是否断裂（断裂标志：summarized_nodes 后直接跟 SELECT *）
        sql = str((r.get('dataset_results') or [{}])[0].get('sql') or '')
        broken = 'FROM summarized_nodes\nSELECT *' in sql or 'FROM summarized_nodes\n\nSELECT *' in sql
        # 找 sql 来源
        ds0 = (r.get('dataset_results') or [{}])[0]
        mode = (ds0.get('query_intent') or {}).get('intent')
        print(f'run{i+1}: rows={rows_total} | intent={mode} | sql_len={len(sql)} | broken={broken}')
    except Exception as e:
        print(f'run{i+1}: EXCEPTION {repr(e)[:100]}')

# ============ Q1 confirm 完整流重跑 ============
print()
print('#' * 60)
print('# Q1 完整流重跑: 开单金额低于500万的业务员有哪些 → confirm 选商用')
print('#' * 60)
q1 = '开单金额低于500万的业务员有哪些'
with contextlib.redirect_stdout(io.StringIO()):
    r = svc.ask(question=q1, session_id='probe-q1-stab', current_user=USER)
route = r.get('route') or {}
print('requires_confirmation =', r.get('requires_confirmation'))
if r.get('requires_confirmation'):
    options = route.get('confirmation_options') or []
    target = None
    for o in options:
        if o.get('dataset_ids') == [3]:
            target = o.get('id') or o.get('option_id')
    print('confirm option:', target)
    with contextlib.redirect_stdout(io.StringIO()):
        r2 = svc.confirm_by_boss(
            session_id='probe-q1-stab',
            selected_option='商用事业部',
            selected_dataset_ids=[3],
            option_id=target or 'arbiter_dataset_3',
            current_user=USER,
        )
    if r2:
        ds = (r2.get('dataset_results') or [])
        rows_total = sum(len(d.get('rows') or []) for d in ds)
        print('after confirm rows_total =', rows_total)
        for d in ds[:1]:
            rows = d.get('rows') or []
            qi = d.get('query_intent') or {}
            print('  intent =', qi.get('intent'), '| target_level =', qi.get('target_level'))
            print('  filter =', qi.get('filter_metric_column'), qi.get('filter_operator'), qi.get('filter_value'))
            sql = str(d.get('sql') or '')
            print('  sql_len =', len(sql))
            print('  sql tail 400:')
            print(' ', sql[-400:])
            for row in rows[:5]:
                print('   ', row.get('层级'), '|', row.get('节点名称'), '| 开单 =', row.get('年度开单金额'))
        print('  analysis:', str(r2.get('analysis') or '')[:200])
        print('  error:', str(r2.get('error') or '')[:200])