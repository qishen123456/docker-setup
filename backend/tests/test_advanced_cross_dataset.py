import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smartask_advanced.service import AdvancedAskService
from smartask_advanced.skills.route_guard import RouteGuardSkill


class FakeRepo:
    def get_agent1_catalog(self):
        return []


class FakeFallback:
    def __init__(self):
        self.repository = FakeRepo()
        self.calls = []

    def ask(self, **kwargs):
        question = str(kwargs.get("question") or "")
        dataset_id = int((kwargs.get("preferred_dataset_ids") or [0])[0] or 0)
        self.calls.append({"question": question, "preferred_dataset_ids": kwargs.get("preferred_dataset_ids")})
        return {
            "question": question,
            "analysis": f"{question}分析",
            "final_answer": "",
            "dataset_results": [
                {
                    "dataset_id": dataset_id,
                    "dataset_name": f"数据集{dataset_id}",
                    "analysis": f"{question}分析",
                    "rows": [{"节点名称": question.replace("的业绩", "")}],
                    "row_count": 1,
                    "report_spec": {"kpis": []},
                }
            ],
        }


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

    def test_cross_dataset_conclusion_uses_business_subject_names_from_route_guard(self):
        service = AdvancedAskService(fallback_service=object())
        result = {
            "analysis": "",
            "dataset_results": [
                {
                    "dataset_id": 3,
                    "dataset_name": "商用事业部（阶段一升级版）",
                    "analysis": "",
                    "report_spec": {"kpis": [{"label": "整体达成率", "value": 15.8}]},
                },
                {
                    "dataset_id": 11,
                    "dataset_name": "消费者测试数据集",
                    "analysis": "",
                    "report_spec": {"kpis": [{"label": "整体达成率", "value": 26.5}]},
                },
            ],
        }
        route_guard = {
            "organization_route": {
                "organization_mentions": [
                    {"node_name": "商用事业部", "dataset_ids": [3]},
                    {"node_name": "消费者事业部", "dataset_ids": [11]},
                ]
            }
        }

        payload = service._apply_cross_dataset_conclusion(result, route_guard)

        self.assertTrue(payload["applied"])
        self.assertIn("消费者事业部达成率26.5%", result["analysis"])
        self.assertNotIn("消费者测试数据集达成率", result["analysis"])

    def test_cross_dataset_subject_overview_prefers_explicit_subject_row(self):
        service = AdvancedAskService(fallback_service=object())
        result = {
            "dataset_results": [
                {
                    "dataset_id": 2,
                    "dataset_name": "消费者事业部任务达成分析（标准版）",
                    "rows": [
                        {
                            "层级": "消费者事业部总体",
                            "节点名称": "消费者事业部",
                            "上级名称": None,
                            "总任务金额": 1789710000,
                            "年度开单金额": 925702951.55,
                            "达成率": 51.72,
                            "剩余任务金额": 864007048.45,
                        }
                    ],
                },
                {
                    "dataset_id": 3,
                    "dataset_name": "商用事业部开单金额",
                    "rows": [
                        {
                            "条线": "事业部层级",
                            "层级": "事业部",
                            "节点名称": "商用事业部",
                            "上级名称": None,
                            "总任务金额": 455000000,
                            "年度开单金额": 188711870.60,
                            "达成率": 41.48,
                            "剩余任务金额": 266288129.4,
                        },
                        {
                            "条线": "事业部层级",
                            "层级": "事业部",
                            "节点名称": "商用事业部",
                            "上级名称": None,
                            "总任务金额": 455000000,
                            "年度开单金额": 199707006.72,
                            "达成率": 43.89,
                            "剩余任务金额": 255292993.28,
                        },
                        {
                            "层级": "分公司",
                            "节点名称": "东部分公司",
                            "上级名称": "商用事业部",
                            "总任务金额": 95000000,
                            "年度开单金额": 36450428.47,
                            "达成率": 38.37,
                            "剩余任务金额": 58549571.53,
                        },
                    ],
                },
            ],
        }
        route_guard = {
            "organization_route": {
                "organization_mentions": [
                    {"node_name": "消费者事业部", "dataset_ids": [2]},
                    {"node_name": "商用事业部", "dataset_ids": [3]},
                ]
            }
        }

        service._enrich_cross_dataset_subject_overviews(result, route_guard)

        left = result["dataset_results"][0]["cross_dataset_subject_overview"]
        right = result["dataset_results"][1]["cross_dataset_subject_overview"]
        self.assertEqual(left["name"], "消费者事业部")
        self.assertAlmostEqual(left["rate"], 51.72, places=2)
        self.assertEqual(right["name"], "商用事业部")
        self.assertAlmostEqual(right["actual"], 199707006.72, places=2)
        self.assertAlmostEqual(right["rate"], 43.89, places=2)

    def test_cross_dataset_conclusion_prefers_subject_overview_over_internal_comparison_kpis(self):
        service = AdvancedAskService(fallback_service=object())
        result = {
            "analysis": "",
            "dataset_results": [
                {
                    "dataset_id": 2,
                    "dataset_name": "消费者事业部任务达成分析（标准版）",
                    "comparison_subject_name": "消费者事业部",
                    "cross_dataset_subject_overview": {
                        "name": "消费者事业部",
                        "level": "事业部",
                        "task": 1789710000,
                        "actual": 925702951.55,
                        "rate": 51.72,
                        "remain": 864007048.45,
                    },
                    "report_spec": {
                        "kpis": [
                            {"label": "累计总任务金额", "value": 1789710000},
                            {"label": "累计年度开单金额", "value": 811895205.01},
                            {"label": "整体达成率", "value": 45.36},
                        ]
                    },
                },
                {
                    "dataset_id": 3,
                    "dataset_name": "商用事业部开单金额",
                    "comparison_subject_name": "商用事业部",
                    "cross_dataset_subject_overview": {
                        "name": "商用事业部",
                        "level": "事业部",
                        "task": 455000000,
                        "actual": 199707006.72,
                        "rate": 43.89,
                        "remain": 255292993.28,
                    },
                    "report_spec": {
                        "kpis": [
                            {"label": "累计总任务金额", "value": 600000000},
                            {"label": "累计年度开单金额", "value": 285063805.27},
                            {"label": "整体达成率", "value": 47.51},
                        ]
                    },
                },
            ],
        }

        payload = service._apply_cross_dataset_conclusion(result)

        self.assertTrue(payload["applied"])
        self.assertIn("消费者事业部达成率51.72%", result["analysis"])
        self.assertIn("高于商用事业部7.83个百分点", result["analysis"])
        self.assertNotIn("45.36%", result["analysis"])
        self.assertNotIn("47.51%", result["analysis"])

    def test_cross_dataset_compare_executes_split_subject_queries_per_dataset(self):
        fallback = FakeFallback()
        service = AdvancedAskService(fallback_service=fallback)
        service._run_advanced_trace = lambda *args, **kwargs: {
            "trace_id": "trace-1",
            "route_guard": {
                "action": "cross_dataset_compare",
                "apply_dataset_ids": [3, 62],
                "organization_route": {
                    "organization_mentions": [
                        {"node_name": "商用事业部", "dataset_ids": [3], "dataset_names": ["商用事业部"]},
                        {"node_name": "电商事业部", "dataset_ids": [62], "dataset_names": ["电商事业部"]},
                    ]
                },
            },
            "effective_preferred_dataset_ids": [3, 62],
            "assets": [],
            "skills": [],
            "intent": {},
            "golden_sql": {},
        }
        service._run_result_trace = lambda **kwargs: {}

        result = service.ask(question="商用和电商的业绩对比", allowed_dataset_ids=[3, 62])

        self.assertEqual(
            fallback.calls,
            [
                {"question": "商用事业部的业绩", "preferred_dataset_ids": [3]},
                {"question": "电商事业部的业绩", "preferred_dataset_ids": [62]},
            ],
        )
        self.assertEqual(len(result["dataset_results"]), 2)
        self.assertEqual(result["route"]["intent"], "comparison")
        self.assertEqual(
            result["advanced_execution_question"]["queries"],
            [
                {"dataset_id": 3, "subject_name": "商用事业部", "query": "商用事业部的业绩"},
                {"dataset_id": 62, "subject_name": "电商事业部", "query": "电商事业部的业绩"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
