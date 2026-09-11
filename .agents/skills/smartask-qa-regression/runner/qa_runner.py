#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SmartAsk 问数回归测试 runner —— 跑在容器内，直接 import 最新代码。

用法:
    python qa_runner.py <case.json> [id前缀过滤]

支持三种用例：
1. 单轮直查：question + asserts
2. 多轮追问：turns（同 session 连续问）
3. 弹确认走完：question + confirm（数组，每个分支 = 选哪个数据集 + 确认后的 asserts）
   会真正调 confirm_by_boss 走完流程，而不是停在"弹确认"。

用例级可选 "user" 字段覆盖默认 USER（缺省字段回退默认 super_admin）。

自检失败输出 ENV-FAIL 并 exit 1。
"""
import sys
import io
import os
import re
import json
import hashlib
import datetime
import importlib
import contextlib

sys.path.insert(0, "/app/backend")

USER = {"role": "super_admin", "id": 99999, "username": "qa",
        "organization_codes": ["*"], "organization_node_ids": ["*"]}

# path 段语法 dataset_results[ds=62]：在 list 中按 dataset_id 选元素
_DS_SELECTOR = re.compile(r"^(\w+)\[ds=(\d+)\]$")


# ============================================================ 环境自检
def preflight():
    """返回 (errs, pg_status)。pg_status = [(数据源名, None 或失败原因)]，供报告头展示。

    PG 探活分级：跳过 is_active=false 的源；全部活跃源不可达才 ENV-FAIL，
    至少一个可达即放行（死源降级为警告，不阻断）。
    """
    errs = []
    pg_status = []
    try:
        import psycopg2
        from config_manager import get_datasources, decode_secret
        dss = get_datasources()
        pgs = [d for d in dss
               if d.get("type") == "postgresql" and d.get("is_active", True)]
        if not pgs:
            errs.append("无活跃的 PostgreSQL 数据源")
        for pg in pgs:  # datasources.json 有多个 PG 源，逐一探活
            name = pg.get("name") or pg.get("id") or pg.get("database_name") or "(未命名)"
            try:
                # get_datasources() 只返回 password_b64（可能是加密串而非纯 base64），统一走 decode_secret
                pw = decode_secret(pg.get("password_b64") or "") or None
                conn = psycopg2.connect(host=pg["host"], port=pg["port"],
                                        database=pg["database_name"], user=pg["username"], password=pw)
                conn.cursor().execute("SELECT 1")
                conn.close()
                pg_status.append((name, None))
            except Exception as e:
                pg_status.append((name, str(e).splitlines()[0]))
        if pgs and all(reason for _, reason in pg_status):
            errs.append("全部活跃 PostgreSQL 数据源不可达（跑下去必是全假'没结果'）")
    except Exception as e:
        errs.append("PostgreSQL 自检失败（将导致假'没结果'）: %s" % e)

    try:
        importlib.import_module("four_agent_ask")
    except Exception as e:
        errs.append("four_agent_ask 导入失败: %s" % e)

    return errs, pg_status


# ============================================================ 报告头：md5 自检（报告项，非阻断闸）
def _file_md5_mtime(path):
    try:
        with open(path, "rb") as f:
            md5 = hashlib.md5(f.read()).hexdigest()
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
        return md5, mtime
    except Exception as e:
        return "(读取失败: %s)" % e, "-"


def print_drift_header(case_path):
    """容器内无 .git，只打 md5+mtime。宿主机比对: md5sum backend/four_agent_ask.py"""
    print("=" * 78)
    print("代码漂移自检（报告项，不阻断；宿主机比对: md5sum backend/four_agent_ask.py）")
    for label, path in (("four_agent_ask.py", "/app/backend/four_agent_ask.py"),
                        ("qa_runner.py", os.path.abspath(__file__)),
                        ("用例文件", case_path)):
        md5, mtime = _file_md5_mtime(path)
        print("  %-18s md5=%s  mtime=%s  (%s)" % (label, md5, mtime, path))
    print("=" * 78)


# ============================================================ 断言引擎
def get_path(obj, path):
    for k in path.split("."):
        if obj is None:
            return None
        m = _DS_SELECTOR.match(k)
        if m:  # dataset_results[ds=62]：在 list 中找 dataset_id==62 的元素
            key, ds_id = m.group(1), int(m.group(2))
            if not isinstance(obj, dict):
                return None
            obj = obj.get(key)
            if not isinstance(obj, list):
                return None
            obj = next((e for e in obj
                        if isinstance(e, dict) and e.get("dataset_id") == ds_id), None)
            continue
        if isinstance(obj, list):
            try:
                obj = obj[int(k)]
            except (ValueError, IndexError):
                return None
        elif isinstance(obj, dict):
            obj = obj.get(k)
        else:
            return None
    return obj


def _dataset_for_assert(result, path):
    """从 dataset_results.0 或 dataset_results[ds=N] 取当前结果。"""
    return get_path(result, path) if isinstance(result, dict) else None


def _rows_for_assert(result, path):
    dataset = _dataset_for_assert(result, path)
    if not isinstance(dataset, dict):
        return None
    rows = dataset.get("rows")
    return rows if isinstance(rows, list) else []


def _analysis_text(result, path):
    """analysis 断言允许简写 ``analysis``，默认检查首个数据集解读。"""
    if path in ("analysis", "dataset_results.0.analysis"):
        dataset = _dataset_for_assert(result, "dataset_results.0")
        return dataset.get("analysis") if isinstance(dataset, dict) else None
    return get_path(result, path)


def _node_hint(question):
    """提取题干的显式节点名，过滤时间、意图和层级词。"""
    if not question:
        return ""
    text = re.sub(r"去年|今年|前年|往年|20\d{2}年", "", str(question))
    candidates = re.findall(r"[\u4e00-\u9fff\d]{1,12}(?:分公司|代表处|业务部|城市公司)", text)
    if not candidates:
        return ""
    hint = max(candidates, key=len)
    hint = re.sub(r"^(?:各|每个)", "", hint)
    hint = re.sub(r"(?:业绩|排名|条线|区域|整体|盘点|咋样|怎么样|最近|的)", "", hint)
    return hint.strip()


def _parse_number(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    multiplier = 1.0
    if "亿" in text:
        multiplier = 1e8
        text = text.replace("亿", "")
    elif "万" in text:
        multiplier = 1e4
        text = text.replace("万", "")
    elif "千" in text:
        multiplier = 1e3
        text = text.replace("千", "")
    if "%" in text:
        text = text.replace("%", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0)) * multiplier
    except (TypeError, ValueError):
        return None


def _kpi_value(kpi):
    if not isinstance(kpi, dict):
        return None
    for key in ("value", "displayValue", "display_value", "raw", "number"):
        if kpi.get(key) not in (None, ""):
            parsed = _parse_number(kpi.get(key))
            if parsed is not None:
                return parsed
    return None


def _kpi_label(kpi):
    if not isinstance(kpi, dict):
        return ""
    return "".join(str(kpi.get(k) or "") for k in ("label", "name", "title", "key", "column"))


def _find_kpi(report_spec, metric):
    kpis = report_spec.get("kpis") or [] if isinstance(report_spec, dict) else []
    aliases = [str(metric), "任务金额" if metric == "总任务金额" else metric]
    for kpi in kpis:
        if not isinstance(kpi, dict):
            continue
        label = _kpi_label(kpi)
        if any(alias and alias in label for alias in aliases):
            return kpi
    return None


def _matches(got, op, expect, question=None, result=None, path=None):
    if op in ("entity_exists", "rows_semantic_check"):
        rows = _rows_for_assert(result, path) if result is not None and path else []
        if op == "entity_exists":
            if not rows:
                return True
            expected = str(expect or "").strip()
            return any(expected and expected in str(row.get("节点名称") or "") for row in rows if isinstance(row, dict))
        hint = _node_hint(question)
        if not rows:
            # 空结果只有在解读明确提示“未找到”才算通过。
            analyses = []
            if isinstance(result, dict):
                for item in result.get("dataset_results") or []:
                    if isinstance(item, dict):
                        analyses.append(str(item.get("analysis") or ""))
            return "未找到" in "".join(analyses)
        if not hint:
            return True
        return any(hint in str(row.get("节点名称") or "") for row in rows if isinstance(row, dict))
    if op == "kpi_equals_sum":
        dataset = _dataset_for_assert(result, path) if result is not None and path else {}
        if not isinstance(dataset, dict):
            return False
        kpi = _find_kpi(dataset.get("report_spec") or {}, str(expect or ""))
        if not kpi:
            return False
        total = _kpi_value(kpi)
        if total is None:
            return False
        metric = str(expect or "")
        row_values = []
        for row in dataset.get("rows") or []:
            if not isinstance(row, dict):
                continue
            value = row.get(metric)
            if value is None and metric == "总任务金额":
                value = row.get("任务金额")
            parsed = _parse_number(value)
            if parsed is not None:
                row_values.append(parsed)
        if not row_values:
            return False
        return abs(total - sum(row_values)) <= max(abs(total), 1.0) * 0.01
    if op == "analysis_contains":
        return str(expect) in str(got or "")
    if op == "analysis_not_contains":
        return str(expect) not in str(got or "")
    if op == "eq":
        return got == expect
    if op == "contains":
        return str(expect) in str(got)
    if op == "not_contains":
        return str(expect) not in str(got)
    if op in ("gt", "gte", "lt", "lte", "range"):
        # 非数值（含 None / 字符串）一律 False，不抛 TypeError
        if not isinstance(got, (int, float)) or isinstance(got, bool):
            return False
        if op == "gt":
            return got > expect
        if op == "gte":
            return got >= expect
        if op == "lt":
            return got < expect
        if op == "lte":
            return got <= expect
        return expect[0] <= got <= expect[1]
    if op == "nonempty":
        return got not in (None, "", [], {})
    return False


def sql_summary(sql):
    """仅用于报告展示；断言匹配用完整 SQL 文本，不用本摘要。"""
    if not sql:
        return ""
    keys = []
    for line in sql.splitlines():
        s = line.strip()
        if any(k in s.upper() for k in ("ORDER BY", "LIMIT", "WHERE")):
            keys.append(s[:90])
    return " | ".join(keys[:4])


def _run_assert(r, a):
    """返回 (path, got, status)，status ∈ PASS / FAIL / CONFIRM / EXC"""
    path = a["path"]
    op = a["op"]
    expect = a.get("expect")

    try:
        if op == "allow_confirm":
            confirm = isinstance(r, dict) and r.get("requires_confirmation")
            return ("requires_confirmation", confirm,
                    "CONFIRM" if confirm else "FAIL(未弹确认)")

        # .sql 的 contains/not_contains 对完整 SQL 文本匹配；analysis 支持显式 analysis_* 操作符，
        # 也兼容 path=analysis + contains/not_contains 的简写。
        analysis_ops = {"contains": "analysis_contains", "not_contains": "analysis_not_contains"}
        effective_op = analysis_ops.get(op, op) if path in ("analysis", "dataset_results.0.analysis") else op
        got = _analysis_text(r, path) if effective_op in ("analysis_contains", "analysis_not_contains") else get_path(r, path)
        ok = _matches(got, effective_op, expect, question=r.get("question") if isinstance(r, dict) else None,
                       result=r, path=path)
        return (path, got, "PASS" if ok else "FAIL")
    except Exception as e:  # 单条断言崩溃不许炸掉整个 runner
        return (path, repr(e), "EXC")


def _err_row(r):
    """ask/confirm 结果被吞成 {"error": ...} 时返回错误行，否则 None。"""
    if isinstance(r, dict) and r.get("error"):
        return ("error", r["error"], "EXC")
    return None


def _ask(svc, q, sid, user):
    with contextlib.redirect_stdout(io.StringIO()):
        return svc.ask(question=q, session_id=sid, conversation_history=None, current_user=user)


def _confirm(svc, r, sel_ds, user):
    """走完 confirm：从 r 的 confirmation_options 找匹配 sel_ds 的选项并 confirm。"""
    opts = r.get("confirmation_options") or []
    opt = None
    for o in opts:
        if set(o.get("dataset_ids") or []) == set(sel_ds):
            opt = o
            break
    if opt is None:
        return None, None
    with contextlib.redirect_stdout(io.StringIO()):
        r2 = svc.confirm_by_boss(
            session_id=r.get("session_id"),
            selected_option=opt.get("label") or "",
            selected_dataset_ids=sel_ds,
            option_id=opt.get("id") or "",
            current_user=user,
        )
    return opt, r2


# ============================================================ 用例执行
def run_case(case, svc):
    cid = case.get("id")
    if not cid:  # 与 main 的过滤口径一致，缺 id 给干净报错而不是 KeyError
        return {"id": "(缺id)", "source": case.get("source", ""),
                "turns": [{"q": "", "results": [("case", "用例缺 id 字段", "EXC")]}]}
    out = {"id": cid, "source": case.get("source", ""), "turns": []}
    sid = "qa-" + str(cid)
    user = dict(USER)  # 用例级 user 覆盖，缺省字段回退默认 super_admin
    user.update(case.get("user") or {})

    # 多轮直查（同 session 连续问）
    if "turns" in case:
        for turn in case["turns"]:
            q = turn["question"]
            try:
                r = _ask(svc, q, sid, user)
            except Exception as e:
                out["turns"].append({"q": q, "results": [("EXC", repr(e), "EXC")]})
                continue
            err = _err_row(r)  # error 特判：跳过该 turn 其余断言，避免一片 None FAIL 噪音
            if err:
                out["turns"].append({"q": q, "results": [err]})
                continue
            results = [_run_assert(r, a) for a in turn.get("asserts", [])]
            out["turns"].append({"q": q, "results": results})
        return out

    q = case["question"]
    try:
        r = _ask(svc, q, sid, user)
    except Exception as e:
        out["turns"].append({"q": q, "results": [("EXC", repr(e), "EXC")]})
        return out

    err = _err_row(r)
    if err:
        out["turns"].append({"q": q, "results": [err]})
        return out

    # 直查断言
    results = [_run_assert(r, a) for a in case.get("asserts", [])]
    out["turns"].append({"q": q, "results": results})

    # 弹确认走完：每个分支重新 ask + confirm + 断言
    # 2026-09-03：分支各自用独立 sid（-cf0/-cf1…）。分支是"平行宇宙"（选2 vs 选3），
    # 共享 sid 会让上一分支 confirm 写入的短期记忆污染下一分支的 ask——
    # 实测 N6 第二分支被记忆劫持改弹节点级确认卡（选项无 dataset_ids），误报"找不到选项"。
    for branch_idx, branch in enumerate(case.get("confirm", [])):
        sel_ds = branch.get("select", {}).get("dataset_ids")
        if not sel_ds:
            out["turns"].append({"q": q + " → confirm(缺select)", "results": [("confirm", None, "FAIL(缺select)")]})
            continue
        try:
            r_ask = _ask(svc, q, f"{sid}-cf{branch_idx}", user)
        except Exception as e:
            out["turns"].append({"q": q + " → 选{}".format(sel_ds), "results": [("EXC", repr(e), "EXC")]})
            continue
        err = _err_row(r_ask)
        if err:
            out["turns"].append({"q": q + " → 选{}".format(sel_ds), "results": [err]})
            continue
        if not r_ask.get("requires_confirmation"):
            out["turns"].append({"q": q + " → 选{}".format(sel_ds),
                                 "results": [("confirm", "未弹确认", "FAIL(应弹确认)")]})
            continue
        try:
            opt, r2 = _confirm(svc, r_ask, sel_ds, user)
        except Exception as e:  # confirm_by_boss 异常不许炸掉整轮回归
            out["turns"].append({"q": q + " → 选{}".format(sel_ds), "results": [("EXC", repr(e), "EXC")]})
            continue
        if r2 is None:
            opts_summary = [o.get("dataset_ids") for o in (r_ask.get("confirmation_options") or [])]
            out["turns"].append({"q": q + " → 选{}".format(sel_ds),
                                 "results": [("confirm", opts_summary, "FAIL(找不到选项)")]})
            continue
        err = _err_row(r2)
        if err:
            out["turns"].append({"q": q + " → 选{}".format(sel_ds), "results": [err]})
            continue
        cresults = [_run_assert(r2, a) for a in branch.get("asserts", [])]
        out["turns"].append({"q": q + " → 选{}".format(sel_ds), "results": cresults})

    return out


# ============================================================ 报告
def report(results):
    total = pass_n = fail_n = confirm_n = exc_n = 0
    print()
    print("=" * 116)
    print(f"{'用例':<10} {'来源':<20} {'问题':<30} {'断言':<30} {'实测':<28} 结果")
    print("=" * 116)
    for c in results:
        for t in c["turns"]:
            q = t["q"]
            for path, got, status in t["results"]:
                total += 1
                if status == "PASS":
                    pass_n += 1
                elif status == "CONFIRM":
                    confirm_n += 1
                elif status == "EXC":
                    exc_n += 1
                else:
                    fail_n += 1
                # .sql 路径展示截断摘要（断言用的是完整 SQL）
                got_s = sql_summary(str(got)) if str(path).endswith(".sql") else str(got)
                got_s = got_s[:26]
                print(f"{c['id']:<10} {c['source']:<20} {q:<30} {path:<30} {got_s:<28} {status}")
    print("=" * 116)
    print(f"合计 {total} | PASS {pass_n} | FAIL {fail_n} | CONFIRM {confirm_n} | EXC {exc_n}")
    return fail_n + exc_n


# ============================================================ main
def main():
    if len(sys.argv) < 2:
        print("用法: python qa_runner.py <case.json> [id前缀过滤]")
        sys.exit(2)
    case_path = sys.argv[1]
    id_filter = sys.argv[2] if len(sys.argv) > 2 else ""

    errs, pg_status = preflight()
    if pg_status:  # 每个活跃 PG 源的连通结果进报告头（含被放行的死源警告）
        print("PG 探活：")
        for name, reason in pg_status:
            print("  %-24s %s" % (name, "OK" if reason is None else "不可达(警告): " + reason))
    if errs:
        print("✗ ENV-FAIL 自检失败，中止：")
        for e in errs:
            print("  -", e)
        sys.exit(1)

    print_drift_header(case_path)

    try:
        with open(case_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("✗ 用例文件不可读或 JSON 非法: %s (%s)" % (case_path, e))
        sys.exit(2)
    cases = data.get("cases", [])
    # variants.json 是矩阵而不是 cases 数组：自动展平为可执行 case，保留每组 source 锚点。
    if not cases and data.get("groups"):
        cases = []
        for group in data.get("groups", []):
            category = group.get("category", "未分类")
            for variant in group.get("variants", []):
                case = dict(variant)
                case["source"] = "variants.json category=" + category
                if "assert" in case:
                    case["asserts"] = [case.pop("assert")]
                cases.append(case)
    if id_filter:
        cases = [c for c in cases if str(c.get("id", "")).startswith(id_filter)]
        print(f"过滤后 {len(cases)} 个用例（前缀 {id_filter}）")

    # skip 标记：数据前提不存在等原因暂停的用例——不执行、不打 LLM、不计入断言，单独列示
    skipped = [c for c in cases if c.get("skip")]
    cases = [c for c in cases if not c.get("skip")]
    for c in skipped:
        print(f"SKIP {c.get('id')}: {c.get('skip_reason') or '未注明原因'}")

    from four_agent_ask import four_agent_ask_service as svc

    results = [run_case(c, svc) for c in cases]
    fail_count = report(results)
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
