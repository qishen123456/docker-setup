import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from four_agent_ask import FourAgentAskService


MINIMAL_PROFILE = {
    "levels": [
        {
            "dimension_name": "分公司",
            "aliases": ["分公司"],
            "members": ["东部分公司", "西部分公司", "南部分公司", "北部分公司"],
            "groups": [],
        },
        {
            "dimension_name": "城市分公司",
            "aliases": ["城市分公司", "城市公司"],
            "members": ["上海城市分公司", "北京城市分公司"],
            "groups": [],
        },
    ]
}


class EntityResolutionGuardTest(unittest.TestCase):
    def _service(self):
        return object.__new__(FourAgentAskService)

    def test_normalize_preserves_has_specific_node_false(self):
        service = self._service()
        raw = {
            "intent": "unknown",
            "scope_mode": "unknown",
            "entities": [],
            "ranking_params": None,
            "confidence": 0.9,
            "has_specific_node": False,
        }
        fallback = {"all_members": [], "entities": [], "confidence": 0}
        result = service._normalize_entity_resolution(raw, fallback, MINIMAL_PROFILE)
        self.assertIn("has_specific_node", result)
        self.assertFalse(result["has_specific_node"])

    def test_normalize_defaults_has_specific_node_to_true_when_missing(self):
        service = self._service()
        raw = {
            "intent": "single",
            "scope_mode": "single",
            "entities": [
                {
                    "dimension_name": "分公司",
                    "members": ["东部分公司"],
                    "matched_phrase": "东部分公司",
                    "reason": "test",
                }
            ],
            "ranking_params": None,
            "confidence": 0.9,
        }
        fallback = {"all_members": [], "entities": [], "confidence": 0}
        result = service._normalize_entity_resolution(raw, fallback, MINIMAL_PROFILE)
        self.assertTrue(result["has_specific_node"])

    def test_normalize_defaults_has_specific_node_to_false_when_missing_and_no_members(self):
        service = self._service()
        raw = {
            "intent": "filter",
            "scope_mode": "filter",
            "entities": [],
            "ranking_params": None,
            "confidence": 0.9,
        }
        fallback = {"all_members": [], "entities": [], "confidence": 0}
        result = service._normalize_entity_resolution(raw, fallback, MINIMAL_PROFILE)
        self.assertFalse(result["has_specific_node"])

    def test_has_specific_node_returns_false_from_context(self):
        service = self._service()
        context = {
            "resolved_entities": {
                "has_specific_node": False,
                "all_members": [],
                "entities": [],
            }
        }
        self.assertFalse(service._has_specific_node(context))

    def test_has_specific_node_defaults_to_true_when_missing(self):
        service = self._service()
        context = {}
        self.assertTrue(service._has_specific_node(context))

    def test_question_subject_names_skips_regex_when_no_specific_node(self):
        service = self._service()
        context = {
            "resolved_entities": {
                "has_specific_node": False,
                "all_members": [],
                "entities": [],
            }
        }
        names = service._question_subject_names("看下大于一个亿的分公司", context)
        self.assertEqual(names, [])

    def test_question_subject_names_still_finds_node_when_specific_node_true(self):
        service = self._service()
        context = {
            "resolved_entities": {
                "has_specific_node": True,
                "all_members": [],
                "entities": [],
            }
        }
        names = service._question_subject_names("看下东部分公司的业绩", context)
        self.assertIn("东部分公司", names)


    def test_normalize_chinese_numbers(self):
        service = self._service()
        self.assertEqual(service._normalize_chinese_numbers("一个亿"), "1亿")
        self.assertEqual(service._normalize_chinese_numbers("两千万"), "2000万")
        self.assertEqual(service._normalize_chinese_numbers("三点五亿"), "3.5亿")
        self.assertEqual(service._normalize_chinese_numbers("看下大于一个亿的分公司"), "看下大于1亿的分公司")


if __name__ == "__main__":
    unittest.main()
