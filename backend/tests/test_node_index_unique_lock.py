# -*- coding: utf-8 -*-
"""节点索引唯一性直锁单测（基线 §3.6：唯一真实节点命中时直接直出）。

场景：
- "南部的业绩"（南部=ds3 唯一别名，但含指标词"业绩"，_extract_bare_node_candidate 拒收）
  → 必须由 node_index_unique 直锁 ds3，不再落 LLM 仲裁弹确认卡
- "湖南的业绩"（湖南同时存在于 ds2/ds3）→ 不锁，维持原仲裁流程
- 节点索引缺失/无命中 → 不锁（fail-open）
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from four_agent_ask import FourAgentAskService

CATALOG = [
    {"id": 2, "dataset_name": "消费者事业部开单金额", "dataset_code": "consumer_business_standard_v1",
     "business_domain": "消费者事业部", "synonyms": ["消费者事业部"]},
    {"id": 3, "dataset_name": "商用事业部开单金额", "dataset_code": "angel_business_2026_phase1",
     "business_domain": "商用事业部", "synonyms": ["商用事业部"]},
]

NODE_INDEX = {
    "datasets": [],
    "flat_alias_index": [
        {"alias": "南部", "matches": [
            {"dataset_id": 3, "dataset_name": "商用事业部开单金额", "node_name": "南部分公司", "node_level": "分公司"}]},
        {"alias": "南部分公司", "matches": [
            {"dataset_id": 3, "dataset_name": "商用事业部开单金额", "node_name": "南部分公司", "node_level": "分公司"}]},
        {"alias": "湖南", "matches": [
            {"dataset_id": 2, "dataset_name": "消费者事业部开单金额", "node_name": "湖南分公司", "node_level": "分公司"},
            {"dataset_id": 3, "dataset_name": "商用事业部开单金额", "node_name": "湖南代表处", "node_level": "代表处"}]},
    ],
}


class _FakeRepo:
    def get_agent1_catalog(self):
        return CATALOG

    def get_dataset_context(self, dataset_id, question, top_k_samples=5):
        return {}


class NodeIndexUniqueLockTest(unittest.TestCase):
    def _route(self, question, node_index=NODE_INDEX):
        service = FourAgentAskService()
        service.repository = _FakeRepo()
        service._dataset_node_index = node_index
        # 屏蔽上游 LLM 主体消解（node_index_dataset_unique 路径），让流量确定性到达直锁块
        # 不走到 LLM 仲裁：未锁定时由 mock 仲裁器兜底返回"无需确认"
        no_confirm = {"need_confirm": False, "options": [], "auto_pick_option_id": ""}
        with patch.object(service.organization_route_resolver, "resolve", return_value=None), \
             patch.object(service, "_agent1_resolve_org_subject", return_value=None), \
             patch.object(service.disambiguation_arbiter, "evaluate", return_value=no_confirm):
            return service.route_with_agent1(question)

    def test_unique_node_alias_locks_dataset_despite_metric_word(self):
        route = self._route("南部的业绩")
        self.assertEqual(route.get("dataset_ids"), [3])
        self.assertFalse(route.get("requires_confirmation"))
        self.assertEqual(route.get("arbiter_reason"), "node_index_unique")

    def test_full_node_name_also_locks(self):
        route = self._route("南部分公司业绩如何")
        self.assertEqual(route.get("dataset_ids"), [3])
        self.assertEqual(route.get("arbiter_reason"), "node_index_unique")

    def test_cross_dataset_alias_does_not_lock(self):
        # "湖南"在 ds2/ds3 都存在 → 不许直锁，维持原流程（mock 仲裁器接管）
        route = self._route("湖南的业绩")
        self.assertNotEqual(route.get("arbiter_reason"), "node_index_unique")

    def test_no_alias_hit_does_not_lock(self):
        route = self._route("各分公司业绩排名")
        self.assertNotEqual(route.get("arbiter_reason"), "node_index_unique")

    def test_empty_index_fail_open(self):
        route = self._route("南部的业绩", node_index={"datasets": [], "flat_alias_index": []})
        self.assertNotEqual(route.get("arbiter_reason"), "node_index_unique")

    def test_permission_catalog_restricts_lock(self):
        # 用户只有 ds2 权限时，南部（ds3 唯一）不得锁到越权数据集
        service = FourAgentAskService()
        service.repository = _FakeRepo()
        service._dataset_node_index = NODE_INDEX
        no_confirm = {"need_confirm": False, "options": [], "auto_pick_option_id": ""}
        with patch.object(service.organization_route_resolver, "resolve", return_value=None), \
             patch.object(service, "_agent1_resolve_org_subject", return_value=None), \
             patch.object(service.disambiguation_arbiter, "evaluate", return_value=no_confirm):
            route = service.route_with_agent1("南部的业绩", allowed_dataset_ids=[2])
        self.assertNotEqual(route.get("arbiter_reason"), "node_index_unique")
        self.assertNotIn(3, route.get("dataset_ids") or [])


if __name__ == "__main__":
    unittest.main()


class NodeIndexAmbiguousConfirmTest(unittest.TestCase):
    """跨数据集/多节点命中 → 真实节点级确认卡（不弹模糊"指标存在"卡）。"""

    def _route(self, question, node_index=NODE_INDEX):
        service = FourAgentAskService()
        service.repository = _FakeRepo()
        service._dataset_node_index = node_index
        no_confirm = {"need_confirm": False, "options": [], "auto_pick_option_id": ""}
        with patch.object(service.organization_route_resolver, "resolve", return_value=None), \
             patch.object(service, "_agent1_resolve_org_subject", return_value=None), \
             patch.object(service.disambiguation_arbiter, "evaluate", return_value=no_confirm):
            return service.route_with_agent1(question)

    def test_cross_dataset_alias_shows_real_nodes(self):
        route = self._route("湖南的业绩")
        self.assertTrue(route.get("requires_confirmation"))
        self.assertEqual(route.get("arbiter_reason"), "node_index_ambiguous")
        labels = [o.get("label") for o in route.get("confirmation_options") or []]
        # 统一完整问句格式（2026-08-31 定稿）
        self.assertIn("消费者事业部 · 湖南分公司的业绩", labels)
        self.assertIn("商用事业部 · 湖南代表处的业绩", labels)
        # 选项带真实节点名和层级，不是模糊的"指标存在"
        for o in route["confirmation_options"]:
            self.assertTrue(o.get("resolved_subject_name"))
            self.assertEqual(o.get("option_type"), "dataset_disambiguation")

    def test_initials_latin_token_expands_to_node_options(self):
        # "sh的业绩"：原始问句无别名命中 → 首字母护栏扩展 sh→上海/深圳 → 节点级确认卡
        index = {
            "datasets": [],
            "flat_alias_index": [
                {"alias": "上海", "matches": [
                    {"dataset_id": 2, "dataset_name": "消费者事业部开单金额", "node_name": "上海城市公司", "node_level": "城市分公司"},
                    {"dataset_id": 3, "dataset_name": "商用事业部开单金额", "node_name": "上海代表处", "node_level": "代表处"}]},
                {"alias": "深圳", "matches": [
                    {"dataset_id": 2, "dataset_name": "消费者事业部开单金额", "node_name": "深圳城市公司", "node_level": "城市分公司"}]},
            ],
        }
        with patch("disambiguation.initials_guardrail.map_token", return_value=["上海", "深圳"]):
            route = self._route("sh的业绩", node_index=index)
        self.assertTrue(route.get("requires_confirmation"))
        self.assertEqual(route.get("arbiter_reason"), "node_index_ambiguous")
        labels = [o.get("label") for o in route.get("confirmation_options") or []]
        # 统一完整问句格式（2026-08-31 定稿）
        self.assertIn("商用事业部 · 上海代表处的业绩", labels)
        self.assertIn("消费者事业部 · 上海城市公司的业绩", labels)
        self.assertIn("消费者事业部 · 深圳城市公司的业绩", labels)

    def test_initials_single_dataset_still_locks(self):
        # 缩写扩展后全部命中同一数据集 → 直锁不弹卡（如 jd→京东直营 只有电商有）
        index = {
            "datasets": [],
            "flat_alias_index": [
                {"alias": "京东", "matches": [
                    {"dataset_id": 4, "dataset_name": "电商事业部开单金额", "node_name": "京东直营", "node_level": "业务部"}]},
            ],
        }
        catalog = CATALOG + [{"id": 4, "dataset_name": "电商事业部开单金额", "dataset_code": "ecom",
                              "business_domain": "电商事业部", "synonyms": ["电商事业部"]}]
        service = FourAgentAskService()
        service.repository = type("R", (), {"get_agent1_catalog": lambda s: catalog,
                                            "get_dataset_context": lambda s, d, q, top_k_samples=5: {}})()
        service._dataset_node_index = index
        with patch.object(service.organization_route_resolver, "resolve", return_value=None), \
             patch.object(service, "_agent1_resolve_org_subject", return_value=None), \
             patch("disambiguation.initials_guardrail.map_token", return_value=["京东"]):
            route = service.route_with_agent1("jd的业绩")
        self.assertEqual(route.get("dataset_ids"), [4])
        self.assertFalse(route.get("requires_confirmation"))
        self.assertEqual(route.get("arbiter_reason"), "node_index_unique")

    SAME_DS_INDEX = {
        "datasets": [],
        "flat_alias_index": [
            {"alias": "南部", "matches": [
                {"dataset_id": 3, "dataset_name": "商用事业部开单金额", "node_name": "南部分公司", "node_level": "分公司"}]},
            {"alias": "南部分公司", "matches": [
                {"dataset_id": 3, "dataset_name": "商用事业部开单金额", "node_name": "南部分公司", "node_level": "分公司"}]},
            {"alias": "北部", "matches": [
                {"dataset_id": 3, "dataset_name": "商用事业部开单金额", "node_name": "北部分公司", "node_level": "分公司"}]},
            {"alias": "北部分公司", "matches": [
                {"dataset_id": 3, "dataset_name": "商用事业部开单金额", "node_name": "北部分公司", "node_level": "分公司"}]},
            {"alias": "上海", "matches": [
                {"dataset_id": 3, "dataset_name": "商用事业部开单金额", "node_name": "上海城市公司", "node_level": "城市分公司"},
                {"dataset_id": 3, "dataset_name": "商用事业部开单金额", "node_name": "上海代表处", "node_level": "代表处"}]},
            {"alias": "上海城市公司", "matches": [
                {"dataset_id": 3, "dataset_name": "商用事业部开单金额", "node_name": "上海城市公司", "node_level": "城市分公司"}]},
        ],
    }

    def test_initials_same_dataset_collision_shows_node_card(self):
        # nb→[南部分公司, 北部分公司] 同属 ds3：主体本身歧义，必须出节点确认卡而非静默直锁
        with patch("disambiguation.initials_guardrail.map_token", return_value=["南部分公司", "北部分公司"]):
            route = self._route("nb的业绩", node_index=self.SAME_DS_INDEX)
        self.assertTrue(route.get("requires_confirmation"))
        self.assertEqual(route.get("arbiter_reason"), "node_index_ambiguous")
        labels = [o.get("label") for o in route.get("confirmation_options") or []]
        # 统一完整问句格式：同数据集也带数据集前缀（2026-08-31 定稿）
        self.assertIn("商用事业部 · 南部分公司的业绩", labels)
        self.assertIn("商用事业部 · 北部分公司的业绩", labels)
        # 统一确认话术
        self.assertEqual(route.get("confirmation_question"), "你是不是想问：")
        for o in route["confirmation_options"]:
            self.assertEqual(o.get("dataset_ids"), [3])
            self.assertTrue(o.get("resolved_subject_name"))
            # 描述必须带数据集名，用户才知道每个节点属于哪个数据集
            self.assertIn("商用事业部开单金额", o.get("description") or "")

    def test_same_dataset_multi_node_literal_shows_node_card(self):
        # "上海的业绩"：上海在同数据集有城市公司+代表处两个节点 → 出节点选择卡
        route = self._route("上海的业绩", node_index=self.SAME_DS_INDEX)
        self.assertTrue(route.get("requires_confirmation"))
        self.assertEqual(route.get("arbiter_reason"), "node_index_ambiguous")
        labels = [o.get("label") for o in route.get("confirmation_options") or []]
        # 统一完整问句格式（2026-08-31 定稿）
        self.assertIn("商用事业部 · 上海城市公司的业绩", labels)
        self.assertIn("商用事业部 · 上海代表处的业绩", labels)

    def test_longest_alias_wins_no_overconfirm(self):
        # "上海城市公司的业绩"：长别名已精确到节点 → 直锁，不被短前缀"上海"带出兄弟节点弹卡
        route = self._route("上海城市公司的业绩", node_index=self.SAME_DS_INDEX)
        self.assertEqual(route.get("dataset_ids"), [3])
        self.assertFalse(route.get("requires_confirmation"))
        self.assertEqual(route.get("arbiter_reason"), "node_index_unique")
        self.assertEqual(route.get("resolved_subject_name"), "上海城市公司")
