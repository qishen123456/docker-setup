# -*- coding: utf-8 -*-
"""100 道纠错专项测试（错字为主 + 对照组），内置 429 退避，并发 2。
输出：/app/config/shadow_gatekeeper_typo100.jsonl
"""
import json
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, "/app/backend")
from disambiguation import shadow_gatekeeper as sg

random.seed(7)
OUT = "/app/config/shadow_gatekeeper_typo100.jsonl"
DS2, DS3, DS62ID = 2, 3, 62

# (正确实体, 数据集, [错字变体])
TYPO_ENTITIES = [
    ("山东分公司", DS2, ["山冬分公司", "山东分司", "山東分公司", "山东分公"]),
    ("云贵渝分公司", DS2, ["云贵俞分公司", "云贵雨分公司", "云贵渝分司"]),
    ("江浙沪分公司", DS2, ["江浙沪分司", "江浙户分公司", "江淅沪分公司"]),
    ("豫晋分公司", DS2, ["豫普分公司", "预晋分公司", "豫晋分司"]),
    ("消费者事业部", DS2, ["消费者事业不", "消费这事业部", "消費者事业部"]),
    ("东部分公司", DS3, ["东部分公事", "东部分司", "冬部分公司", "东部风公司"]),
    ("南部分公司", DS3, ["南部分司", "难部分公司", "南部分公"]),
    ("商用事业部", DS3, ["商泳事业部", "商用事业不", "伤用事业部", "商用事業部"]),
    ("迟昊", DS3, ["迟浩", "池昊", "迟吴"]),
    ("丁杰", DS3, ["丁洁", "丁傑", "订杰"]),
    ("刘志伟", DS3, ["刘志伟", "刘志威", "刘至伟"]),
    ("靳锋", DS3, ["靳峰", "劲锋", "靳风"]),
    ("京东直营", DS62ID, ["京东直赢", "京冬直营", "京东直银"]),
    ("天猫直营", DS62ID, ["天猫直赢", "甜猫直营", "天喵直营"]),
]
TYPO_TPL = ["{}的业绩", "{}业绩怎么样", "看下{}", "{}达成率多少", "{}完成情况"]

questions = []
for name, ds, variants in TYPO_ENTITIES:
    for v in variants:
        questions.append((random.choice(TYPO_TPL).format(v), ds))
random.shuffle(questions)
questions = questions[:70]  # 70 道错字

# 15 道歧义对照
AMB = ["最不好的，还有第二不好的分公司", "最好的和最差的分公司", "前三名和倒数前三名",
       "最高和最低的分别是", "最好不分公司", "第二差的代表处", "排名靠后的前三名",
       "倒数第一的分公司最好的城市", "好不好都看一下", "中等的分公司",
       "不是最好的分公司", "最差也是最好的分公司", "好的坏的都要",
       "完成最好不分公司情况怎么样了", "最差的前两名分公司"]
for q in AMB:
    questions.append((q, random.choice([DS2, DS3])))

# 15 道清晰对照组（必须 pass，误伤率看这里）
CLEAR = ["山东分公司的业绩", "东部分公司业绩", "消费者事业部整体业绩",
         "各分公司业绩排名", "京东直营和天猫直营对比", "迟昊的业绩",
         "云贵渝分公司各城市分公司的业绩", "达成率大于50%的分公司",
         "前三的分公司", "商用事业部业绩分析", "南部分公司这个月开单",
         "京津分公司达成率", "西北分公司业绩怎么样", "河南代表处的业绩", "消费者事业部排名"]
for q in CLEAR:
    ds = DS62ID if "京东" in q else (DS3 if any(k in q for k in ["东部", "南部", "迟昊", "商用", "河南"]) else DS2)
    questions.append((q, ds))

questions = questions[:100]
print(f"题目: {len(questions)}")

settings = sg._load_settings()
lock = threading.Lock()
done = [0]
if os.path.exists(OUT):
    os.remove(OUT)

def work(item):
    q, ds = item
    record = {
        "question": q, "session_id": f"typo100-{ds}", "user_id": "sim", "timestamp": 0,
        "dataset_id": ds, "prompt_version": sg.PROMPT_VERSION, "gk_status": "ok",
        "sql_status": "ok", "rows_returned": -1, "model_id": settings.get("model_id"),
    }
    for attempt in range(3):
        try:
            parsed = sg._call_gatekeeper(q, sg._load_bookshelf_summary([ds]), settings)
            action = str(parsed.get("action") or "pass").lower()
            record.update({
                "gk_action": action,
                "would_block": action in ("suggest", "block"),
                "block_reason": str(parsed.get("reason") or "")[:200],
                "self_confidence": parsed.get("confidence"),
                "candidate_options_topN": [str(c)[:120] for c in (parsed.get("candidates") or [])][:3],
            })
            break
        except Exception as exc:
            record.update({"gk_status": "error", "gk_error": str(exc)[:200], "would_block": None})
            if "429" in str(exc):
                time.sleep(5 * (attempt + 1))
            else:
                break
    sg._append_log(record, OUT)
    with lock:
        done[0] += 1
        if done[0] % 10 == 0:
            print(f"进度 {done[0]}/{len(questions)}", flush=True)

with ThreadPoolExecutor(max_workers=2) as ex:
    list(ex.map(work, questions))
err = sum(1 for l in open(OUT, encoding='utf-8') if json.loads(l).get('gk_status') != 'ok')
print(f"TYPO100_DONE 失败 {err}")
