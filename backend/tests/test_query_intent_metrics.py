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

        self.assertIn("城市公司排序", sql)
        self.assertIn("前排名", sql)
        self.assertIn("后排名", sql)
        self.assertIn("WHERE 前排名 <= 3 OR 后排名 <= 3", sql)
        self.assertIn("LIMIT 6", sql)


if __name__ == "__main__":
    unittest.main()
