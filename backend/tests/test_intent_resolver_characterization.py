import inspect
import os
import sys
import unittest
from typing import Any, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dataset_report_config as report_config_store
from four_agent_ask import FourAgentAskService


class IntentResolverCharacterizationTest(unittest.TestCase):
    def setUp(self):
        self.service = object.__new__(FourAgentAskService)
        self.context = {"report_config": report_config_store.get_default_config()}

    def test_locked_intent_json_golden(self):
        cases = {
            "": {"intent": "unknown", "source": "report_config.intentPolicies", "target_level": "", "top_n": None, "sort_metric_key": "", "sort_metric_column": "", "direction": "", "rank_sides": "", "output_mode": "", "matched_triggers": []},
            "看下销售金额前三的代表处": {"intent": "ranking", "source": "report_config.intentPolicies", "target_level": "代表处", "top_n": 3, "sort_metric_key": "actual", "sort_metric_column": "年度开单金额", "direction": "desc", "rank_sides": "top", "output_mode": "topn_only", "matched_triggers": ["前"], "top_limit": 3, "bottom_limit": 0},
            "看下完成率最低的三个代表处": {"intent": "ranking", "source": "report_config.intentPolicies", "target_level": "代表处", "top_n": 3, "sort_metric_key": "rate", "sort_metric_column": "达成率", "direction": "asc", "rank_sides": "bottom", "output_mode": "topn_only", "matched_triggers": ["最低", "extra_sort"], "top_limit": 0, "bottom_limit": 3},
            "达成率在20%到40%之间的分公司": {"intent": "filter", "source": "report_config.intentPolicies", "target_level": "分公司", "top_n": None, "sort_metric_key": "", "sort_metric_column": "", "direction": "asc", "rank_sides": "", "output_mode": "matched_nodes_first", "matched_triggers": ["filter_range"], "filter_metric_key": "rate", "filter_metric_column": "达成率", "filter_operator": "between", "filter_value": 20.0, "filter_value2": 40.0},
            "没有开张的业务代表": {"intent": "filter", "source": "report_config.intentPolicies", "target_level": "业务代表", "top_n": None, "sort_metric_key": "", "sort_metric_column": "", "direction": "asc", "rank_sides": "", "output_mode": "matched_nodes_first", "matched_triggers": ["spoken_zero_actual"], "filter_metric_key": "actual", "filter_metric_column": "年度开单金额", "filter_operator": "=", "filter_value": 0},
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                self.assertEqual(self.service._resolve_query_intent(question, self.context), expected)

    def test_locked_rank_spec_json_golden(self):
        self.assertEqual(
            self.service._rank_request_spec("前3和倒数2个代表处"),
            {"limit": 3, "top_limit": 3, "bottom_limit": 2, "sides": "both", "direction": "desc"},
        )

    def test_facade_signatures_match_locked_baseline(self):
        class SignatureBaseline:
            def _resolve_query_intent(self, question: str, context: Dict[str, Any]) -> Dict[str, Any]:
                raise NotImplementedError

            def _rank_request_spec(self, text: str, default_limit: int = 0, max_limit: int = 20) -> Dict[str, Any]:
                raise NotImplementedError

        for name in ("_resolve_query_intent", "_rank_request_spec"):
            self.assertEqual(
                inspect.signature(getattr(FourAgentAskService, name)),
                inspect.signature(getattr(SignatureBaseline, name)),
            )


if __name__ == "__main__":
    unittest.main()
