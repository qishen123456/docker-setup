import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from four_agent_ask import FourAgentAskService
import dataset_report_config as report_config_store


class QueryIntentMetricTest(unittest.TestCase):
    def _service(self):
        return object.__new__(FourAgentAskService)

    def test_ranking_question_prefers_actual_metric_for_sales_amount(self):
        service = self._service()
        context = {
            "report_config": report_config_store.get_default_config(),
        }

        intent = service._resolve_query_intent("看下销售金额前三的代表处", context)

        self.assertEqual(intent["intent"], "ranking")
        self.assertEqual(intent["target_level"], "代表处")
        self.assertEqual(intent["sort_metric_key"], "actual")
        self.assertEqual(intent["sort_metric_column"], "年度开单金额")

    def test_ranking_question_still_uses_rate_when_asking_completion_rate(self):
        service = self._service()
        context = {
            "report_config": report_config_store.get_default_config(),
        }

        intent = service._resolve_query_intent("看下达成率前三的代表处", context)

        self.assertEqual(intent["intent"], "ranking")
        self.assertEqual(intent["sort_metric_key"], "rate")
        self.assertEqual(intent["sort_metric_column"], "达成率")

    def test_lowest_three_phrase_sets_top_n(self):
        service = self._service()
        context = {
            "report_config": report_config_store.get_default_config(),
        }

        intent = service._resolve_query_intent("看下完成率最低的三个代表处", context)

        self.assertEqual(intent["intent"], "ranking")
        self.assertEqual(intent["target_level"], "代表处")
        self.assertEqual(intent["top_n"], 3)
        self.assertEqual(intent["direction"], "asc")

    def test_llm_ranking_params_fills_missing_top_n_for_colloquial_bottom(self):
        service = self._service()
        context = {
            "report_config": report_config_store.get_default_config(),
            "resolved_entities": {
                "ranking_params": {
                    "top_n": 3,
                    "rank_sides": "bottom",
                    "direction": "asc",
                    "metric_hint": "达成率",
                }
            },
        }

        # "垫底"被规则识别为 bottom 方向，但数量解析不到，应由 LLM 补充
        intent = service._resolve_query_intent("消费者事业部，业绩排名垫底的 3 家分公司", context)

        self.assertEqual(intent["intent"], "ranking")
        self.assertEqual(intent["target_level"], "分公司")
        self.assertEqual(intent["top_n"], 3)
        self.assertEqual(intent["direction"], "asc")
        self.assertEqual(intent["rank_sides"], "bottom")

    def test_rule_top_n_takes_precedence_over_llm_ranking_params(self):
        service = self._service()
        context = {
            "report_config": report_config_store.get_default_config(),
            "resolved_entities": {
                "ranking_params": {
                    "top_n": 5,
                    "rank_sides": "bottom",
                }
            },
        }

        # 规则已明确提取到"前三"，应优先使用规则，不受 LLM 的 5 干扰
        intent = service._resolve_query_intent("看下前三的分公司", context)

        self.assertEqual(intent["intent"], "ranking")
        self.assertEqual(intent["target_level"], "分公司")
        self.assertEqual(intent["top_n"], 3)

    def test_explicit_lowest_three_rep_offices_use_global_limit(self):
        service = self._service()
        context = {
            "dataset": {
                "dataset_code": "angel_business_2026_phase1",
                "dataset_name": "商用事业部（阶段一升级版）",
            },
            "query_intent": {
                "intent": "ranking",
                "target_level": "代表处",
                "top_n": 3,
                "sort_metric_key": "rate",
                "sort_metric_column": "达成率",
                "direction": "asc",
            },
            "data_dictionary": [],
        }

        sql = service._build_rule_based_sql("看下完成率最低的三个代表处", {}, context)

        self.assertIn("代表处全局排序", sql)
        self.assertIn("WHERE 全局排名 <= 3", sql)
        self.assertIn("LIMIT 3", sql)
        self.assertNotIn("PARTITION BY 上级名称", sql)

    def test_top_and_bottom_business_people_sets_both_sides(self):
        service = self._service()
        context = {
            "report_config": report_config_store.get_default_config(),
        }

        intent = service._resolve_query_intent("看下前三和后三的业务员", context)

        self.assertEqual(intent["intent"], "ranking")
        self.assertEqual(intent["target_level"], "业务代表")
        self.assertEqual(intent["top_n"], 3)
        self.assertEqual(intent["rank_sides"], "both")
        self.assertEqual(intent["direction"], "desc")

    def test_first_and_last_branch_sets_both_sides(self):
        service = self._service()
        context = {
            "report_config": report_config_store.get_default_config(),
        }

        intent = service._resolve_query_intent("看下第一和倒数第一的分公司", context)

        self.assertEqual(intent["intent"], "ranking")
        self.assertEqual(intent["target_level"], "分公司")
        self.assertEqual(intent["top_n"], 1)
        self.assertEqual(intent["rank_sides"], "both")
        self.assertEqual(intent["direction"], "desc")

    def test_ranking_branch_question_is_not_misread_as_subject_name(self):
        service = self._service()
        context = {
            "dataset": {
                "dataset_code": "angel_business_2026_phase1",
                "dataset_name": "商用事业部（阶段一升级版）",
            },
            "report_config": report_config_store.get_default_config(),
        }

        names = service._question_subject_names("看下第一和倒数第一的分公司", context, include_resolved=False)

        self.assertEqual(names, [])

    def test_business_person_comparison_question_splits_two_names(self):
        service = self._service()
        context = {
            "dataset": {
                "dataset_code": "angel_business_2026_phase1",
                "dataset_name": "商用事业部（阶段一升级版）",
            },
            "report_config": report_config_store.get_default_config(),
        }

        names = service._question_subject_names("对比下业务员赵标和靳锋的业绩完成情况", context, include_resolved=False)

        self.assertEqual(names, ["赵标", "靳锋"])

    def test_business_person_question_splits_two_names_without_role_prefix(self):
        service = self._service()
        context = {
            "dataset": {
                "dataset_code": "angel_business_2026_phase1",
                "dataset_name": "商用事业部（阶段一升级版）",
            },
            "report_config": report_config_store.get_default_config(),
        }

        names = service._question_subject_names("看下赵标和靳锋的业绩", context, include_resolved=False)

        self.assertEqual(names, ["赵标", "靳锋"])

    def test_branch_comparison_question_splits_two_full_branch_names(self):
        service = self._service()
        context = {
            "dataset": {
                "dataset_code": "angel_business_2026_phase1",
                "dataset_name": "商用事业部（阶段一升级版）",
            },
            "report_config": report_config_store.get_default_config(),
        }

        names = service._question_subject_names("对比下东部分公司和西部分公司的业绩完成情况", context, include_resolved=False)

        self.assertEqual(names, ["东部分公司", "西部分公司"])

    def test_branch_comparison_question_splits_compound_branch_alias_without_and(self):
        service = self._service()
        context = {
            "dataset": {
                "dataset_code": "angel_business_2026_phase1",
                "dataset_name": "商用事业部（阶段一升级版）",
            },
            "report_config": report_config_store.get_default_config(),
        }

        names = service._question_subject_names("对比下东部西部分公司业绩完成情况", context, include_resolved=False)

        self.assertEqual(names, ["东部分公司", "西部分公司"])

    def test_branch_comparison_question_splits_compound_short_alias(self):
        service = self._service()
        context = {
            "dataset": {
                "dataset_code": "angel_business_2026_phase1",
                "dataset_name": "商用事业部（阶段一升级版）",
            },
            "report_config": report_config_store.get_default_config(),
        }

        names = service._question_subject_names("对比下东西部业绩完成情况", context, include_resolved=False)

        self.assertEqual(names, ["东部分公司", "西部分公司"])

    def test_branch_comparison_question_uses_parallel_compare_sql_not_recursive_drill(self):
        service = self._service()
        context = {
            "dataset": {
                "dataset_code": "angel_business_2026_phase1",
                "dataset_name": "商用事业部（阶段一升级版）",
            },
            "report_config": report_config_store.get_default_config(),
            "resolved_entities": {
                "all_members": ["东部分公司", "西部分公司"],
                "entities": [{"members": ["东部分公司", "西部分公司"]}],
            },
            "data_dictionary": [{"jsonb_key": "业务部"}],
        }

        sql = service._build_rule_based_sql("对比下东西部业绩完成情况", {}, context)

        self.assertIn("WHERE 节点名称 IN ('东部分公司','西部分公司') OR 上级名称 IN ('东部分公司','西部分公司')", sql)
        self.assertNotIn("WITH RECURSIVE", sql)
        self.assertNotIn("JOIN 命中链路", sql)

    def test_consumer_first_and_last_branch_sql_uses_two_windows(self):
        service = self._service()
        context = {
            "dataset": {
                "dataset_code": "consumer_business_standard_v1",
                "dataset_name": "消费者事业部",
            },
            "query_intent": {
                "intent": "ranking",
                "target_level": "分公司",
                "top_n": 1,
                "sort_metric_key": "rate",
                "sort_metric_column": "达成率",
                "direction": "desc",
                "rank_sides": "both",
            },
            "data_dictionary": [{"jsonb_key": "城市分公司"}],
        }

        sql = service._build_rule_based_sql("看下第一和倒数第一的分公司", {}, context)

        self.assertIn("分公司排序", sql)
        self.assertIn("前排名", sql)
        self.assertIn("后排名", sql)
        self.assertIn("WHERE 前排名 <= 1 OR 后排名 <= 1", sql)
        self.assertIn("LIMIT 2", sql)

    def test_phase1_business_people_top_and_bottom_sql_uses_two_windows(self):
        service = self._service()
        context = {
            "dataset": {
                "dataset_code": "angel_business_2026_phase1",
                "dataset_name": "商用事业部（阶段一升级版）",
            },
            "query_intent": {
                "intent": "ranking",
                "target_level": "业务代表",
                "top_n": 3,
                "sort_metric_key": "rate",
                "sort_metric_column": "达成率",
                "direction": "desc",
                "rank_sides": "both",
            },
            "data_dictionary": [],
        }

        sql = service._build_rule_based_sql("看下前三和后三的业务员", {}, context)

        self.assertIn("业务代表双向排序", sql)
        self.assertIn("前排名", sql)
        self.assertIn("后排名", sql)
        self.assertIn("WHERE 前排名 <= 3 OR 后排名 <= 3", sql)
        self.assertIn("LIMIT 6", sql)

    def test_phase1_first_and_last_branch_sql_uses_ranking_template(self):
        service = self._service()
        context = {
            "dataset": {
                "dataset_code": "angel_business_2026_phase1",
                "dataset_name": "商用事业部（阶段一升级版）",
            },
            "query_intent": {
                "intent": "ranking",
                "target_level": "分公司",
                "top_n": 1,
                "sort_metric_key": "rate",
                "sort_metric_column": "达成率",
                "direction": "desc",
                "rank_sides": "both",
            },
            "data_dictionary": [],
        }

        sql = service._build_rule_based_sql("看下第一和倒数第一的分公司", {}, context)

        self.assertIn("分公司排序", sql)
        self.assertIn("前排名", sql)
        self.assertIn("后排名", sql)
        self.assertIn("WHERE 前排名 <= 1 OR 后排名 <= 1", sql)
        self.assertIn("LIMIT 2", sql)

    def test_phase1_management_levels_share_two_sided_ranking(self):
        service = self._service()
        base_context = {
            "dataset": {
                "dataset_code": "angel_business_2026_phase1",
                "dataset_name": "商用事业部（阶段一升级版）",
            },
            "query_intent": {
                "intent": "ranking",
                "top_n": 3,
                "sort_metric_key": "rate",
                "sort_metric_column": "达成率",
                "direction": "desc",
                "rank_sides": "both",
            },
            "data_dictionary": [{"jsonb_key": "业务部"}],
        }

        for level, cte_name in [("代表处", "代表处双向排序"), ("分公司", "分公司排序"), ("业务部", "业务部排序")]:
            context = {
                **base_context,
                "query_intent": {**base_context["query_intent"], "target_level": level},
            }
            sql = service._build_rule_based_sql(f"看下前三和后三的{level}", {}, context)
            self.assertIn(cte_name, sql)
            self.assertIn("前排名", sql)
            self.assertIn("后排名", sql)
            self.assertIn("LIMIT 6", sql)

    def test_consumer_city_top_and_bottom_sql_uses_two_windows(self):
        service = self._service()
        context = {
            "dataset": {
                "dataset_code": "consumer_business_standard_v1",
                "dataset_name": "消费者事业部",
            },
            "query_intent": {
                "intent": "ranking",
                "target_level": "城市公司",
                "top_n": 3,
                "sort_metric_key": "rate",
                "sort_metric_column": "达成率",
                "direction": "desc",
                "rank_sides": "both",
            },
            "data_dictionary": [{"jsonb_key": "城市公司"}],
        }

        sql = service._build_rule_based_sql("看下前三和后三的城市公司", {}, context)

        self.assertIn("城市分公司排序", sql)
        self.assertIn("前排名", sql)
        self.assertIn("后排名", sql)
        self.assertIn("WHERE 前排名 <= 3 OR 后排名 <= 3", sql)
        self.assertIn("LIMIT 6", sql)


    def test_city_branch_overview_is_ranking_all_nodes(self):
        service = self._service()
        context = {
            "report_config": report_config_store.get_default_config(),
        }

        intent = service._resolve_query_intent("城市分公司的业绩", context)

        self.assertEqual(intent["intent"], "ranking")
        self.assertEqual(intent["target_level"], "城市分公司")
        self.assertEqual(intent["top_n"], 0)
        self.assertEqual(intent["sort_metric_key"], "rate")
        self.assertTrue(intent.get("_level_overview"))

    def test_branch_overview_is_ranking_all_nodes(self):
        service = self._service()
        context = {
            "report_config": report_config_store.get_default_config(),
        }

        intent = service._resolve_query_intent("分公司的业绩", context)

        self.assertEqual(intent["intent"], "ranking")
        self.assertEqual(intent["target_level"], "分公司")
        self.assertEqual(intent["top_n"], 0)

    def test_level_only_terms_are_not_org_subject_questions(self):
        service = self._service()

        self.assertFalse(service._looks_like_org_subject_question("城市分公司的业绩"))
        self.assertFalse(service._looks_like_org_subject_question("分公司业绩"))
        self.assertFalse(service._looks_like_org_subject_question("业务部业绩"))

    def test_specific_node_is_still_org_subject_question(self):
        service = self._service()

        self.assertTrue(service._looks_like_org_subject_question("郑州城市公司业绩"))
        self.assertTrue(service._looks_like_org_subject_question("江浙沪分公司业绩"))

    def test_consumer_sql_default_branch_filters_by_target_level(self):
        service = self._service()
        context = {
            "dataset": {
                "dataset_code": "consumer_business_standard_v1",
                "dataset_name": "消费者事业部",
            },
            "query_intent": {
                "intent": "unknown",
                "target_level": "城市分公司",
            },
            "data_dictionary": [{"jsonb_key": "城市分公司"}],
            "resolved_entities": {"all_members": [], "entities": []},
        }

        sql = service._build_consumer_business_sql("城市分公司", context)

        self.assertIn("WHERE 层级 = '城市分公司'", sql)

    def test_superlative_bottom_without_number_defaults_to_one(self):
        service = self._service()
        context = {
            "report_config": report_config_store.get_default_config(),
        }

        intent = service._resolve_query_intent("业绩最差的业务代表", context)

        self.assertEqual(intent["intent"], "ranking")
        self.assertEqual(intent["target_level"], "业务代表")
        self.assertEqual(intent["top_n"], 1)
        self.assertEqual(intent["direction"], "asc")
        self.assertEqual(intent["rank_sides"], "bottom")

    def test_superlative_top_without_number_defaults_to_one(self):
        service = self._service()
        context = {
            "report_config": report_config_store.get_default_config(),
        }

        intent = service._resolve_query_intent("业绩最好的分公司", context)

        self.assertEqual(intent["intent"], "ranking")
        self.assertEqual(intent["target_level"], "分公司")
        self.assertEqual(intent["top_n"], 1)
        self.assertEqual(intent["direction"], "desc")
        self.assertEqual(intent["rank_sides"], "top")

    def test_superlative_with_explicit_number_uses_number(self):
        service = self._service()
        context = {
            "report_config": report_config_store.get_default_config(),
        }

        intent = service._resolve_query_intent("业绩最差的 3 个业务代表", context)

        self.assertEqual(intent["intent"], "ranking")
        self.assertEqual(intent["target_level"], "业务代表")
        self.assertEqual(intent["top_n"], 3)
        self.assertEqual(intent["direction"], "asc")

    def test_plain_ranking_without_number_still_returns_all(self):
        service = self._service()
        context = {
            "report_config": report_config_store.get_default_config(),
        }

        intent = service._resolve_query_intent("业务代表业绩排名", context)

        self.assertEqual(intent["intent"], "ranking")
        self.assertEqual(intent["target_level"], "业务代表")
        self.assertEqual(intent["top_n"], 0)


if __name__ == "__main__":
    unittest.main()
