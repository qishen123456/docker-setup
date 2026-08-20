import sys, os, time, json, psycopg2
import pandas as pd

sys.path.insert(0, '/app/backend')
from ask_flow import ask_flow_controller
from ask_flow.contracts import AskRequest

conn = psycopg2.connect(host='postgres', port=5432, database='postgres', user='postgres', password='6670326')
conn.autocommit = True
cur = conn.cursor()

print("🔍 第一步：深度学习底层业务真实数据 (Ground Truth Learning)...")

# 1. 学习电商事业部真实数据 (负责人 -> 业务部 / 平台 / 真实任务与开单)
cur.execute("""
SELECT 负责人, 业务部, 细分业务, 年度目标营收, 年度开单金额,
       ROUND(总任务达成率 * 100, 2) AS 达成率
FROM v_feishu_tbldianshang
WHERE 当前年 = '2026' AND 负责人 IS NOT NULL AND 负责人 <> ''
ORDER BY 年度开单金额 DESC;
""")
ec_rows = cur.fetchall()
ec_truth_map = {}
for r in ec_rows:
    p, d, b, t, a, r_pct = r[0], r[1], r[2], float(r[3] or 0), float(r[4] or 0), float(r[5] or 0)
    ec_truth_map[p] = {
        "负责人": p,
        "业务部": d,
        "细分业务": b,
        "总任务金额": t,
        "年度开单金额": a,
        "达成率": r_pct
    }
print(f"  ✓ 学习到电商核心负责人真值数据: {len(ec_truth_map)} 位")

# 2. 学习消费者事业部真实数据 (省区/分公司/城市公司/渠道分布)
cur.execute("""
SELECT 销售大区, 城市公司, 省份标签,
       COALESCE(年度目标营收, 0)::FLOAT AS 年度目标营收,
       COALESCE(年度开单金额, 0)::FLOAT AS 年度开单金额,
       COALESCE(新零售开单金额, 0)::FLOAT AS 新零售开单金额,
       COALESCE(线下开单金额, 0)::FLOAT AS 线下开单金额,
       ROUND(总任务达成率 * 100, 2)::FLOAT AS 达成率
FROM v_feishu_xiaofeizhe
WHERE 当前年 = '2026'
ORDER BY 年度开单金额 DESC;
""")
consumer_rows = cur.fetchall()
consumer_df = pd.DataFrame(consumer_rows, columns=['销售大区', '城市公司', '省份标签', '年度目标营收', '年度开单金额', '新零售开单金额', '线下开单金额', '达成率'])
print(f"  ✓ 学习到消费者业务节点真值数据: {len(consumer_df)} 行")

# 3. 学习商用事业部真实数据 (代表处 / 所属分公司 / 全国商用均值)
cur.execute("""
SELECT AVG(总任务达成率) AS 全国商用平均达成率
FROM v_angel_group_data
WHERE 当前年 = '2026' AND 层级级别 = '代表处';
""")
national_sy_avg = round(float(cur.fetchone()[0] or 0) * 100, 2)

cur.execute("""
SELECT 代表处, 分公司, 条线,
       COALESCE(年度目标营收, 0)::FLOAT AS 年度目标营收,
       COALESCE(年度开单金额, 0)::FLOAT AS 年度开单金额,
       ROUND(总任务达成率 * 100, 2)::FLOAT AS 达成率,
       城市标签
FROM v_angel_group_data
WHERE 当前年 = '2026' AND 代表处 IS NOT NULL AND 代表处 <> ''
ORDER BY 年度开单金额 DESC;
""")
sy_rows = cur.fetchall()
sy_df = pd.DataFrame(sy_rows, columns=['代表处', '分公司', '条线', '年度目标营收', '年度开单金额', '达成率', '城市标签'])
print(f"  ✓ 学习到商用业务代表处真值数据: {len(sy_df)} 个，全国商用平均达成率真值: {national_sy_avg}%")

# 4. 构建包含预期真值（Ground Truth Value）的评测题库
test_cases_with_truth = []

# (1) 电商人名实体与指标准确度
for person, data in list(ec_truth_map.items())[:10]:
    test_cases_with_truth.append({
        "id": f"EC_{person}",
        "domain": "电商事业部",
        "question": f"{person}负责的那个业务部今年目标是多少？",
        "expected_entity": data['业务部'] or person,
        "expected_metrics": {
            "总任务金额": data['总任务金额'],
            "年度开单金额": data['年度开单金额']
        },
        "check_type": "entity_metric_match"
    })

