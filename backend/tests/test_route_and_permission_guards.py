import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dataset_report_config as report_config_store
from data_permission_store import apply_row_level_filter
from four_agent_ask import FourAgentAskService
from organization_route_resolver import OrganizationRouteResolver
from report_spec_builder import build_report_spec
from smartask_advanced.skills.dataset_route import DatasetRouteSkill
from smartask_advanced.skills.route_guard import RouteGuardSkill


CATALOG = [
    {"id": 3, "dataset_name": "商用事业部", "dataset_code": "angel_business_2026"},
    {"id": 11, "dataset_name": "消费者测试数据集", "dataset_code": "consumer_business_standard_v1"},
]


class FakeRepo:
    def get_agent1_catalog(self):
        return CATALOG


def _node(node_id, parent_id, name, path_ids, path_names, level):
    return {
        "id": node_id,
        "tree_type_id": "tree_main",
        "parent_id": parent_id,
        "name": name,
        "enabled": True,
        "path_ids": path_ids,
        "path_names": path_names,
        "level": level,
    }


BASE_TREE = {
    "nodes": [
        _node("root", "", "安吉尔集团总部", ["root"], ["安吉尔集团总部"], 1),
        _node("commercial", "root", "商用事业部", ["root", "commercial"], ["安吉尔集团总部", "商用事业部"], 2),
        _node("south", "commercial", "南部分公司", ["root", "commercial", "south"], ["安吉尔集团总部", "商用事业部", "南部分公司"], 3),
        _node("consumer", "root", "消费者事业部", ["root", "consumer"], ["安吉尔集团总部", "消费者事业部"], 2),
        _node("hunan_consumer", "consumer", "湖南分公司", ["root", "consumer", "hunan_consumer"], ["安吉尔集团总部", "消费者事业部", "湖南分公司"], 3),
    ]
}

PERMISSIONS = {
    "rules": {
        "3": {
            "mode": "org_tree",
            "tree_type_id": "tree_main",
            "organization_node_ids": ["commercial", "south"],
        },
        "11": {
            "mode": "org_tree",
            "tree_type_id": "tree_main",
            "organization_node_ids": ["consumer", "hunan_consumer"],
        },
    }
}


