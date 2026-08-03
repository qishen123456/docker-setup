import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from organization_route_resolver import OrganizationRouteResolver


CATALOG = [
    {"id": 3, "dataset_name": "商用事业部"},
    {"id": 11, "dataset_name": "消费者事业部"},
]


def _tree_node():
    return {
        "id": "hunan",
        "tree_type_id": "tree_main",
        "name": "湖南分公司",
        "enabled": True,
        "path_ids": ["root", "consumer", "hunan"],
        "path_names": ["集团", "消费者事业部", "湖南分公司"],
        "level": 3,
    }


def _org_rule(selected_node):
    return {
        "mode": "org_tree",
        "tree_type_id": "tree_main",
        "organization_node_ids": [selected_node],
    }


def _index_dataset(dataset_id):
    return {
        "dataset_id": dataset_id,
        "dataset_name": f"数据集 {dataset_id}",
        "nodes": [
            {
                "node_name": "湖南分公司",
                "parent_name": "消费者事业部",
                "aliases": ["湖南分公司", "湖南"],
            }
        ],
    }


class OrganizationRouteCatalogBoundaryTest(unittest.TestCase):
    def test_tree_candidates_are_limited_by_catalog_before_allowed_ids(self):
        resolver = OrganizationRouteResolver()
        permissions = {
            "rules": {
                "2": _org_rule("hunan"),
                "11": _org_rule("hunan"),
            }
        }

        with patch(
            "organization_route_resolver.load_organization_trees",
            return_value={"nodes": [_tree_node()]},
        ), patch(
            "organization_route_resolver.load_data_permissions",
            return_value=permissions,
        ), patch.object(
            resolver,
            "_load_dataset_node_index",
            return_value={"datasets": []},
        ):
            route = resolver.resolve(
                "湖南分公司的业绩",
                CATALOG,
                allowed_dataset_ids=[2, 11],
            )

        self.assertIsNotNone(route)
        self.assertEqual(route["dataset_ids"], [11])
        self.assertEqual(route["candidate_dataset_ids"], [11])
        self.assertEqual(route["resolved_members"], ["湖南分公司"])
        self.assertFalse(route["requires_confirmation"])

    def test_node_index_candidates_outside_catalog_are_ignored(self):
        resolver = OrganizationRouteResolver()
        node_index = {"datasets": [_index_dataset(2)]}
        permissions = {"rules": {"11": _org_rule("hunan")}}

        with patch(
            "organization_route_resolver.load_organization_trees",
            return_value={"nodes": [_tree_node()]},
        ), patch(
            "organization_route_resolver.load_data_permissions",
            return_value=permissions,
        ), patch.object(
            resolver,
            "_load_dataset_node_index",
            return_value=node_index,
        ):
            route = resolver.resolve(
                "湖南分公司的业绩",
                CATALOG,
                allowed_dataset_ids=[2, 11],
            )

        self.assertIsNotNone(route)
        self.assertEqual(route["dataset_ids"], [11])
        self.assertEqual(route["candidate_dataset_ids"], [11])
        self.assertEqual(route["resolved_members"], ["湖南分公司"])
        self.assertFalse(route["requires_confirmation"])

    def test_tree_candidates_are_intersected_with_allowed_ids(self):
        resolver = OrganizationRouteResolver()
        permissions = {
            "rules": {
                "3": _org_rule("hunan"),
                "11": _org_rule("hunan"),
            }
        }

        with patch(
            "organization_route_resolver.load_organization_trees",
            return_value={"nodes": [_tree_node()]},
        ), patch(
            "organization_route_resolver.load_data_permissions",
            return_value=permissions,
        ), patch.object(
            resolver,
            "_load_dataset_node_index",
            return_value={"datasets": []},
        ):
            route = resolver.resolve(
                "湖南分公司的业绩",
                CATALOG,
                allowed_dataset_ids=[11],
            )

        self.assertEqual(route["dataset_ids"], [11])
        self.assertEqual(route["resolved_members"], ["湖南分公司"])
        self.assertFalse(route["requires_confirmation"])

    def test_node_index_candidates_are_intersected_with_allowed_ids(self):
        resolver = OrganizationRouteResolver()
        node_index = {"datasets": [_index_dataset(3), _index_dataset(11)]}
        permissions = {
            "rules": {
                "3": {"mode": "public"},
                "11": {"mode": "public"},
            }
        }

        with patch(
            "organization_route_resolver.load_organization_trees",
            return_value={"nodes": []},
        ), patch(
            "organization_route_resolver.load_data_permissions",
            return_value=permissions,
        ), patch.object(
            resolver,
            "_load_dataset_node_index",
            return_value=node_index,
        ):
            route = resolver.resolve(
                "湖南分公司的业绩",
                CATALOG,
                allowed_dataset_ids=[11],
            )

        self.assertEqual(route["dataset_ids"], [11])
        self.assertEqual(route["resolved_members"], ["湖南分公司"])
        self.assertFalse(route["requires_confirmation"])

    def test_catalog_internal_ambiguity_keeps_confirmation_semantics(self):
        resolver = OrganizationRouteResolver()
        node_index = {"datasets": [_index_dataset(3), _index_dataset(11)]}
        permissions = {
            "rules": {
                "3": {"mode": "public"},
                "11": {"mode": "public"},
            }
        }

        with patch(
            "organization_route_resolver.load_organization_trees",
            return_value={"nodes": []},
        ), patch(
            "organization_route_resolver.load_data_permissions",
            return_value=permissions,
        ), patch.object(
            resolver,
            "_load_dataset_node_index",
            return_value=node_index,
        ):
            route = resolver.resolve("湖南分公司的业绩", CATALOG)

        self.assertTrue(route["requires_confirmation"])
        self.assertEqual(route["decision"], "wait_boss_confirm")
        self.assertEqual(route["candidate_dataset_ids"], [3, 11])
        self.assertEqual(
            [option["dataset_ids"] for option in route["confirmation_options"]],
            [[3], [11]],
        )


if __name__ == "__main__":
    unittest.main()
