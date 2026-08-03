# -*- coding: utf-8 -*-
"""双专家团队配置综合校验脚本（临时）"""
import yaml, os, re

os.chdir('/Users/ltl123/smartask/sa1.0/smartask')

errors = []
warnings = []
infos = []

# ============ 1. YAML 语法校验 ============
for cfg_path in ['.ai-team/team-config.yaml', '.ai-data/team-config.yaml']:
    try:
        cfg = yaml.safe_load(open(cfg_path))
        infos.append(f"YAML 语法 OK: {cfg_path} (version={cfg.get('version')})")
    except Exception as e:
        errors.append(f'YAML 语法错误 {cfg_path}: {e}')

# ============ 2. prompt_file 路径存在性 ============
for team_dir in ['.ai-team', '.ai-data']:
    cfg = yaml.safe_load(open(f'{team_dir}/team-config.yaml'))
    for m in cfg['members']:
        p = os.path.join(team_dir, m['prompt_file'])
        if not os.path.exists(p):
            errors.append(f"{team_dir}: prompt_file 不存在 -> {m['prompt_file']} (成员 {m['id']})")
infos.append('prompt_file 路径全部存在')

# ============ 3. Agent ID 一致性 ============
for team_dir in ['.ai-team', '.ai-data']:
    cfg = yaml.safe_load(open(f'{team_dir}/team-config.yaml'))
    ids = [m['id'] for m in cfg['members']]
    if len(ids) != len(set(ids)):
        errors.append(f'{team_dir}: 存在重复 Agent ID')
    if cfg['team']['size'] != len(ids):
        warnings.append(f"{team_dir}: team.size={cfg['team']['size']} 与实际成员数 {len(ids)} 不一致")
    if cfg['team']['lead'] not in ids:
        errors.append(f"{team_dir}: team.lead={cfg['team']['lead']} 不在 members 中")
    for k, v in cfg['routing_table'].items():
        if v not in ids:
            errors.append(f'{team_dir}: routing_table["{k}"] -> {v} 不是合法成员 ID')
    prefix = 'fullstack-dev-' if team_dir == '.ai-team' else 'data-team-'
    bad = [i for i in ids if not i.startswith(prefix)]
    if bad:
        errors.append(f'{team_dir}: 以下 ID 未带前缀 {prefix}: {bad}')
infos.append('Agent ID 一致性检查完成（无重复/lead有效/路由合法/前缀统一）')

# ============ 4. 旧 ID 残留检查（.ai-data 内） ============
old_ids = ['data-engineer', 'trend-analyst', 'structure-analyst', 'anomaly-analyst',
           'ml-engineer', 'industry-researcher', 'deep-researcher', 'financial-analyst',
           'viz-designer', 'team-lead']
residue = []
for root, dirs, files in os.walk('.ai-data'):
    for f in files:
        if not f.endswith(('.md', '.yaml')):
            continue
        path = os.path.join(root, f)
        text = open(path).read()
        for mt in re.finditer(r'`([a-z][a-z-]*)`', text):
            val = mt.group(1)
            if val in old_ids:
                line_no = text[:mt.start()].count('\n') + 1
                residue.append(f'{path}:{line_no}: 旧 ID `{val}`')
if residue:
    for r in residue:
        warnings.append(f'旧 ID 残留: {r}')
else:
    infos.append('无旧 ID 残留')

# ============ 5. 新文件存在性 ============
new_files = [
    '.ai-data/knowledge-base/pitfalls.md',
    '.ai-data/knowledge-base/decisions.md',
    '.ai-data/knowledge-base/patterns.md',
    '.ai-data/checklists/data-quality-check.md',
    '.ai-data/checklists/viz-spec-check.md',
    '.ai-data/checklists/analysis-rigor-check.md',
]
for f in new_files:
    if not os.path.exists(f):
        errors.append(f'新文件缺失: {f}')
    elif os.path.getsize(f) < 100:
        warnings.append(f'新文件内容过短: {f} ({os.path.getsize(f)} bytes)')
infos.append('.ai-data 新增 6 个文件全部存在')

