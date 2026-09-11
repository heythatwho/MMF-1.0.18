import pandas as pd
import unittest

from mmf_engine.beta_v110 import (
    BETA_VERSION,
    apply_ticker_aware_overrides,
    build_beta_analysis,
    classify_instrument,
    daily_brief,
    opex_context,
    put_call_context,
    review_markdown,
)


def sample_frame():
    dates = pd.date_range("2026-05-01", periods=100, freq="B")
    close = pd.Series([100 + i * 0.25 for i in range(100)])
    return pd.DataFrame({
        "Date": dates,
        "Open": close - 0.2,
        "High": close + 1,
        "Low": close - 1,
        "Close": close,
        "Volume": [1_000_000 + i * 1_000 for i in range(100)],
        "EMA20": close.ewm(span=20, adjust=False).mean(),
        "EMA50": close.ewm(span=50, adjust=False).mean(),
    })


def sample_inputs(ticker):
    benchmark = classify_instrument(ticker)["benchmark"]
    return dict(
        ticker=ticker,
        df=sample_frame(),
        quote={"close": 125.0, "prevCloseChangePct": 1.8},
        volume={"available": True, "ratio": 1.3},
        heat={"groups": [
            {"role": "riskAppetite", "avgChangePct": 0.8, "items": [{"ticker": benchmark, "changePct": 0.7}]},
            {"role": "aiSemis", "avgChangePct": 1.2, "items": [{"ticker": "SOXX", "changePct": 1.0}]},
            {"role": "financials", "avgChangePct": 0.4, "items": [{"ticker": "XLF", "changePct": 0.4}]},
            {"role": "defense", "avgChangePct": 0.2, "items": [{"ticker": "XLE", "changePct": 0.2}]},
        ]},
        options={"available": True, "putCallVolumeRatio": 1.45, "putCallOpenInterestRatio": 1.2, "averageIVPct": 42, "netGammaExposureProxy": -1200},
        macro={"items": [{"ticker": "TLT", "changePct": -0.5}, {"ticker": "UUP", "changePct": 0.5}, {"ticker": "USO", "changePct": 0.2}], "vix": {"last": 19}},
        macro_transmission={"status": "TIGHTENING / HEADWIND"},
        news={"available": True, "items": [{"title": "Markets assess rates and growth"}]},
        structure={"micro": {"referenceLow": 120, "referenceHigh": 130, "position": "inside"}, "daily": {"low": 118, "high": 132}},
        account={"currentPositionPct": 20},
        earnings={"available": True, "riskLevel": "WATCH", "summaryCN": "预计财报仍在观察窗。", "summaryEN": "The expected earnings date remains on watch.", "actionCN": "保留事件风险预算。", "actionEN": "Preserve event-risk capacity."},
        data_freshness={"isStale": False, "noteCN": "current"},
    )


def test_ticker_profiles_load_only_relevant_specialists():
    soxl = classify_instrument("SOXL")
    nvda = classify_instrument("NVDA")
    aapl = classify_instrument("AAPL")
    qqq = classify_instrument("QQQ")
    xle = classify_instrument("XLE")
    assert soxl["type"] == "LEVERAGED_ETF" and "soxl" in soxl["specialists"]
    assert nvda["type"] == "INDIVIDUAL_STOCK" and "soxl" not in nvda["specialists"]
    assert aapl["sector"] == "Technology Hardware" and aapl["benchmark"] == "XLK"
    assert qqq["type"] == "BROAD_MARKET_ETF"
    assert xle["type"] == "SECTOR_ETF" and xle["sector"] == "Energy"


def test_put_call_is_context_not_direction():
    zones = []
    for ratio in (0.8, 1.1, 1.4, 1.8):
        result = put_call_context({"available": True, "putCallVolumeRatio": ratio}, 0, {"micro": {"position": "inside"}}, {"ratio": 1})
        zones.append(result["zone"])
        assert "cannot" in result["limitationEN"]
    assert zones == ["CALL_HEAVY / OPTIMISTIC", "NEUTRAL_TO_DEFENSIVE", "ELEVATED_CAUTION", "UNUSUALLY_DEFENSIVE"]


def test_opex_is_volatility_amplifier_not_direction():
    result = opex_context("2026-09-18")
    assert result["riskLevel"] == "HIGH"
    assert result["quarterlyWindow"] is True
    assert result["directionalSignal"] is False


def test_uat_matrix_has_six_blocks_and_four_paths():
    for ticker in ("SOXL", "NVDA", "AAPL", "QQQ", "XLE"):
        beta = build_beta_analysis(**sample_inputs(ticker))
        assert beta["version"] == BETA_VERSION
        assert len(beta["decisionBlocks"]) == 6
        assert len(beta["scenarios"]) == 4
        assert beta["probabilityTotal"] == 100
        assert "may" in beta["trendRallyQuality"]["possibleFlowEN"] or "cannot identify" in beta["trendRallyQuality"]["possibleFlowEN"]


def test_non_semiconductor_report_does_not_inherit_soxl_template():
    beta = build_beta_analysis(**sample_inputs("AAPL"))
    report = {
        "meta": {"ticker": "AAPL"},
        "executiveSummary": {},
        "dailyReplay": {"whoCausedCN": "NVDA / AVGO / SMH 半导体权重股"},
        "positionEngineering": {"readCN": "SOXL 半导体"},
        "betaV110": beta,
    }
    output = apply_ticker_aware_overrides(report)
    assert output["meta"]["version"] == BETA_VERSION
    assert output["semiconductorLeadership"]["status"] == "NOT_APPLICABLE"
    assert "SOXL" not in str(output["dailyReplay"])
    assert output["relativeStrengthMatrix"]["benchmark"] == "XLK"


def test_review_and_bilingual_email_cover_beta_evidence():
    beta = build_beta_analysis(**sample_inputs("NVDA"))
    report = {"meta": {"ticker": "NVDA"}, "betaV110": beta, "strategic401k": {"dailySummaryCN": "长期组合维持纪律。", "dailySummaryEN": "Keep the long-horizon allocation disciplined."}}
    cn_review = review_markdown(report, "cn")
    en_review = review_markdown(report, "en")
    cn_mail = daily_brief(report, "cn")
    en_mail = daily_brief(report, "en")
    assert "六个决策块" in cn_review and "Four-path" in en_review
    assert "缺失数据" in cn_review and "Missing-data" in en_review
    assert "四路径应对图" in cn_mail and "Four-Path Contingency Map" in en_mail
    assert "SOXL execution" not in en_mail


class BetaV110Tests(unittest.TestCase):
    def test_ticker_profiles(self):
        test_ticker_profiles_load_only_relevant_specialists()

    def test_put_call_context(self):
        test_put_call_is_context_not_direction()

    def test_opex_context(self):
        test_opex_is_volatility_amplifier_not_direction()

    def test_uat_matrix(self):
        test_uat_matrix_has_six_blocks_and_four_paths()

    def test_non_semiconductor_sanitization(self):
        test_non_semiconductor_report_does_not_inherit_soxl_template()

    def test_review_and_email_coverage(self):
        test_review_and_bilingual_email_cover_beta_evidence()
