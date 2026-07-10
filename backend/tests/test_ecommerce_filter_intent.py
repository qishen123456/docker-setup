import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from four_agent_ask import FourAgentAskService
import dataset_report_config as report_config_store


ECOMMERCE_PROFILE = {
    "levels": [
        {"dimension_name": "事业部", "aliases": ["事业部"], "members": ["电商事业部"], "groups": []},
        {"dimension_name": "业务部", "aliases": ["业务部"], "members": ["国内业务部", "跨境业务部", "直营零售部"], "groups": []},
        {"dimension_name": "业务承接角色", "aliases": ["业务承接角色", "承接角色"], "members": ["京东直营", "亚马逊"], "groups": []},
        {"dimension_name": "承接人", "aliases": ["承接人", "业务承接人", "负责人"], "members": ["张三", "李四"], "groups": []},
    ]
}


class EcommerceFilterIntentTest(unittest.TestCase):
    def _service(self):
        return object.__new__(FourAgentAskService)

    def _profile(self):
        return ECOMMERCE_PROFILE

    def _context(self):
        return {
            "dataset": {
                "dataset_code": "feishu_tbldianshang",
                "dataset_name": "飞书电商事业部经营预算",
            },
            "report_config": report_config_store.merge_with_default_config({}),
            "dimension_profile": self._profile(),
        }

    def test_complete_amount_phrase_resolves_to_actual_metric(self):
        service = self._service()
        intent = service._resolve_query_intent("国内业务部完成超过500万的", self._context())

        self.assertEqual(intent["intent"], "filter")
        self.assertEqual(intent["filter_metric_key"], "年度开单金额")
        self.assertEqual(intent["filter_operator"], ">")
        self.assertEqual(intent["filter_value"], 500.0)

    def test_amount_unit_without_metric_prefers_actual_over_rate(self):
        service = self._service()
        intent = service._resolve_query_intent("业务部超过500万的", self._context())

        self.assertEqual(intent["intent"], "filter")
        self.assertEqual(intent["filter_metric_key"], "actual")
        self.assertEqual(intent["filter_operator"], ">=")
        self.assertEqual(intent["filter_value"], 500.0)

    def test_rate_phrase_still_uses_rate(self):
        service = self._service()
        intent = service._resolve_query_intent("业务部达成率超过50%的", self._context())

        self.assertEqual(intent["intent"], "filter")
        self.assertEqual(intent["filter_metric_key"], "达成率")
        self.assertEqual(intent["filter_operator"], ">")
        self.assertEqual(intent["filter_value"], 50.0)

    def test_filter_focused_branch_drills_to_child_level(self):
        service = self._service()
        context = self._context()
        question = "国内业务部完成超过500万的"
        intent = service._resolve_query_intent(question, context)
        context["query_intent"] = intent
        context["original_question"] = question

        sql = service._build_rule_based_sql(question, {}, context)

        self.assertIn("层级级别 = '业务经理'", sql)
        self.assertIn("组织路径 LIKE '电商事业部;国内业务部%'", sql)
        self.assertIn("(年度开单金额) > 5000000.0", sql)

    def test_amount_metric_with_completion_verb_is_filtered(self):
        service = self._service()
        context = self._context()
        question = "开单金额完成超过500万"
        intent = service._resolve_query_intent(question, context)
        self.assertEqual(intent["intent"], "filter")
        self.assertEqual(intent["filter_metric_key"], "年度开单金额")
        self.assertEqual(intent["filter_operator"], ">")
        self.assertEqual(intent["filter_value"], 500.0)

        context["query_intent"] = intent
        context["original_question"] = question
        sql = service._build_rule_based_sql(question, {}, context)

        self.assertIn("层级级别 = '业务经理'", sql)
        self.assertIn("(年度开单金额) > 5000000.0", sql)
        self.assertNotIn("组织路径 LIKE", sql)

    def test_display_title_uses_dataset_and_intent(self):
        service = self._service()
        dataset_result = {
            "dataset_name": "飞书电商事业部经营预算",
            "query_intent": {
                "intent": "filter",
                "filter_metric_key": "actual",
                "filter_metric_column": "年度开单金额",
                "filter_operator": ">",
                "filter_value": 500.0,
            },
            "rows": [{"层级": "业务承接角色"}],
        }
        title = service._build_display_title("开单金额完成超过500万", dataset_result)
        self.assertEqual(title, "电商事业部开单金额大于500万的业务承接角色")

    def test_business_bearer_ranking_resolves_to_person_level(self):
        service = self._service()
        context = self._context()
        question = "看下前三的业务承接人"
        intent = service._resolve_query_intent(question, context)

        self.assertEqual(intent["intent"], "ranking")
        self.assertEqual(intent["target_level"], "承接人")
        self.assertEqual(intent["top_n"], 3)

        context["query_intent"] = intent
        context["original_question"] = question
        sql = service._build_rule_based_sql(question, {}, context)

        self.assertIn("层级级别 = '业务经理'", sql)
        self.assertIn("'承接人' AS 层级", sql)
        self.assertIn("LIMIT 3", sql)

    def test_business_bearer_display_title_no_duplicate(self):
        service = self._service()
        dataset_result = {
            "dataset_name": "飞书电商事业部经营预算",
            "query_intent": {
                "intent": "ranking",
                "target_level": "承接人",
                "top_n": 3,
                "sort_metric_key": "rate",
                "direction": "desc",
            },
            "rows": [{"层级": "承接人"}],
        }
        title = service._build_display_title("看下前三的业务承接人", dataset_result)
        self.assertEqual(title, "排名前3的承接人")

    def test_ecommerce_root_performance_drills_to_business_departments(self):
        service = self._service()
        context = self._context()
        question = "电商事业部的业绩"
        intent = service._resolve_query_intent(question, context)

        context["query_intent"] = intent
        context["original_question"] = question
        sql = service._build_rule_based_sql(question, {}, context)

        self.assertIn("层级级别 = '业务部'", sql)
        self.assertNotIn("WHERE 当前年 = '2026' AND 层级级别 = '事业部'", sql)

    def test_bearer_level_not_overridden_by_rewritten_business_department_query(self):
        """模拟 confirm_by_boss 把 resolved_subject 改写成业务部后，意图仍解析为承接人"""
        service = self._service()
        context = self._context()

        # _run_pipeline 里拼接的 intent_question：
        # original_question=看下前三的业务承接人
        # refined_query=国内业务部的业绩
        combined = "国内业务部的业绩\n看下前三的业务承接人"

        intent = service._resolve_query_intent(combined, context)
        self.assertEqual(intent["intent"], "ranking")
        self.assertEqual(intent["target_level"], "承接人")
        self.assertEqual(intent["top_n"], 3)

        context["query_intent"] = intent
        context["original_question"] = "看下前三的业务承接人"
        sql = service._build_rule_based_sql(combined, {}, context)

        self.assertIn("层级级别 = '业务经理'", sql)
        self.assertIn("'承接人' AS 层级", sql)
        self.assertIn("LIMIT 3", sql)

        dataset_result = {
            "dataset_name": "飞书电商事业部经营预算",
            "query_intent": intent,
            "rows": [{"层级": "承接人"}],
        }
        title = service._build_display_title("看下前三的业务承接人", dataset_result)
        self.assertEqual(title, "排名前3的承接人")

    def test_ranking_bearer_question_not_treated_as_org_subject(self):
        """排名类问题不应被组织主体解析器改写，避免丢失 top_n 与原始语义"""
        service = self._service()
        self.assertFalse(
            service._looks_like_org_subject_question("看下前三的业务承接人")
        )
        self.assertFalse(
            service._looks_like_org_subject_question("业务承接人业绩排名")
        )
        # 普通单对象问法仍应识别为主体问题
        self.assertTrue(
            service._looks_like_org_subject_question("国内业务部的业绩如何")
        )

    def test_level_only_display_title_uses_entity_names(self):
        """level_only 过滤标题应按 filter 语义展示，不再拼 raw metric key"""
        service = self._service()
        dataset_result = {
            "dataset_name": "飞书商用事业部经营预算",
            "resolved_entities": {
                "all_members": ["靳锋", "赵标"],
                "entities": [{"members": ["靳锋", "赵标"]}],
            },
            "query_intent": {
                "intent": "filter",
                "target_level": "业务代表",
                "filter_metric_key": "level_only",
                "filter_metric_column": "",
                "filter_operator": "",
                "filter_value": None,
            },
            "rows": [{"层级": "业务代表"}],
        }
        title = service._build_display_title("看下靳锋、赵标的业绩情况", dataset_result)
        self.assertEqual(title, "商用事业部靳锋、赵标的筛选结果")


if __name__ == "__main__":
    unittest.main()