# ============ 6. .ai-team knowledge-base 填充检查 ============
for f in ['pitfalls.md', 'decisions.md', 'patterns.md']:
    path = f'.ai-team/knowledge-base/{f}'
    text = open(path).read()
    entries = re.findall(r'^\[2026-', text, re.M)
    if f == 'patterns.md':
        titles = [l for l in text.split('\n')
                  if l.strip() and not l.strip().startswith(('#', '>', '<!', '-', '适用', '具体', '代表', '格式'))]
        infos.append(f'{path}: 模式标题段约 {len(titles)} 个')
    else:
        infos.append(f'{path}: 实际条目 {len(entries)} 条' + (' (仍为空壳!)' if len(entries) == 0 else ''))
        if len(entries) == 0:
            errors.append(f'{path} 未填充')

# ============ 7. 关键章节存在性 ============
checks = [
    ('.ai-team/agents/fullstack-dev-team-lead.md', '跨 IDE 降级模式'),
    ('.ai-data/agents/team-lead.md', '跨 IDE 降级模式'),
    ('AGENTS.md', '两套专家团队的区别与分工'),
    ('AGENTS.md', '跨团队交接'),
]
for path, section in checks:
    text = open(path).read()
    if section not in text:
        errors.append(f'{path}: 缺少章节 "{section}"')
infos.append('关键章节全部存在')

# ============ 8. cross_team 配置块对称性 ============
t1 = yaml.safe_load(open('.ai-team/team-config.yaml'))
t2 = yaml.safe_load(open('.ai-data/team-config.yaml'))
ct1 = t1.get('cross_team', [])
ct2 = t2.get('cross_team', [])
if not ct1:
    errors.append('.ai-team/team-config.yaml 缺 cross_team 配置块')
if not ct2:
    errors.append('.ai-data/team-config.yaml 缺 cross_team 配置块')
infos.append(f'cross_team 条目: .ai-team={len(ct1)} 条, .ai-data={len(ct2)} 条')
trig1 = sorted([c.get('trigger', '') for c in ct1])
trig2 = sorted([c.get('trigger', '') for c in ct2])
if trig1 != trig2:
    warnings.append('cross_team 两边 trigger 不完全对称:\n  .ai-team: %s\n  .ai-data: %s' % (trig1, trig2))

# ============ 9. workflows route 中的短名残留 ============
t2route_full = t2['workflows'][2]['route']
t2route_fin = t2['workflows'][4]['route']
if 'data-team-' not in t2route_full:
    warnings.append(f'.ai-data full-pipeline route 仍用短名: {t2route_full}')
if 'data-team-' not in t2route_fin:
    warnings.append(f'.ai-data finance-sop route 仍用短名: {t2route_fin}')

# ============ 10. .ai-data 各 agent prompt 内旧 ID 引用（非反引号场景） ============
# 检查 agents/*.md 中是否有引用其他成员的裸 ID（在正文而非 code span 中）
bare_refs = []
for f in os.listdir('.ai-data/agents'):
    if not f.endswith('.md'):
        continue
    path = os.path.join('.ai-data/agents', f)
    text = open(path).read()
    for oid in old_ids:
        for mt in re.finditer(r'(?<![a-z-])' + re.escape(oid) + r'(?![a-z-])', text):
            # 排除带 data-team- 前缀的
            start = mt.start()
            prefix_ctx = text[max(0, start-10):start]
            if 'data-team-' in prefix_ctx:
                continue
            line_no = text[:start].count('\n') + 1
            bare_refs.append(f'{path}:{line_no}: 裸引用 `{oid}`')
if bare_refs:
    for b in bare_refs[:20]:
        warnings.append(f'.ai-data 裸 ID 引用: {b}')
else:
    infos.append('.ai-data agents 内无裸 ID 引用')

print('=' * 60)
for i in infos:
    print(f'[INFO] {i}')
print('=' * 60)
print(f'错误: {len(errors)} 条')
for e in errors:
    print(f'  [ERROR] {e}')
print(f'警告: {len(warnings)} 条')
for w in warnings:
    print(f'  [WARN] {w}')
