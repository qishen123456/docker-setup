import sys, json, time

sys.path.insert(0, '/app/backend')
from ask_flow import ask_flow_controller
from ask_flow.contracts import AskRequest

# 验证之前测试中失败的典型场景
TARGET_CASES = [
    {"domain": "电商事业部", "q": "黄超负责的那个业务部今年目标是多少？", "desc": "口语化实体修饰词剥离"},
    {"domain": "电商事业部", "q": "电商部门达成率低于20%的细分业务有哪些？", "desc": "比率小数换算"},
    {"domain": "电商事业部", "q": "电商整体总任务和年度开单分别是多少？", "desc": "顶层组织层级枚举"},
    {"domain": "电商事业部", "q": "天猫直营和京东直营占直营零售部总开单的比例分别是多少？", "desc": "份额占比派生计算"},
    {"domain": "商用事业部", "q": "商用事业部目前还有多少任务金额没有完成？", "desc": "商用顶层层级枚举"},
    {"domain": "商用事业部", "q": "商用上海代表处的业绩怎么样？", "desc": "代表处下钻"},
    {"domain": "消费者事业部", "q": "燃气定制业务今年完成了多少开单金额？", "desc": "渠道指标列聚合"},
    {"domain": "消费者事业部", "q": "地产渠道的年度任务和开单金额是多少？", "desc": "渠道指标列聚合"}
]

print("==================================================")
print("正在执行核心 Bad Cases 优化后实跑回归验证...")
print("==================================================")

pass_cnt = 0
for idx, item in enumerate(TARGET_CASES, 1):
    q = item['q']
    dom = item['domain']
    desc = item['desc']
    
    t0 = time.time()
    req = AskRequest(question=q, current_user={'id': 'admin', 'role': 'super_admin'})
    res = ask_flow_controller.ask(req)
    dur = round(time.time() - t0, 3)
    
    rows = res.get('row_count') or 0
    sql = res.get('sql') or ''
    ana = res.get('analysis') or ''
    
    is_ok = (rows > 0) and ("未找到匹配数据" not in ana)
    if is_ok:
        pass_cnt += 1
        print(f"[{idx:02d}/08] 🟢 [已修复] 【{dom}】 {q}")
        print(f"       -> 返回 {rows} 行，耗时 {dur}s")
        print(f"       -> SQL 摘要: {sql[:100]}...")
    else:
        print(f"[{idx:02d}/08] 🔴 [待调优] 【{dom}】 {q} -> 返回 {rows} 行")

print(f"\n核心 Bad Cases 回归通过率: {pass_cnt}/{len(TARGET_CASES)} ({round(pass_cnt/len(TARGET_CASES)*100, 1)}%)")
