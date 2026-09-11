from __future__ import annotations

import copy
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from mmf_engine.data import fetch_daily, round2


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "401k_strategy.json"

DEFAULT_CONFIG = {
    "baseline_allocation": {"SP500": 0.60, "EXTENDED_MARKET": 0.25, "INTERNATIONAL": 0.15},
    "current_allocation": {"SP500": None, "EXTENDED_MARKET": None, "INTERNATIONAL": None},
    "employee_contribution_pct": 9,
    "max_tilt_pct": 0.15,
    "drift_band_pct": 0.05,
    "opportunity_threshold": 75,
    "confirmation_threshold": 60,
    "moderate_opportunity_threshold": 85,
    "moderate_confirmation_threshold": 65,
    "rare_opportunity_threshold": 90,
    "rare_confirmation_threshold": 70,
    "tilt_exit_opportunity": 65,
    "tilt_exit_confirmation": 45,
    "assets": {
        "SP500": {
            "ticker": "SPY",
            "nameCN": "标普500",
            "nameEN": "S&P 500",
            "fund": "Vanguard Institutional 500 Index Trust",
            "valuation_score": 50,
            "valuation_label": "NEUTRAL / MANUAL INPUT",
        },
        "EXTENDED_MARKET": {
            "ticker": "VXF",
            "nameCN": "美国扩展市场",
            "nameEN": "U.S. Extended Market",
            "fund": "Vanguard Extended Market Index Trust",
            "valuation_score": 50,
            "valuation_label": "NEUTRAL / MANUAL INPUT",
        },
        "INTERNATIONAL": {
            "ticker": "VXUS",
            "nameCN": "国际股票",
            "nameEN": "International Equity",
            "fund": "Vanguard Total International Stock Index",
            "valuation_score": 50,
            "valuation_label": "NEUTRAL / MANUAL INPUT",
        },
    },
    "rollover_context": {
        "status": "PROCESSING / ARRIVAL DATE UNCONFIRMED",
        "source_plan": "Principal 401(k)",
        "estimated_incoming_amount": 23391.75,
        "permanent_portfolio_value": False,
    },
}


def _clip(value, low=0.0, high=100.0):
    return float(np.clip(float(value), low, high))


def load_401k_config(path: Path | None = None):
    config = copy.deepcopy(DEFAULT_CONFIG)
    source = path or CONFIG_PATH
    if source.exists():
        loaded = json.loads(source.read_text(encoding="utf-8"))
        for key, value in loaded.items():
            if key == "assets":
                for asset, asset_values in value.items():
                    config.setdefault("assets", {}).setdefault(asset, {}).update(asset_values)
            elif isinstance(value, dict) and isinstance(config.get(key), dict):
                config[key].update(value)
            else:
                config[key] = value
    return config


def portfolio_drift(baseline, current, band_pct=0.05):
    rows = []
    known = all(current.get(key) is not None for key in baseline)
    for key, target in baseline.items():
        actual = current.get(key)
        drift = None if actual is None else float(actual) - float(target)
        rows.append({
            "asset": key,
            "baselinePct": round2(float(target) * 100),
            "currentPct": None if actual is None else round2(float(actual) * 100),
            "driftPctPoints": None if drift is None else round2(drift * 100),
            "outsideBand": False if drift is None else abs(drift) > float(band_pct),
        })
    outside = [row for row in rows if row["outsideBand"]]
    if not known:
        status = "CURRENT ALLOCATION NOT AVAILABLE"
        action = "HOLD; ENTER CURRENT BALANCES BEFORE A DRIFT DECISION"
    elif outside:
        status = "REBALANCE WATCH"
        action = "USE NEW CONTRIBUTIONS FIRST; DO NOT AUTO-SELL"
    else:
        status = "NORMAL"
        action = "NO REBALANCE REQUIRED"
    return {"status": status, "action": action, "known": known, "rows": rows}


def classify_action(opportunity, confirmation, systemic_status, config=None):
    cfg = config or DEFAULT_CONFIG
    systemic = str(systemic_status or "LOW").upper()
    if systemic == "HIGH":
        return "CAUTION"
    if opportunity >= cfg["rare_opportunity_threshold"] and confirmation >= cfg["rare_confirmation_threshold"]:
        return "RARE_OPPORTUNITY"
    if opportunity >= cfg["opportunity_threshold"] and confirmation >= cfg["confirmation_threshold"]:
        return "ACCUMULATE"
    if opportunity >= 70:
        return "WATCH"
    return "HOLD"


