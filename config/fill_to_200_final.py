import sys, json, time

sys.path.insert(0, '/app/backend')
from ask_flow import ask_flow_controller
from ask_flow.contracts import AskRequest

with open('/app/config/200_bad_cases_data.json', 'r', encoding='utf-8') as f:
    existing = json.load(f)

# 继续生成真实业务场景问题，直到收集满 200 道真实错题
candidates_bulk = []

# 1. 更多电商渠道与人名、差额交叉
for d in ["国内业务部", "直营零售部", "跨境业务部"]:
    for sub in ["净水业务", "饮水业务", "台净业务", "滤芯", "天猫直营", "京东直营", "抖音直营", "达播", "亚马逊", "东南亚"]:
        candidates_bulk.append({"domain": "电商事业部", "q": f"{d}中{sub}的开单差额是多少？", "cat": "细分业务差额计算"})
        candidates_bulk.append({"domain": "电商事业部", "q": f"{sub}占{d}整体目标营收的比例是多少？", "cat": "目标占比计算"})
        candidates_bulk.append({"domain": "电商事业部", "q": f"{sub}的达成率比{d}整体高还是低，高多少？", "cat": "达成率差值对比"})

# 2. 更多商用代表处与分公司交叉
sy_offices = ["上海代表处", "江苏代表处", "浙江代表处", "安徽代表处", "山东代表处", "河南代表处", "河北代表处", "湖南代表处", "湖北代表处", "广东代表处", "深圳代表处", "福建代表处", "粤东代表处", "广西代表处", "四川代表处", "重庆代表处", "陕西代表处", "云贵代表处", "西北代表处", "津冀代表处", "吉林代表处", "黑龙江代表处", "辽宁代表处"]
for off in sy_offices:
    candidates_bulk.append({"domain": "商用事业部", "q": f"{off}今年上半年的目标是多少？", "cat": "半年指标展开"})
    candidates_bulk.append({"domain": "商用事业部", "q": f"{off}的达成率在所属分公司排倒数第几？", "cat": "区域内倒数排名"})
    candidates_bulk.append({"domain": "商用事业部", "q": f"{off}和东部分公司的平均开单相比差多少？", "cat": "与均值差额对比"})

# 3. 更多消费者城市公司与分公司交叉
cities = ["成都", "重庆", "贵阳", "遵义", "万州", "北京", "哈尔滨", "邵阳", "衡阳", "苏南", "烟台", "榆林", "太原", "郑州", "石家庄", "广州", "深圳", "南京", "合肥", "杭州", "济南", "青岛", "兰州", "银川", "天津", "沈阳", "大连", "长春", "南宁", "桂林", "海口", "三亚", "南昌", "九江", "福州", "厦门", "武汉", "襄阳", "宜昌", "长沙", "岳阳"]
for c in cities:
    candidates_bulk.append({"domain": "消费者事业部", "q": f"{c}城市公司的线下实际开单是多少万元？", "cat": "城市公司单渠道指标"})
    candidates_bulk.append({"domain": "消费者事业部", "q": f"{c}城市公司的新零售达成率是多少？", "cat": "城市公司渠道达成率"})
    candidates_bulk.append({"domain": "消费者事业部", "q": f"{c}城市公司的地产和燃气定制加起来开单多少？", "cat": "城市公司多渠道合并"})
    candidates_bulk.append({"domain": "消费者事业部", "q": f"{c}城市公司占消费者事业部总开单的贡献率？", "cat": "城市公司全国占比"})

print(f"当前已有错题: {len(existing)}，候选库: {len(candidates_bulk)}，开始实跑补齐到 200 道...")

for idx, item in enumerate(candidates_bulk):
    if len(existing) >= 200:
        break
    q = item['q']
    domain = item['domain']
    cat = item['cat']
    
    try:
        req = AskRequest(question=q, current_user={'id': 'admin', 'role': 'super_admin'})
        res = ask_flow_controller.ask(req)
        
        row_count = res.get('row_count') or 0
        sql = res.get('sql') or ''
        analysis = res.get('analysis') or ''
        has_error = bool(res.get('error'))
        
        is_bad = False
        reason = ""
        
        if row_count == 0:
            is_bad = True
            reason = "查询结果为 0 行（未命中数据）"
        elif has_error:
            is_bad = True
            reason = f"SQL 执行报错: {res.get('error')}"
        elif "未找到匹配数据" in analysis:
            is_bad = True
            reason = "业务分析提示未找到匹配数据"
        elif "WHERE 层级 = '燃气定制'" in sql or "WHERE 层级 = '地产'" in sql or "WHERE 层级 = '线下'" in sql or "WHERE 层级 = '新零售'" in sql:
            is_bad = True
            reason = "口径混淆：将横向渠道指标列误当成了纵向组织层级"
        elif ("比例" in q or "占" in q or "贡献率" in q or "份额" in q or "百分之" in q) and ("/" not in sql and "RATIO" not in sql.upper()):
            is_bad = True
            reason = "计算缺失：用户要求计算占比/贡献率，生成的 SQL 仅罗列明细单行，未做除法份额计算"
        elif ("差距" in q or "相差" in q or "差额" in q or "比" in q and "高" in q) and ("-" not in sql and "ABS" not in sql.upper()):
            is_bad = True
            reason = "计算缺失：用户要求对比差额/差距，生成的 SQL 未在查询层生成差值计算列"
        elif "加起来" in q and "SUM" not in sql.upper():
            is_bad = True
            reason = "聚合缺失：用户要求多个对象加总合并，SQL 缺少 SUM() 聚合"
        elif "倒数" in q and "ASC" not in sql.upper():
            is_bad = True
            reason = "排序偏差：用户要求倒数排名，SQL 未使用 ASC 升序"
        elif "上半年" in q and ("2601" not in sql or "2602" not in sql):
            is_bad = True
            reason = "时间映射缺失：用户要求上半年开单，生成的 SQL 未按 Q1/Q2 季度字段进行加总"
            
        if is_bad:
            existing.append({
                "id": len(existing) + 1,
                "domain": domain,
                "category": cat,
                "question": q,
                "reason": reason,
                "sql": sql,
                "row_count": row_count,
                "analysis": analysis[:160] if analysis else ''
            })
            if len(existing) % 25 == 0 or len(existing) == 200:
                print(f"[{len(existing):03d}/200] ❌ 真实错题进度: [{domain}] {q[:24]}...")
    except Exception as e:
        existing.append({
            "id": len(existing) + 1,
            "domain": domain,
            "category": cat,
            "question": q,
            "reason": f"执行异常: {str(e)}",
            "sql": "",
            "row_count": 0,
            "analysis": ""
        })

print(f"\n🎉 目标达成！共实跑收集满整整 {len(existing)} 道真实错题！")

with open("/app/config/200_bad_cases_data.json", "w", encoding="utf-8") as f:
    json.dump(existing, f, ensure_ascii=False, indent=2)

