import sys, contextlib, io
sys.path.insert(0, '/app/backend')
import logging
for n in ['werkzeug','urllib3','requests','neo4j']:
    logging.getLogger(n).setLevel(logging.ERROR)
from four_agent_ask import four_agent_ask_service as svc
USER={'source':'admin','role':'super_admin','role_label':'超级管理员','username':'admin','name':'超级管理员'}

# 查"黄超"在哪个数据集
print('=== 节点索引：搜"黄超" ===')
idx = svc._load_dataset_node_index()
for ds in idx.get('datasets') or []:
    nodes = ds.get('nodes') or []
    hits = []
    for n in nodes:
        if not isinstance(n, dict): continue
        nm = n.get('node_name') or ''
        a = n.get('aliases') or []
        if '黄超' in nm or any('黄超' in str(x) for x in a):
            hits.append((nm, a))
    if hits:
        print(f'  ds_id={ds.get("dataset_id")} {ds.get("dataset_name")}: {hits}')

# 查各数据集的所有人员节点
print('\n=== 各数据集人员节点（人名 = 2-3 汉字但非通用词）===')
for ds in idx.get('datasets') or []:
    nodes = ds.get('nodes') or []
    persons = []
    for n in nodes:
        if not isinstance(n, dict): continue
        nm = (n.get('node_name') or '').strip()
        # 排除通用层级词
        if any(kw in nm for kw in ['分公司', '事业部', '业务部', '代表处', '公司', '业务', '城市', '工业', '公共', '餐饮', '住宅', '商用', '消费', '电商', '燃气', '新零售', '线下', '地产']):
            continue
        if 2 <= len(nm) <= 4:
            persons.append(nm)
    print(f'  ds_id={ds.get("dataset_id")} {ds.get("dataset_name")} 人名候选({len(persons)}): {persons[:15]}')
