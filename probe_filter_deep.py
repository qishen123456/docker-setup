import sys, contextlib, io, json
sys.path.insert(0, '/app/backend')
for n in ['werkzeug','urllib3','requests','neo4j']:
    import logging; logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

# ============ Q1: 走 confirm 选商用 ============
print('#' * 70)
print('# Q1 confirm 流: 开单金额低于500万的业务员有哪些 → 选商用[3]')
print('#' * 70)
q1 = '开单金额低于500万的业务员有哪些'
with contextlib.redirect_stdout(io.StringIO()):
    r = svc.ask(question=q1, session_id='probe-q1-confirm', current_user=USER)
route = r.get('route') or {}
if r.get('requires_confirmation'):
    # 模拟选商用
    confirm_token = route.get('confirmation_token') or r.get('confirmation_token')
    options = route.get('confirmation_options') or []
    target = None
    for o in options:
        if o.get('dataset_ids') == [3]:
            target = o.get('id') or o.get('option_id')
            break
    print('confirm option selected:', target)
    with contextlib.redirect_stdout(io.StringIO()):
        r2 = svc.confirm_by_boss(
            session_id='probe-q1-confirm',
            selected_option='商用事业部',
            selected_dataset_ids=[3],
            option_id=target,
            current_user=USER,
        )
    if r2:
        ds = (r2.get('dataset_results') or [])
        print('after confirm: rows total =', sum(len(d.get('rows') or []) for d in ds))
        for d in ds[:1]:
            rows = d.get('rows') or []
            qi = d.get('query_intent') or {}
            print('  intent =', qi.get('intent'), '| target_level =', qi.get('target_level'))
            print('  filter =', qi.get('filter_metric_column'), qi.get('filter_operator'), qi.get('filter_value'))
            print('  rows =', len(rows))
            for row in rows[:5]:
                print('   ', row.get('层级'), '|', row.get('节点名称'), '| 开单 =', row.get('年度开单金额'), '| 任务 =', row.get('总任务金额'))
        print('  analysis head:', str(r2.get('analysis') or '')[:300])
    else:
        print('confirm_by_boss not available or returned None')

# ============ Q2: 完整 SQL + 数据校验 ============
print()
print('#' * 70)
print('# Q2 完整诊断: 没有业绩的业务代表有哪些（开单金额=0）')
print('#' * 70)
q2 = '没有业绩的业务代表有哪些（开单金额=0）'
with contextlib.redirect_stdout(io.StringIO()):
    r3 = svc.ask(question=q2, session_id='probe-q2-full', current_user=USER)
for d in (r3.get('dataset_results') or [])[:1]:
    sql = str(d.get('sql') or '')
    print('=== FULL SQL (len={}) ==='.format(len(sql)))
    print(sql[-1500:])  # 尾部 1500 字符（含外层过滤）
    print()
    rows = d.get('rows') or []
    print('rows =', len(rows))
    # 校验：这3行的开单金额真的是0吗
    for row in rows:
        print('  verify:', row.get('节点名称'), '| 开单 =', row.get('年度开单金额'), '| 达成率 =', row.get('达成率'))

# 直接查数据库对比：到底有多少业务代表开单=0
print()
print('=== DB 直查对比：业务代表开单=0 的真实人数 ===')
import psycopg2, psycopg2.extras
conn = psycopg2.connect(host='postgres', port=5432, dbname='postgres', user='postgres', password='6670326')
cur = conn.cursor()
cur.execute("""
SELECT COUNT(*) FROM (
  SELECT
    TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) AS 业务代表,
    SUM(COALESCE(NULLIF(regexp_replace(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC) AS 开单
  FROM angel_group_data
  WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
    AND TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) <> ''
  GROUP BY 1
) t WHERE t.开单 = 0
""")
print('开单=0 的业务代表真实人数:', cur.fetchone()[0])
cur.execute("""
SELECT COUNT(DISTINCT TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')))
FROM angel_group_data
WHERE COALESCE(NULLIF(TRIM(CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END), ''), '2026') = '2026'
  AND TRIM(COALESCE(CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END, '')) <> ''
""")
print('业务代表总人数:', cur.fetchone()[0])
conn.close()