#!/usr/bin/env python3
"""Unit tests for ThreeToday deterministic planning (no AWS required)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lambda_function import enforce_three, _extract_json  # noqa: E402


def cand(title, hours=1.0, score=70, bucket="today", effort="medium", why="w", move="m"):
    return {
        "title": title,
        "hours": hours,
        "priority_score": score,
        "bucket_suggestion": bucket,
        "effort": effort,
        "why": why,
        "first_move": move,
    }


class EnforceThreeTests(unittest.TestCase):
    def test_hard_cap_of_three(self):
        model = {
            "rationale": "test",
            "candidates": [
                cand("A", 1, 100),
                cand("B", 1, 90),
                cand("C", 1, 80),
                cand("D", 1, 70),
                cand("E", 1, 60),
            ],
        }
        plan = enforce_three(model, hours=8, energy="medium")
        self.assertEqual(len(plan["today"]), 3)
        self.assertEqual([t["title"] for t in plan["today"]], ["A", "B", "C"])
        self.assertGreaterEqual(len(plan["parked"]), 2)

    def test_hour_budget_blocks_overflow(self):
        model = {
            "candidates": [
                cand("Deep", 3.0, 100),
                cand("Quick", 1.0, 90),
                cand("Other", 1.0, 80),
            ]
        }
        plan = enforce_three(model, hours=3.0, energy="medium")
        self.assertEqual(len(plan["today"]), 1)
        self.assertEqual(plan["today"][0]["title"], "Deep")
        self.assertAlmostEqual(plan["hours_allocated"], 3.0)
        titles_parked = {p["title"] for p in plan["parked"]}
        self.assertIn("Quick", titles_parked)

    def test_kill_low_score_suggestions(self):
        model = {
            "candidates": [
                cand("Must", 1, 95, "today"),
                cand("Noise", 2, 20, "killed", why="not worth it"),
            ]
        }
        plan = enforce_three(model, hours=4, energy="medium")
        self.assertEqual(plan["today"][0]["title"], "Must")
        self.assertTrue(any(k["title"] == "Noise" for k in plan["killed"]))

    def test_low_energy_downranks_high_effort(self):
        model = {
            "candidates": [
                cand("Hard", 2, 80, "today", effort="high"),
                cand("Easy", 1, 75, "today", effort="low"),
                cand("Mid", 1, 70, "today", effort="medium"),
            ]
        }
        plan = enforce_three(model, hours=6, energy="low")
        titles = [t["title"] for t in plan["today"]]
        # Easy should survive; hard is penalized but may still fit if budget allows
        self.assertIn("Easy", titles)
        self.assertLessEqual(len(titles), 3)

    def test_schedule_created_for_today_items(self):
        model = {"candidates": [cand("Only", 1.0, 99)]}
        plan = enforce_three(model, hours=2, energy="high")
        self.assertEqual(len(plan["today"]), 1)
        self.assertGreaterEqual(len(plan["schedule"]), 1)
        self.assertIn("Only", plan["schedule"][0]["focus"])

    def test_empty_candidates(self):
        plan = enforce_three({"candidates": []}, hours=4, energy="medium")
        self.assertEqual(plan["today"], [])
        self.assertEqual(plan["hours_allocated"], 0)

    def test_extract_json_from_fence(self):
        raw = 'Here you go:\n```json\n{"candidates": []}\n```\n'
        data = _extract_json(raw)
        self.assertEqual(data, {"candidates": []})

    def test_extract_json_raw_object(self):
        raw = 'prefix {"rationale":"x","candidates":[]} suffix'
        data = _extract_json(raw)
        self.assertEqual(data["rationale"], "x")


if __name__ == "__main__":
    unittest.main()
