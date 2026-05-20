from __future__ import annotations

from typing import Any, Dict, List


class AssetPackSkill:
    key = "asset_pack"

    def __init__(self, repository):
        self.repository = repository

    def run(self, question: str, candidates: List[Dict[str, Any]], limit: int = 3) -> Dict[str, Any]:
        snapshots: List[Dict[str, Any]] = []
        contexts: Dict[str, Dict[str, Any]] = {}
        for item in candidates[:limit]:
            dataset_id = int(item.get("id") or 0)
            if not dataset_id:
                continue
            try:
                context = self.repository.get_dataset_context(dataset_id, question, top_k_samples=8)
            except Exception as exc:
                snapshots.append(
                    {
                        "dataset_id": dataset_id,
                        "dataset_name": item.get("dataset_name") or f"数据集 {dataset_id}",
                        "error": str(exc),
                    }
                )
                continue

            contexts[str(dataset_id)] = context
            prompt_count = sum(len(rows or []) for rows in (context.get("agent_prompts") or {}).values())
            snapshots.append(
                {
                    "dataset_id": dataset_id,
                    "dataset_name": (context.get("dataset") or {}).get("dataset_name") or item.get("dataset_name"),
                    "business_domain": (context.get("dataset") or {}).get("business_domain") or item.get("business_domain"),
                    "dictionary_count": len(context.get("data_dictionary") or []),
                    "schema_count": len(context.get("schema_definition") or []),
                    "golden_sql_count": len(context.get("golden_sql_samples") or []),
                    "common_question_count": len(context.get("common_questions") or []),
                    "prompt_count": prompt_count,
                    "lld_ready": bool((context.get("lld_document") or {}).get("content")),
                    "golden_sql_examples": [
                        sample.get("question") or sample.get("intent_type") or f"样例 {sample.get('id')}"
                        for sample in (context.get("golden_sql_samples") or [])[:3]
                    ],
                    "dictionary_examples": [
                        item.get("semantic_name") or item.get("jsonb_key") or item.get("column_name")
                        for item in (context.get("data_dictionary") or [])[:6]
                    ],
                }
            )
        return {"assets": snapshots, "contexts": contexts}
