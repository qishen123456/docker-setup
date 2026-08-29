# -*- coding: utf-8 -*-
"""P1-a 输入理解层影子模式单测（冻结范围 3 条）。

覆盖：候选出口书架校验（编造节点/拼接污染/错字残留/fail-open）、
首字母静默护栏（检测/映射/verdict/风险标记/fail-open）、
方向观察位候选对、方向卡级联修错字（含遮蔽兜底）、correct_question 纯纠正函数、
影子日志新字段写入（candidate_validation / initials_guardrail / proposed_candidates）。

依赖真实 config/dataset_node_index.json（商用事业部/上海代表处/达播/丁杰/东部分公司等别名）
与 pypinyin；不触网（LLM 调用全部 mock 掉）。
"""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from disambiguation import candidate_validator as cv
from disambiguation import direction_ambiguity as da
from disambiguation import initials_guardrail as ig
from disambiguation import shadow_gatekeeper as sg
from disambiguation import typo_fastpath as tf


class CandidateValidatorTest(unittest.TestCase):
    """冻结范围 1：候选出口书架校验（影子，只记录不拦截）。"""

    def test_fabricated_node_rejected(self):
        # 纯编造：候选出现书架不存在的 X分公司 形态节点
        r = cv.validate_candidates(["昆仑分公司业绩怎么样"], question="各分公司业绩怎么样")
        self.assertFalse(r["pass"])
        self.assertEqual(len(r["rejected"]), 1)
        self.assertEqual(r["rejected"][0]["candidate"], "昆仑分公司业绩怎么样")
        self.assertIn("昆仑分公司", r["rejected"][0]["reason"])
        self.assertEqual(r["rejected"][0]["code"], "fabricated_node")

    def test_fabricated_node_from_splice_rejected(self):
        # 实锤：「东北三省」→ 候选"东北部分公司"=「东」+「北部分公司」（残段拼接书架节点）
        r = cv.validate_candidates(["东北部分公司业绩怎么样"], question="东北三省业绩怎么样")
        self.assertFalse(r["pass"])
        self.assertEqual(r["rejected"][0]["code"], "spliced_alias")
        self.assertIn("北部分公司", r["rejected"][0]["reason"])

    def test_spliced_alias_rejected(self):
        # 实锤：候选"达成率100%以上海代表处" =「100%以」+「上海代表处」拼接污染
        r = cv.validate_candidates(["达成率100%以上海代表处"], question="达成率100%以上的代表处")
        self.assertFalse(r["pass"])
        self.assertEqual(r["rejected"][0]["code"], "spliced_alias")
        self.assertIn("上海代表处", r["rejected"][0]["reason"])

    def test_spliced_short_alias_rejected(self):
        # 实锤：「未达百分之百」→"未达播分之百"（"达播"节点名注入）
        r = cv.validate_candidates(["未达播分之百"], question="未达百分之百")
        self.assertFalse(r["pass"])
        self.assertEqual(r["rejected"][0]["code"], "spliced_alias")
        self.assertIn("达播", r["rejected"][0]["reason"])

    def test_legit_candidate_passes(self):
        r = cv.validate_candidates(
            ["东部分公司排名第一的业务员", "商用事业部今年达成率"],
            question="东部分公司最好最坏的业务员",
        )
        self.assertTrue(r["pass"])
        self.assertEqual(r["rejected"], [])
        self.assertEqual(len(r["candidates"]), 2)

    def test_typo_residue_near_alias(self):
        # 候选残留错字"商泳事业部"（书架近似"商用事业部"）→ near_alias_node
        r = cv.validate_candidates(
            ["商泳事业部排名第一的业务员"], question="商泳事业部最好最坏的业务员"
        )
        self.assertFalse(r["pass"])
        self.assertEqual(r["rejected"][0]["code"], "near_alias_node")
        self.assertIn("商用事业部", r["rejected"][0]["reason"])

    def test_legit_correction_not_flagged_as_splice(self):
        # 合法错字纠正候选（看商泳→看商用）："看商"不是功能词，不得误判拼接
        r = cv.validate_candidates(["看商用事业部的业绩"], question="看商泳事业部的业绩")
        self.assertTrue(r["pass"])

    def test_empty_and_blank_candidates(self):
        self.assertTrue(cv.validate_candidates([])["pass"])
        self.assertTrue(cv.validate_candidates(["", "  "])["pass"])

    def test_fail_open_on_alias_load_error(self):
        with mock.patch.object(cv, "_load_alias_entries", side_effect=RuntimeError("boom")):
            r = cv.validate_candidates(["东北部分公司业绩怎么样"], question="东北三省")
        self.assertTrue(r["pass"])
        self.assertEqual(r["rejected"], [])
        self.assertEqual(r["candidates"], ["东北部分公司业绩怎么样"])

    def test_validate_and_log_fail_open(self):
        # 配置/日志全挂也不许抛
        with mock.patch.object(cv, "is_enabled", side_effect=RuntimeError("boom")):
            self.assertIsNone(cv.validate_and_log("zero_row_diagnosis", "q", ["c"]))


