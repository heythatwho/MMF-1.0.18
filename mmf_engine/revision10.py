from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _r2(value):
    try:
        if value is None or not np.isfinite(float(value)):
            return None
        return round(float(value), 2)
    except Exception:
        return None


def _number(value, default=None):
    try:
        value = float(value)
        return value if np.isfinite(value) else default
    except Exception:
        return default


def _returns(frame: pd.DataFrame, periods: int):
    if frame is None or frame.empty or len(frame) <= periods:
        return None
    start = _number(frame.iloc[-periods - 1].Close)
    end = _number(frame.iloc[-1].Close)
    return (end / start - 1) * 100 if start and end else None


def _aligned_pair(left: pd.DataFrame, right: pd.DataFrame):
    a = left[["Date", "Close"]].rename(columns={"Close": "left"}).copy()
    b = right[["Date", "Close"]].rename(columns={"Close": "right"}).copy()
    a["Date"] = pd.to_datetime(a.Date).dt.tz_localize(None)
    b["Date"] = pd.to_datetime(b.Date).dt.tz_localize(None)
    return a.merge(b, on="Date", how="inner").dropna().sort_values("Date")


def relative_strength_matrix(histories: dict[str, pd.DataFrame]):
    """Compare leadership with level and change kept separate."""
    pair_specs = [
        ("NVDA", "SOXX", "NVDA vs Semiconductor"),
        ("SOXL", "SOXX", "SOXL vs SOXX"),
        ("SOXX", "QQQ", "SOXX vs QQQ"),
        ("NVDA", "QQQ", "NVDA vs QQQ"),
    ]
    rows = []
    for left_name, right_name, label in pair_specs:
        left, right = histories.get(left_name), histories.get(right_name)
        if left is None or right is None or left.empty or right.empty:
            rows.append({"relationship": label, "status": "Unavailable", "change": "Unavailable"})
            continue
        merged = _aligned_pair(left, right)
        if len(merged) < 22:
            rows.append({"relationship": label, "status": "Unavailable", "change": "Unavailable"})
            continue
        ratio = merged.left / merged.right.replace(0, np.nan)
        relative_20d = (ratio.iloc[-1] / ratio.iloc[-21] - 1) * 100
        recent_5d = (ratio.iloc[-1] / ratio.iloc[-6] - 1) * 100
        prior_5d = (ratio.iloc[-6] / ratio.iloc[-11] - 1) * 100
        momentum_change = recent_5d - prior_5d
        latest_1d = (ratio.iloc[-1] / ratio.iloc[-2] - 1) * 100
        prior_1d = (ratio.iloc[-2] / ratio.iloc[-3] - 1) * 100
        previous_relative_20d = (ratio.iloc[-2] / ratio.iloc[-22] - 1) * 100
        previous_recent_5d = (ratio.iloc[-2] / ratio.iloc[-7] - 1) * 100
        previous_prior_5d = (ratio.iloc[-7] / ratio.iloc[-12] - 1) * 100
        previous_momentum_change = previous_recent_5d - previous_prior_5d
        status = "Stronger" if relative_20d > 1.5 else "Weaker" if relative_20d < -1.5 else "Neutral"
        change = "Improving" if momentum_change > 0.5 else "Deteriorating" if momentum_change < -0.5 else "Stable"
        previous_status = "Stronger" if previous_relative_20d > 1.5 else "Weaker" if previous_relative_20d < -1.5 else "Neutral"
        previous_change = "Improving" if previous_momentum_change > 0.5 else "Deteriorating" if previous_momentum_change < -0.5 else "Stable"
        daily_inflection = bool(
            abs(latest_1d) >= 0.35
            and np.sign(latest_1d) != np.sign(prior_1d)
        )
        changed_today = status != previous_status or change != previous_change or daily_inflection
        rows.append({
            "relationship": label,
            "left": left_name,
            "right": right_name,
            "status": status,
            "change": change,
            "relative20dPct": _r2(relative_20d),
            "recent5dPct": _r2(recent_5d),
            "changeVsPrior5dPct": _r2(momentum_change),
            "latest1dPct": _r2(latest_1d),
            "prior1dPct": _r2(prior_1d),
            "previousStatus": previous_status,
            "previousChange": previous_change,
            "statusChangedToday": status != previous_status,
            "momentumChangedToday": change != previous_change,
            "dailyInflection": daily_inflection,
            "changedToday": changed_today,
            "readCN": f"{left_name} 相对 {right_name} 的20日表现为 {status}，最近变化为 {change}；变化方向优先于静态标签。",
        })

    ranking = []
    for symbol in ("QQQ", "NVDA", "SOXX", "SOXL"):
        value = _returns(histories.get(symbol), 20)
        if value is not None:
            ranking.append((symbol, value))
    ranking.sort(key=lambda item: item[1], reverse=True)
    ordering = " > ".join(symbol for symbol, _ in ranking) if ranking else "Unavailable"
    return {
        "asOf": str(pd.to_datetime(next(iter(histories.values())).iloc[-1].Date).date()) if histories else None,
        "rows": rows,
        "ordering20d": ordering,
        "returns20d": {symbol: _r2(value) for symbol, value in ranking},
        "principleCN": "相对强弱的变化比静态强弱更重要；SOXL含3倍杠杆，和SOXX比较时主要看方向与拐点，不把幅度直接等同为基本面领导力。",
    }


