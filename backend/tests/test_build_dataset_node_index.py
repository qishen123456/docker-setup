import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from build_dataset_node_index import affected_dataset_codes_for_source_table, merge_dataset_entries


class BuildDatasetNodeIndexTest(unittest.TestCase):
    def test_affected_dataset_codes_for_source_table_normalizes_name(self):
        self.assertEqual(
            affected_dataset_codes_for_source_table(" FEISHU_TBL_XIOAFEIZHE "),
            ["consumer_business_standard_v1"],
        )
        self.assertEqual(
            affected_dataset_codes_for_source_table("angel_group_data"),
            ["angel_business_2026_phase1"],
        )
        self.assertEqual(affected_dataset_codes_for_source_table("unknown_table"), [])

    def test_merge_dataset_entries_preserves_unaffected_datasets(self):
        existing = [
            {
                "dataset_id": 3,
                "dataset_code": "angel_business_2026_phase1",
                "dataset_name": "商用事业部（旧）",
                "node_count": 10,
                "alias_count": 5,
                "nodes": [{"node_name": "旧商用节点"}],
                "alias_index": [{"alias": "旧商用节点", "matches": []}],
            },
            {
                "dataset_id": 62,
                "dataset_code": "feishu_tbldianshang",
                "dataset_name": "电商事业部",
                "node_count": 8,
                "alias_count": 4,
                "nodes": [{"node_name": "电商节点"}],
                "alias_index": [{"alias": "电商节点", "matches": []}],
            },
        ]
        rebuilt = [
            {
                "dataset_id": 3,
                "dataset_code": "angel_business_2026_phase1",
                "dataset_name": "商用事业部（新）",
                "node_count": 12,
                "alias_count": 6,
                "nodes": [{"node_name": "新商用节点"}],
                "alias_index": [{"alias": "新商用节点", "matches": []}],
            }
        ]

        merged = merge_dataset_entries(existing, rebuilt)

        self.assertEqual([item["dataset_id"] for item in merged], [3, 62])
        self.assertEqual(merged[0]["dataset_name"], "商用事业部（新）")
        self.assertEqual(merged[0]["nodes"][0]["node_name"], "新商用节点")
        self.assertEqual(merged[1]["dataset_name"], "电商事业部")
        self.assertEqual(merged[1]["nodes"][0]["node_name"], "电商节点")


if __name__ == "__main__":
    unittest.main()
