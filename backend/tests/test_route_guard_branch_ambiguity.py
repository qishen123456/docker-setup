import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smartask_advanced.skills.route_guard import RouteGuardSkill


class FakeRepo:
    def get_agent1_catalog(self):
        return []


class RouteGuardBranchAmbiguityTest(unittest.TestCase):
    def test_branch_only_cross_bu_question_requires_confirmation(self):
        question = "看下第一和倒数第一的分公司"
        candidates = [
            {"id": 11, "dataset_name": "消费者事业部任务达成分析（标准版）", "advanced_score": 88},
            {"id": 3, "dataset_name": "商用事业部", "advanced_score": 76},
        ]
        guard = RouteGuardSkill(FakeRepo())
        guard.organization_resolver.resolve = lambda *args, **kwargs: None

        result = guard.run(question=question, candidates=candidates)

        self.assertEqual(result["action"], "needs_confirmation")
        self.assertEqual(result["apply_dataset_ids"], [])
        self.assertIn("分公司", result["reason"])


if __name__ == "__main__":
    unittest.main()