# (2) 消费者省区渠道开单与目标判定
provinces = ["广东", "湖南", "湖北", "江西", "四川", "江苏", "浙江", "安徽", "山东", "河南"]
for prov in provinces:
    prov_sub = consumer_df[consumer_df['省份标签'].str.contains(prov, na=False)]
    tot_retail = round(float(prov_sub['新零售开单金额'].sum()), 2)
    tot_offline = round(float(prov_sub['线下开单金额'].sum()), 2)
    tot_target = round(float(prov_sub['年度目标营收'].sum()), 2)
    tot_bill = round(float(prov_sub['年度开单金额'].sum()), 2)
    
    test_cases_with_truth.append({
        "id": f"CS_RETAIL_{prov}",
        "domain": "消费者事业部",
        "question": f"{prov}省区零售渠道目前的累计开单是多少？",
        "expected_entity": prov,
        "expected_metrics": {
            "渠道开单金额": tot_retail
        },
        "check_type": "channel_metric_match"
    })
    
    test_cases_with_truth.append({
        "id": f"CS_HALF_{prov}",
        "domain": "消费者事业部",
        "question": f"{prov}零售渠道开单是否完成了全年目标的50%？",
        "expected_entity": prov,
        "expected_metrics": {
            "已完成50%判定": "已完成50%" if tot_retail >= tot_target * 0.5 else "未完成50%"
        },
        "check_type": "derived_judgement_match"
    })

# (3) 商用代表处与全国均值对比、占比
sy_cities = ["广州", "深圳", "东莞", "佛山", "南京", "杭州", "合肥", "武汉", "长沙", "成都"]
for city in sy_cities:
    city_sub = sy_df[sy_df['城市标签'].str.contains(city, na=False)]
    if not city_sub.empty:
        office_name = city_sub.iloc[0]['代表处']
        branch_name = city_sub.iloc[0]['分公司']
        task_val = float(city_sub.iloc[0]['年度目标营收'])
        bill_val = float(city_sub.iloc[0]['年度开单金额'])
        rate_val = float(city_sub.iloc[0]['达成率'])
        
        # 计算分公司总开单
        branch_tot_bill = float(sy_df[sy_df['分公司'] == branch_name]['年度开单金额'].sum())
        expected_ratio = round(bill_val * 100.0 / branch_tot_bill, 2) if branch_tot_bill > 0 else 0
        expected_compare = "高于全国平均" if rate_val >= national_sy_avg else "低于全国平均"
        
        test_cases_with_truth.append({
            "id": f"SY_TASK_{city}",
            "domain": "商用事业部",
            "question": f"{city}代表处今年的总营收任务和已开单各是多少？",
            "expected_entity": office_name,
            "expected_metrics": {
                "总任务金额": task_val,
                "年度开单金额": bill_val
            },
            "check_type": "entity_metric_match"
        })
        
        test_cases_with_truth.append({
            "id": f"SY_AVG_{city}",
            "domain": "商用事业部",
            "question": f"{city}代表处的达成率是否高过全国商用平均水平？",
            "expected_entity": office_name,
            "expected_metrics": {
                "对比判定": expected_compare,
                "代表处达成率": rate_val,
                "全国平均达成率": national_sy_avg
            },
            "check_type": "derived_judgement_match"
        })

print(f"\n📊 第二步：构建真值基准测试集完成，共 {len(test_cases_with_truth)} 道核心业务题，开始端到端问数实跑校验...\n")

# 开始真实问数执行并校验数据准确性
benchmark_results = []
correct_data_count = 0

