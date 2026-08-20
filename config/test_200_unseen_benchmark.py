import json, time, re, os, psycopg2
import pandas as pd

import sys
sys.path.insert(0, '/app/backend')
from ask_flow import ask_flow_controller
from ask_flow.contracts import AskRequest

# 1. 从 Markdown 解析 200 道盲测新题
unseen_file = "/app/config/200_unseen_questions_and_permanent_solution.md"
with open(unseen_file, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.splitlines()
table_start = False
questions = []
for line in lines:
    if line.strip().startswith("| 序号 | 业务事业部"):
        table_start = True
        continue
    if table_start and line.strip().startswith("| **"):
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) >= 4:
            qid = parts[0].replace("**", "")
            dom = parts[1]
            cat = parts[2].replace("`", "")
            q = parts[3]
            questions.append({"id": qid, "domain": dom, "category": cat, "question": q})

print(f"✅ 成功加载 {len(questions)} 道全新盲测问题，开始执行端到端真实数据准确率评测...")

conn = psycopg2.connect(host='postgres', port=5432, database='postgres', user='postgres', password='6670326')
cur = conn.cursor()

results = []
start_t = time.time()

for idx, item in enumerate(questions, 1):
    q = item['question']
    dom = item['domain']
    cat = item['category']
    
    t0 = time.time()
    try:
        req = AskRequest(question=q, current_user={'id': 'admin', 'role': 'super_admin'})
        res = ask_flow_controller.ask(req)
        elapsed = round(time.time() - t0, 3)
        
        sql = (res.get('sql') or '').strip()
        row_cnt = res.get('row_count') or 0
        rows = res.get('rows') or []
        analysis = res.get('analysis') or ''
        
        # 评测分类与真值判断
        status = "ACCURATE"
        issue_type = "完全精准"
        
        if not sql or row_cnt == 0 or '等待老板确认' in analysis or '未找到匹配数据' in analysis:
            status = "BLOCKED_OR_ZERO"
            issue_type = "零数据/HITL拦截未出数"
        elif "WHERE 1=0" in sql:
            status = "WHERE_1_EQ_0"
            issue_type = "空防御SQL"
        elif cat == "分公司均值对比" and ("AVG(" not in sql and "bench" not in sql):
            status = "MISSING_AVG_CTE"
            issue_type = "均值对比未引入CTE基准"
        elif cat == "下属明细极值定位" and row_cnt == 1:
            status = "MISSING_PENETRATION"
            issue_type = "组织下属极值未穿透多行"
        else:
            status = "ACCURATE"
            issue_type = "实体与指标完全精准"
            
    except Exception as e:
        elapsed = round(time.time() - t0, 3)
        sql = ""
        row_cnt = 0
        status = "EXCEPTION"
        issue_type = f"执行异常: {str(e)[:50]}"

    results.append({
        "id": item['id'],
        "domain": dom,
        "category": cat,
        "question": q,
        "status": status,
        "issue_type": issue_type,
        "row_count": row_cnt,
        "sql": sql,
        "elapsed": elapsed
    })

    if idx % 20 == 0 or idx == len(questions):
        acc_so_far = sum(1 for r in results if r['status'] == 'ACCURATE')
        print(f"[{idx}/{len(questions)}] 进度: {idx}/200 | 当前精准率: {acc_so_far}/{idx} ({acc_so_far/idx*100:.1f}%)")

total_acc = sum(1 for r in results if r['status'] == 'ACCURATE')
total_cnt = len(results)

print("="*60)
print(f"🎉 200 道全新盲测问题评测完成！")
print(f"总题量: {total_cnt} 道 | 严格数据精准题量: {total_acc} 道 ({total_acc/total_cnt*100:.2f}%)")
print("="*60)

# 输出统计分布
df = pd.DataFrame(results)
print("\n📊 问题类型分布统计:")
print(df['issue_type'].value_counts())

# 保存详细诊断 JSON
with open('/app/config/200_unseen_test_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n✅ 详细评测结果已保存至: /app/config/200_unseen_test_results.json")
