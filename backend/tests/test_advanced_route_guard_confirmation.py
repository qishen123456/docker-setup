import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smartask_advanced.service import AdvancedAskService


class FakeRepo:
    def get_agent1_catalog(self):
        return [
            {"id": 3, "dataset_name": "商用事业部", "dataset_code": "angel_business_2026"},
            {"id": 11, "dataset_name": "消费者事业部任务达成分析（标准版）", "dataset_code": "consumer_business_standard_v1"},
        ]


class FakeFallbackService:
    def __init__(self):
        self.repository = FakeRepo()

    def ask(self, **kwargs):
        raise AssertionError("needs_confirmation should short-circuit before fallback ask")

    def confirm_by_boss(self, **kwargs):
        return {}


class AdvancedRouteGuardConfirmationTest(unittest.TestCase):
    def test_ask_returns_confirmation_payload_when_route_guard_requires_confirmation(self):
        service = AdvancedAskService(fallback_service=FakeFallbackService())
        service._run_advanced_trace = lambda *args, **kwargs: {
            "trace_id": "trace-test",
            "effective_preferred_dataset_ids": [],
            "route_guard": {
                "action": "needs_confirmation",
                "reason": "问题只提到“分公司”，但当前候选同时包含商用事业部和消费者事业部，存在数据集歧义，需要先确认口径。",
                "recommended_dataset_ids": [3, 11],
                "organization_route": {},
            },
            "assets": [],
            "skills": [],
            "intent": {},
            "golden_sql": {},
        }

        result = service.ask(question="看下第一和倒数第一的分公司")

        self.assertTrue(result["requires_confirmation"])
        self.assertEqual(result["question"], "看下第一和倒数第一的分公司")
        self.assertGreaterEqual(len(result["confirmation_options"]), 2)
        labels = [item.get("label") for item in result["confirmation_options"]]
        self.assertIn("商用事业部", labels)
        self.assertIn("消费者事业部任务达成分析（标准版）", labels)


if __name__ == "__main__":
    unittest.main()
