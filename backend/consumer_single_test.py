#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单个问题完整链路测试（消费者数据集 id=13），带超时。"""
import json
import os
import signal
import sys

os.chdir('/app/backend')
sys.path.insert(0, '/app/backend')

from ask_flow import ask_flow_controller
from ask_flow.contracts import AskRequest


def timeout_handler(signum, frame):
    raise TimeoutError("Question processing timeout")


def test(question, timeout_secs=90):
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_secs)
    try:
        req = AskRequest(
            question=question,
            preferred_dataset_ids=[13],
            allowed_dataset_ids=[13],
            current_user={"role": "admin", "username": "tester"},
        )
        result = ask_flow_controller.ask(req)
        signal.alarm(0)
        route = result.get("route", {})
        dr = (result.get("dataset_results") or [{}])[0]
        spec = dr.get("report_spec") or {}

        summary = {
            "question": question,
            "status": "error" if (dr.get("error") or result.get("error")) else "success",
            "route": {
                "dataset_ids": route.get("dataset_ids"),
                "intent": route.get("intent"),
                "requires_confirmation": route.get("requires_confirmation"),
                "refined_query": route.get("refined_query"),
            },
            "row_count": len(dr.get("rows", [])),
            "focus_node": spec.get("scope", {}).get("focusNode"),
            "kpis": [
                {"label": k.get("label"), "displayValue": k.get("displayValue")}
                for k in (spec.get("kpis") or [])
            ],
            "sections": [
                {"title": s.get("title"), "narrative": s.get("narrative", "")[:200]}
                for s in (spec.get("sections") or [])
            ],
            "error": dr.get("error") or result.get("error") or "",
        }
        return summary
    except TimeoutError as exc:
        return {
            "question": question,
            "status": "timeout",
            "error": str(exc),
        }
    except Exception as exc:
        return {
            "question": question,
            "status": "exception",
            "error": str(exc),
        }


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "消费者事业部的年度开单是多少？"
    print(json.dumps(test(q), ensure_ascii=False, indent=2))