t0 = time.time()
for idx, tc in enumerate(test_cases_with_truth, 1):
    q = tc['question']
    dom = tc['domain']
    exp_ent = tc['expected_entity']
    exp_metrics = tc['expected_metrics']
    check_t = tc['check_type']
    
    t_start = time.time()
    req = AskRequest(question=q, current_user={'id': 'admin', 'role': 'super_admin'})
    res = ask_flow_controller.ask(req)
    dur = round(time.time() - t_start, 3)
    
    sql = res.get('sql') or ''
    rows = res.get('rows') or []
    cols = res.get('columns') or []
    analysis = res.get('analysis') or ''
    row_cnt = res.get('row_count') or len(rows)
    
    # 准确性核验逻辑：数据级比对
    data_accurate = False
    accuracy_detail = ""
    
    if not sql or row_cnt == 0:
        data_accurate = False
        accuracy_detail = "系统未生成有效 SQL 或返回 0 行"
    else:
        df_res = pd.DataFrame(rows, columns=cols)
        
        if check_t == "entity_metric_match":
            # 校验指标数值与实体
            matched_row = None
            for _, r in df_res.iterrows():
                row_str = " ".join([str(v) for v in r.values])
                if exp_ent in row_str:
                    matched_row = r
                    break
            
            if matched_row is None and len(df_res) == 1:
                matched_row = df_res.iloc[0]
                
            if matched_row is not None:
                val_ok = True
                val_diffs = []
                for k, expected_v in exp_metrics.items():
                    found_col = None
                    for c in df_res.columns:
                        if k in c or ("任务" in k and "任务" in c) or ("开单" in k and "开单" in c):
                            found_col = c
                            break
                    if found_col:
                        actual_v = float(pd.to_numeric(matched_row[found_col], errors='coerce') or 0)
                        # 允许万元与元的换算误差或数值误差 < 1%
                        if abs(actual_v - expected_v) > max(1.0, expected_v * 0.01) and abs(actual_v * 10000 - expected_v) > max(1.0, expected_v * 0.01) and abs(actual_v / 10000 - expected_v) > max(1.0, expected_v * 0.01):
                            val_ok = False
                            val_diffs.append(f"{k}期望{expected_v}实际{actual_v}")
                    else:
                        val_diffs.append(f"未找到列{k}")
                        val_ok = False
                        
                if val_ok:
                    data_accurate = True
                    accuracy_detail = f"实体与核心数值完全吻合 ({exp_metrics})"
                else:
                    data_accurate = False
                    accuracy_detail = f"数值存在偏差: {', '.join(val_diffs)}"
            else:
                data_accurate = False
                accuracy_detail = f"未精准命中目标实体 {exp_ent}"
                
        elif check_t == "channel_metric_match":
            # 校验渠道开单
            expected_v = list(exp_metrics.values())[0]
            val_ok = False
            for c in df_res.columns:
                if any(x in c for x in ["开单", "金额", "实际", "零售", "渠道"]):
                    actual_v = float(pd.to_numeric(df_res[c], errors='coerce').sum())
                    if abs(actual_v - expected_v) <= max(1.0, expected_v * 0.01) or abs(actual_v * 10000 - expected_v) <= max(1.0, expected_v * 0.01):
                        val_ok = True
                        break
            if val_ok:
                data_accurate = True
                accuracy_detail = f"渠道开单金额完全吻合真值 ({expected_v}元)"
            else:
                data_accurate = False
                accuracy_detail = f"渠道金额不吻合 (真值期望: {expected_v})"
                
        elif check_t == "derived_judgement_match":
            # 校验衍生计算与判定结论（如：已完成50% / 高于全国平均）
            exp_judgement = list(exp_metrics.values())[0]
            if exp_judgement in str(df_res.to_dict()) or exp_judgement in analysis:
                data_accurate = True
                accuracy_detail = f"衍生计算与业务结论准确得出: 【{exp_judgement}】"
            else:
                data_accurate = False
                accuracy_detail = f"衍生业务结论不准确 (期望得出: {exp_judgement})"

    if data_accurate:
        correct_data_count += 1
        badge = "🟢 [数据准确]"
    else:
        badge = "🔴 [数据偏差]"
        
    benchmark_results.append({
        "id": tc['id'],
        "domain": dom,
        "question": q,
        "expected_entity": exp_ent,
        "expected_metrics": exp_metrics,
        "is_accurate": data_accurate,
        "accuracy_detail": accuracy_detail,
        "rows": row_cnt,
        "duration": dur,
        "sql": sql
    })
    
    print(f"[{idx:02d}/{len(test_cases_with_truth)}] {badge} 【{dom}】 {q[:22]}... -> {accuracy_detail} ({dur}s)")

total_acc_rate = round(correct_data_count / len(test_cases_with_truth) * 100, 2)
print("\n" + "="*60)
print(f"🎉 真实数据基准核验完成！数据准确率: {total_acc_rate}% ({correct_data_count}/{len(test_cases_with_truth)})")
print("="*60)

# 生成诊断 MD 报告
md_report = []
md_report.append("# SmartAsk 真实业务数据基准学习与数据准确性深度诊断报告\n\n")
md_report.append("> **评测核心准则**：拒绝单纯以“是否有数据（`row_count > 0`）”为标准，必须先透彻学习底层物理数据库真值（Ground Truth），针对实体定位、核心指标数值吻合度、衍生计算逻辑进行**数据级三维严格比对**。\n\n")
md_report.append(f"> **全量数据准确率**：**{total_acc_rate}%** ({correct_data_count}/{len(test_cases_with_truth)} 道核心题完全符合业务真值)\n\n")
md_report.append("---\n\n")

