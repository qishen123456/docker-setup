import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smartask_advanced.service import AdvancedAskService
from smartask_advanced.skills.route_guard import RouteGuardSkill


class FakeRepo:
    def get_agent1_catalog(self):
        return []


class AdvancedCrossDatasetTest(unittest.TestCase):
    def test_manual_single_selection_is_overridden_by_explicit_cross_dataset_compare(self):
        guard = RouteGuardSkill(FakeRepo())
        guard.organization_resolver.resolve = lambda *args, **kwargs: {
            "dataset_ids": [3],
            "candidate_dataset_ids": [3, 11],
            "requires_confirmation": True,
            "organization_mentions": [
                {"node_name": "商用事业部", "dataset_ids": [3], "dataset_names": ["商用事业部"]},
                {"node_name": "消费者事业部", "dataset_ids": [11], "dataset_names": ["消费者"]},
            ],
        }

        result = guard.run(
            question="商用事业部和消费者的目标达成对比",
            candidates=[],
            preferred_dataset_ids=[3],
        )

        self.assertEqual(result["action"], "cross_dataset_compare")
        self.assertEqual(result["apply_dataset_ids"], [3, 11])

    def test_cross_dataset_conclusion_is_prepended_to_first_dataset_analysis(self):
        service = AdvancedAskService(fallback_service=object())
        result = {
            "analysis": "原始综合分析",
            "dataset_results": [
                {
                    "dataset_name": "商用事业部",
                    "analysis": "商用原始分析",
                    "report_spec": {
                        "kpis": [
                            {"label": "累计总任务金额", "value": 455000000},
                            {"label": "累计年度开单金额", "value": 71880000},
                            {"label": "整体达成率", "value": 15.8},
                        ]
                    },
                },
                {
                    "dataset_name": "消费者事业部",
                    "analysis": "消费者原始分析",
                    "report_spec": {
                        "kpis": [
                            {"label": "累计总任务金额", "value": 300000000},
                            {"label": "累计年度开单金额", "value": 90000000},
                            {"label": "整体达成率", "value": 30},
                        ]
                    },
                },
            ],
        }

        payload = service._apply_cross_dataset_conclusion(result)

        self.assertTrue(payload["applied"])
        self.assertIn("跨数据集对比结论", result["analysis"])
        self.assertIn("消费者事业部达成率30%", result["dataset_results"][0]["analysis"])
        self.assertIn("高于商用事业部14.2个百分点", result["dataset_results"][0]["analysis"])


if __name__ == "__main__":
    unittest.main()
