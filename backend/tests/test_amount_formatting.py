#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""金额格式化单元测试：验证元/万元口径统一展示。"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from report_spec_builder import _format_amount, _infer_metric_from_columns, _column_uses_wan_unit
from four_agent_ask import FourAgentAskService


class ColumnWanUnitTest(unittest.TestCase):
    def test_column_uses_wan_unit(self):
        self.assertTrue(_column_uses_wan_unit("线下任务_万元"))
        self.assertTrue(_column_uses_wan_unit("总任务_万元"))
        self.assertTrue(_column_uses_wan_unit("年度开单金额转换万"))
        self.assertFalse(_column_uses_wan_unit("总任务金额"))
        self.assertFalse(_column_uses_wan_unit("年度开单金额"))


class InferMetricUnitTest(unittest.TestCase):
    def test_infer_yuan_for_standard_columns(self):
        m = _infer_metric_from_columns(
            ["总任务金额", "年度开单金额"], "task", "总任务金额", ["任务", "目标"], "amount"
        )
        self.assertIsNotNone(m)
        self.assertEqual(m["unit"], "元")
        self.assertEqual(m["scale"], 1)

    def test_infer_wan_for_wan_columns(self):
        m = _infer_metric_from_columns(
            ["总任务_万元", "线下任务_万元"], "task", "总任务金额", ["任务", "目标"], "amount"
        )
        self.assertIsNotNone(m)
        self.assertEqual(m["unit"], "万元")
        self.assertEqual(m["scale"], 1)


class FormatAmountTest(unittest.TestCase):
    def test_yuan_small(self):
        self.assertEqual(_format_amount(9000), "9000")
        self.assertEqual(_format_amount(1234.56), "1234.56")

    def test_yuan_wan_range(self):
        self.assertEqual(_format_amount(10000), "1万")
        self.assertEqual(_format_amount(123456), "12.3万")
        self.assertEqual(_format_amount(9876543), "988万")

    def test_yuan_yi_range(self):
        self.assertEqual(_format_amount(126286318), "1.26亿")
        self.assertEqual(_format_amount(455000000), "4.55亿")

    def test_wan_small(self):
        self.assertEqual(_format_amount(1789, {"unit": "万元", "scale": 1}), "1789万")

    def test_wan_to_yi(self):
        self.assertEqual(_format_amount(15610.13, {"unit": "万元", "scale": 1}), "1.56亿")
        self.assertEqual(_format_amount(178971, {"unit": "万元", "scale": 1}), "17.9亿")

    def test_wan_inferred_from_column(self):
        self.assertEqual(_format_amount(1789, {"column": "总任务_万元"}), "1789万")
        self.assertEqual(_format_amount(15610.13, {"column": "年度开单金额转换万"}), "1.56亿")


class FourAgentFormatMetricTest(unittest.TestCase):
    def test_default_yuan(self):
        self.assertEqual(FourAgentAskService._format_metric(9000), "9000")
        self.assertEqual(FourAgentAskService._format_metric(126286318), "1.26亿")

    def test_with_metric_wan(self):
        self.assertEqual(
            FourAgentAskService._format_metric(1789, metric={"format": "amount", "unit": "万元", "scale": 1}),
            "1789万",
        )
        self.assertEqual(
            FourAgentAskService._format_metric(15610.13, metric={"format": "amount", "unit": "万元", "scale": 1}),
            "1.56亿",
        )
        self.assertEqual(
            FourAgentAskService._format_metric(178971, metric={"format": "amount", "unit": "万元", "scale": 1}),
            "17.9亿",
        )

    def test_with_metric_column_hint(self):
        self.assertEqual(
            FourAgentAskService._format_metric(1789, metric={"format": "amount", "column": "总任务_万元"}),
            "1789万",
        )

    def test_percent(self):
        self.assertEqual(FourAgentAskService._format_metric(27.76, "%"), "27.76%")


if __name__ == "__main__":
    unittest.main()
