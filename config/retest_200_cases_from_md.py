import sys, re, json, time

sys.path.insert(0, '/app/backend')
from ask_flow import ask_flow_controller
from ask_flow.contracts import AskRequest

# 从 Markdown 文件中解析出 200 道题目
with open('/app/config/200_bad_cases_diagnosis_report.md', 'r', encoding='utf-8') as f:
    text = f.read()

# 匹配模式：### [错题 001] 【电商事业部】 黄超负责的那个部门年度目标是多少？
pattern = re.compile(r'###\s+\[错题\s+(\d+)\]\s+【(.*?)】\s+(.*?)\n')
matches = pattern.findall(text)

print(f"从 200 题诊断报告中成功解析出 {len(matches)} 道题目！开始执行优化后全量回归复测...")

t0 = time.time()
fixed_count = 0
partial_count = 0
still_bad_count = 0
detailed_results = []

for item in matches:
    cid_str, domain, q = item
    cid = int(cid_str)
    
    t_start = time.time()
    try:
        req = AskRequest(question=q, current_user={'id': 'admin', 'role': 'super_admin'})
        res = ask_flow_controller.ask(req)
        dur = round(time.time() - t_start, 3)
        
        row_count = res.get('row_count') or 0
        sql = res.get('sql') or ''
        analysis = res.get('analysis') or ''
        has_error = bool(res.get('error'))
        
        is_fixed = False
        status_desc = ""
        
        if (not has_error) and row_count > 0 and ("未找到匹配数据" not in analysis):
            if "WHERE 层级 = '燃气定制'" not in sql and "WHERE 层级 = '地产'" not in sql:
                is_fixed = True
                fixed_count += 1
                status_desc = "🟢 完全修复出数 (Fixed)"
            else:
                partial_count += 1
                status_desc = "🟡 部分出数 (Partial)"
        else:
            still_bad_count += 1
            status_desc = "🔴 待进一步优化 (Pending)"
            
        detailed_results.append({
            "id": cid,
            "domain": domain,
            "question": q,
            "new_rows": row_count,
            "new_status": status_desc,
            "duration": dur,
            "sql_preview": sql[:100] if sql else ''
        })
        
        if cid % 20 == 0 or cid <= 5 or is_fixed:
            badge = "🟢" if is_fixed else ("🟡" if "部分" in status_desc else "🔴")
            print(f"[{cid:03d}/200] {badge} 【{domain}】 {q[:24]}... -> {status_desc} ({row_count}行, {dur}s)")
            
    except Exception as e:
        still_bad_count += 1
        detailed_results.append({
            "id": cid,
            "domain": domain,
            "question": q,
            "new_rows": 0,
            "new_status": f"❌ 异常: {str(e)[:30]}",
            "duration": round(time.time() - t_start, 3),
            "sql_preview": ""
        })

total_time = round(time.time() - t0, 2)
fix_rate = round(fixed_count / len(matches) * 100, 2)
effective_rate = round((fixed_count + partial_count) / len(matches) * 100, 2)

print("\n==================================================")
print("🎉 200 道真实错题优化后全量回归实测完成！")
print("==================================================")
print(f"总复测题量: {len(matches)}")
print(f"总耗时: {total_time}s")
print(f"完全修复题数 (Fixed): {fixed_count} 道 ({fix_rate}%)")
print(f"部分改善出数 (Partial): {partial_count} 道")
print(f"仍待调优题数 (Pending): {still_bad_count} 道")
print(f"综合改善有效率: {effective_rate}%")
print("==================================================")

with open("/app/config/200_bad_cases_retest_summary.json", "w", encoding="utf-8") as f:
    json.dump({
        "total_count": len(matches),
        "fixed_count": fixed_count,
        "partial_count": partial_count,
        "still_bad_count": still_bad_count,
        "fix_rate": fix_rate,
        "effective_rate": effective_rate,
        "total_time": total_time,
        "results": detailed_results
    }, f, ensure_ascii=False, indent=2)

