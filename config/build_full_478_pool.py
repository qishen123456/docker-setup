import json, os, re

full_pool = []
seen = set()

def add(q, dom, src):
    q = q.strip()
    if q and q not in seen:
        seen.add(q)
        full_pool.append({
            "id": len(full_pool) + 1,
            "question": q,
            "domain": dom,
            "source": src
        })

base_dir = "/Users/ltq/Desktop/ambitious/4.Lin_project/1.智能问数/3.项目代码/smartask"

# 1. 100 benchmark
p1 = os.path.join(base_dir, "config/100_questions_benchmark.json")
if os.path.exists(p1):
    with open(p1, 'r', encoding='utf-8') as f:
        for it in json.load(f):
            add(it['question'], it.get('domain', '全场景'), '100_benchmark')

# 2. round3 200 cases
p2 = os.path.join(base_dir, "config/round3_200_bad_cases.json")
if os.path.exists(p2):
    with open(p2, 'r', encoding='utf-8') as f:
        for it in json.load(f):
            add(it['question'], it.get('domain', '全场景'), 'round3_200')

# 3. doc history questions
for fn in ["50_bad_cases_diagnosis_report.md", "200_bad_cases_diagnosis_report.md", "278_bad_cases_diagnosis_report.md"]:
    fp = os.path.join(base_dir, "docs", fn)
    if os.path.exists(fp):
        with open(fp, 'r', encoding='utf-8') as f:
            for line in f:
                m = re.search(r'###\s+\[.*?\]\s+【(.*?)】\s+(.*)', line)
                if m:
                    add(m.group(2).strip(), m.group(1).strip(), fn)

out_p = os.path.join(base_dir, "config/all_478_questions_pool.json")
with open(out_p, 'w', encoding='utf-8') as f:
    json.dump(full_pool, f, ensure_ascii=False, indent=2)

print(f"成功构建历史全量问题池: 共 {len(full_pool)} 道题，已写入 {out_p}")
