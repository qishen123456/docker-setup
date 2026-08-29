# -*- coding: utf-8 -*-
"""结构化解析条单测（parse-bar-design.md v1）。

覆盖：三槽位聚合、span 定位三来源（matched_phrase 直击/别名反查/继承标记）、
占用区间去重、出条铁律（确认卡/纠正卡/early_clarify/错误不出条）、
开关与可见角色、fail-open。

依赖真实 config/dataset_node_index.json（南部→南部分公司 别名反查）；
不触网。settings 一律 mock，不依赖 parse_bar_settings.json 实际开关状态。
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from disambiguation import parse_spans as ps

_USER = {"role": "super_admin"}
_SETTINGS = {"enabled": True, "visible_roles": ["super_admin"],
             "metric_aliases": {"开单金额": "开单金额", "业绩": "开单金额", "达成率": "达成率"}}


def _result(q, members=None, matched_phrase="", **over):
    """构造 ask() 风格 result：单数据集 ds3 + resolved_entities。"""
    entities = []
    if members:
        entities = [{"dimension_name": "组织树节点", "members": members,
                     "matched_phrase": matched_phrase, "source": "organization_tree_route"}]
    r = {
        "question": q,
        "row_count": 7,
        "route": {"dataset_ids": [3], "requires_confirmation": False},
        "dataset_results": [{
            "dataset_id": 3, "dataset_name": "商用事业部开单金额",
            "resolved_entities": {"intent": "single", "entities": entities,
                                  "all_members": members or [], "confidence": 1.0},
            "query_intent": {},
        }],
    }
    r.update(over)
    return r


def _bar(question, result, user=_USER, settings=None):
    with mock.patch.object(ps, "_load_settings", return_value=settings or _SETTINGS):
        return ps.build_parse_bar(question=question, result=result, user=user)


class ParseBarSlotsTest(unittest.TestCase):
    """三槽位聚合 + span 定位三来源。"""

    def test_three_slots_with_alias_reverse_lookup(self):
        # 实锤场景：「南部的业绩」→ matched_phrase 是全名"南部分公司"find 不到，
        # 反查别名"南部"命中 [0,2)；指标"业绩"[3,5)
        bar = _bar("南部的业绩", _result("南部的业绩", ["南部分公司"], "南部分公司"))
        self.assertIsNotNone(bar)
        slots = {s["slot"]: s for s in bar["slots"]}
        self.assertEqual(slots["dataset"]["resolved_value"], "商用事业部开单金额")
        self.assertEqual(slots["node"]["resolved_value"], "南部分公司")
        self.assertEqual(slots["node"]["span_text"], "南部")
        self.assertEqual((slots["node"]["start"], slots["node"]["end"]), (0, 2))
        self.assertEqual(slots["metric"]["resolved_value"], "开单金额")
        self.assertEqual(slots["metric"]["span_text"], "业绩")
        self.assertIn("南部分公司", bar["text"])
        self.assertIn("商用事业部开单金额", bar["text"])

    def test_matched_phrase_direct_hit(self):
        # 原句就是全名：matched_phrase 直击，不走反查
        bar = _bar("南部分公司的业绩", _result("南部分公司的业绩", ["南部分公司"], "南部分公司"))
        node = next(s for s in bar["slots"] if s["slot"] == "node")
        self.assertEqual((node["start"], node["end"]), (0, 5))
        self.assertEqual(node["span_text"], "南部分公司")

    def test_inherited_node_no_forced_span(self):
        # §3.5 追问：实体继承自上文，原句无字面出现 → inherited，不硬找 span
        bar = _bar("那他的达成率呢", _result("那他的达成率呢", ["南部分公司"], "南部分公司"))
        node = next(s for s in bar["slots"] if s["slot"] == "node")
        self.assertTrue(node.get("inherited"))
        self.assertNotIn("start", node)
        self.assertIn("继承自上文", bar["inherited_note"])
        # 指标槽不受影响：达成率正常框出
        metric = next(s for s in bar["slots"] if s["slot"] == "metric")
        self.assertEqual(metric["span_text"], "达成率")

    def test_occupied_regions_no_overlap(self):
        # 双对象：「东部」「南部」各自框出，span 不重叠
        r = _result("东部和南部的对比", ["东部分公司"], "东部分公司")
        r["dataset_results"][0]["resolved_entities"]["entities"].append(
            {"dimension_name": "组织树节点", "members": ["南部分公司"],
             "matched_phrase": "南部分公司", "source": "organization_tree_route"})
        bar = _bar("东部和南部的对比", r)
        nodes = [s for s in bar["slots"] if s["slot"] == "node"]
        self.assertEqual(len(nodes), 2)
        spans = sorted((n["start"], n["end"]) for n in nodes)
        self.assertEqual(spans, [(0, 2), (3, 5)])  # 东部[0,2) 南部[3,5)

    def test_metric_longest_word_first(self):
        # 长词优先：「开单金额」整体命中，不被「金额」截断
        bar = _bar("商用开单金额", _result("商用开单金额", ["商用事业部"], "商用事业部"))
        metric = next(s for s in bar["slots"] if s["slot"] == "metric")
        self.assertEqual(metric["span_text"], "开单金额")
        self.assertEqual((metric["start"], metric["end"]), (2, 6))


class ParseBarGateTest(unittest.TestCase):
    """出条铁律 + 开关 + 可见角色 + fail-open。"""

    def test_confirm_card_message_no_bar(self):
        r = _result("各分公司业绩排名", requires_confirmation=True)
        self.assertIsNone(_bar("各分公司业绩排名", r))

    def test_clarify_suggestion_message_no_bar(self):
        r = _result("南部的业绩", ["南部分公司"], clarify_suggestion={"candidates": ["x"]})
        self.assertIsNone(_bar("南部的业绩", r))

    def test_early_clarify_no_bar(self):
        r = _result("商泳的业绩", early_clarify=True, dataset_results=[])
        self.assertIsNone(_bar("商泳的业绩", r))

    def test_error_no_bar(self):
        self.assertIsNone(_bar("南部的业绩", _result("南部的业绩", ["南部分公司"], error="boom")))

    def test_no_dataset_results_no_bar(self):
        self.assertIsNone(_bar("南部的业绩", _result("南部的业绩", dataset_results=[])))

    def test_switch_off_no_bar(self):
        r = _result("南部的业绩", ["南部分公司"], "南部分公司")
        self.assertIsNone(_bar("南部的业绩", r, settings={"enabled": False, "visible_roles": ["super_admin"]}))

    def test_invisible_user_no_bar(self):
        r = _result("南部的业绩", ["南部分公司"], "南部分公司")
        self.assertIsNone(_bar("南部的业绩", r, user={"role": "viewer"}))

    def test_fail_open(self):
        r = _result("南部的业绩", ["南部分公司"], "南部分公司")
        with mock.patch.object(ps, "_extract_node_slots", side_effect=RuntimeError("boom")):
            self.assertIsNone(_bar("南部的业绩", r))
        with mock.patch.object(ps, "_load_settings", side_effect=RuntimeError("boom")):
            self.assertIsNone(ps.build_parse_bar("南部的业绩", r, _USER))

    def test_empty_slots_no_bar(self):
        # 无实体无指标无数据集名 → 不出条（空条没意义）
        r = _result("排名", dataset_results=[{"dataset_id": 3, "dataset_name": "",
                                              "resolved_entities": {"entities": []}, "query_intent": {}}])
        self.assertIsNone(_bar("排名", r))


if __name__ == "__main__":
    unittest.main()
