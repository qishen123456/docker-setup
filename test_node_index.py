import sys, json
sys.path.insert(0, '/app/backend')
from four_agent_ask import four_agent_ask_service as svc

# 找各数据集节点索引
idx = svc._load_dataset_node_index()
for ds in idx.get('datasets') or []:
    nodes = ds.get('nodes') or []
    names = {n.get('node_name') for n in nodes if isinstance(n, dict)}
    aliases = set()
    for n in nodes:
        if isinstance(n, dict):
            for a in n.get('aliases') or []:
                aliases.add(str(a).strip())
    all_names = names | aliases
    print(f"\n=== ds_id={ds.get('dataset_id')} {ds.get('dataset_name')} ({len(nodes)} nodes) ===")
    has_east = '东部分公司' in all_names or '东部' in all_names or any('东' in n for n in all_names)
    print(f"  含'东部分公司'? {has_east}")
    print(f"  含'东'节点: {[n for n in sorted(all_names) if '东' in n][:20]}")