def _tiles(heat: dict[str, Any]):
    return {
        item.get("ticker"): _number(item.get("changePct"))
        for group in (heat or {}).get("groups", [])
        for item in group.get("items", [])
    }


def _group_map(heat: dict[str, Any]):
    return {group.get("nameCN"): _number(group.get("avgChangePct")) for group in (heat or {}).get("groups", [])}


def capital_rotation_layer(heat: dict[str, Any], relative: dict[str, Any]):
    groups = _group_map(heat)
    tiles = _tiles(heat)
    equity_groups = {name: value for name, value in groups.items() if name not in {"宏观 / 避险"} and value is not None}
    broad_values = [tiles.get(key) for key in ("SPY", "QQQ", "IWM") if tiles.get(key) is not None]
    broad = float(np.mean(broad_values)) if broad_values else None
    semis = groups.get("半导体链")
    breadth_negative = (
        sum(1 for value in equity_groups.values() if value < -0.35) / max(1, len(equity_groups))
    )
    destinations = [
        {"name": name, "changePct": _r2(value)}
        for name, value in sorted(equity_groups.items(), key=lambda item: item[1], reverse=True)
        if value > 0.15 and name != "半导体链"
    ][:5]
    safe_havens = []
    for symbol, name in (("TLT", "Bonds"), ("GLD", "Gold"), ("UUP", "USD")):
        if tiles.get(symbol) is not None and tiles[symbol] > 0.25:
            safe_havens.append({"name": name, "ticker": symbol, "changePct": _r2(tiles[symbol])})

    soxx_qqq = next((row for row in relative.get("rows", []) if row.get("relationship") == "SOXX vs QQQ"), {})
    leaving_equities = bool(broad is not None and broad < -0.75 and breadth_negative >= 0.6)
    leaving_semis = bool(
        (semis is not None and broad is not None and semis < broad - 0.75)
        or soxx_qqq.get("change") == "Deteriorating"
    )
    if leaving_equities and safe_havens and breadth_negative >= 0.7:
        classification = "CAPITAL FLIGHT"
        summary = "资金同时离开多数股票板块并流向债券、黄金或美元代理，优先按资本逃离处理。"
    elif leaving_semis and not leaving_equities and destinations:
        classification = "CAPITAL ROTATION"
        summary = "资金主要离开半导体，但没有同步离开整个股票市场，并流向其它板块；这是轮动，不自动等于全面Risk-Off。"
    elif leaving_semis:
        classification = "SEMICONDUCTOR DELEVERAGING"
        summary = "半导体相对走弱，但广泛资本逃离证据不足；先按板块去杠杆/领导力收缩处理。"
    else:
        classification = "MIXED / NO CONFIRMED FLIGHT"
        summary = "尚未看到一致的资本逃离证据；资金更可能在局部腾挪或等待。"
    destination_names = [item["name"] for item in destinations] + [item["name"] for item in safe_havens]
    return {
        "classification": classification,
        "isMoneyLeavingEquities": leaving_equities,
        "isMoneyLeavingSemiconductors": leaving_semis,
        "destinations": destinations,
        "safeHavens": safe_havens,
        "broadEquityChangePct": _r2(broad),
        "negativeBreadthRatio": _r2(breadth_negative),
        "summaryCN": summary,
        "whereMoneyWentCN": "、".join(destination_names) if destination_names else "当前数据没有确认清晰目的地",
    }