class RouteAndPermissionGuardsTest(unittest.TestCase):
    def _resolve(self, question, tree=None):
        resolver = OrganizationRouteResolver()
        with patch("organization_route_resolver.load_organization_trees", return_value=tree or BASE_TREE), patch(
            "organization_route_resolver.load_data_permissions", return_value=PERMISSIONS
        ):
            return resolver.resolve(question, CATALOG)

    def test_suffix_conflict_does_not_route_hunan_rep_office_to_consumer_branch(self):
        self.assertIsNone(self._resolve("分析下湖南代表处的业绩"))

    def test_matching_suffix_still_routes_hunan_consumer_branch(self):
        route = self._resolve("分析下湖南分公司的业绩")

        self.assertIsNotNone(route)
        self.assertEqual(route["dataset_ids"], [11])
        self.assertEqual(route["resolved_members"], ["湖南分公司"])

    def test_commercial_rep_office_routes_when_tree_contains_the_node(self):
        tree = {
            "nodes": [
                *BASE_TREE["nodes"],
                _node(
                    "hunan_rep",
                    "south",
                    "湖南代表处",
                    ["root", "commercial", "south", "hunan_rep"],
                    ["安吉尔集团总部", "商用事业部", "南部分公司", "湖南代表处"],
                    4,
                ),
            ]
        }

        route = self._resolve("分析下湖南代表处的业绩", tree=tree)

        self.assertIsNotNone(route)
        self.assertEqual(route["dataset_ids"], [3])
        self.assertEqual(route["resolved_members"], ["湖南代表处"])

    def test_row_level_filter_allows_descendant_rows_by_path_columns(self):
        permissions = {
            "rules": {
                "3": {
                    "mode": "org_tree",
                    "scope": {"organization_field": "组织编码"},
                }
            }
        }
        with patch(
            "data_permission_store.user_org_scope_for_rule",
            return_value={"codes": ["SOUTH_CODE"], "names": ["南部分公司"], "node_ids": ["south"], "tree_type_ids": ["tree_main"]},
        ):
            filtered = apply_row_level_filter("SELECT * FROM demo", {"role": "user"}, 3, permissions=permissions)

        self.assertIn("链接字段(勿删)", filtered)
        self.assertIn("组织路径", filtered)
        self.assertIn("POSITION('南部分公司'", filtered)

    def test_rep_office_level_terms_boost_commercial_dataset_route(self):
        question = "分析下湖南代表处的业绩"
        commercial = {"id": 3, "dataset_name": "商用事业部", "dataset_code": "angel_business_2026"}
        consumer = {"id": 11, "dataset_name": "消费者测试数据集", "dataset_code": "consumer_business_standard_v1"}

        self.assertGreater(DatasetRouteSkill.score(question, commercial), DatasetRouteSkill.score(question, consumer))
        self.assertLessEqual(DatasetRouteSkill.score(question, consumer), 0)
        self.assertGreaterEqual(
            FourAgentAskService._profile_level_alias_score(
                question,
                {"levels": [{"dimension_name": "代表处", "aliases": ["代表处"]}]},
            ),
            90,
        )

    def test_route_guard_locks_commercial_when_org_tree_lacks_rep_office_node(self):
        question = "分析下湖南代表处的业绩"
        candidates = DatasetRouteSkill(FakeRepo()).run(question, limit=2)
        guard = RouteGuardSkill(FakeRepo())
        guard.organization_resolver.resolve = lambda *args, **kwargs: None

        result = guard.run(question=question, candidates=candidates)

        self.assertEqual(result["action"], "auto_lock")
        self.assertEqual(result["apply_dataset_ids"], [3])

    def test_known_sql_alias_typos_are_normalized_before_execution(self):
        sql = "SELECT * FROM 基础数据 WHERE 条线_type='区域条线' OR 条线Type='行业条线'"

        normalized = FourAgentAskService._normalize_known_sql_alias_typos(sql)

        self.assertIn("条线类型='区域条线'", normalized)
        self.assertIn("条线类型='行业条线'", normalized)
        self.assertNotIn("条线_type", normalized)
        self.assertNotIn("条线Type", normalized)

    def test_golden_sql_subject_literal_is_rewritten_for_current_question(self):
        service = object.__new__(FourAgentAskService)
        sample_sql = "WITH 汇总结果 AS (SELECT 1) SELECT * FROM 汇总结果 WHERE 节点名称 = '靳锋' LIMIT 100"
        context = {
            "dataset": {"dataset_code": "angel_business_2026", "dataset_name": "商用事业部"},
            "resolved_entities": {},
            "golden_sql_samples": [
                {
                    "id": 7,
                    "question": "看下靳锋的业绩",
                    "sql_text": sample_sql,
                    "match_score": 98,
                    "quality_score": 95,
                }
            ],
            "data_dictionary": [],
        }

        strategy = service._select_sql_strategy("看下赵标的业绩呢", {"match_score": 90, "route_margin": 20}, context)

        self.assertEqual(strategy["mode"], "sample_direct")
        self.assertTrue(strategy["sample_rewritten"])
        self.assertIn("节点名称 = '赵标'", strategy["sql"])
        self.assertNotIn("靳锋", strategy["sql"])

    def test_business_person_question_gets_dynamic_rule_scope(self):
        service = object.__new__(FourAgentAskService)
        context = {
            "dataset": {"dataset_code": "angel_business_2026", "dataset_name": "商用事业部"},
            "resolved_entities": {},
            "data_dictionary": [],
        }

        sql = service._build_rule_based_sql("看下赵标的业绩呢", {}, context)

        # 赵标被识别为末端业务代表，直接按业务代表字段过滤，不再递归下钻
        self.assertIn("'赵标'", sql)
        self.assertIn("业务代表 IN ('赵标')", sql)
        self.assertNotIn("WITH RECURSIVE", sql)
        self.assertNotIn("JOIN 命中链路 父节点", sql)

    def test_business_person_role_prefix_extracts_person_name(self):
        service = object.__new__(FourAgentAskService)
        context = {
            "dataset": {"dataset_code": "angel_business_2026_phase1", "dataset_name": "商用事业部（阶段一升级版）"},
            "resolved_entities": {},
        }

        names = service._question_subject_names("看下商用业务代表靳锋 的业绩情况", context)

        self.assertEqual(names, ["靳锋"])

    def test_business_person_role_prefix_uses_dynamic_rule_scope(self):
        service = object.__new__(FourAgentAskService)
        context = {
            "dataset": {"dataset_code": "angel_business_2026_phase1", "dataset_name": "商用事业部（阶段一升级版）"},
            "resolved_entities": {},
            "data_dictionary": [{"jsonb_key": "业务部"}],
        }

        # "业务代表...业绩情况" 命中层级 Overview（ranking）语义，整体走 ranking/list
        # 若需测试角色前缀的单节点范围，应使用非 Overview  metric 词（如达成率）
        sql = service._build_rule_based_sql("看下商用业务代表靳锋 的达成率", {}, context)

        self.assertIn("'靳锋'", sql)
        # 业务代表属于末端节点，按基线 1.1 只返回本节点，不再下钻
        self.assertNotIn("WITH RECURSIVE", sql)
        self.assertIn("业务代表 IN ('靳锋')", sql)
        self.assertNotIn("JOIN 命中链路 父节点", sql)

    def test_agent1_resolved_entities_take_priority_over_local_rules(self):
        """Agent1 解析结果优先，本地规则兜底"""
        service = object.__new__(FourAgentAskService)
        context = {
            "dataset": {"dataset_code": "angel_business_2026_phase1", "dataset_name": "商用事业部（阶段一升级版）"},
            "resolved_entities": {
                "all_members": ["赵标", "靳锋"],
                "entities": [{"members": ["赵标", "靳锋"]}],
            },
            "data_dictionary": [{"jsonb_key": "业务部"}],
        }

        sql = service._build_rule_based_sql("看下赵标和靳锋的业绩", {}, context)

        # 多主体对比按业务代表字段 IN 并行查询，不是递归 CTE
        self.assertIn("业务代表 IN ('赵标','靳锋')", sql)
        self.assertNotIn("节点名称 IN ('标和靳锋')", sql)

    def test_multi_person_level_overview_goes_filter_not_leaf(self):
        service = object.__new__(FourAgentAskService)
        context = {
            "dataset": {"dataset_code": "angel_business_2026_phase1", "dataset_name": "商用事业部（阶段一升级版）"},
            "report_config": report_config_store.get_default_config(),
            "resolved_entities": {},
            "data_dictionary": [{"jsonb_key": "业务部"}],
        }

        intent = service._resolve_query_intent("看下靳锋、赵标的业绩情况", context)
        self.assertEqual(intent["intent"], "filter")
        self.assertEqual(intent["target_level"], "业务代表")

        context["query_intent"] = intent
        sql = service._build_rule_based_sql("看下靳锋、赵标的业绩情况", intent, context)
        self.assertIn("业务代表 IN ('靳锋','赵标')", sql)
        self.assertIn("层级 = '业务代表'", sql)
        self.assertNotIn("WITH RECURSIVE", sql)

    def test_multi_parent_display_title_uses_performance_suffix(self):
        """multi_parent 标题应使用'的业绩'，且不应包含数据集根节点别名"""
        service = object.__new__(FourAgentAskService)
        dataset_result = {
            "dataset_name": "飞书商用事业部经营预算",
            "resolved_entities": {
                # 根节点别名可能混入解析结果
                "all_members": ["商用事业部", "东部分公司", "西部分公司"],
                "entities": [{"members": ["商用事业部", "东部分公司", "西部分公司"]}],
            },
            "query_intent": {
                "intent": "filter",
                "target_level": "分公司",
                "filter_metric_key": "level_only",
                "_multi_parent": True,
                "_multi_parent_names": ["东部分公司", "西部分公司"],
            },
            "rows": [{"层级": "分公司"}],
        }
        title = service._build_display_title("看下东部分公司、西部分公司业绩", dataset_result)
        self.assertEqual(title, "商用事业部东部分公司、西部分公司的业绩")

    def test_multi_branch_parent_overview_goes_multi_parent(self):
        """多个非叶子节点（分公司）的 overview 应走 multi_parent，并过滤掉数据集根节点别名"""
        service = object.__new__(FourAgentAskService)
        context = {
            "dataset": {"dataset_code": "angel_business_2026_phase1", "dataset_name": "商用事业部（阶段一升级版）"},
            "report_config": report_config_store.get_default_config(),
            "resolved_entities": {
                # 模拟 entity resolver 把数据集根节点别名也带进来的情况
                "all_members": ["商用事业部", "东部分公司", "西部分公司"],
                "entities": [{"members": ["商用事业部", "东部分公司", "西部分公司"]}],
            },
            "data_dictionary": [{"jsonb_key": "业务部"}],
        }

        intent = service._resolve_query_intent("看下东部分公司、西部分公司业绩", context)
        self.assertEqual(intent["intent"], "filter")
        self.assertEqual(intent["target_level"], "分公司")
        self.assertTrue(intent.get("_multi_parent"))
        self.assertEqual(intent.get("_multi_parent_names"), ["东部分公司", "西部分公司"])

        context["query_intent"] = intent
        sql = service._build_rule_based_sql("看下东部分公司、西部分公司业绩", intent, context)
        # 多父节点 overview 外层 WHERE 应以对象过滤开头，不应以层级过滤开头
        self.assertIn("\nWHERE 节点名称 IN ('东部分公司','西部分公司') OR 上级名称 IN ('东部分公司','西部分公司')\n", sql)
        # 根节点别名只出现在 CASE 的默认父节点兜底里，不能出现在 WHERE 过滤条件中
        self.assertNotIn("节点名称 IN ('商用事业部'", sql)
        self.assertNotIn("上级名称 IN ('商用事业部'", sql)
        self.assertNotIn("WHERE 层级 = '分公司'", sql)
        self.assertNotIn("WITH RECURSIVE", sql)

    def test_question_subject_names_can_ignore_resolved_root_alias(self):
        service = object.__new__(FourAgentAskService)
        context = {
            "dataset": {"dataset_code": "angel_business_2026_phase1", "dataset_name": "商用事业部（阶段一升级版）"},
            "resolved_entities": {
                "all_members": ["商用事业部"],
                "entities": [{"members": ["商用事业部"]}],
            },
        }

        names = service._question_subject_names("看下赵标的业绩", context, include_resolved=False)

        self.assertEqual(names, ["赵标"])

    def test_agent1_resolved_root_alias_used_when_no_explicit_person(self):
        """Agent1 解析出根节点别名且无显式人名时，使用 Agent1 结果"""
        service = object.__new__(FourAgentAskService)
        context = {
            "dataset": {"dataset_code": "angel_business_2026_phase1", "dataset_name": "商用事业部（阶段一升级版）"},
            "resolved_entities": {
                "all_members": ["商用事业部"],
                "entities": [{"members": ["商用事业部"]}],
            },
            "data_dictionary": [{"jsonb_key": "业务部"}],
        }

        sql = service._build_rule_based_sql("看下商用事业部的业绩", {}, context)

        self.assertIn("节点名称 IN ('商用事业部')", sql)

    def test_single_person_layered_analysis_answers_person_first(self):
        service = object.__new__(FourAgentAskService)
        rows = [
            {
                "条线": "行业条线",
                "层级": "业务代表",
                "节点名称": "赵标",
                "上级名称": "公共办公业务部",
                "总任务金额": 7000000,
                "年度开单金额": 4120000,
                "达成率": 58.88,
                "剩余任务金额": 2880000,
            },
            {
                "条线": "行业条线",
                "层级": "业务部",
                "节点名称": "公共办公业务部",
                "上级名称": "商用事业部",
                "总任务金额": 230000000,
                "年度开单金额": 135792000,
                "达成率": 59.04,
                "剩余任务金额": 94208000,
            },
        ]
        report_config = {
            "nameColumn": "节点名称",
            "parentColumn": "上级名称",
            "levelColumn": "层级",
            "trackColumn": "条线",
            "metrics": [
                {"key": "task", "label": "总任务金额", "column": "总任务金额", "format": "amount"},
                {"key": "actual", "label": "年度开单金额", "column": "年度开单金额", "format": "amount"},
                {"key": "rate", "label": "达成率", "column": "达成率", "format": "percent"},
                {"key": "remain", "label": "剩余任务金额", "column": "剩余任务金额", "format": "amount"},
            ],
            "levels": [
                {"name": "业务部", "values": ["业务部"]},
                {"name": "业务代表", "values": ["业务代表"]},
            ],
        }

        analysis = service._build_layered_management_report(
            "看下赵标的业绩",
            "商用事业部（阶段一升级版）",
            rows,
            list(rows[0].keys()),
            "",
            "",
            report_config,
            {"all_members": ["赵标"], "entities": [{"members": ["赵标"]}]},
            {},
        )

        self.assertIn("赵标当前作为业务代表", analysis)
        self.assertNotIn("商用事业部整体进度", analysis)

    def test_single_person_report_spec_focuses_person_node(self):
        rows = [
            {
                "条线": "行业条线",
                "层级": "业务代表",
                "节点名称": "赵标",
                "上级名称": "公共办公业务部",
                "总任务金额": 7000000,
                "年度开单金额": 4120000,
                "达成率": 58.88,
                "剩余任务金额": 2880000,
            },
            {
                "条线": "行业条线",
                "层级": "业务部",
                "节点名称": "公共办公业务部",
                "上级名称": "商用事业部",
                "总任务金额": 230000000,
                "年度开单金额": 135792000,
                "达成率": 59.04,
                "剩余任务金额": 94208000,
            },
        ]
        config = {
            "nameColumn": "节点名称",
            "parentColumn": "上级名称",
            "levelColumn": "层级",
            "trackColumn": "条线",
            "metrics": [
                {"key": "task", "label": "总任务金额", "column": "总任务金额", "format": "amount"},
                {"key": "actual", "label": "年度开单金额", "column": "年度开单金额", "format": "amount"},
                {"key": "rate", "label": "达成率", "column": "达成率", "format": "percent"},
                {"key": "remain", "label": "剩余任务金额", "column": "剩余任务金额", "format": "amount"},
            ],
            "levels": [
                {"name": "业务部", "values": ["业务部"]},
                {"name": "业务代表", "values": ["业务代表"]},
            ],
        }

        spec = build_report_spec(
            question="看下赵标的业绩",
            rows=rows,
            columns=list(rows[0].keys()),
            report_config=config,
            sql="",
            dataset={"dataset_code": "angel_business_2026_phase1", "dataset_name": "商用事业部（阶段一升级版）"},
            resolved_entities={"all_members": ["赵标"], "entities": [{"members": ["赵标"]}]},
        )

        self.assertEqual(spec.get("scope", {}).get("focusNode"), "赵标")

    def test_level_only_filter_summary_uses_entity_names(self):
        """level_only 过滤的报告摘要不应 fallback 到 rate_metric 和默认阈值"""
        rows = [
            {
                "节点名称": "靳锋",
                "上级名称": "华东分公司",
                "层级": "业务代表",
                "年度开单金额": 1000000,
                "总任务金额": 2000000,
                "达成率": 50.0,
                "剩余任务金额": 1000000,
            },
            {
                "节点名称": "赵标",
                "上级名称": "华北分公司",
                "层级": "业务代表",
                "年度开单金额": 1200000,
                "总任务金额": 2000000,
                "达成率": 60.0,
                "剩余任务金额": 800000,
            },
        ]
        config = {
            "queryIntent": {
                "intent": "filter",
                "target_level": "业务代表",
                "filter_metric_key": "level_only",
                "filter_metric_column": "",
                "filter_operator": "",
                "filter_value": None,
            },
            "nameColumn": "节点名称",
            "parentColumn": "上级名称",
            "levelColumn": "层级",
            "trackColumn": "条线",
            "metrics": [
                {"key": "task", "label": "总任务金额", "column": "总任务金额", "format": "amount"},
                {"key": "actual", "label": "年度开单金额", "column": "年度开单金额", "format": "amount"},
                {"key": "rate", "label": "达成率", "column": "达成率", "format": "percent"},
                {"key": "remain", "label": "剩余任务金额", "column": "剩余任务金额", "format": "amount"},
            ],
            "levels": [
                {"name": "业务部", "values": ["业务部"]},
                {"name": "业务代表", "values": ["业务代表"]},
            ],
        }

        spec = build_report_spec(
            question="看下靳锋、赵标的业绩情况",
            rows=rows,
            columns=list(rows[0].keys()),
            report_config=config,
            sql="",
            dataset={"dataset_code": "angel_business_2026_phase1", "dataset_name": "商用事业部（阶段一升级版）"},
            resolved_entities={"all_members": ["靳锋", "赵标"], "entities": [{"members": ["靳锋", "赵标"]}]},
        )

        summary = spec.get("answerSummary") or {}
        self.assertEqual(summary.get("title"), "筛选结果")
        self.assertEqual(summary.get("text"), "筛选出 2 个业务代表")
        self.assertEqual(summary.get("metricLabel"), "")
        self.assertEqual(summary.get("operator"), "")
        self.assertIsNone(summary.get("value"))
        self.assertEqual(summary.get("matchedCount"), 2)
        self.assertEqual(len(spec.get("matchedNodes") or []), 2)

    def test_multi_parent_spec_uses_parent_nodes_as_comparison_nodes(self):
        """multi_parent overview 的 matchedNodes 应为父节点，摘要携带 _multi_parent 标记"""
        rows = [
            {
                "节点名称": "东部分公司",
                "上级名称": "商用事业部",
                "层级": "分公司",
                "年度开单金额": 5000000,
                "总任务金额": 10000000,
                "达成率": 50.0,
                "剩余任务金额": 5000000,
            },
            {
                "节点名称": "西部分公司",
                "上级名称": "商用事业部",
                "层级": "分公司",
                "年度开单金额": 6000000,
                "总任务金额": 12000000,
                "达成率": 50.0,
                "剩余任务金额": 6000000,
            },
            {
                "节点名称": "山东代表处",
                "上级名称": "东部分公司",
                "层级": "代表处",
                "年度开单金额": 1000000,
                "总任务金额": 2000000,
                "达成率": 50.0,
                "剩余任务金额": 1000000,
            },
            {
                "节点名称": "陕西代表处",
                "上级名称": "西部分公司",
                "层级": "代表处",
                "年度开单金额": 1200000,
                "总任务金额": 2400000,
                "达成率": 50.0,
                "剩余任务金额": 1200000,
            },
        ]
        config = {
            "queryIntent": {
                "intent": "filter",
                "target_level": "分公司",
                "filter_metric_key": "level_only",
                "filter_metric_column": "",
                "filter_operator": "",
                "filter_value": None,
                "_multi_parent": True,
                "_multi_parent_names": ["东部分公司", "西部分公司"],
            },
            "nameColumn": "节点名称",
            "parentColumn": "上级名称",
            "levelColumn": "层级",
            "trackColumn": "条线",
            "metrics": [
                {"key": "task", "label": "总任务金额", "column": "总任务金额", "format": "amount"},
                {"key": "actual", "label": "年度开单金额", "column": "年度开单金额", "format": "amount"},
                {"key": "rate", "label": "达成率", "column": "达成率", "format": "percent"},
                {"key": "remain", "label": "剩余任务金额", "column": "剩余任务金额", "format": "amount"},
            ],
            "levels": [
                {"name": "分公司", "values": ["分公司"]},
                {"name": "代表处", "values": ["代表处"]},
            ],
        }

        spec = build_report_spec(
            question="看下东部分公司、西部分公司业绩",
            rows=rows,
            columns=list(rows[0].keys()),
            report_config=config,
            sql="",
            dataset={"dataset_code": "angel_business_2026_phase1", "dataset_name": "商用事业部（阶段一升级版）"},
            resolved_entities={
                # 模拟根节点别名被一起解析出来
                "all_members": ["商用事业部", "东部分公司", "西部分公司"],
                "entities": [{"members": ["商用事业部", "东部分公司", "西部分公司"]}],
            },
        )

        summary = spec.get("answerSummary") or {}
        self.assertEqual(summary.get("title"), "多对象业绩")
        self.assertEqual(summary.get("text"), "东部分公司、西部分公司及其下级")
        self.assertTrue(summary.get("_multi_parent"))
        self.assertEqual(summary.get("matchedCount"), 2)
        matched_names = [node.get("name") for node in spec.get("matchedNodes") or []]
        self.assertEqual(sorted(matched_names), ["东部分公司", "西部分公司"])


if __name__ == "__main__":
    unittest.main()
