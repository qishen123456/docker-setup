#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""历史快照自环异常检测单元测试。"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from smartask_report_history_store import _has_self_parent_anomaly, _is_stale_history_snapshot


class SelfParentAnomalyTest(unittest.TestCase):
    def test_normal_rows_no_anomaly(self):
        dataset_result = {
            "rows": [
                {"节点名称": "消费者事业部", "上级名称": None, "层级": "消费者事业部总体"},
                {"节点名称": "山东分公司", "上级名称": "消费者事业部", "层级": "分公司"},
                {"节点名称": "临沂城市公司", "上级名称": "山东分公司", "层级": "城市分公司"},
            ]
        }
        self.assertFalse(_has_self_parent_anomaly(dataset_result))

    def test_self_parent_city_company(self):
        dataset_result = {
            "rows": [
                {"节点名称": "消费者事业部", "上级名称": None, "层级": "消费者事业部总体"},
                {"节点名称": "山东分公司", "上级名称": "消费者事业部", "层级": "分公司"},
                {"节点名称": "山东分公司", "上级名称": "山东分公司", "层级": "城市分公司"},
            ]
        }
        self.assertTrue(_has_self_parent_anomaly(dataset_result))

    def test_self_parent_with_english_keys(self):
        dataset_result = {
            "rows": [
                {"name": "山东分公司", "parent": "山东分公司", "level": "城市分公司"},
            ]
        }
        self.assertTrue(_has_self_parent_anomaly(dataset_result))

    def test_empty_rows(self):
        self.assertFalse(_has_self_parent_anomaly({}))
        self.assertFalse(_has_self_parent_anomaly({"rows": []}))


class StaleSnapshotSelfParentTest(unittest.TestCase):
    def test_snapshot_with_self_parent_marked_stale(self):
        item = {
            "reportSnapshot": {
                "result": {
                    "dataset_results": [
                        {
                            "dataset_id": 2,
                            "rows": [
                                {"节点名称": "山东分公司", "上级名称": "山东分公司", "层级": "城市分公司"},
                            ],
                        }
                    ]
                }
            }
        }
        self.assertTrue(_is_stale_history_snapshot(item))


if __name__ == "__main__":
    unittest.main()
