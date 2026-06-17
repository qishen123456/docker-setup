import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from four_agent_ask import FourAgentAskService


class BasicRouteBranchDisambiguationTest(unittest.TestCase):
    def test_detect_ambiguity_returns_real_dataset_options_for_branch_cross_bu(self):
        service = object.__new__(FourAgentAskService)
        ranked_candidates = [
            ({"id": 11, "dataset_name": "消费者事业部任务达成分析（标准版）"}, 88),
            ({"id": 3, "dataset_name": "商用事业部"}, 82),
        ]

        result = service._detect_ambiguity("看下第一和倒数第一的分公司", ranked_candidates)

        self.assertIsNotNone(result)
        self.assertTrue(result["requires_confirmation"])
        self.assertEqual(result.get("confirmation_type"), "dataset_disambiguation")
        options = result.get("confirmation_options") or []
        self.assertEqual(len(options), 2)
        labels = [item.get("label") for item in options]
        self.assertIn("商用事业部", labels)
        self.assertIn("消费者事业部任务达成分析（标准版）", labels)
        for item in options:
            self.assertEqual(len(item.get("dataset_ids") or []), 1)

    def test_explicit_consumer_alias_skips_dataset_confirmation(self):
        service = object.__new__(FourAgentAskService)
        service._dataset_alias_match_score = FourAgentAskService._dataset_alias_match_score.__get__(service, FourAgentAskService)
        ranked_candidates = [
            (
                {
                    "id": 11,
                    "dataset_name": "消费者事业部任务达成分析（标准版）",
                    "dataset_code": "consumer_business_standard_v1",
                    "business_domain": "消费者事业部年度任务达成与业务线分析",
                    "synonyms": ["消费者事业部", "消费者事业", "消费者"],
                },
                88,
            ),
            (
                {
                    "id": 3,
                    "dataset_name": "商用事业部（阶段一升级版）",
                    "dataset_code": "angel_business_2026_phase1",
                    "business_domain": "商用事业部",
                    "synonyms": ["商用事业部", "商用"],
                },
                82,
            ),
        ]

        result = service._detect_ambiguity("消费者事业部整体达成率是多少", ranked_candidates)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