def contribution_tilt(baseline, best_asset, status, config=None, opportunity=None, confirmation=None):
    cfg = config or DEFAULT_CONFIG
    result = {key: float(value) for key, value in baseline.items()}
    if status not in {"ACCUMULATE", "RARE_OPPORTUNITY"}:
        return result
    if status == "RARE_OPPORTUNITY":
        shift = 0.15
    elif (
        opportunity is not None
        and confirmation is not None
        and opportunity >= cfg["moderate_opportunity_threshold"]
        and confirmation >= cfg["moderate_confirmation_threshold"]
    ):
        shift = 0.10
    else:
        shift = 0.05
    shift = min(shift, float(cfg.get("max_tilt_pct", 0.15)))
    if best_asset == "SP500":
        donors = ["EXTENDED_MARKET", "INTERNATIONAL"]
    else:
        donors = ["SP500"]
    available = sum(max(0.0, result[key] - max(0.0, baseline[key] - cfg["max_tilt_pct"])) for key in donors)
    shift = min(shift, available, max(0.0, baseline[best_asset] + cfg["max_tilt_pct"] - result[best_asset]))
    result[best_asset] += shift
    remaining = shift
    for donor in donors:
        take = min(remaining, max(0.0, result[donor] - max(0.0, baseline[donor] - cfg["max_tilt_pct"])))
        result[donor] -= take
        remaining -= take
    return {key: round(value, 4) for key, value in result.items()}


def _return_pct(close, sessions):
    if len(close) <= sessions:
        return None
    base = float(close.iloc[-sessions - 1])
    return None if base == 0 else (float(close.iloc[-1]) / base - 1) * 100


def _price_features(frame):
    if frame is None or frame.empty or len(frame) < 30:
        return None
    df = frame.copy().sort_values("Date").reset_index(drop=True)
    close = pd.to_numeric(df["Close"], errors="coerce").dropna()
    if len(close) < 30:
        return None
    last = float(close.iloc[-1])
    high52 = float(close.tail(min(252, len(close))).max())
    high_available = float(close.max())
    ma50 = float(close.tail(min(50, len(close))).mean())
    ma100 = float(close.tail(min(100, len(close))).mean())
    ma200 = float(close.tail(min(200, len(close))).mean())
    ma200_prior = float(close.iloc[:-20].tail(min(200, max(1, len(close) - 20))).mean()) if len(close) > 40 else ma200
    dd52 = (last / high52 - 1) * 100 if high52 else 0
    dd_available = (last / high_available - 1) * 100 if high_available else 0
    distance200 = (last / ma200 - 1) * 100 if ma200 else 0
    slope200 = (ma200 / ma200_prior - 1) * 100 if ma200_prior else 0
    trend_score = 20
    trend_score += 25 if last >= ma200 else max(0, 25 + distance200)
    trend_score += 20 if last >= ma100 else 4
    trend_score += 15 if last >= ma50 else 3
    trend_score += _clip(10 + slope200 * 4, 0, 20)
    ret1m = _return_pct(close, 21)
    ret3m = _return_pct(close, 63)
    ret6m = _return_pct(close, 126)
    ret1y = _return_pct(close, 252)
    breadth_proxy = _clip(50 + (8 if last >= ma50 else -8) + (10 if last >= ma200 else -10) + _clip((ret1m or 0) * 1.2, -12, 12))
    return {
        "last": round2(last),
        "asOf": str(pd.to_datetime(df.iloc[-1]["Date"]).date()),
        "drawdown52WeekPct": round2(dd52),
        "drawdownAvailableHistoryPct": round2(dd_available),
        "distanceFrom200DmaPct": round2(distance200),
        "ma50": round2(ma50),
        "ma100": round2(ma100),
        "ma200": round2(ma200),
        "ma200Slope20dPct": round2(slope200),
        "return1MonthPct": round2(ret1m),
        "return3MonthPct": round2(ret3m),
        "return6MonthPct": round2(ret6m),
        "return1YearPct": round2(ret1y),
        "trendScore": round2(_clip(trend_score)),
        "breadthProxyScore": round2(breadth_proxy),
        "trendLabel": "STABILIZING / POSITIVE" if trend_score >= 60 else "WEAK / UNCONFIRMED",
        "breadthLabel": "IMPROVING" if breadth_proxy >= 60 else "MIXED" if breadth_proxy >= 45 else "WEAK",
    }