def adaptive_market_structure(df: pd.DataFrame, q: dict[str, Any], fib: dict[str, Any]):
    current = _number(q.get("close") or q.get("last") or df.iloc[-1].Close)
    prior = df.iloc[:-1].copy() if len(df) > 1 else df.copy()
    micro_reference = prior.tail(min(8, len(prior)))
    daily = prior.tail(min(20, len(prior)))
    higher = prior.tail(min(120, len(prior)))

    def robust_band(frame):
        if frame.empty:
            return (current, current)
        low_count = min(3, len(frame))
        high_count = min(3, len(frame))
        return float(frame.Low.nsmallest(low_count).median()), float(frame.High.nlargest(high_count).median())

    reference_low, reference_high = robust_band(micro_reference)
    quote_low = _number(q.get("low"))
    quote_high = _number(q.get("high"))
    quote_range_valid = bool(
        quote_low is not None
        and quote_high is not None
        and quote_low > 0
        and quote_high >= quote_low
        and current is not None
        and quote_low <= current <= quote_high
        and (quote_high - quote_low) / current <= 0.30
    )
    if quote_range_valid:
        micro_low, micro_high = quote_low, quote_high
        micro_source = "current_session_range"
    else:
        active_micro = df.tail(min(5, len(df)))
        micro_low, micro_high = robust_band(active_micro)
        micro_source = "recent_5_session_band"
    daily_low, daily_high = robust_band(daily)
    higher_low = float(higher.Low.min()) if not higher.empty else current
    higher_high = float(higher.High.max()) if not higher.empty else current
    last = df.iloc[-1]
    ema20 = _number(last.get("EMA20"), current)
    ema50 = _number(last.get("EMA50"), current)
    ema20_prior = _number(df.iloc[-6].get("EMA20"), ema20) if len(df) >= 6 else ema20
    slope = (ema20 / ema20_prior - 1) if ema20_prior else 0
    width = (micro_high - micro_low) / current if current else 0
    if current > ema20 > ema50 and slope > 0.005:
        regime = "TREND_UP"
        regime_cn = "上升趋势"
    elif current < ema20 < ema50 and slope < -0.005:
        regime = "TREND_DOWN"
        regime_cn = "下降趋势"
    elif width <= 0.18 and abs(slope) <= 0.015:
        regime = "RANGE"
        regime_cn = "震荡区间"
    else:
        regime = "TRANSITION"
        regime_cn = "过渡状态"

    position = "inside"
    if current > reference_high * 1.01:
        position = "provisional_breakout"
    elif current < reference_low * 0.99:
        position = "provisional_breakdown"
    previous_close = _number(prior.iloc[-1].Close) if not prior.empty else current
    prior_position = "inside"
    if previous_close > reference_high * 1.01:
        prior_position = "provisional_breakout"
    elif previous_close < reference_low * 0.99:
        prior_position = "provisional_breakdown"
    boundary_changed_today = position != "inside" and position != prior_position
    nearest_fib = sorted(
        [cluster for cluster in (fib or {}).get("clusters", []) if _number(cluster.get("mid")) is not None],
        key=lambda cluster: abs(_number(cluster.get("mid")) - current),
    )[:3]
    return {
        "regime": regime,
        "regimeCN": regime_cn,
        "micro": {
            "low": _r2(micro_low),
            "high": _r2(micro_high),
            "position": position,
            "source": micro_source,
            "lookback": 1 if quote_range_valid else min(5, len(df)),
            "referenceLow": _r2(reference_low),
            "referenceHigh": _r2(reference_high),
            "previousPosition": prior_position,
            "boundaryChangedToday": boundary_changed_today,
        },
        "daily": {"low": _r2(daily_low), "high": _r2(daily_high), "ema20": _r2(ema20), "ema50": _r2(ema50), "lookback": len(daily)},
        "higherOrder": {"low": _r2(higher_low), "high": _r2(higher_high), "fibonacciGates": nearest_fib, "lookback": len(higher)},
        "levelSignalRuleCN": "价位只是触发复核的坐标，不是买卖信号。突破/跌破必须由量能、SOXX、QQQ、NVDA、相对强弱、广度、VIX与宏观传导共同确认。",
        "timeframeRuleCN": "微观区间优先使用当前有效交易时段的真实高低区间；微观突破不自动等于高阶趋势反转，日线和高阶结构必须分别确认。",
    }


