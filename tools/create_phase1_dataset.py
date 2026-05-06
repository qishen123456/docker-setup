from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import requests


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from dataset_copilot.syyb_rule_generator import BASE_SQL  # noqa: E402


BASE_URL = "http://127.0.0.1:5002"
SOURCE_DATASET_CODE = "angel_business_2026"
PHASE1_DATASET_CODE = "angel_business_2026_phase1"
PHASE1_DATASET_NAME = "商用事业部（阶段一升级版）"


def request_json(method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
    response = requests.request(method, url, timeout=120, **kwargs)
    try:
        body = response.json()
    except Exception:
        body = {"raw": response.text}
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {url} failed: {response.status_code} {body}")
    return body


def list_datasets() -> List[Dict[str, Any]]:
    body = request_json("GET", f"{BASE_URL}/api/bookshelves/datasets")
    return body.get("datasets") or []


def find_dataset(code: str) -> Dict[str, Any] | None:
    for item in list_datasets():
        if item.get("dataset_code") == code:
            return item
    return None


def full_dataset(dataset_id: int) -> Dict[str, Any]:
    return request_json("GET", f"{BASE_URL}/api/bookshelves/datasets/{dataset_id}/full")


def create_or_update_phase1_dataset(source_dataset: Dict[str, Any]) -> Dict[str, Any]:
    existing = find_dataset(PHASE1_DATASET_CODE)
    payload = {
        "dataset_code": PHASE1_DATASET_CODE,
        "dataset_name": PHASE1_DATASET_NAME,
        "business_domain": source_dataset.get("business_domain") or "安吉尔商用事业部销售业绩分析",
        "source_id": source_dataset.get("source_id") or 5,
        "description": "阶段一升级对照数据集：以字段字典、LLD 和少量标杆 SQL 教会系统口径，避免把问数做成答案库。",
        "is_active": True,
    }
    if existing:
        body = request_json("PUT", f"{BASE_URL}/api/bookshelves/datasets/{existing['id']}", json=payload)
        return body["dataset"]
    body = request_json("POST", f"{BASE_URL}/api/bookshelves/datasets", json=payload)
    return body["dataset"]


def wrap_base_sql(where_clause: str = "", order_clause: str = "条线 DESC, 层级 DESC, 上级名称, 节点名称", limit: int = 10000) -> str:
    sql = f"WITH 汇总结果 AS (\n{BASE_SQL}\n)\nSELECT *\nFROM 汇总结果"
    if where_clause:
        sql += f"\nWHERE {where_clause}"
    sql += f"\nORDER BY {order_clause}\nLIMIT {limit}"
    return sql


def phase1_golden_sql_samples() -> List[Dict[str, Any]]:
    return [
        {
            "intent_type": "summary",
            "question": "商用事业部整体达成率是多少",
            "sql_text": wrap_base_sql("层级 IN ('分公司','业务部')", "条线 DESC, 达成率 DESC, 节点名称", 100),
            "tags": ["phase1", "summary", "verified_candidate"],
            "quality_score": 92,
            "is_active": True,
        },
        {
            "intent_type": "single_entity",
            "question": "东部分公司业绩怎么样",
            "sql_text": wrap_base_sql(
                "节点名称 = '东部分公司' OR 上级名称 = '东部分公司'",
                "层级 DESC, 上级名称, 节点名称",
                10000,
            ),
            "tags": ["phase1", "single_entity", "east_branch"],
            "quality_score": 95,
            "is_active": True,
        },
        {
            "intent_type": "ranking_template",
            "question": "按某个组织层级查看达成率排名",
            "sql_text": wrap_base_sql("层级 = '代表处'", "达成率 ASC, 剩余任务金额 DESC, 节点名称", 20),
            "tags": ["phase1", "ranking_template", "representative_office"],
            "quality_score": 96,
            "is_active": True,
        },
    ]


def strip_ids(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned = []
    for item in items or []:
        copied = dict(item)
        for key in ("id", "dataset_id", "created_at", "updated_at", "last_used_at", "usage_count"):
            copied.pop(key, None)
        cleaned.append(copied)
    return cleaned


def build_phase1_payload(source_full: Dict[str, Any]) -> Dict[str, Any]:
    lld_documents = strip_ids(source_full.get("lld_documents") or [])
    if lld_documents:
        lld_documents[0]["title"] = "商用事业部阶段一升级 LLD"
        lld_documents[0]["content"] = (
            str(lld_documents[0].get("content") or "")
            + "\n\n## 阶段一升级说明\n"
            + "- Golden SQL 只保留少量标杆模板，用来说明字段口径和聚合方式，不作为答案库。\n"
            + "- 排名类问题必须走排名 SQL，不能被实体过滤误命中。\n"
            + "- SQL 返回 0 行时不能直接包装成正式报告，必须进入自检或口径提示。\n"
            + "- 当前目标是对比新版和旧版问数结果差异，不替换原数据集。\n"
        )

    agent_prompts = strip_ids(source_full.get("agent_prompts") or [])
    for prompt in agent_prompts:
        agent_no = int(prompt.get("agent_no") or 0)
        if agent_no == 1:
            prompt["prompt_content"] = str(prompt.get("prompt_content") or "") + "\n8. 阶段一升级版：先识别意图类型，排名/Top/Bottom/风险问题不得当作实体名过滤。"
        if agent_no == 2:
            prompt["prompt_content"] = str(prompt.get("prompt_content") or "") + "\n9. 阶段一升级版：Golden SQL 只是口径模板；必须根据用户问题动态生成 SQL，不得把样例当固定答案。"
        if agent_no == 3:
            prompt["prompt_content"] = str(prompt.get("prompt_content") or "") + "\n10. 阶段一升级版：执行后如果返回 0 行，必须判断是否为实体误过滤、排名意图误识别或层级条件过窄。"
        if agent_no == 4:
            prompt["prompt_content"] = str(prompt.get("prompt_content") or "") + "\n7. 阶段一升级版：报告必须说明 SQL 来源和结果可信度；空结果不得包装成经营结论。"

    common_questions = [
        {"question_text": "商用事业部整体达成率是多少", "sort_order": 10, "is_active": True},
        {"question_text": "东部分公司业绩怎么样", "sort_order": 20, "is_active": True},
        {"question_text": "哪些代表处达成率最低", "sort_order": 30, "is_active": True},
        {"question_text": "业务代表年度开单金额 Top10 是谁", "sort_order": 40, "is_active": True},
        {"question_text": "哪些节点达成率低于10%", "sort_order": 50, "is_active": True},
        {"question_text": "东部表现怎么样", "sort_order": 60, "is_active": True},
    ]

    regression_cases = [
        {
            "case_type": "summary",
            "question_text": "商用事业部整体达成率是多少",
            "expected_focus": "返回分公司/业务部层级汇总，不应为空",
            "expected_intent": "generate_sql",
            "sort_order": 10,
            "is_active": True,
        },
        {
            "case_type": "single_entity",
            "question_text": "东部分公司业绩怎么样",
            "expected_focus": "返回东部分公司及下级代表处/业务代表",
            "expected_intent": "generate_sql",
            "sort_order": 20,
            "is_active": True,
        },
        {
            "case_type": "ranking",
            "question_text": "哪些代表处达成率最低",
            "expected_focus": "返回代表处层级，按达成率升序，不允许空报告",
            "expected_intent": "generate_sql",
            "sort_order": 30,
            "is_active": True,
        },
        {
            "case_type": "ranking",
            "question_text": "业务代表年度开单金额 Top10 是谁",
            "expected_focus": "返回业务代表层级，按年度开单金额降序",
            "expected_intent": "generate_sql",
            "sort_order": 40,
            "is_active": True,
        },
        {
            "case_type": "risk",
            "question_text": "哪些节点达成率低于10%",
            "expected_focus": "返回低达成节点，按达成率升序",
            "expected_intent": "generate_sql",
            "sort_order": 50,
            "is_active": True,
        },
        {
            "case_type": "confirmation",
            "question_text": "东部表现怎么样",
            "expected_focus": "需要明确整体、代表处还是业务代表口径",
            "expected_intent": "confirm",
            "sort_order": 60,
            "is_active": True,
        },
    ]

    synonyms = strip_ids(source_full.get("synonyms") or [])
    synonyms.extend(
        [
            {"synonym": "阶段一升级版", "normalized_synonym": "阶段一升级版", "weight": 10},
            {"synonym": "新版商用事业部", "normalized_synonym": "新版商用事业部", "weight": 9},
            {"synonym": "升级版商用事业部", "normalized_synonym": "升级版商用事业部", "weight": 9},
        ]
    )

    payload = {
        "synonyms": synonyms,
        "lld_documents": lld_documents,
        "data_dictionary": strip_ids(source_full.get("data_dictionary") or []),
        "schema_definition": strip_ids(source_full.get("schema_definition") or []),
        "table_relations": strip_ids(source_full.get("table_relations") or []),
        "golden_sql_samples": phase1_golden_sql_samples(),
        "agent_prompts": agent_prompts,
        "common_questions": common_questions,
        "external_configs": strip_ids(source_full.get("external_configs") or []),
        "regression_cases": regression_cases,
    }
    if source_full.get("report_config"):
        payload["report_config"] = source_full["report_config"]
    return payload


def main() -> None:
    source_dataset = find_dataset(SOURCE_DATASET_CODE)
    if not source_dataset:
        raise SystemExit(f"source dataset not found: {SOURCE_DATASET_CODE}")

    phase1_dataset = create_or_update_phase1_dataset(source_dataset)
    source_full = full_dataset(int(source_dataset["id"]))
    payload = build_phase1_payload(source_full)
    request_json("PUT", f"{BASE_URL}/api/bookshelves/datasets/{phase1_dataset['id']}/full", json=payload)

    print(
        json.dumps(
            {
                "ok": True,
                "dataset_id": phase1_dataset["id"],
                "dataset_code": PHASE1_DATASET_CODE,
                "dataset_name": PHASE1_DATASET_NAME,
                "golden_sql_samples": len(payload["golden_sql_samples"]),
                "regression_cases": len(payload["regression_cases"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