class InitialsGuardrailTest(unittest.TestCase):
    """冻结范围 2：首字母静默护栏（影子，只观察记录）。"""

    def test_detect_dj_with_pass_verdict(self):
        # 实锤场景：DJ→83 行静默答错类
        entries = ig.build_guardrail_entries("DJ业绩怎么样", {"row_count": 83, "route": {}})
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["detected"], "DJ")
        self.assertEqual(entries[0]["pipeline_verdict"], "pass")
        self.assertIn("丁杰", entries[0]["mapping_candidates"])

    def test_full_pinyin_token_maps_to_entity(self):
        self.assertIn("东部", ig.map_token("dongbu"))
        self.assertIn("商用", ig.map_token("shangyong"))

    def test_verdict_confirm_card_zero(self):
        self.assertEqual(ig.pipeline_verdict({"route": {"requires_confirmation": True}}), "confirm")
        self.assertEqual(ig.pipeline_verdict({"route": {"decision": "early_clarify"}}), "card")
        self.assertEqual(ig.pipeline_verdict({"row_count": 0, "route": {}}), "zero")
        self.assertEqual(ig.pipeline_verdict({"row_count": 5, "route": {}}), "pass")
        self.assertEqual(ig.pipeline_verdict({"error": "x"}), "error")

    def test_risk_flag_silent_wrong_suspect(self):
        # pass + 多候选 → 风险标记；pass + 唯一候选 → 不标；非 pass → 不标
        with mock.patch.object(ig, "map_token", return_value=["丁杰", "杜建"]):
            e = ig.build_guardrail_entries("DJ业绩", {"row_count": 83, "route": {}})[0]
            self.assertEqual(e.get("risk"), "silent_wrong_suspect")
        with mock.patch.object(ig, "map_token", return_value=[]):
            e = ig.build_guardrail_entries("DJ业绩", {"row_count": 83, "route": {}})[0]
            self.assertEqual(e.get("risk"), "silent_wrong_suspect")
        with mock.patch.object(ig, "map_token", return_value=["丁杰"]):
            e = ig.build_guardrail_entries("DJ业绩", {"row_count": 83, "route": {}})[0]
            self.assertNotIn("risk", e)
        with mock.patch.object(ig, "map_token", return_value=[]):
            e = ig.build_guardrail_entries(
                "DJ业绩", {"row_count": 0, "route": {"requires_confirmation": True}}
            )[0]
            self.assertNotIn("risk", e)

    def test_no_latin_returns_empty(self):
        self.assertEqual(ig.build_guardrail_entries("东部分公司业绩怎么样", {"row_count": 1}), [])

    def test_fail_open(self):
        with mock.patch.object(ig, "pipeline_verdict", side_effect=RuntimeError("boom")):
            self.assertEqual(ig.build_guardrail_entries("DJ业绩怎么样", {}), [])
        with mock.patch.object(ig, "map_token", side_effect=RuntimeError("boom")):
            self.assertEqual(ig.build_guardrail_entries("DJ业绩怎么样", {}), [])


class CorrectQuestionTest(unittest.TestCase):
    """typo_fastpath.correct_question：纯纠正函数，复用同一张别名表。"""

    def test_hit_returns_corrected(self):
        self.assertEqual(tf.correct_question("商泳事业部的业绩"), "商用事业部的业绩")

    def test_miss_returns_original(self):
        q = "东部分公司业绩怎么样"
        self.assertEqual(tf.correct_question(q), q)

    def test_fail_open(self):
        with mock.patch.object(tf, "detect_obvious_typo", side_effect=RuntimeError("boom")):
            self.assertEqual(tf.correct_question("商泳事业部的业绩"), "商泳事业部的业绩")
        self.assertEqual(tf.correct_question(""), "")


