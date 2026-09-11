import unittest

import numpy as np
import pandas as pd

from mmf_engine.revision10 import (
    adaptive_market_structure,
    four_scenario_model,
    relative_strength_matrix,
    structural_change_review,
    systemic_risk_filter,
)


class Revision10Tests(unittest.TestCase):
    def test_micro_range_prefers_current_session_without_losing_reference_band(self):
        dates = pd.date_range("2026-07-01", periods=30, freq="B")
        closes = np.linspace(150, 126, 30)
        frame = pd.DataFrame({
            "Date": dates,
            "Open": closes + 1,
            "High": closes + 3,
            "Low": closes - 3,
            "Close": closes,
            "EMA20": pd.Series(closes).ewm(span=20, adjust=False).mean(),
            "EMA50": pd.Series(closes).ewm(span=50, adjust=False).mean(),
        })
        frame.loc[frame.index[-1], ["Open", "High", "Low", "Close"]] = [128, 130, 116, 122]
        result = adaptive_market_structure(frame, {"close": 122, "high": 130, "low": 116}, {"clusters": []})
        self.assertEqual(result["micro"]["low"], 116)
        self.assertEqual(result["micro"]["high"], 130)
        self.assertEqual(result["micro"]["source"], "current_session_range")
        self.assertIn("referenceLow", result["micro"])

    def test_sustained_relative_weakness_is_not_repeated_as_new_information(self):
        dates = pd.date_range("2026-06-01", periods=40, freq="B")
        benchmark = pd.DataFrame({"Date": dates, "Close": np.linspace(100, 110, 40)})
        weak = pd.DataFrame({"Date": dates, "Close": np.linspace(100, 80, 40)})
        histories = {"QQQ": benchmark, "SOXX": weak, "NVDA": weak.copy(), "SOXL": weak.copy()}
        relative = relative_strength_matrix(histories)
        self.assertTrue(all(not row.get("changedToday") for row in relative["rows"]))
        review = structural_change_review(
            {"micro": {"position": "inside", "boundaryChangedToday": False}},
            relative,
            {"status": "LOW"},
            {},
        )
        self.assertFalse(review["materialChange"])

    def test_continuous_selling_reweights_four_scenarios(self):
        structure = {"regime": "RANGE", "micro": {"low": 116, "high": 130}, "daily": {"ema20": 142}}
        leadership = {"status": "WEAKENING"}
        rotation = {"classification": "CAPITAL ROTATION"}
        systemic = {"status": "LOW"}
        catalyst = {"isWaitingRegime": False}
        balanced = four_scenario_model(structure, leadership, rotation, systemic, catalyst, {}, {"classification": "BALANCED / MIXED AUCTION"})
        selling = four_scenario_model(structure, leadership, rotation, systemic, catalyst, {}, {"classification": "CONTINUOUS SELLING"})
        self.assertEqual(selling["probabilityTotal"], 100)
        self.assertEqual(selling["auctionInput"], "CONTINUOUS SELLING")
        self.assertGreater(
            selling["scenarios"][2]["probability"] + selling["scenarios"][3]["probability"],
            balanced["scenarios"][2]["probability"] + balanced["scenarios"][3]["probability"],
        )

    def test_systemic_filter_reports_direction_and_level_separately(self):
        heat = {"groups": [
            {"nameCN": "半导体链", "avgChangePct": -2.0, "items": [
                {"ticker": "SOXX", "changePct": -2.0}, {"ticker": "NVDA", "changePct": -2.0}
            ]},
            {"nameCN": "大盘", "avgChangePct": -1.2, "items": [
                {"ticker": "QQQ", "changePct": -1.3}, {"ticker": "SPY", "changePct": -1.0}
            ]},
            {"nameCN": "信用", "avgChangePct": -0.8, "items": [{"ticker": "HYG", "changePct": -0.7}]},
        ]}
        result = systemic_risk_filter(heat, {"rows": []}, {"vix": {"last": 25, "changePct": 8}})
        self.assertEqual(result["direction"], "INCREASING")
        self.assertIn(result["status"], {"ELEVATED", "HIGH"})


if __name__ == "__main__":
    unittest.main()
