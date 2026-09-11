import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from mmf_engine import data, engine
from mmf_engine.revision10 import catalyst_and_risk_regime, final_daily_output


class EarningsCalendarTests(unittest.TestCase):
    def setUp(self):
        data._TTL_CACHE.clear()

    def test_shared_calendar_filters_symbols_and_preserves_unknown_session(self):
        response = Mock()
        response.status_code = 200
        response.text = (
            "symbol,name,reportDate,fiscalDateEnding,estimate,currency\n"
            "NVDA,NVIDIA,2026-08-26,2026-07-31,1.23,USD\n"
            "AVGO,Broadcom,2026-09-03,2026-07-31,1.50,USD\n"
            "IBM,IBM,2026-10-20,2026-09-30,2.10,USD\n"
        )
        with patch.object(data, "ALPHA_VANTAGE_API_KEY", "test"), patch.object(data.requests, "get", return_value=response) as request:
            result = data.fetch_earnings_calendar(["NVDA", "AVGO"])
        self.assertTrue(result["available"])
        self.assertEqual([x["symbol"] for x in result["events"]], ["NVDA", "AVGO"])
        self.assertTrue(all(x["reportSession"] == "TIME_NOT_PROVIDED" for x in result["events"]))
        self.assertEqual(request.call_count, 1)
        self.assertNotIn("apikey", str(result))

    def test_near_term_weighted_event_creates_high_risk_window(self):
        report_date = (datetime.now().date() + timedelta(days=2)).isoformat()
        raw = {
            "available": True,
            "source": "Alpha Vantage Earnings Calendar",
            "asOf": datetime.utcnow().isoformat() + "Z",
            "horizon": "3month",
            "events": [{"symbol": "NVDA", "reportDate": report_date, "reportSession": "TIME_NOT_PROVIDED", "estimate": 1.2, "currency": "USD"}],
        }
        with patch.object(engine, "fetch_earnings_calendar", return_value=raw):
            result = engine.earnings_calendar_context("SOXL")
        self.assertEqual(result["riskLevel"], "HIGH")
        self.assertTrue(result["requiresWaiting"])
        self.assertEqual(result["nextEvent"]["trackedWeightPct"], 22.0)

    def test_headline_mention_alone_does_not_become_confirmed_calendar_risk(self):
        result = catalyst_and_risk_regime(
            {"items": [{"title": "Company reports earnings results"}]},
            {"regime": "TREND_DOWN"},
            {"score": 7},
            {"status": "LOW"},
            {"available": False, "riskLevel": "UNCONFIRMED", "events": []},
        )
        self.assertEqual(result["eventRisk"], "HEADLINE ONLY / UNCONFIRMED")
        self.assertFalse(result["isWaitingRegime"])

    def test_daily_regime_answer_includes_earnings_risk(self):
        output = final_daily_output(
            {}, {}, {}, {"regime": "RANGE", "regimeCN": "震荡区间"}, {}, {"direction": "UNCHANGED", "status": "LOW"},
            {"scenarios": []}, {"answerCN": "No material structural change."}, {"state": "OBSERVATION", "reasonCN": "等待"}, {},
            {"status": "WAITING"}, {"riskLevel": "HIGH", "summaryCN": "NVDA两天后披露"},
        )
        self.assertIn("财报风险=HIGH", output["answers"][5]["answerCN"])


if __name__ == "__main__":
    unittest.main()
