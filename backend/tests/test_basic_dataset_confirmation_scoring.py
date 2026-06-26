import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from disambiguation.scoring import needs_llm_arbitration, score_snapshot
from four_agent_ask import FourAgentAskService


def _ctx(score: int, dataset_id: int = 1) -> tuple:
    return ({"id": dataset_id, "dataset_name": f"数据集{dataset_id}"}, {}, score)


class BasicDatasetConfirmationScoringTest(unittest.TestCase):
    def test_clear_winner_with_explicit_scope_does_not_arbitrate(self):
        """头部数据集名称已命中且大幅领先，不应进入确认。"""
        contexts = [
            _ctx(100, 1),
            _ctx(55, 2),
        ]
        question = "消费者事业部的业绩"
        self.assertFalse(needs_llm_arbitration(question, contexts, []))

    def test_close_runner_up_still_arbitrates(self):
        """亚军分数也很高且差距很小，仍需要确认。"""
        contexts = [
            _ctx(90, 1),
            _ctx(78, 2),
        ]
        question = "分公司业绩"
        self.assertTrue(needs_llm_arbitration(question, contexts, []))

    def test_low_score_still_arbitrates(self):
        """最高分本身不高，需要确认。"""
        contexts = [
            _ctx(65, 1),
            _ctx(30, 2),
        ]
        question = "看下业绩"
        self.assertTrue(needs_llm_arbitration(question, contexts, []))

    def test_scope_keyword_with_explicit_scope_does_not_force_arbitrate(self):
        """问题含'分公司'但已明确数据集，不应仅因 margin 不高而确认。"""
        contexts = [
            _ctx(95, 1),
            _ctx(50, 2),
        ]
        question = "消费者事业部四川分公司的业绩"
        self.assertFalse(needs_llm_arbitration(question, contexts, []))

    def test_lacks_explicit_scope_force_arbitrate(self):
        """多个候选且问题未明确数据集/业务域，必须确认。"""
        contexts = [
            _ctx(80, 1),
            _ctx(60, 2),
        ]
        question = "看下业绩"
        self.assertTrue(needs_llm_arbitration(question, contexts, []))

    def test_score_snapshot(self):
        contexts = [_ctx(88, 1), _ctx(66, 2), _ctx(40, 3)]
        snapshot = score_snapshot(contexts)
        self.assertEqual(snapshot["top_score"], 88)
        self.assertEqual(snapshot["runner_up_score"], 66)
        self.assertEqual(snapshot["margin"], 22)
        self.assertEqual(snapshot["candidate_count"], 3)

    def test_metric_synonym_does_not_override_dataset_scope_alias(self):
        """通用指标类同义词（如'达成率'）不应让不相关的数据集获得高别名分。"""
        service = FourAgentAskService()
        commercial = {
            "id": 3,
            "dataset_name": "商用事业部（阶段一升级版）",
            "dataset_code": "angel_business_2026",
            "business_domain": "安吉尔商用事业部销售业绩分析",
            "synonyms": ["商用事业部", "安吉尔商用", "阶段一升级版"],
        }
        consumer = {
            "id": 2,
            "dataset_name": "消费者事业部任务达成分析（标准版）",
            "dataset_code": "consumer_business_standard_v1",
            "business_domain": "消费者事业部年度任务达成与业务线分析",
            "synonyms": ["消费者事业部", "达成率", "开单金额", "年度开单"],
        }
        question = "商用事业部的达成率"
        commercial_score = service._dataset_alias_match_score(question, commercial)
        consumer_score = service._dataset_alias_match_score(question, consumer)
        self.assertGreater(commercial_score, consumer_score)
        self.assertGreaterEqual(commercial_score, 90)
        self.assertLess(consumer_score, 90)


if __name__ == "__main__":
    unittest.main()