md_report.append("## 一、底层真实数据基准学习字典 (Ground Truth Knowledge)\n\n")
md_report.append("### 1. 电商事业部核心负责人与业务部真值表\n\n")
md_report.append("| 负责人 | 负责业务部 | 细分业务/平台 | 2026 年度总任务 | 2026 年度开单金额 | 真实达成率 |\n")
md_report.append("| :--- | :--- | :--- | :---: | :---: | :---: |\n")
for p, d in list(ec_truth_map.items())[:8]:
    md_report.append(f"| **{p}** | {d['业务部']} | {d['细分业务']} | {d['总任务金额']:,.2f} 元 | {d['年度开单金额']:,.2f} 元 | {d['达成率']}% |\n")

md_report.append("\n### 2. 消费者事业部 10 大重点省区渠道开单真值表\n\n")
md_report.append("| 重点省份 | 所属销售大区 | 新零售开单真值 | 线下开单真值 | 省区总开单真值 | 零售是否完成50%目标 |\n")
md_report.append("| :--- | :--- | :---: | :---: | :---: | :---: |\n")
for prov in provinces[:8]:
    sub = consumer_df[consumer_df['省份标签'].str.contains(prov, na=False)]
    r_v = float(sub['新零售开单金额'].sum())
    o_v = float(sub['线下开单金额'].sum())
    tot_v = float(sub['年度开单金额'].sum())
    tar_v = float(sub['年度目标营收'].sum())
    half_str = "🟢 已完成50%" if r_v >= tar_v * 0.5 else "🔴 未完成50%"
    d_name = sub.iloc[0]['销售大区'] if not sub.empty else '-'
    md_report.append(f"| **{prov}** | {d_name} | {r_v:,.2f} 元 | {o_v:,.2f} 元 | {tot_v:,.2f} 元 | {half_str} |\n")

md_report.append("\n### 3. 商用事业部代表处与全国均值对比真值表\n\n")
md_report.append(f"> 📌 **2026 年全国商用代表处平均达成率真值基准**：`{national_sy_avg}%`\n\n")
md_report.append("| 重点城市/代表处 | 所属分公司 | 代表处总任务 | 代表处已开单 | 代表处达成率 | 全国均值对比判定 |\n")
md_report.append("| :--- | :--- | :---: | :---: | :---: | :---: |\n")
for city in sy_cities[:8]:
    c_sub = sy_df[sy_df['城市标签'].str.contains(city, na=False)]
    if not c_sub.empty:
        off = c_sub.iloc[0]['代表处']
        br = c_sub.iloc[0]['分公司']
        t_v = float(c_sub.iloc[0]['年度目标营收'])
        b_v = float(c_sub.iloc[0]['年度开单金额'])
        r_v = float(c_sub.iloc[0]['达成率'])
        cmp_s = "🟢 高于全国平均" if r_v >= national_sy_avg else "🔴 低于全国平均"
        md_report.append(f"| **{off}** | {br} | {t_v:,.2f} 元 | {b_v:,.2f} 元 | {r_v}% | {cmp_s} |\n")

md_report.append("\n---\n\n")
md_report.append("## 二、端到端真机问数数据准确性逐题核验明细\n\n")
for item in benchmark_results:
    i_id = item['id']
    d = item['domain']
    q = item['question']
    acc = item['is_accurate']
    det = item['accuracy_detail']
    sql = item['sql']
    dur = item['duration']
    
    badge = "🟢 **数据准确 (Accurate)**" if acc else "🔴 **数据偏差 (Inaccurate)**"
    md_report.append(f"### [{i_id}] 【{d}】 {q}\n")
    md_report.append(f"- **数据准确性核验**：{badge}\n")
    md_report.append(f"- **核验详情与真值比对**：`{det}` | 耗时 `{dur}s`\n")
    md_report.append(f"- **系统生成并执行的 SQL**：\n```sql\n{sql if sql else '-- 未生成 SQL --'}\n```\n\n")

final_content = "".join(md_report)
report_path = "/app/config/ground_truth_accuracy_diagnosis_report.md"
with open(report_path, "w", encoding="utf-8") as f:
    f.write(final_content)

print(f"\n✅ 诊断报告已成功写入: {report_path}")
