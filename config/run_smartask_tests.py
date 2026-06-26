#!/usr/bin/env python3
"""SmartAsk 端到端批量测试脚本（在 backend 容器内执行）"""
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime
from urllib.parse import urljoin

import requests
import urllib3

urllib3.disable_warnings()

BASE_URL = os.environ.get("SMARTASK_TEST_BASE_URL", "http://localhost:5002")
ADMIN_USER = os.environ.get("SMARTASK_ADMIN_USERNAME", "admin")
ADMIN_PASS = os.environ.get("SMARTASK_ADMIN_PASSWORD", "admin123456")
MD_PATH = "/app/config/smartask_test_question_list.md"
OUT_DIR = "/app/config"
PER_Q_TIMEOUT = int(os.environ.get("SMARTASK_TEST_TIMEOUT", "180"))


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)


def login(session):
    url = urljoin(BASE_URL, "/api/auth/login")
    r = session.post(url, json={"username": ADMIN_USER, "password": ADMIN_PASS}, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not data.get("success") or not data.get("token"):
        raise RuntimeError(f"登录失败: {data}")
    return data["token"]


def parse_questions(md_path):
    with open(md_path, "r", encoding="utf-8") as fh:
        text = fh.read()
    questions = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        if line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        # 表头或空行跳过
        if len(cells) < 4 or cells[0] in ("编号", "目标数据集", "问题"):
            continue
        qid, target, question, expected = cells[0], cells[1], cells[2], cells[3]
        if not qid or not question:
            continue
        questions.append({
            "id": qid,
            "target": target,
            "question": question,
            "expected": expected,
        })
    return questions


def expected_dataset_id(target_text):
    mapping = {"2": 2, "3": 3, "62": 62}
    # target_text like "3" or "数据集 3" or "需确认"
    for k, v in mapping.items():
        if target_text == k or target_text.startswith(f"数据集 {k}") or target_text.startswith(k + " "):
            return v
    return None


def _safe_text(value, limit=800):
    if value is None:
        return ""
    if isinstance(value, str):
        return value[:limit]
    try:
        return json.dumps(value, ensure_ascii=False)[:limit]
    except Exception:
        return str(value)[:limit]


def extract_card_info(report_spec):
    info = {
        "report_title": report_spec.get("reportTitle", "") if isinstance(report_spec, dict) else "",
        "answer_summary": _safe_text(report_spec.get("answerSummary") if isinstance(report_spec, dict) else ""),
        "narrative": _safe_text(report_spec.get("narrative") if isinstance(report_spec, dict) else ""),
        "kpis": [],
        "sections": [],
        "charts": [],
        "accordions": [],
        "scope": {},
    }
    if not isinstance(report_spec, dict):
        return info
    for kpi in report_spec.get("kpis") or []:
        if isinstance(kpi, dict):
            info["kpis"].append({
                "title": kpi.get("title") or kpi.get("label") or "",
                "value": _safe_text(kpi.get("value") or kpi.get("displayValue"), limit=200),
            })
    for sec in report_spec.get("sections") or []:
        if isinstance(sec, dict):
            info["sections"].append(sec.get("title") or sec.get("name") or "")
    for chart in report_spec.get("charts") or []:
        if isinstance(chart, dict):
            info["charts"].append(chart.get("title") or chart.get("name") or "")
    for acc in report_spec.get("accordions") or []:
        if isinstance(acc, dict):
            info["accordions"].append(acc.get("title") or acc.get("name") or "")
    scope = report_spec.get("scope")
    if isinstance(scope, dict):
        info["scope"] = {k: _safe_text(v, limit=300) for k, v in scope.items() if k in ("level", "matched_nodes", "filters", "sort")}
    return info


def keyword_set(text):
    text = str(text or "")
    # 保留中文字符、英文、数字
    tokens = re.findall(r"[a-zA-Z0-9\u4e00-\u9fa5]+", text)
    stop = {"的", "了", "是", "和", "与", "或", "在", "为", "从", "到", "对", "及", "等", "哪", "哪些", "哪个", "什么", "怎么", "如何", "业绩", "达成率", "完成率", "事业部", "分公司", "代表处", "业务部", "城市分公司", "城市公司", "业务员", "业务代表", "负责人", "承接人", "细分业务", "国内业务部", "直营零售部", "跨境业务部", "商用", "消费者", "电商"}
    return {t for t in tokens if len(t) > 1 and t not in stop}


def title_match_score(question, title, report_title):
    qk = keyword_set(question)
    tk = keyword_set(title) | keyword_set(report_title)
    if not qk:
        return 1.0
    if not tk:
        return 0.0
    inter = qk & tk
    return len(inter) / len(qk)


def run_one(session, token, q):
    url = urljoin(BASE_URL, "/api/smart-chat")
    start = time.time()
    try:
        r = session.post(
            url,
            headers={"X-Auth-Token": token, "Content-Type": "application/json"},
            json={"question": q["question"]},
            timeout=PER_Q_TIMEOUT,
        )
        duration = round(time.time() - start, 2)
        if r.status_code >= 400:
            return {
                "status_code": r.status_code,
                "http_error": r.text[:2000],
                "duration": duration,
            }
        data = r.json()
        if data.get("error"):
            return {
                "status_code": r.status_code,
                "service_error": data.get("error"),
                "duration": duration,
                "raw": data,
            }
        route = data.get("route") or {}
        report_spec = data.get("report_spec") or {}
        card = extract_card_info(report_spec)
        result = {
            "status_code": r.status_code,
            "duration": duration,
            "requires_confirmation": bool(data.get("requires_confirmation") or route.get("requires_confirmation")),
            "dataset_ids": route.get("dataset_ids") or route.get("candidate_dataset_ids") or [],
            "intent": route.get("intent", ""),
            "decision": route.get("decision", ""),
            "display_title": data.get("display_title", ""),
            "effective_question": data.get("effective_question", ""),
            "report_title": card["report_title"],
            "answer_summary": card["answer_summary"][:800] if card["answer_summary"] else "",
            "narrative": card["narrative"][:800] if card["narrative"] else "",
            "kpis": card["kpis"],
            "sections": card["sections"],
            "charts": card["charts"],
            "accordions": card["accordions"],
            "scope": card["scope"],
            "row_count": data.get("row_count"),
            "sql": (data.get("sql") or "")[:1500],
            "confidence": data.get("confidence"),
            "analysis_excerpt": (data.get("analysis") or "")[:800],
        }
        return result
    except requests.exceptions.Timeout:
        return {"error": "timeout", "duration": round(time.time() - start, 2)}
    except Exception as exc:
        return {"error": str(exc), "trace": traceback.format_exc(), "duration": round(time.time() - start, 2)}


def evaluate(result, q):
    flags = []
    expected_ds = expected_dataset_id(q["target"])
    actual_ds_list = result.get("dataset_ids", [])

    if result.get("error") or result.get("service_error") or result.get("http_error"):
        flags.append("执行异常")
        return flags

    if q["target"] == "需确认":
        if not result.get("requires_confirmation"):
            flags.append("未按预期弹确认")
    else:
        if result.get("requires_confirmation"):
            flags.append("意外弹确认")

    if expected_ds is not None:
        if actual_ds_list and actual_ds_list[0] != expected_ds:
            flags.append(f"数据集不匹配(期望{expected_ds}, 实际{actual_ds_list})")

    if q["target"] == "跨数据集":
        if len(actual_ds_list) < 2 and not result.get("requires_confirmation"):
            flags.append("未识别跨数据集对比")

    if result.get("row_count") == 0 and result.get("kpis") == []:
        flags.append("结果为空")

    score = title_match_score(q["question"], result.get("display_title", ""), result.get("report_title", ""))
    if score < 0.3:
        flags.append("卡片标题与问题关联度低")

    return flags


def save_progress(results, out_json):
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)