def _relative_features(asset_frame, benchmark_frame):
    if asset_frame is None or benchmark_frame is None or asset_frame.empty or benchmark_frame.empty:
        return {"score": 50, "label": "UNAVAILABLE", "oneMonthPct": None, "threeMonthPct": None, "sixMonthPct": None, "oneYearPct": None}
    left = asset_frame[["Date", "Close"]].rename(columns={"Close": "asset"})
    right = benchmark_frame[["Date", "Close"]].rename(columns={"Close": "benchmark"})
    merged = left.merge(right, on="Date", how="inner").sort_values("Date")
    ratio = pd.to_numeric(merged["asset"], errors="coerce") / pd.to_numeric(merged["benchmark"], errors="coerce")
    ratio = ratio.replace([np.inf, -np.inf], np.nan).dropna()
    periods = {"oneMonthPct": 21, "threeMonthPct": 63, "sixMonthPct": 126, "oneYearPct": 252}
    values = {name: round2(_return_pct(ratio, days)) for name, days in periods.items()}
    score = _clip(50 + (values["oneMonthPct"] or 0) * 3 + (values["threeMonthPct"] or 0) * 1.3)
    label = "IMPROVING" if score >= 58 else "WEAK" if score < 43 else "STABLE / MIXED"
    return {"score": round2(score), "label": label, **values}


def _market_regime(macro_context, systemic_status, sp500_features):
    systemic = str(systemic_status or "LOW").upper()
    if systemic == "HIGH":
        return "SYSTEMIC_STRESS"
    macro_status = str((macro_context or {}).get("status") or "").upper()
    below200 = bool(sp500_features and (sp500_features.get("distanceFrom200DmaPct") or 0) < 0)
    ret3m = (sp500_features or {}).get("return3MonthPct") or 0
    if "TIGHTENING" in macro_status and below200 and ret3m < -8:
        return "STRONG_RISK_OFF"
    if "TIGHTENING" in macro_status or (below200 and ret3m < 0):
        return "MILD_RISK_OFF"
    if below200 and ret3m >= 0:
        return "RECOVERY"
    if ret3m > 10:
        return "STRONG_RISK_ON"
    if ret3m > 3:
        return "MILD_RISK_ON"
    return "NORMAL"


def _macro_score(regime):
    return {
        "NORMAL": 58,
        "MILD_RISK_ON": 60,
        "STRONG_RISK_ON": 52,
        "MILD_RISK_OFF": 52,
        "STRONG_RISK_OFF": 38,
        "SYSTEMIC_STRESS": 15,
        "RECOVERY": 72,
    }.get(regime, 50)


def _systemic_score(status):
    return {"LOW": 78, "ELEVATED": 48, "HIGH": 12}.get(str(status or "LOW").upper(), 55)


