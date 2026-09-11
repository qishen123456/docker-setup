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
        service._dataset_node_index = {"flat_alias_index": [], "datasets": []}
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

    def test_generic_bottom_branch_question_requires_dataset_confirmation(self):
        service = object.__new__(FourAgentAskService)
        service.repository = Mock()
        service.organization_route_resolver = Mock()
        service.organization_route_resolver.resolve.return_value = None

        consumer_dataset = {
            "id": 2,
            "dataset_name": "消费者事业部任务达成分析（标准版）",
            "dataset_code": "consumer_business_standard_v1",
            "business_domain": "消费者事业部",
            "synonyms": ["消费者事业部", "城市分公司"],
        }
        commercial_dataset = {
            "id": 3,
            "dataset_name": "商用事业部开单金额",
            "dataset_code": "angel_business_2026_phase1",
            "business_domain": "商用事业部",
            "synonyms": ["商用事业部", "代表处", "业务代表"],
        }
        service_provider_dataset = {
            "id": 9,
            "dataset_name": "服务商履约分析",
            "dataset_code": "service_provider_v1",
            "business_domain": "服务商",
            "synonyms": ["服务商", "分公司"],
        }
        service.repository.get_agent1_catalog.return_value = [consumer_dataset, commercial_dataset, service_provider_dataset]
        service.repository.get_dataset_context.return_value = {
            "common_questions": [],
            "golden_sql_samples": [],
            "data_dictionary": [],
            "schema_definition": [],
            "agent_prompts": {},
            "lld_content": "",
        }
        service._dataset_node_index = {
            "datasets": [
                {
                    "dataset_id": 2,
                    "dataset_code": "consumer_business_standard_v1",
                    "dataset_name": "消费者事业部任务达成分析（标准版）",
                    "nodes": [{"node_name": "云贵渝分公司", "node_level": "分公司"}],
                },
                {
                    "dataset_id": 3,
                    "dataset_code": "angel_business_2026_phase1",
                    "dataset_name": "商用事业部开单金额",
                    "nodes": [{"node_name": "东部分公司", "node_level": "分公司"}],
                },
                {
                    "dataset_id": 9,
                    "dataset_code": "service_provider_v1",
                    "dataset_name": "服务商履约分析",
                    "nodes": [{"node_name": "上海服务商分公司", "node_level": "分公司"}],
                },
            ],
            "flat_alias_index": [],
        }

        result = service.route_with_agent1("垫底的三个分公司")

        self.assertTrue(result.get("requires_confirmation"))
        self.assertEqual(result.get("intent"), "confirm")
        self.assertEqual(result.get("confirmation_type"), "dataset_disambiguation")
        self.assertIn("generic_level_requires_confirmation:分公司", result.get("arbiter_reason", ""))
        self.assertEqual(set(result.get("dataset_ids") or []), {2, 3, 9})
        option_dataset_ids = {
            dataset_id
            for option in result.get("confirmation_options") or []
            for dataset_id in option.get("dataset_ids", [])
        }
        self.assertEqual(option_dataset_ids, {2, 3, 9})

    def test_bare_node_with_multiple_dataset_levels_requires_confirmation(self):
        service = object.__new__(FourAgentAskService)
        service.repository = Mock()
        service.organization_route_resolver = Mock()
        service.organization_route_resolver.resolve.return_value = None
        service._looks_like_org_subject_question = Mock(return_value=True)
        service._agent1_resolve_org_subject = Mock(return_value={
            "subject_name": "上海",
            "subject_level": "",
            "rewritten_question": "上海的情况",
        })

        consumer_dataset = {
            "id": 2,
            "dataset_name": "消费者事业部任务达成分析（标准版）",
            "dataset_code": "consumer_business_standard_v1",
            "business_domain": "消费者事业部",
            "synonyms": ["消费者事业部"],
        }
        commercial_dataset = {
            "id": 3,
            "dataset_name": "商用事业部开单金额",
            "dataset_code": "angel_business_2026_phase1",
            "business_domain": "商用事业部",
            "synonyms": ["商用事业部"],
        }
        service.repository.get_agent1_catalog.return_value = [consumer_dataset, commercial_dataset]
        service._dataset_node_index = {
            "datasets": [],
            "flat_alias_index": [
                {
                    "alias": "上海",
                    "matches": [
                        {
                            "dataset_id": 2,
                            "dataset_name": "消费者事业部任务达成分析（标准版）",
                            "node_name": "上海城市公司",
                            "node_level": "城市分公司",
                        },
                        {
                            "dataset_id": 3,
                            "dataset_name": "商用事业部开单金额",
                            "node_name": "上海代表处",
                            "node_level": "代表处",
                        },
                    ],
                }
            ],
        }

        result = service.route_with_agent1("上海的情况")

        self.assertTrue(result.get("requires_confirmation"))
        self.assertEqual(result.get("intent"), "confirm")
        self.assertEqual(result.get("arbiter_reason"), "node_index_dataset_ambiguous")
        labels = [option.get("label") for option in result.get("confirmation_options") or []]
        # 统一确认卡：候选为"业务名 · 节点 的 指标"完整问句格式（原"数据集名 - 节点名"）
        self.assertTrue(any("上海城市公司" in label for label in labels), f"labels={labels}")
        self.assertTrue(any("上海代表处" in label for label in labels), f"labels={labels}")
        self.assertTrue(any("的业绩" in label for label in labels), f"labels={labels}")

    def test_bare_node_with_multiple_nodes_in_same_dataset_requires_confirmation(self):
        service = object.__new__(FourAgentAskService)
        service.repository = Mock()
        service.organization_route_resolver = Mock()
        service.organization_route_resolver.resolve.return_value = None
        service._looks_like_org_subject_question = Mock(return_value=True)
        service._agent1_resolve_org_subject = Mock(return_value={
            "subject_name": "上海",
            "subject_level": "",
            "rewritten_question": "上海的情况",
        })

        service.repository.get_agent1_catalog.return_value = [
            {
                "id": 9,
                "dataset_name": "服务商履约分析",
                "dataset_code": "service_provider_v1",
                "business_domain": "服务商",
                "synonyms": ["服务商"],
            }
        ]
        service._dataset_node_index = {
            "datasets": [],
            "flat_alias_index": [
                {
                    "alias": "上海",
                    "matches": [
                        {
                            "dataset_id": 9,
                            "dataset_name": "服务商履约分析",
                            "node_name": "上海服务商",
                            "node_level": "服务商",
                        },
                        {
                            "dataset_id": 9,
                            "dataset_name": "服务商履约分析",
                            "node_name": "上海服务商分公司",
                            "node_level": "分公司",
                        },
                    ],
                }
            ],
        }

        result = service.route_with_agent1("上海的情况")

        self.assertTrue(result.get("requires_confirmation"))
        self.assertEqual(result.get("intent"), "confirm")
        self.assertEqual(result.get("dataset_ids"), [9])
        self.assertEqual(len(result.get("confirmation_options") or []), 2)


if __name__ == "__main__":
    unittest.main()
