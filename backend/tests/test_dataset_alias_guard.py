import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from four_agent_ask import FourAgentAskService


class DatasetAliasGuardTest(unittest.TestCase):
    def test_generic_branch_term_does_not_trigger_explicit_dataset_alias(self):
        service = object.__new__(FourAgentAskService)
        consumer_dataset = {
            "dataset_name": "消费者测试数据集",
            "business_domain": "消费者事业部",
            "synonyms": ["消费者事业部", "分公司", "城市公司"],
            "dataset_code": "public_feishu_tbl_xioafeizhe",
        }

        score = service._dataset_alias_match_score("看下第一和倒数第一的分公司", consumer_dataset)

        self.assertLess(score, 90)


if __name__ == "__main__":
    unittest.main()
