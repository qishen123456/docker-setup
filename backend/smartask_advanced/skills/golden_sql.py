from __future__ import annotations

from typing import Any, Dict


class GoldenSqlSkill:
    key = "golden_sql"

    @staticmethod
    def run(contexts: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        samples = []
        for dataset_id, context in (contexts or {}).items():
            dataset = context.get("dataset") or {}
            for sample in context.get("golden_sql_samples") or []:
                samples.append(
                    {
                        "dataset_id": dataset_id,
                        "dataset_name": dataset.get("dataset_name"),
                        "sample_id": sample.get("id"),
                        "question": sample.get("question"),
                        "intent_type": sample.get("intent_type"),
                        "match_score": int(sample.get("match_score") or 0),
                        "quality_score": int(sample.get("quality_score") or 0),
                        "tags": sample.get("tags") or [],
                    }
                )
        samples.sort(key=lambda item: (item.get("match_score") or 0, item.get("quality_score") or 0), reverse=True)
        return {
            "count": len(samples),
            "top_samples": samples[:5],
            "best_sample": samples[0] if samples else None,
        }
