import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import smartask_report_history_store as history_store


def make_history_item(question, dataset_result):
    return {
        "id": "history-report-test",
        "title": question,
        "question": question,
        "reportSnapshot": {
            "version": 2,
            "question": question,
            "result": {"dataset_results": [dataset_result]},
        },
    }


class SmartAskReportHistoryStoreTest(unittest.TestCase):
    def test_non_leaf_node_snapshot_marked_stale_against_node_index(self):
        item = make_history_item(
            "电商事业部的业绩",
            {
                "dataset_id": 62,
                "row_count": 1,
                "rows": [{"层级": "事业部", "节点名称": "电商事业部"}],
                "report_spec": {
                    "scope": {
                        "focusNode": "电商事业部",
                        "focusNodeIsLeaf": True,
                    }
                },
            },
        )
        node_index = {
            "datasets": [
                {
                    "dataset_id": 62,
                    "nodes": [
                        {"node_name": "电商事业部", "node_level": "事业部", "parent_name": None},
                        {"node_name": "国内业务部", "node_level": "业务部", "parent_name": "电商事业部"},
                    ],
                }
            ]
        }

        with patch.object(history_store, "read_json", return_value=node_index):
            self.assertTrue(history_store._is_stale_history_snapshot(item))

    def test_explicit_aggregate_single_node_snapshot_not_marked_stale(self):
        item = make_history_item(
            "电商事业部整体业绩",
            {
                "dataset_id": 62,
                "row_count": 1,
                "rows": [{"层级": "事业部", "节点名称": "电商事业部"}],
                "report_spec": {
                    "scope": {
                        "focusNode": "电商事业部",
                        "focusNodeIsLeaf": True,
                    }
                },
            },
        )
        node_index = {
            "datasets": [
                {
                    "dataset_id": 62,
                    "nodes": [
                        {"node_name": "电商事业部", "node_level": "事业部", "parent_name": None},
                        {"node_name": "国内业务部", "node_level": "业务部", "parent_name": "电商事业部"},
                    ],
                }
            ]
        }

        with patch.object(history_store, "read_json", return_value=node_index):
            self.assertFalse(history_store._is_stale_history_snapshot(item))

    def test_ranking_snapshot_with_smaller_saved_limit_marked_stale(self):
        item = make_history_item(
            "消费者事业部垫底的5个城市分公司",
            {
                "dataset_id": 2,
                "row_count": 1,
                "rows": [{"层级": "城市分公司", "节点名称": "洛阳城市公司"}],
                "query_intent": {
                    "intent": "ranking",
                    "target_level": "城市分公司",
                    "top_n": 1,
                    "direction": "asc",
                },
            },
        )

        self.assertTrue(history_store._is_stale_history_snapshot(item))


if __name__ == "__main__":
    unittest.main()
