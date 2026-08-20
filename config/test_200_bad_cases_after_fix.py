import sys, json, time

sys.path.insert(0, '/app/backend')
from ask_flow import ask_flow_controller
from ask_flow.contracts import AskRequest

with open('/app/config/200_bad_cases_data.json', 'r', encoding='utf-8') as f:
    cases = json.load(f)

print("==================================================")
print(f"开始对全部 {len(cases)} 道错题进行优化后全量回归实测...")
print("==================================================")

t0 = time.time()
fixed_count = 0
partial_count = 0
still_bad_count = 0

detailed_results = []

for idx, c in enumerate(cases, 1):
    q = c['question']
    domain = c['domain']
    cat = c['category']
    old_reason = c['reason']
    
    start_single = time.time()
    try:
        req = AskRequest(question=q, current_user={'id': 'admin', 'role': 'super_admin'})
        res = ask_flow_controller.ask(req)
        dur = round(time.time() - start_single, 3)
        
        row_count = res.get('row_count') or 0
        sql = res.get('sql') or ''
        analysis = res.get('analysis') or ''
        has_error = bool(res.get('error'))
        
        # 判定优化后状态
        is_fixed = False
        status_desc = ""
        
        if (not has_error) and row_count > 0 and ("未找到匹配数据" not in analysis):
            # 进一步检查是否有实质性改善
            if "WHERE 层级 = '燃气定制'" not in sql and "WHERE 层级 = '地产'" not in sql:
                is_fixed = True
                fixed_count += 1
                status_desc = "🟢 完全修复 (Fixed)"
            else:
                partial_count += 1
                status_desc = "🟡 部分出数 (Partial)"
        else:
            still_bad_count += 1
            status_desc = "🔴 仍待调优 (Pending)"
            
        detailed_results.append({
            "id": idx,
            "domain": domain,
            "category": cat,
            "question": q,
            "old_defect": old_reason,
            "new_rows": row_count,
            "new_status": status_desc,
            "duration": dur,
            "sql_preview": sql[:100] if sql else ''
        })
        
        if idx % 20 == 0 or idx <= 5 or is_fixed:
            badge = "🟢" if is_fixed else ("🟡" if "部分" in status_desc else "🔴")
            print(f"[{idx:03d}/200] {badge} 【{domain}】 {q[:24]}... -> {status_desc} ({row_count}行, {dur}s)")
            
    except Exception as e:
        still_bad_count += 1
        detailed_results.append({
            "id": idx,
            "domain": domain,
            "category": cat,
            "question": q,
            "old_defect": old_reason,
            "new_rows": 0,
            "new_status": f"❌ 异常: {str(e)[:30]}",
            "duration": round(time.time() - start_single, 3),
            "sql_preview": ""
        })

total_time = round(time.time() - t0, 2)
fix_rate = round(fixed_count / len(cases) * 100, 2)
effective_rate = round((fixed_count + partial_count) / len(cases) * 100, 2)

print("\n==================================================")
print("🎉 200 道真实错题优化后全量回归实测完成！")
print("==================================================")
print(f"总复测题量: {len(cases)}")
print(f"总耗时: {total_time}s")
print(f"完全修复题数 (Fixed): {fixed_count} 道 ({fix_rate}%)")
print(f"部分改善出数 (Partial): {partial_count} 道")
print(f"仍待调优题数 (Pending): {still_bad_count} 道")
print(f"综合改善有效率: {effective_rate}%")
print("==================================================")

# 保存复测结果
with open("/app/config/200_bad_cases_retest_results.json", "w", encoding="utf-8") as f:
    json.dump({
        "total_count": len(cases),
        "fixed_count": fixed_count,
        "partial_count": partial_count,
        "still_bad_count": still_bad_count,
        "fix_rate": fix_rate,
        "effective_rate": effective_rate,
        "total_time": total_time,
        "results": detailed_results
    }, f, ensure_ascii=False, indent=2)