def _asset_result(key, asset_config, features, relative, regime, systemic_status, config):
    if not features:
        return {
            "key": key, "ticker": asset_config["ticker"], "nameCN": asset_config["nameCN"], "nameEN": asset_config["nameEN"],
            "fund": asset_config["fund"], "available": False, "opportunityScore": 50, "confirmationScore": 0,
            "baselineWeightPct": round2(config["baseline_allocation"][key] * 100),
            "currentWeightPct": None if config["current_allocation"].get(key) is None else round2(config["current_allocation"][key] * 100),
            "status": "HOLD", "reasonCN": "长期价格数据不足，维持基线，不依据缺失数据调整退休资产。",
            "reasonEN": "Long-horizon price data is insufficient. Hold baseline and do not change retirement allocation on missing evidence.",
        }
    valuation_score = _clip(asset_config.get("valuation_score", 50))
    dd52 = abs(min(0.0, float(features.get("drawdown52WeekPct") or 0)))
    distance200 = abs(min(0.0, float(features.get("distanceFrom200DmaPct") or 0)))
    drawdown_score = _clip(35 + dd52 * 2 + distance200 * 0.35, 20, 95)
    macro_score = _macro_score(regime)
    trend_score = float(features["trendScore"])
    breadth_score = float(features["breadthProxyScore"])
    systemic_score = _systemic_score(systemic_status)
    relative_score = float(relative.get("score") or 50)
    relative_trend_score = _clip(0.65 * trend_score + 0.35 * relative_score)
    opportunity = _clip(
        0.25 * valuation_score
        + 0.20 * drawdown_score
        + 0.20 * macro_score
        + 0.15 * relative_trend_score
        + 0.10 * breadth_score
        + 0.10 * systemic_score
    )
    confirmation = _clip(
        0.40 * trend_score
        + 0.20 * breadth_score
        + 0.15 * relative_score
        + 0.15 * systemic_score
        + 0.10 * macro_score
    )
    status = classify_action(opportunity, confirmation, systemic_status, config)
    if opportunity >= 70 and confirmation >= 60 and str(systemic_status).upper() != "HIGH":
        discount_type = "HEALTHY DISCOUNT / CONFIRMED"
    elif opportunity >= 70:
        discount_type = "UNCONFIRMED DISCOUNT / FALLING-KNIFE WATCH"
    elif str(systemic_status).upper() == "HIGH" or (features.get("distanceFrom200DmaPct") or 0) < -12:
        discount_type = "STRUCTURAL DETERIORATION RISK"
    else:
        discount_type = "NORMAL"
    why_cn = [
        f"52周回撤 {features['drawdown52WeekPct']}%，回撤分只占机会评分20%。",
        f"估值输入 {round2(valuation_score)}/100（{asset_config.get('valuation_label', 'MANUAL INPUT')}）。",
        f"长期趋势 {round2(trend_score)}/100，广度代理 {round2(breadth_score)}/100。",
        f"相对强弱 {relative.get('label')}，确认分 {round2(confirmation)}/100。",
    ]
    why_en = [
        f"52-week drawdown is {features['drawdown52WeekPct']}%; drawdown contributes only 20% of Opportunity.",
        f"Valuation input is {round2(valuation_score)}/100 ({asset_config.get('valuation_label', 'MANUAL INPUT')}).",
        f"Long-term trend is {round2(trend_score)}/100; breadth proxy is {round2(breadth_score)}/100.",
        f"Relative strength is {relative.get('label')}; Confirmation is {round2(confirmation)}/100.",
    ]
    risks_cn = []
    risks_en = []
    if features.get("distanceFrom200DmaPct", 0) < 0:
        risks_cn.append(f"仍低于200日均线 {abs(features['distanceFrom200DmaPct'])}%；便宜尚未完全转化为稳定。")
        risks_en.append(f"Still {abs(features['distanceFrom200DmaPct'])}% below the 200DMA; cheapness is not yet full stabilization.")
    if confirmation < config["confirmation_threshold"]:
        risks_cn.append("确认分未达到贡献倾斜门槛；不得仅凭下跌加码。")
        risks_en.append("Confirmation is below the contribution-tilt threshold; a decline alone cannot authorize accumulation.")
    if str(systemic_status).upper() in {"ELEVATED", "HIGH"}:
        risks_cn.append(f"系统风险为 {systemic_status}，极端恐慌不能自动解释为机会。")
        risks_en.append(f"Systemic risk is {systemic_status}; extreme fear is not automatically an opportunity.")
    return {
        "key": key,
        "ticker": asset_config["ticker"],
        "nameCN": asset_config["nameCN"],
        "nameEN": asset_config["nameEN"],
        "fund": asset_config["fund"],
        "available": True,
        "baselineWeightPct": round2(config["baseline_allocation"][key] * 100),
        "currentWeightPct": None if config["current_allocation"].get(key) is None else round2(config["current_allocation"][key] * 100),
        "opportunityScore": round2(opportunity),
        "confirmationScore": round2(confirmation),
        "status": status,
        "discountType": discount_type,
        "valuation": {"score": round2(valuation_score), "label": asset_config.get("valuation_label", "MANUAL INPUT"), "source": "config/401k_strategy.json"},
        "drawdown": {name: features.get(name) for name in ["drawdown52WeekPct", "drawdownAvailableHistoryPct", "distanceFrom200DmaPct", "return1MonthPct", "return3MonthPct", "return6MonthPct", "return1YearPct"]},
        "trend": {"score": round2(trend_score), "label": features["trendLabel"], "ma50": features["ma50"], "ma100": features["ma100"], "ma200": features["ma200"], "ma200Slope20dPct": features["ma200Slope20dPct"]},
        "breadth": {"score": round2(breadth_score), "label": features["breadthLabel"], "method": "fund-price participation proxy; not constituent breadth"},
        "relativeStrength": relative,
        "macro": {"regime": regime, "score": macro_score},
        "systemicRisk": {"status": systemic_status, "score": systemic_score},
        "scoreComponents": {
            "valuation": {"score": round2(valuation_score), "weightPct": 25},
            "drawdown": {"score": round2(drawdown_score), "weightPct": 20},
            "macro": {"score": round2(macro_score), "weightPct": 20},
            "relativeTrend": {"score": round2(relative_trend_score), "weightPct": 15},
            "breadth": {"score": round2(breadth_score), "weightPct": 10},
            "systemicRisk": {"score": round2(systemic_score), "weightPct": 10},
        },
        "whyCN": why_cn,
        "whyEN": why_en,
        "risksCN": risks_cn,
        "risksEN": risks_en,
        "asOf": features["asOf"],
    }