def generate_report(results, out_md):
    total = len(results)
    anomaly = [r for r in results if r.get("flags")]
    lines = [
        "# SmartAsk 端到端测试报告",
        "",
        f"- 测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 问题总数：{total}",
        f"- 异常/待确认数：{len(anomaly)}",
        f"- 服务端点：{BASE_URL}/api/smart-chat",
        "",
        "## 汇总",
        "",
        "| 类别 | 数量 |",
        "|---|---|",
    ]
    cat_counts = {}
    for r in results:
        cat_counts[r.get("category", "未知")] = cat_counts.get(r.get("category", "未知"), 0) + 1
    for cat, cnt in sorted(cat_counts.items()):
        lines.append(f"| {cat} | {cnt} |")
    lines.append("")
    lines.append("## 异常问题索引")
    lines.append("")
    if anomaly:
        lines.append("| 编号 | 问题 | 预期 | 异常点 |")
        lines.append("|---|---|---|---|")
        for r in anomaly:
            lines.append(f"| {r['id']} | {r['question']} | {r['target']} | {'; '.join(r['flags'])} |")
    else:
        lines.append("未发现明显异常。")
    lines.append("")

    lines.append("## 详细记录")
    lines.append("")
    for r in results:
        lines.append(f"### {r['id']}：{r['question']}")
        lines.append("")
        lines.append(f"- **目标数据集**：{r['target']}")
        lines.append(f"- **预期行为**：{r['expected']}")
        res = r.get("result", {})
        if res.get("error") or res.get("service_error") or res.get("http_error"):
            lines.append(f"- **状态**：❌ 异常 - {res.get('error') or res.get('service_error') or res.get('http_error')[:200]}")
        elif res.get("status_code") == 200:
            lines.append("- **状态**：✅ 成功")
        else:
            lines.append(f"- **状态**：⚠️ HTTP {res.get('status_code')}")
        lines.append(f"- **耗时**：{res.get('duration', '-')}s")
        lines.append(f"- **路由决策**：{res.get('decision', '-')}")
        lines.append(f"- **意图**：{res.get('intent', '-')}")
        lines.append(f"- **是否需要确认**：{res.get('requires_confirmation', '-')}")
        lines.append(f"- **命中数据集**：{res.get('dataset_ids', '-')}")
        lines.append(f"- **显示标题**：{res.get('display_title', '-')}")
        lines.append(f"- **报告标题**：{res.get('report_title', '-')}")
        if res.get("kpis"):
            lines.append(f"- **KPI 卡**：{json.dumps(res['kpis'], ensure_ascii=False)}")
        if res.get("sections"):
            lines.append(f"- **章节**：{' / '.join(res['sections'])}")
        if res.get("charts"):
            lines.append(f"- **图表**：{' / '.join(res['charts'])}")
        if res.get("accordions"):
            lines.append(f"- **折叠面板**：{' / '.join(res['accordions'])}")
        if res.get("answer_summary"):
            lines.append(f"- **答案摘要**：{res['answer_summary']}")
        if res.get("narrative"):
            lines.append(f"- **叙述**：{res['narrative'][:500]}")
        sql = res.get("sql", "")
        if sql:
            lines.append(f"- **SQL 样例**：")
            lines.append("```sql")
            lines.append(sql)
            lines.append("```")
        if r.get("flags"):
            lines.append(f"- **⚠️ 异常点**：{'; '.join(r['flags'])}")
        lines.append("")

    with open(out_md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main():
    log("开始解析问题清单...")
    questions = parse_questions(MD_PATH)
    log(f"解析到 {len(questions)} 个问题")
    if not questions:
        log("没有问题，退出")
        sys.exit(1)

    session = requests.Session()
    token = login(session)
    log("登录成功")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_json = os.path.join(OUT_DIR, f"smartask_test_results_{ts}.json")
    out_md = os.path.join(OUT_DIR, f"smartask_test_report_{ts}.md")

    results = []
    for idx, q in enumerate(questions, 1):
        log(f"[{idx}/{len(questions)}] 提问：{q['question']}")
        res = run_one(session, token, q)
        record = {
            "id": q["id"],
            "category": q["id"][0] if q["id"] else "",
            "target": q["target"],
            "question": q["question"],
            "expected": q["expected"],
            "result": res,
            "flags": evaluate(res, q),
        }
        results.append(record)
        # 每题保存进度
        save_progress({"timestamp": ts, "total": len(questions), "results": results}, out_json)
        if res.get("error") == "timeout":
            log(f"  -> 超时，继续下一题")
        elif res.get("error") or res.get("service_error") or res.get("http_error"):
            log(f"  -> 异常：{res.get('error') or res.get('service_error') or res.get('http_error')[:120]}")
        else:
            log(f"  -> 完成，数据集 {res.get('dataset_ids')}，标题：{res.get('display_title', '')[:40]}")

    log("生成报告...")
    save_progress({"timestamp": ts, "total": len(questions), "results": results}, out_json)
    generate_report(results, out_md)
    log(f"报告已保存：{out_md}")
    log(f"原始结果：{out_json}")


if __name__ == "__main__":
    main()