class DirectionCascadeTest(unittest.TestCase):
    """冻结范围 3：观察位候选对（影子）+ 方向卡级联修错字（唯一活体改动）。"""

    def test_observe_proposed_candidates(self):
        hit = da.detect_direction_ambiguity("看下最差不的业务员")
        self.assertTrue(hit["observe_only"])
        self.assertEqual(
            hit["proposed_candidates"], ["看下最差的业务员", "看下最好的业务员"]
        )

    def test_observe_pairs_mapping(self):
        # 映射表：高→[最高,最低]、多→[最多,最少]、少→[最少,最多]
        self.assertEqual(
            da.detect_direction_ambiguity("最高不的分公司")["proposed_candidates"],
            ["最高的分公司", "最低的分公司"],
        )
        self.assertEqual(
            da.detect_direction_ambiguity("最少不的人")["proposed_candidates"],
            ["最少的人", "最多的人"],
        )

    def _no_llm(self):
        return mock.patch.object(sg, "generate_direction_candidates", return_value=[])

    def test_cascade_fixes_typo_in_candidates(self):
        # 实锤：「商泳事业部最好最坏的业务员」候选必须是"商用事业部…"不带"商泳"
        question = "商泳事业部最好最坏的业务员"
        hit = da.detect_direction_ambiguity(question)
        self.assertIsNotNone(hit)
        with self._no_llm():
            result = da.build_direction_clarify_result(question, hit)
        candidates = result["clarify_suggestion"]["candidates"]
        self.assertTrue(candidates)
        self.assertTrue(all("商泳" not in c for c in candidates))
        self.assertTrue(any("商用事业部" in c for c in candidates))
        # 活体结构不变：question/interpretation 仍是原问题
        self.assertEqual(result["question"], question)
        self.assertEqual(result["clarify_suggestion"]["interpretation"], question)

    def test_cascade_fail_open_keeps_original_candidates(self):
        question = "商泳事业部最好最坏的业务员"
        hit = da.detect_direction_ambiguity(question)
        with self._no_llm(), mock.patch.object(
            tf, "correct_question", side_effect=RuntimeError("boom")
        ):
            result = da.build_direction_clarify_result(question, hit)
        candidates = result["clarify_suggestion"]["candidates"]
        self.assertEqual(candidates, hit["candidates"])  # 回退原候选（带错字也不许崩）

    def test_no_typo_keeps_original(self):
        question = "东部分公司最好最坏的业务员"
        hit = da.detect_direction_ambiguity(question)
        with self._no_llm():
            result = da.build_direction_clarify_result(question, hit)
        self.assertEqual(result["clarify_suggestion"]["candidates"], hit["candidates"])


class ShadowLogFieldsTest(unittest.TestCase):
    """影子日志新字段：candidate_validation / initials_guardrail / proposed_candidates。"""

    def _fake_settings(self, log_path):
        return {"enabled": True, "log_path": log_path, "model_id": 0}

    def test_run_shadow_log_writes_new_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "shadow.jsonl")
            fake_gk = {
                "action": "suggest",
                "confidence": 0.9,
                "reason": "x",
                "candidates": ["达成率100%以上海代表处"],
            }
            with mock.patch.object(sg, "_load_settings", return_value=self._fake_settings(log_path)), \
                 mock.patch.object(sg, "_call_gatekeeper", return_value=fake_gk):
                sg.run_shadow_log(
                    "达成率100%以上的代表处",
                    {"route": {"dataset_ids": [3]}, "row_count": 0},
                )
            record = json.loads(open(log_path, encoding="utf-8").readline())
            val = record.get("candidate_validation") or {}
            self.assertFalse(val.get("pass", True))
            self.assertEqual(val["rejected"][0]["code"], "spliced_alias")

    def test_run_shadow_log_writes_initials_guardrail(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "shadow.jsonl")
            fake_gk = {"action": "pass", "confidence": 0.9, "reason": "", "candidates": []}
            with mock.patch.object(sg, "_load_settings", return_value=self._fake_settings(log_path)), \
                 mock.patch.object(sg, "_call_gatekeeper", return_value=fake_gk):
                sg.run_shadow_log("DJ业绩怎么样", {"route": {"dataset_ids": [3]}, "row_count": 83})
            record = json.loads(open(log_path, encoding="utf-8").readline())
            guard = record.get("initials_guardrail") or []
            self.assertEqual(guard[0]["detected"], "DJ")
            self.assertEqual(guard[0]["pipeline_verdict"], "pass")

    def test_run_shadow_log_fail_open_on_validator_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "shadow.jsonl")
            with mock.patch.object(sg, "_load_settings", return_value=self._fake_settings(log_path)), \
                 mock.patch.object(sg, "_call_gatekeeper", side_effect=RuntimeError("timeout")), \
                 mock.patch.object(cv, "validate_candidates", side_effect=RuntimeError("boom")), \
                 mock.patch.object(ig, "build_guardrail_entries", side_effect=RuntimeError("boom")):
                sg.run_shadow_log("DJ业绩怎么样", {"route": {"dataset_ids": [3]}, "row_count": 0})
            record = json.loads(open(log_path, encoding="utf-8").readline())
            self.assertEqual(record["gk_status"], "error")  # 日志照写，主流程零感知

    def test_log_direction_writes_proposed_and_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "shadow.jsonl")
            hit = da.detect_direction_ambiguity("东北三省最差不的业务员")
            with mock.patch.object(sg, "_load_settings", return_value=self._fake_settings(log_path)):
                da.log_direction("东北三省最差不的业务员", hit)
            record = json.loads(open(log_path, encoding="utf-8").readline())
            self.assertEqual(record["gk_action"], "observe")
            self.assertEqual(
                record.get("proposed_candidates"),
                ["东北三省最差的业务员", "东北三省最好的业务员"],
            )
            # 观察位候选过书架校验："东北三省"不在书架，但"三省最"... 无组织后缀，不误判
            self.assertIn("candidate_validation", record)
    def test_log_direction_uses_shown_candidates(self):
        # 弹卡路径：影子校验与 candidate_options_topN 以实际展示候选为准（级联修错字后的版本）
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "shadow.jsonl")
            hit = da.detect_direction_ambiguity("商泳事业部最好最坏的业务员")
            shown = ["商用事业部排名第一的业务员", "商用事业部排名倒数第一的业务员"]
            with mock.patch.object(sg, "_load_settings", return_value=self._fake_settings(log_path)):
                da.log_direction("商泳事业部最好最坏的业务员", hit, shown_candidates=shown)
            record = json.loads(open(log_path, encoding="utf-8").readline())
            self.assertEqual(record["candidate_options_topN"], shown)
            self.assertTrue(record["candidate_validation"]["pass"])


