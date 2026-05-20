import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_permission_store import apply_row_level_filter
from four_agent_ask import FourAgentAskService
from organization_route_resolver import OrganizationRouteResolver
from smartask_advanced.skills.dataset_route import DatasetRouteSkill


CATALOG = [
    {"id": 3, "dataset_name": "商用事业部", "dataset_code": "angel_business_2026"},
    {"id": 11, "dataset_name": "消费者测试数据集", "dataset_code": "consumer_business_standard_v1"},
]


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
        self.assertGreaterEqual(
            FourAgentAskService._profile_level_alias_score(
                question,
                {"levels": [{"dimension_name": "代表处", "aliases": ["代表处"]}]},
            ),
            90,
        )


if __name__ == "__main__":
    unittest.main()
