import sys, contextlib, io, json
sys.path.insert(0, '/app/backend')
for n in ['werkzeug','urllib3','requests','neo4j']:
    import logging; logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

# 选假测试模型 id=100 (GPT-5.2 Pro, base_url=api.test.local) 问一个简单问题
q = '商用事业部的整体业绩'
with contextlib.redirect_stdout(io.StringIO()):
    r = svc.ask(question=q, session_id='probe-fallback-test', current_user=USER, model_id=100)

print('=' * 60)
print('选模型 id=100 (GPT-5.2 Pro @ api.test.local) 问数结果:')
print('=' * 60)
ds = r.get('dataset_results') or []
rows_total = sum(len(d.get('rows') or []) for d in ds)
print('rows_total =', rows_total)
print('error =', str(r.get('error') or '')[:200])
d0 = ds[0] if ds else {}
qi = d0.get('query_intent') or {}
print('intent =', qi.get('intent'))

# 抓 trace 看 llm.call 的候选切换
steps = r.get('steps') or []
llm_events = [s for s in steps if 'llm' in str(s.get('stage') or s.get('name') or '')]
print()
print('=== LLM 调用轨迹（候选切换证据）===')
for s in llm_events[:20]:
    ev = s if isinstance(s, dict) else {}
    stage = ev.get('stage') or ev.get('name')
    level = ev.get('level') or ''
    model = ev.get('model') or ''
    cidx = ev.get('candidate_index')
    ccount = ev.get('candidate_count')
    err = str(ev.get('error') or '')[:80]
    retry = ev.get('retry_with_next_model')
    dur = ev.get('duration_seconds')
    if err or retry or (stage and 'llm' in str(stage)):
        print(f'  [{stage}] level={level} model={model} cand={cidx}/{ccount} dur={dur}s err={err} retry_next={retry}')

# 也从 trace 字段找
trace = r.get('trace') or {}
if isinstance(trace, dict):
    for key in ('events', 'steps'):
        evts = trace.get(key) or []
        if evts and not llm_events:
            print(f'(trace.{key} 共 {len(evts)} 条)')

print()
print('=== 结论 ===')
if rows_total > 0:
    print(f'问数成功（{rows_total} 行）——假模型失败后自动回退到真实模型 ✓' if rows_total else '返回 0 行')
elif r.get('error'):
    print('问数失败：', str(r.get('error'))[:150])
else:
    print('返回 0 行，需进一步检查')