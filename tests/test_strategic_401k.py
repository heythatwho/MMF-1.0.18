import unittest

import numpy as np
import pandas as pd

from mmf_engine.strategic_401k import (
    DEFAULT_CONFIG,
    build_401k_strategic_module,
    classify_action,
    contribution_tilt,
    portfolio_drift,
)


def frame(prices):
    prices = np.asarray(prices, dtype=float)
    return pd.DataFrame({
        "Date": pd.date_range("2025-01-01", periods=len(prices), freq="B"),
        "Open": prices,
        "High": prices * 1.01,
        "Low": prices * 0.99,
        "Close": prices,
        "Volume": np.full(len(prices), 1_000_000),
    })


class Strategic401kTests(unittest.TestCase):
    def test_drift_and_opportunity_are_independent(self):
        drift = portfolio_drift(
            {"SP500": .60, "EXTENDED_MARKET": .25, "INTERNATIONAL": .15},
            {"SP500": .68, "EXTENDED_MARKET": .20, "INTERNATIONAL": .12},
        )
        self.assertEqual(drift["status"], "REBALANCE WATCH")
        self.assertIn("NEW CONTRIBUTIONS FIRST", drift["action"])

    def test_drawdown_alone_cannot_create_accumulation(self):
        falling = frame(np.linspace(120, 65, 320))
        frames = {"SPY": falling, "VXF": falling, "VXUS": falling}

        def loader(ticker, years=3):
            return frames[ticker].copy()

        result = build_401k_strategic_module(
            macro_context={"status": "TIGHTENING / HEADWIND"},
            systemic_context={"status": "ELEVATED"},
            history_loader=loader,
            config=DEFAULT_CONFIG,
        )
        self.assertFalse(result["contributionTiltRecommended"])
        self.assertEqual(result["recommendedContributionPct"], {"SP500": 60.0, "EXTENDED_MARKET": 25.0, "INTERNATIONAL": 15.0})
        self.assertTrue(all(asset["confirmationScore"] < 60 for asset in result["assets"]))

    def test_thresholds_require_opportunity_and_confirmation(self):
        self.assertEqual(classify_action(84, 48, "LOW"), "WATCH")
        self.assertEqual(classify_action(82, 67, "LOW"), "ACCUMULATE")
        self.assertEqual(classify_action(93, 74, "LOW"), "RARE_OPPORTUNITY")
        self.assertEqual(classify_action(95, 90, "HIGH"), "CAUTION")

    def test_new_contribution_tilt_does_not_change_existing_holdings(self):
        baseline = {"SP500": .60, "EXTENDED_MARKET": .25, "INTERNATIONAL": .15}
        tilted = contribution_tilt(baseline, "EXTENDED_MARKET", "ACCUMULATE")
        self.assertEqual(tilted, {"SP500": .55, "EXTENDED_MARKET": .30, "INTERNATIONAL": .15})
        self.assertEqual(baseline, {"SP500": .60, "EXTENDED_MARKET": .25, "INTERNATIONAL": .15})

    def test_moderate_and_rare_tilts_are_bounded(self):
        baseline = {"SP500": .60, "EXTENDED_MARKET": .25, "INTERNATIONAL": .15}
        moderate = contribution_tilt(
            baseline, "EXTENDED_MARKET", "ACCUMULATE",
            opportunity=87, confirmation=68,
        )
        rare = contribution_tilt(
            baseline, "EXTENDED_MARKET", "RARE_OPPORTUNITY",
            opportunity=94, confirmation=75,
        )
        self.assertEqual(moderate, {"SP500": .50, "EXTENDED_MARKET": .35, "INTERNATIONAL": .15})
        self.assertEqual(rare, {"SP500": .45, "EXTENDED_MARKET": .40, "INTERNATIONAL": .15})


if __name__ == "__main__":
    unittest.main()
