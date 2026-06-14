import os
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from four_agent_ask import FourAgentAskService


class BasicUniqueLevelRoutingTest(unittest.TestCase):
    def test_city_branch_question_routes_to_consumer_without_confirmation(self):
        service = object.__new__(FourAgentAskService)
        service.repository = Mock()
        service.organization_route_resolver = Mock()
        service.organization_route_resolver.resolve.return_value = None

        consumer_dataset = {
            "id": 13,
            "dataset_name": "消费者测试数据集",
            "dataset_code": "consumer_business_standard_v1",
            "business_domain": "消费者事业部",
            "synonyms": ["消费者事业部", "城市分公司"],
        }
        commercial_dataset = {
            "id": 3,
            "dataset_name": "商用事业部（阶段一升级版）",
            "dataset_code": "angel_business_2026_phase1",
            "business_domain": "商用事业部",
            "synonyms": ["商用事业部", "分公司", "代表处", "业务代表"],
        }
        catalog = [consumer_dataset, commercial_dataset]
        service.repository.get_agent1_catalog.return_value = catalog
        service.repository.get_dataset_context.return_value = {
            "common_questions": [],
            "golden_sql_samples": [],
            "data_dictionary": [],
            "schema_definition": [],
            "agent_prompts": {},
            "lld_content": "",
        }

        result = service.route_with_agent1("哪些城市分公司达成率低于10%？")

        self.assertFalse(result.get("requires_confirmation"))
        self.assertEqual(result.get("dataset_ids"), [13])
        self.assertEqual(result.get("arbiter_reason"), "target_level_unique:城市分公司")


if __name__ == "__main__":
    unittest.main()