def intraday_auction_structure(intraday: dict[str, Any], q: dict[str, Any], volume: dict[str, Any]):
    if intraday.get("mode") != "real_5m" or not intraday.get("bars"):
        return {
            "available": False,
            "classification": "UNCONFIRMED / NO RELIABLE INTRADAY AUCTION",
            "summaryCN": "当前没有可靠的完整5分钟拍卖数据；不能只用日K推断开盘抛售、午盘承接或尾盘竞价。",
            "volumeInterpretationCN": "日线量能仅说明当日总换手，无法回答量发生在何时、何处以及之后价格如何反应。",
        }
    bars = intraday["bars"]
    opens = np.array([_number(item.get("open"), 0) for item in bars])
    highs = np.array([_number(item.get("high"), 0) for item in bars])
    lows = np.array([_number(item.get("low"), 0) for item in bars])
    closes = np.array([_number(item.get("close"), 0) for item in bars])
    volumes = np.array([_number(item.get("volume"), 0) for item in bars])
    n = len(bars)
    opening_n = min(6, n)
    closing_n = min(6, n)
    opening_change = (closes[opening_n - 1] / opens[0] - 1) * 100 if opens[0] else 0
    session_low_index = int(np.argmin(lows))
    recovery = (closes[-1] / lows[session_low_index] - 1) * 100 if lows[session_low_index] else 0
    closing_change = (closes[-1] / opens[-closing_n] - 1) * 100 if opens[-closing_n] else 0
    total_volume = volumes.sum()
    open_share = volumes[:opening_n].sum() / total_volume if total_volume else None
    close_share = volumes[-closing_n:].sum() / total_volume if total_volume else None
    second_half_new_low = lows[n // 2 :].min() < lows[: max(1, n // 2)].min() * 0.998
    phase_changes = [_number(item.get("changeProxy"), 0) for item in intraday.get("phases", [])]
    negative_phases = sum(1 for value in phase_changes if value < -0.15)

    if opening_change <= -1 and recovery >= 1 and not second_half_new_low:
        classification = "OPENING LIQUIDATION → STABILIZATION"
        summary = "开盘先出现急跌，随后数小时没有继续刷新低点并有一定修复；这与全天连续卖出不同。"
        volume_read = "卖压在低位附近被吸收，但吸收不等于已确认吸筹；还需后续收复、相对强弱和收盘承接。"
    elif negative_phases >= 3 and closes[-1] <= lows.min() * 1.01:
        classification = "CONTINUOUS SELLING"
        summary = "卖压贯穿多数时段并收近低位，日跌幅主要来自持续拍卖失衡。"
        volume_read = "成交量伴随持续走低，暂不使用“吸收”或“机构吸筹”措辞。"
    elif opening_change > 0.7 and closes[-1] < opens[0]:
        classification = "OPENING DRIVE FAILURE"
        summary = "开盘上冲未被市场接受，后续回落抹去早盘优势。"
        volume_read = "重点看上冲时的量是否成为换手流动性，而非把开盘强势直接定义为趋势启动。"
    else:
        classification = "BALANCED / MIXED AUCTION"
        summary = "日内拍卖没有形成单边控制，开盘、午盘和尾盘信号仍然混合。"
        volume_read = "量能需要结合发生位置与后续价格接受度解读，不能只用高量/低量下结论。"
    return {
        "available": True,
        "classification": classification,
        "openingDrivePct": _r2(opening_change),
        "recoveryFromSessionLowPct": _r2(recovery),
        "closingAuctionPct": _r2(closing_change),
        "openingVolumeSharePct": _r2(open_share * 100) if open_share is not None else None,
        "closingVolumeSharePct": _r2(close_share * 100) if close_share is not None else None,
        "sessionLowTime": bars[session_low_index].get("time"),
        "summaryCN": summary,
        "volumeInterpretationCN": volume_read,
        "cautionCN": "Absorption ≠ confirmed accumulation；除非价格接受、领导力和后续量价同时确认，不使用“机构正在吸筹”。",
    }


def systemic_risk_filter(heat: dict[str, Any], relative: dict[str, Any], macro: dict[str, Any]):
    tiles = _tiles(heat)
    groups = _group_map(heat)
    signals = []
    checks = []

    def check(name, active, evidence):
        checks.append({"name": name, "active": bool(active), "evidence": evidence})
        if active:
            signals.append(name)

    vix = _number((macro.get("vix") or {}).get("last"))
    vix_change = _number((macro.get("vix") or {}).get("changePct"))
    equity_group_values = [value for name, value in groups.items() if name != "宏观 / 避险" and value is not None]
    broad_ratio = sum(1 for value in equity_group_values if value < -0.6) / max(1, len(equity_group_values))
    check("Semiconductor breakdown", (tiles.get("SOXX") or 0) <= -1.25 and (tiles.get("NVDA") or 0) <= -1.25, f"SOXX={tiles.get('SOXX')}%, NVDA={tiles.get('NVDA')}%")
    check("QQQ breakdown", (tiles.get("QQQ") or 0) <= -1.0, f"QQQ={tiles.get('QQQ')}%")
    check("SPX breakdown", (tiles.get("SPY") or 0) <= -0.8, f"SPY={tiles.get('SPY')}%")
    check("Breadth deterioration", broad_ratio >= 0.65, f"negative group ratio={_r2(broad_ratio)}")
    check("Volatility expansion", bool(vix is not None and vix >= 22 and (vix_change is None or vix_change > 0)), f"VIX={vix}, change={vix_change}%")
    check("Credit stress", (tiles.get("HYG") or 0) <= -0.5, f"HYG={tiles.get('HYG')}%")
    check("Rates / dollar shock", (tiles.get("TLT") or 0) <= -1.0 or (tiles.get("UUP") or 0) >= 0.7, f"TLT={tiles.get('TLT')}%, UUP={tiles.get('UUP')}%")
    count = len(signals)
    status = "HIGH" if count >= 5 else "ELEVATED" if count >= 3 else "LOW"
    rs_rows = relative.get("rows", [])
    rs_worsening_today = sum(
        bool(row.get("changedToday")) and row.get("change") == "Deteriorating"
        for row in rs_rows
    )
    rs_improving_today = sum(
        bool(row.get("changedToday")) and row.get("change") == "Improving"
        for row in rs_rows
    )
    if count >= 3 or (count >= 1 and rs_worsening_today >= 2):
        direction = "INCREASING"
    elif count == 0 and (vix_change is not None and vix_change <= -3) and rs_improving_today >= 1:
        direction = "DECREASING"
    else:
        direction = "UNCHANGED / INCONCLUSIVE"
    if status == "HIGH":
        conclusion = "多市场风险簇同时确认，系统性风险显著上升。"
    elif status == "ELEVATED":
        conclusion = "出现部分跨市场确认，但尚未形成完整系统性风险簇。"
    else:
        conclusion = "系统性风险缺少跨市场确认；单独的SOXL/SOXX下跌优先按板块风险、轮动或去杠杆解释。"
    return {
        "status": status,
        "direction": direction,
        "signalCount": count,
        "signals": signals,
        "checks": checks,
        "conclusionCN": conclusion,
        "ruleCN": "Large move ≠ structural regime change。系统性风险必须由半导体、QQQ、SPX、广度、VIX、信用与宏观冲击中的多个层面共同确认。",
    }


def semiconductor_leadership_test(relative: dict[str, Any], heat: dict[str, Any]):
    rows = {row.get("relationship"): row for row in relative.get("rows", [])}
    soxx = rows.get("SOXX vs QQQ", {})
    nvda = rows.get("NVDA vs QQQ", {})
    nvda_soxx = rows.get("NVDA vs Semiconductor", {})
    semis_daily = _group_map(heat).get("半导体链")
    improving = sum(row.get("change") == "Improving" for row in (soxx, nvda, nvda_soxx))
    deteriorating = sum(row.get("change") == "Deteriorating" for row in (soxx, nvda, nvda_soxx))
    if improving >= 2 and (semis_daily is None or semis_daily >= 0):
        status = "RECOVERING" if soxx.get("status") == "Weaker" else "EXPANDING"
    elif deteriorating >= 2 or (semis_daily is not None and semis_daily < -1.5):
        status = "WEAKENING"
    else:
        status = "STABLE"
    return {
        "status": status,
        "soxxVsQqq": soxx,
        "nvdaVsQqq": nvda,
        "nvdaVsSoxx": nvda_soxx,
        "confirmationRuleCN": "高置信度趋势恢复最好同时看到 SOXL↑、SOXX↑、SOXX/QQQ相对强弱↑、NVDA/QQQ相对强弱↑，并由市场广度支持；SOXL单独上涨不够。",
    }


def catalyst_and_risk_regime(news: dict[str, Any], structure: dict[str, Any], volume_structure: dict[str, Any], systemic: dict[str, Any], earnings: dict[str, Any] | None = None):
    keywords = {
        "FOMC / Fed": ("fomc", "federal reserve", "fed meeting", "powell", "jackson hole"),
        "Inflation": ("cpi", "pce", "inflation"),
        "Employment": ("payroll", "employment", "jobs report"),
        "Earnings": ("earnings", "guidance", "results"),
        "Geopolitics": ("war", "sanction", "geopolitical", "tariff", "export restriction"),
    }
    headline_text = " ".join(str(item.get("title") or "").lower() for item in (news or {}).get("items", []))
    detected = [name for name, words in keywords.items() if any(word in headline_text for word in words)]
    earnings = earnings or {}
    low_conviction = structure.get("regime") in {"RANGE", "TRANSITION"} and (volume_structure or {}).get("score") in {None, 3, 4, 5}
    upcoming_markers = ("ahead of", "awaiting", "before the", "due later", "scheduled", "this week", "later today", "tomorrow")
    headline_upcoming = bool(detected) and any(marker in headline_text for marker in upcoming_markers)
    earnings_upcoming = bool(earnings.get("available") and earnings.get("events"))
    critical_earnings = bool(earnings.get("requiresWaiting"))
    upcoming_event = headline_upcoming or critical_earnings
    waiting = upcoming_event or low_conviction
    status = "WAITING" if waiting else "DIRECTIONAL EVIDENCE AVAILABLE"
    headline_status = "Headline topics: " + ", ".join(detected) if detected else "No catalyst topic detected in connected headlines"
    if earnings.get("available"):
        event_status = f"{earnings.get('summaryCN')} {headline_status}."
    else:
        event_status = f"财报日历未确认。{headline_status}."
    earnings_risk = earnings.get("riskLevel") or "UNCONFIRMED"
    if earnings_risk in {"HIGH", "ELEVATED"}:
        event_risk = earnings_risk
    elif headline_upcoming:
        event_risk = "ELEVATED"
    elif detected:
        event_risk = "HEADLINE ONLY / UNCONFIRMED"
    else:
        event_risk = earnings_risk if earnings.get("available") else "UNCONFIRMED"
    structural_risk = systemic.get("status")
    return {
        "status": status,
        "isWaitingRegime": waiting,
        "hasUpcomingEventCue": upcoming_event,
        "hasUpcomingEarnings": earnings_upcoming,
        "earningsRisk": earnings_risk,
        "earningsCalendarAvailable": bool(earnings.get("available")),
        "nextEarningsEvent": earnings.get("nextEvent"),
        "detectedCatalysts": detected,
        "eventDataStatus": event_status,
        "eventRisk": event_risk,
        "structuralRisk": structural_risk,
        "readCN": "等待期降低方向确信度并提高区间概率；财报日历优先于新闻标题。没有可靠日期时，系统不会虚构即将发生的催化剂。",
        "separationCN": f"事件风险={event_risk}；结构风险={structural_risk}。重大事件可制造大波动，但大波动本身不等于结构性风险。",
    }


def macro_transmission(macro: dict[str, Any], heat: dict[str, Any]):
    tiles = _tiles(heat)
    tlt, dollar = tiles.get("TLT"), tiles.get("UUP")
    if tlt is not None and tlt < -0.75 or dollar is not None and dollar > 0.5:
        pressure = "TIGHTENING / HEADWIND"
        read = "长债走弱或美元走强提高折现率压力，长久期科技与AI/半导体估值承压，SOXX的波动再被SOXL杠杆放大。"
    elif tlt is not None and tlt > 0.75 and (dollar is None or dollar <= 0):
        pressure = "EASING / TAILWIND"
        read = "长债走强且美元未同步施压，折现率环境缓和，对长久期科技与半导体估值形成边际顺风。"
    else:
        pressure = "MIXED / NEUTRAL"
        read = "利率与美元没有形成单向冲击；宏观暂时更多是确认层，而不是独立交易信号。"
    return {
        "status": pressure,
        "chain": ["Rates / Yields", "Valuation discount rate", "Long-duration technology", "AI / Semiconductors", "SOXX", "Leveraged SOXL"],
        "readCN": read,
    }


def structural_change_review(structure: dict[str, Any], relative: dict[str, Any], systemic: dict[str, Any], volume_structure: dict[str, Any]):
    micro = structure.get("micro", {})
    changes = []
    if micro.get("position") == "provisional_breakout" and micro.get("boundaryChangedToday"):
        changes.append("价格暂时越过微观区间上沿；仍需量能、SOXX/QQQ和下一时段接受确认。")
    elif micro.get("position") == "provisional_breakdown" and micro.get("boundaryChangedToday"):
        changes.append("价格暂时跌破微观区间下沿；若不能快速收回，微观结构需要下移重算。")
    improving = [row["relationship"] for row in relative.get("rows", []) if row.get("changedToday") and row.get("change") == "Improving"]
    deteriorating = [row["relationship"] for row in relative.get("rows", []) if row.get("changedToday") and row.get("change") == "Deteriorating"]
    inflections = [row["relationship"] for row in relative.get("rows", []) if row.get("dailyInflection")]
    if len(improving) >= 2:
        changes.append("今日至少两组核心相对强弱关系转向改善。")
    if len(deteriorating) >= 2:
        changes.append("今日至少两组核心相对强弱关系转向恶化。")
    if len(inflections) >= 2 and not improving and not deteriorating:
        changes.append("今日多组相对强弱出现方向拐点，需下一时段确认是否构成结构变化。")
    if systemic.get("status") == "HIGH":
        changes.append("跨市场系统风险簇已形成。")
    material = bool(changes)
    return {
        "materialChange": material,
        "answerCN": " ".join(changes) if material else "No material structural change. / 没有重大结构变化。",
        "newInformationCN": changes,
        "volumeContextCN": (volume_structure or {}).get("readCN"),
    }


def _normalize_probabilities(values: list[float]):
    values = [max(1.0, float(value)) for value in values]
    scale = 100 / sum(values)
    raw = [value * scale for value in values]
    rounded = [int(np.floor(value)) for value in raw]
    for index in sorted(range(len(raw)), key=lambda i: raw[i] - rounded[i], reverse=True)[: 100 - sum(rounded)]:
        rounded[index] += 1
    return rounded


def four_scenario_model(structure: dict[str, Any], leadership: dict[str, Any], rotation: dict[str, Any], systemic: dict[str, Any], catalyst: dict[str, Any], volume: dict[str, Any], auction: dict[str, Any] | None = None):
    weights = [40.0, 25.0, 25.0, 10.0]
    regime = structure.get("regime")
    if regime == "RANGE":
        weights[0] += 10; weights[1] -= 4; weights[2] -= 4; weights[3] -= 2
    elif regime == "TREND_UP":
        weights[1] += 10; weights[0] -= 5; weights[2] -= 3; weights[3] -= 2
    elif regime == "TREND_DOWN":
        weights[2] += 9; weights[0] -= 4; weights[1] -= 4; weights[3] -= 1
    if leadership.get("status") == "WEAKENING":
        weights[2] += 7; weights[1] -= 5; weights[0] -= 2
    elif leadership.get("status") in {"RECOVERING", "EXPANDING"}:
        weights[1] += 7; weights[2] -= 4; weights[0] -= 3
    if systemic.get("status") == "HIGH":
        weights[3] += 22; weights[0] -= 8; weights[1] -= 8; weights[2] -= 6
    elif systemic.get("status") == "ELEVATED":
        weights[3] += 8; weights[1] -= 4; weights[0] -= 2; weights[2] -= 2
    if rotation.get("classification") == "CAPITAL ROTATION":
        weights[2] += 4; weights[3] -= 3; weights[0] -= 1
    elif rotation.get("classification") == "CAPITAL FLIGHT":
        weights[3] += 10; weights[1] -= 4; weights[0] -= 3; weights[2] -= 3
    if catalyst.get("isWaitingRegime"):
        weights[0] += 7; weights[1] -= 3; weights[2] -= 3; weights[3] -= 1
    auction = auction or {}
    auction_class = auction.get("classification")
    if auction_class == "OPENING LIQUIDATION → STABILIZATION":
        weights[0] += 4; weights[2] += 2; weights[1] -= 3; weights[3] -= 3
    elif auction_class == "CONTINUOUS SELLING":
        weights[2] += 7; weights[3] += 4; weights[0] -= 5; weights[1] -= 6
    elif auction_class == "OPENING DRIVE FAILURE":
        weights[2] += 5; weights[0] += 1; weights[1] -= 5; weights[3] -= 1
    elif auction_class == "BALANCED / MIXED AUCTION":
        weights[0] += 4; weights[1] -= 2; weights[2] -= 1; weights[3] -= 1
    probabilities = _normalize_probabilities(weights)
    micro = structure.get("micro", {})
    daily = structure.get("daily", {})
    bullish_gates = [value for value in (micro.get("high"), daily.get("ema20")) if value is not None]
    first_bullish_gate = min(bullish_gates) if bullish_gates else "--"
    second_bullish_gate = max(bullish_gates) if bullish_gates else "--"
    scenarios = [
        {
            "name": "Scenario A — Range / Consolidation",
            "nameCN": "情景A — 区间 / 盘整",
            "probability": probabilities[0],
            "whyCN": "价格仍在消化风险，方向证据与领导力尚未形成一致确认。",
            "conditionCN": f"价格继续被接受在微观区间 {micro.get('low')}–{micro.get('high')} 内，量能与相对强弱没有同步突破。",
            "invalidCN": "价格在区间外获得量能、领导力与市场广度的持续接受。",
            "watchCN": "上下沿反复拒绝、成交量集中位置与相对强弱拐点。",
            "responseCN": "保持观察或Market Vacation，不在区间中部追价。",
        },
        {
            "name": "Scenario B — Bullish Breakout / Trend Resumption",
            "nameCN": "情景B — 向上突破 / 趋势恢复",
            "probability": probabilities[1],
            "whyCN": "只有半导体领导力、QQQ与量能共同改善，趋势恢复才具有较高可信度。",
            "conditionCN": f"依次收复并站稳 {first_bullish_gate} 与 {second_bullish_gate} 两道门槛；同时量能、SOXX/QQQ与NVDA/QQQ改善。",
            "invalidCN": "突破后快速跌回区间，或SOXL上涨但SOXX、NVDA与广度不确认。",
            "watchCN": "SOXX、NVDA、QQQ、广度、回踩量能与收盘接受度。",
            "responseCN": "先从Observation转Active，再按仓位上限分批部署。",
        },
        {
            "name": "Scenario C — Orderly Further Decline (Non-systemic)",
            "nameCN": "情景C — 有序延续下探（非系统性）",
            "probability": probabilities[2],
            "whyCN": "半导体可以在大盘稳定时继续去杠杆或消化拥挤，这不必然升级为系统危机。",
            "conditionCN": f"跌破或测试微观下沿 {micro.get('low')}，但QQQ/SPX稳定、VIX受控、其它板块承接资金。",
            "invalidCN": "卖压扩散到多数板块、信用与波动率，形成跨市场风险簇。",
            "watchCN": "资本去向、SOXX/QQQ、VIX、HYG、盘中是否先杀后稳。",
            "responseCN": "重新计算赔率与区间；价位只触发复核，不机械接盘。",
        },
        {
            "name": "Scenario D — Systemic Risk / Disorderly Selloff",
            "nameCN": "情景D — 系统性风险 / 无序抛售",
            "probability": probabilities[3],
            "whyCN": "该路径只有在多个市场层面同步恶化时才提高权重。",
            "conditionCN": "SOXX、NVDA、QQQ、SPX与多数板块同步走弱，VIX与信用压力上升，跌破后无法收回。",
            "invalidCN": "广泛市场保持稳定、资金流入其它板块，或跌破被快速收回。",
            "watchCN": "跨市场风险簇数量、收盘拍卖、信用与宏观冲击。",
            "responseCN": "冻结新增仓位，先保护账户并重新召开庙算。",
        },
    ]
    return {
        "scenarios": scenarios,
        "probabilityTotal": sum(probabilities),
        "auctionInput": auction_class or "UNAVAILABLE",
        "noteCN": "概率综合结构、领导力、资本轮动、系统风险、等待期与盘中拍卖；它们是当前证据权重，不是预测。",
    }


def market_vacation_state_machine(base_vacation: bool, structure: dict[str, Any], leadership: dict[str, Any], systemic: dict[str, Any], catalyst: dict[str, Any], volume: dict[str, Any], execution_blocked: bool = False):
    micro = structure.get("micro", {})
    boundary_event = micro.get("position") in {"provisional_breakout", "provisional_breakdown"}
    rs_change = leadership.get("status") in {"WEAKENING", "RECOVERING", "EXPANDING"}
    volume_confirmed = bool(volume.get("available") and _number(volume.get("ratio"), 0) >= 1.15)
    active = (
        not base_vacation
        and systemic.get("status") == "LOW"
        and structure.get("regime") in {"TREND_UP", "TRANSITION"}
        and leadership.get("status") in {"RECOVERING", "EXPANDING"}
        and volume_confirmed
    )
    if execution_blocked:
        state = "MARKET VACATION"
        reason = "行情陈旧或执行数据不完整，量价确认与新增仓位保持冻结。"
    elif active:
        state = "ACTIVE MANAGEMENT"
        reason = "趋势/过渡结构、半导体领导力、量能和系统风险过滤器形成多层确认。"
    elif boundary_event or rs_change or systemic.get("status") == "ELEVATED":
        state = "OBSERVATION"
        reason = "重要边界、相对强弱或跨市场风险正在变化，允许提高观察频率，但尚未获得完整执行许可。"
    else:
        state = "MARKET VACATION"
        reason = "市场仍处于区间/等待或证据不完整状态，赔率与确认不足以支持主动管理。"
    if catalyst.get("isWaitingRegime") and state == "ACTIVE MANAGEMENT":
        state = "OBSERVATION"
        reason = "等待期降低突破可信度；即使出现方向信号，也先等待量能与相对强弱延续。"
    return {
        "state": state,
        "reasonCN": reason,
        "transitions": [
            {"from": "MARKET VACATION", "to": "OBSERVATION", "whenCN": "重要边界被接近/触发，或相对强弱开始明显改善/恶化。"},
            {"from": "OBSERVATION", "to": "ACTIVE MANAGEMENT", "whenCN": "价格、量能、领导力、广度与风险闸门多层确认。"},
            {"from": "ACTIVE MANAGEMENT", "to": "OBSERVATION / MARKET VACATION", "whenCN": "突破失败、系统风险升高或结构作废。"},
        ],
    }


def final_daily_output(rotation, relative, leadership, structure, auction, systemic, scenarios, structural_change, vacation_state, volume, catalyst, earnings=None):
    earnings = earnings or {}
    scenario_rows = scenarios.get("scenarios", [])
    invalidation = "；".join(row.get("invalidCN", "") for row in scenario_rows[:2])
    answers = [
        {"question": "1. What happened?", "answerCN": auction.get("summaryCN")},
        {"question": "2. Where did money go?", "answerCN": rotation.get("whereMoneyWentCN")},
        {"question": "3. Market-wide or sector-specific?", "answerCN": rotation.get("summaryCN")},
        {"question": "4. Semiconductor relative strength?", "answerCN": f"领导力={leadership.get('status')}；SOXX vs QQQ={leadership.get('soxxVsQqq', {}).get('status')} / {leadership.get('soxxVsQqq', {}).get('change')}。"},
        {"question": "5. NVDA relative strength?", "answerCN": f"NVDA vs QQQ={leadership.get('nvdaVsQqq', {}).get('status')} / {leadership.get('nvdaVsQqq', {}).get('change')}。"},
        {"question": "6. What regime?", "answerCN": f"{structure.get('regime')} / {structure.get('regimeCN')}；{catalyst.get('status')}。财报风险={earnings.get('riskLevel', 'UNCONFIRMED')}；{earnings.get('summaryCN') or earnings.get('reasonCN') or '日期未确认'}"},
        {"question": "7. Did volume confirm?", "answerCN": auction.get("volumeInterpretationCN") or volume.get("headlineCN")},
        {"question": "8. Did systemic risk change?", "answerCN": f"{systemic.get('direction')}；当前等级 {systemic.get('status')}：{systemic.get('conclusionCN')}"},
        {"question": "9. Four next scenarios?", "answerCN": "；".join(f"{row.get('nameCN')} {row.get('probability')}%" for row in scenario_rows)},
        {"question": "10. What invalidates the base case?", "answerCN": invalidation},
        {"question": "11. Structural change today?", "answerCN": structural_change.get("answerCN")},
        {"question": "12. Vacation / Observation / Active?", "answerCN": f"{vacation_state.get('state')}：{vacation_state.get('reasonCN')}"},
    ]
    return {"answers": answers, "summaryCN": "MMF每日结论必须先说明资金去向与风险范围，再给情景和行动状态；价格本身只触发复核。"}