def build_401k_strategic_module(
    macro_context=None,
    systemic_context=None,
    as_of=None,
    current_allocation=None,
    history_loader: Callable = fetch_daily,
    config=None,
):
    cfg = copy.deepcopy(config or load_401k_config())
    if current_allocation:
        cfg["current_allocation"].update(current_allocation)
    frames = {}
    failures = {}
    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="mmf-401k") as pool:
        futures = {pool.submit(history_loader, asset["ticker"], 3): key for key, asset in cfg["assets"].items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                frame = future.result()
                if as_of:
                    cutoff = pd.to_datetime(as_of).date()
                    frame = frame[pd.to_datetime(frame["Date"]).dt.date <= cutoff].copy()
                frames[key] = frame
            except Exception as exc:
                failures[key] = f"{type(exc).__name__}: {str(exc)[:160]}"
                frames[key] = pd.DataFrame()
    features = {key: _price_features(frame) for key, frame in frames.items()}
    systemic_status = str((systemic_context or {}).get("status") or "LOW").upper()
    regime = _market_regime(macro_context, systemic_status, features.get("SP500"))
    benchmark = frames.get("SP500")
    assets = []
    for key, asset_cfg in cfg["assets"].items():
        relative = {"score": 50, "label": "BENCHMARK", "oneMonthPct": 0, "threeMonthPct": 0, "sixMonthPct": 0, "oneYearPct": 0} if key == "SP500" else _relative_features(frames.get(key), benchmark)
        assets.append(_asset_result(key, asset_cfg, features.get(key), relative, regime, systemic_status, cfg))
    ranking = sorted(assets, key=lambda item: item.get("opportunityScore") or 0, reverse=True)
    best = ranking[0]
    drift = portfolio_drift(cfg["baseline_allocation"], cfg["current_allocation"], cfg["drift_band_pct"])
    recommended = contribution_tilt(
        cfg["baseline_allocation"],
        best["key"],
        best["status"],
        cfg,
        opportunity=best.get("opportunityScore"),
        confirmation=best.get("confirmationScore"),
    )
    contribution_changed = any(abs(recommended[key] - cfg["baseline_allocation"][key]) > 1e-9 for key in recommended)
    if best["status"] == "RARE_OPPORTUNITY":
        overall_status = "RARE LONG-TERM ACCUMULATION OPPORTUNITY"
        overall_status_cn = "罕见长期积累机会"
    elif best["status"] == "ACCUMULATE":
        overall_status = "ACCUMULATE WITH NEW CONTRIBUTIONS"
        overall_status_cn = "用新缴款逐步积累"
    elif best["status"] == "WATCH":
        overall_status = "WATCH"
        overall_status_cn = "进入长期机会观察"
    elif best["status"] == "CAUTION":
        overall_status = "CAUTION / HOLD BASELINE"
        overall_status_cn = "谨慎并维持基线"
    else:
        overall_status = "HOLD BASELINE"
        overall_status_cn = "维持基线"
    action = "REVIEW CONTRIBUTION TILT" if contribution_changed else "NO 401(k) ACTION REQUIRED"
    watch_trigger = f"{best['nameEN']}: Opportunity ≥ {cfg['opportunity_threshold']} AND Confirmation ≥ {cfg['confirmation_threshold']}"
    daily_cn = f"401(k)：{overall_status_cn}。最佳长期机会为{best['nameCN']}（机会 {best['opportunityScore']} / 确认 {best['confirmationScore']}）。{'新缴款可审查临时倾斜；现有持仓不自动卖出。' if contribution_changed else '维持60/25/15；无需行动。'}"
    daily_en = f"401(k): {overall_status}. Best long-term opportunity is {best['nameEN']} (Opportunity {best['opportunityScore']} / Confirmation {best['confirmationScore']}). {'Review a temporary new-contribution tilt; do not automatically sell existing holdings.' if contribution_changed else 'Keep 60/25/15; no action required.'}"
    alert_level = "RARE OPPORTUNITY" if best["status"] == "RARE_OPPORTUNITY" else "ACCUMULATION ALERT" if best["status"] == "ACCUMULATE" else "OPPORTUNITY WATCH" if best["status"] == "WATCH" else "INFO"
    return {
        "version": "401K_STRATEGIC_V1",
        "separationRuleCN": "401(k)与SOXL只共享市场情报，不共享执行逻辑；盘中与五分钟信号不进入退休账户决策。",
        "separationRuleEN": "401(k) and SOXL share market intelligence, not execution logic. Intraday and five-minute signals never drive retirement allocation.",
        "status": overall_status,
        "action": action,
        "marketRegime": regime,
        "bestOpportunity": {"key": best["key"], "nameCN": best["nameCN"], "nameEN": best["nameEN"], "opportunityScore": best["opportunityScore"], "confirmationScore": best["confirmationScore"], "status": best["status"]},
        "baselineAllocationPct": {key: round2(value * 100) for key, value in cfg["baseline_allocation"].items()},
        "currentAllocationPct": {key: None if value is None else round2(value * 100) for key, value in cfg["current_allocation"].items()},
        "employeeContributionPct": cfg["employee_contribution_pct"],
        "existingHoldingsAction": "HOLD",
        "currentContributionPct": {key: round2(value * 100) for key, value in cfg["baseline_allocation"].items()},
        "recommendedContributionPct": {key: round2(value * 100) for key, value in recommended.items()},
        "contributionTiltRecommended": contribution_changed,
        "contributionTiltPctPoints": round2(
            (recommended[best["key"]] - cfg["baseline_allocation"][best["key"]]) * 100
        ),
        "watchTrigger": watch_trigger,
        "portfolioDrift": drift,
        "assets": assets,
        "ranking": [{"rank": idx + 1, "key": item["key"], "nameCN": item["nameCN"], "nameEN": item["nameEN"], "opportunityScore": item["opportunityScore"], "confirmationScore": item["confirmationScore"], "status": item["status"]} for idx, item in enumerate(ranking)],
        "alerts": [{"level": alert_level, "asset": best["key"], "messageCN": daily_cn, "messageEN": daily_en}],
        "dailySummaryCN": daily_cn,
        "dailySummaryEN": daily_en,
        "monthlyReview": {
            "cadence": "MONTHLY",
            "asOf": as_of,
            "driftStatus": drift["status"],
            "bestOpportunity": best["key"],
            "opportunityScore": best["opportunityScore"],
            "confirmationScore": best["confirmationScore"],
            "recommendation": action,
            "recommendedContributionPct": {key: round2(value * 100) for key, value in recommended.items()},
            "historicalOpportunityPercentile": None,
            "historicalPercentileStatus": "ARCHITECTURE READY / V1 DATA NOT YET SUFFICIENT",
        },
        "rolloverContext": cfg.get("rollover_context"),
        "data": {"frequency": ["DAILY", "WEEKLY", "MONTHLY"], "intradayUsed": False, "failures": failures, "valuationSource": "configurable normalized input", "breadthMethod": "V1 fund-price proxy"},
        "guardrails": [
            "NO AUTOMATIC TRADING",
            "NO AUTOMATIC ALLOCATION CHANGES",
            "NEW CONTRIBUTIONS BEFORE SELLING EXISTING HOLDINGS",
            "DRAWDOWN ALONE IS NOT A BUY SIGNAL",
            "MAX TEMPORARY DEVIATION ±15 PERCENTAGE POINTS",
        ],
    }
