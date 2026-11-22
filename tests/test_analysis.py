import math
import os
import tempfile
import unittest

from study.analysis import (
    POLICIES, ALWAYS, NEVER, WHEN, add_specificity, bootstrap_ci, build_report,
    frame_from_records, load_sessions, md_table, mixed_models, power_table,
    required_n, run_contrasts, specificity, summarize,
)
from study.fake_data import fake_records
from study.logger import append_jsonl


class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df, cls.excluded = frame_from_records(fake_records(30, seed=0), "human")

    def test_summary_has_six_cells_with_thirty_sessions_each(self):
        summary = summarize(self.df)
        self.assertEqual(len(summary), 6)
        self.assertTrue((summary["n"] == 30).all())

    def test_contrasts_recover_the_planted_effect(self):
        contrasts = run_contrasts(self.df)
        self.assertEqual(len(contrasts), 6)
        row = contrasts[(contrasts.clarity == "vague") & (contrasts.a == WHEN) & (contrasts.b == NEVER)].iloc[0]
        self.assertTrue(0.7 < row["token_ratio"] < 0.9, row["token_ratio"])
        self.assertLess(row["p_tokens"], 0.05)
        self.assertLess(row["ci_high"], 1.0)

    def test_clear_prompts_show_no_token_effect(self):
        contrasts = run_contrasts(self.df)
        row = contrasts[(contrasts.clarity == "clear") & (contrasts.a == WHEN) & (contrasts.b == NEVER)].iloc[0]
        self.assertTrue(0.85 < row["token_ratio"] < 1.15, row["token_ratio"])

    def test_holm_never_lowers_a_p_value(self):
        contrasts = run_contrasts(self.df)
        self.assertTrue((contrasts["p_tokens_holm"] >= contrasts["p_tokens"] - 1e-12).all())
        self.assertTrue((contrasts["p_success_holm"] >= contrasts["p_success"] - 1e-12).all())

    def test_models_run_and_return_tables(self):
        models = mixed_models(self.df, "human")
        self.assertIn("tokens", models)
        self.assertIn("success", models)
        self.assertTrue(models["tokens"].strip() and models["success"].strip())

    def test_report_contains_every_section(self):
        report = build_report(self.df, 0, "human")
        for heading in ("## Data", "## Descriptives", "## Pre-specified contrasts",
                        "## Mixed models", "## Power planning"):
            self.assertIn(heading, report)

    def test_power_estimate_needs_more_people_for_smaller_effects(self):
        self.assertLess(required_n(0.3, 0.8), required_n(0.3, 0.9))
        table, spread, n = power_table(self.df)
        self.assertEqual(n, 30)
        self.assertGreater(spread, 0)
        self.assertEqual(len(table), 4)

    def test_bootstrap_interval_of_constant_data(self):
        low, high = bootstrap_ci([2.0] * 10)
        self.assertAlmostEqual(low, 2.0)
        self.assertAlmostEqual(high, 2.0)

    def test_specificity_counts_mentioned_ambiguities(self):
        task = {"ambiguities": [{"keywords": ["order"]}, {"keywords": ["format"]}, {"keywords": ["error"]}]}
        self.assertAlmostEqual(specificity("Tell me the order and the error handling", task), 2 / 3)
        self.assertEqual(specificity("make it", task), 0.0)

    def test_add_specificity_never_crashes_without_tasks(self):
        self.assertGreaterEqual(len(add_specificity(self.df)), 180)

    def test_md_table_formats_numbers(self):
        import pandas as pd
        text = md_table(pd.DataFrame([{"a": 1.23456, "b": "x"}]), digits=2)
        self.assertIn("1.23", text)
        self.assertEqual(md_table(pd.DataFrame()), "(no data)")


class LoadingTests(unittest.TestCase):
    def test_technical_failures_are_excluded_and_counted(self):
        records = fake_records(6, seed=1)
        records[0]["technical_failure"] = True
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sessions.jsonl")
            for record in records:
                append_jsonl(path, record)
            df, excluded = load_sessions(path)
        self.assertEqual(excluded, 1)
        self.assertEqual(len(df), 35)

    def test_simulation_arm_pairs_by_task_and_repeat(self):
        records = []
        for task in ("t1", "t2"):
            for repeat in (0, 1):
                for policy in POLICIES:
                    for clarity in ("vague", "clear"):
                        records.append({
                            "participant_id": "SIM", "task_id": task, "repeat": repeat,
                            "policy": policy, "clarity": clarity, "total_tokens": 1000,
                            "passed": True, "n_questions": 0, "student_prompts": 1,
                            "wall_seconds": 60.0, "rating": None, "technical_failure": False,
                            "prompts": ["x"],
                        })
        df, _ = frame_from_records(records, "simulation")
        self.assertEqual(df["unit"].nunique(), 4)
        self.assertEqual(len(run_contrasts(df)), 6)


if __name__ == "__main__":
    unittest.main()