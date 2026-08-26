import sys, contextlib, io, json, re
sys.path.insert(0, '/app/backend')
for n in ['werkzeug','urllib3','requests','neo4j']:
    import logging; logging.getLogger(n).setLevel(logging.ERROR)
import four_agent_ask
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

LOG = []
def dump_qi(tag, qi):
    if not isinstance(qi, dict):
        LOG.append(f'{tag}: query_intent is {type(qi).__name__}')
        return
    keys = ['intent','target_level','filter_metric_key','filter_metric_column',
            'filter_operator','filter_value','filter_unit','top_n','direction',
            '_quantity_verified','matched_triggers']
    LOG.append(f'{tag}: ' + json.dumps({k: qi.get(k) for k in keys}, ensure_ascii=False, default=str))

# ---- wrap _select_sql_strategy ----
orig_select = four_agent_ask.FourAgentAskService._select_sql_strategy
def traced_select(self, question, route, context):
    qi = context.get('query_intent') or {}
    dump_qi('[_select_sql_strategy IN]', qi)
    LOG.append(f'[_select_sql_strategy IN] route.matched_sample_id={route.get("matched_sample_id")} decision={route.get("decision")}')
    result = orig_select(self, question, route, context)
    # 返回后再 dump（可能已被 _build_rule_based_sql 就地改写）
    dump_qi('[_select_sql_strategy OUT(改写后)]', context.get('query_intent') or {})
    if isinstance(result, dict):
        sql = str(result.get('sql') or '')
        LOG.append(f'[_select_sql_strategy OUT] mode={result.get("mode")} sample_id={result.get("sample_id")} sql_len={len(sql)}')
        LOG.append(f'[_select_sql_strategy OUT] sql_head: {" ".join(sql[:180].split())}')
    return result
four_agent_ask.FourAgentAskService._select_sql_strategy = traced_select

# ---- wrap _build_rule_based_sql ----
orig_build = four_agent_ask.FourAgentAskService._build_rule_based_sql
def traced_build(self, question, route, context):
    qi = context.get('query_intent') or {}
    dump_qi('[_build_rule_based_sql IN]', qi)
    sql = orig_build(self, question, route, context)
    dump_qi('[_build_rule_based_sql OUT(可能已改写)]', context.get('query_intent') or {})
    if sql:
        LOG.append(f'[_build_rule_based_sql OUT] 返回 SQL len={len(sql)}')
        LOG.append(f'[_build_rule_based_sql OUT] sql_head: {" ".join(str(sql)[:180].split())}')
        # 检查是否含 filter 约束
        has_level = re.search(r"层级\s*=\s*'业务代表'", str(sql))
        has_thresh = re.search(r"年度开单金额\s*<\s*5000000", str(sql))
        LOG.append(f'[_build_rule_based_sql OUT] 含层级=业务代表: {bool(has_level)} | 含 开单<5000000: {bool(has_thresh)}')
    else:
        LOG.append('[_build_rule_based_sql OUT] 返回 None/空')
    return sql
four_agent_ask.FourAgentAskService._build_rule_based_sql = traced_build

# ---- 跑 Q1 完整 confirm 流 ----
q1 = '开单金额低于500万的业务员有哪些'
LOG.append('=' * 60)
LOG.append('>>> ASK 阶段')
LOG.append('=' * 60)
with contextlib.redirect_stdout(io.StringIO()):
    r = svc.ask(question=q1, session_id='trace-q1', current_user=USER)
token = r.get('session_id') or ''
LOG.append(f'ask: requires_confirmation={r.get("requires_confirmation")} token={token[:8]}...')

if r.get('requires_confirmation') and token:
    LOG.append('=' * 60)
    LOG.append('>>> CONFIRM 阶段（选商用[3]）')
    LOG.append('=' * 60)
    options = (r.get('route') or {}).get('confirmation_options') or []
    target = ''
    for o in options:
        if o.get('dataset_ids') == [3]:
            target = o.get('id') or o.get('option_id') or ''
    with contextlib.redirect_stdout(io.StringIO()):
        r2 = svc.confirm_by_boss(session_id=token, selected_option='商用事业部',
                                   selected_dataset_ids=[3], option_id=target, current_user=USER)
    ds = (r2.get('dataset_results') or [])
    rows_total = sum(len(d.get('rows') or []) for d in ds)
    LOG.append(f'confirm 后 rows_total={rows_total}')
    for d in ds[:1]:
        dump_qi('[最终 dataset_results.0.query_intent]', d.get('query_intent') or {})
        sql = str(d.get('sql') or '')
        LOG.append(f'[最终 SQL] len={len(sql)}')
        LOG.append(f'[最终 SQL] tail: {" ".join(sql[-260:].split())}')
        lv_count = {}
        for row in (d.get('rows') or []):
            lv = row.get('层级') or '?'
            lv_count[lv] = lv_count.get(lv, 0) + 1
        LOG.append(f'[最终 rows 层级分布] {lv_count}')

print('\n'.join(LOG))