class InitialsPreviewTest(unittest.TestCase):
    """首字母提示条（超管预览）：build_initials_preview —— P1-b soft_hint 的预览形态。

    双候选来自索引节点（不硬猜）；精排表 abbreviation_aliases.json 优先于拼音索引。
    预览只挂 clarify_suggestion（source=initials_guardrail），不设 early_clarify。
    """

    _USER = {"role": "super_admin"}

    def _settings(self, **over):
        s = {
            "initials_preview_enabled": True,
            "visible_enabled": True,
            "visible_roles": ["super_admin"],
        }
        s.update(over)
        return s

    def _preview(self, question, user="__default__", **settings_over):
        if user == "__default__":
            user = self._USER
        with mock.patch.object(
            sg, "_load_settings", return_value=self._settings(**settings_over)
        ):
            return ig.build_initials_preview(question, user)

    def test_curated_alias_wins_over_index(self):
        # 精排表 jd→京东直营 优先于拼音索引（索引里 jd 会撞"青岛"等节点）
        p = self._preview("JD的业绩")
        self.assertIsNotNone(p)
        self.assertEqual(p["source"], "initials_guardrail")
        self.assertEqual(p["candidates"], ["京东直营的业绩"])
        self.assertEqual(p["confidence"], 0.9)
        self.assertNotIn("early_clarify", p)  # 预览不设 early_clarify，确认卡照常显示

    def test_collision_lists_index_candidates(self):
        # 撞车组不设默认：CH 由索引出双候选（迟昊/程欢），用户点选，不硬猜
        p = self._preview("CH开了多少单")
        self.assertIsNotNone(p)
        self.assertEqual(len(p["candidates"]), 2)
        self.assertEqual(set(p["candidates"]), {"迟昊开了多少单", "程欢开了多少单"})
        self.assertEqual(p["confidence"], 0.6)

    def test_overlap_dedup_with_following_text(self):
        # TM直营开单金额：实体"天猫直营"后缀与原文"直营…"重叠 → 不叠出"直营直营"
        p = self._preview("TM直营开单金额")
        self.assertIsNotNone(p)
        self.assertEqual(p["candidates"], ["天猫直营开单金额"])

    def test_two_tokens_no_preview(self):
        # 恰 1 个拉丁 token 才提示：JD+TM 双缩写走确认卡，不挂预览
        self.assertIsNone(self._preview("JD和TM的业绩"))

    def test_switch_off_returns_none(self):
        self.assertIsNone(self._preview("JD的业绩", initials_preview_enabled=False))

    def test_invisible_user_returns_none(self):
        self.assertIsNone(self._preview("JD的业绩", user={"role": "viewer"}))

    def test_no_mapping_returns_none(self):
        with mock.patch.object(ig, "map_token", return_value=[]):
            self.assertIsNone(self._preview("ZZ业绩怎么样"))

    def test_fail_open(self):
        with mock.patch.object(ig, "map_token", side_effect=RuntimeError("boom")):
            self.assertIsNone(self._preview("JD的业绩"))
        with mock.patch.object(sg, "_load_settings", side_effect=RuntimeError("boom")):
            self.assertIsNone(ig.build_initials_preview("JD的业绩", self._USER))


if __name__ == "__main__":
    unittest.main()
