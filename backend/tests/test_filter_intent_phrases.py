import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from four_agent_ask import FourAgentAskService
import dataset_report_config as report_config_store


class FilterIntentPhraseTest(unittest.TestCase):
    def _service(self):
        return object.__new__(FourAgentAskService)

    def test_threshold_branch_question_without_interrogative_is_filter(self):
        service = self._service()
        context = {
            "report_config": report_config_store.get_default_config(),
        }

        intent = service._resolve_query_intent("看下低于30%的分公司", context)

        self.assertEqual(intent["intent"], "filter")
        self.assertEqual(intent["filter_operator"], "<")
        self.assertEqual(intent["filter_value"], 30.0)

    def test_threshold_rate_branch_question_without_interrogative_is_filter(self):
        service = self._service()
        context = {
            "report_config": report_config_store.get_default_config(),
        }

        intent = service._resolve_query_intent("看下达成率低于30%的分公司", context)

        self.assertEqual(intent["intent"], "filter")
        self.assertEqual(intent["filter_operator"], "<")
        self.assertEqual(intent["filter_value"], 30.0)

    def test_threshold_amount_with_chinese_number_is_filter(self):
        service = self._service()
        context = {
            "report_config": report_config_store.get_default_config(),
        }

        intent = service._resolve_query_intent("看下大于一个亿的分公司", context)

        self.assertEqual(intent["intent"], "filter")
        self.assertEqual(intent["filter_operator"], ">")
        self.assertEqual(intent["filter_value"], 1.0)

    def test_threshold_amount_with_metric_and_chinese_number_is_filter(self):
        service = self._service()
        context = {
            "report_config": report_config_store.get_default_config(),
        }

        intent = service._resolve_query_intent("开单金额大于一个亿的分公司", context)

        self.assertEqual(intent["intent"], "filter")
        self.assertEqual(intent["filter_metric_column"], "年度开单金额")
        self.assertEqual(intent["filter_operator"], ">")
        self.assertEqual(intent["filter_value"], 1.0)


if __name__ == "__main__":
    unittest.main()
