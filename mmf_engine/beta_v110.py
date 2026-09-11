from __future__ import annotations

import copy
import json
from calendar import monthcalendar
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd


BETA_VERSION = "v1.0.18"


PROFILE_REGISTRY = {
    "SOXL": {"type": "LEVERAGED_ETF", "leverage": 3, "sector": "Semiconductors", "sectorCN": "半导体", "benchmark": "SOXX", "marketBenchmark": "QQQ", "peers": ["SOXX", "SMH", "NVDA", "AVGO", "AMD"], "specialists": ["soxl", "leveraged_etf", "semiconductor"]},
    "TQQQ": {"type": "LEVERAGED_ETF", "leverage": 3, "sector": "Large-Cap Growth", "sectorCN": "大型成长", "benchmark": "QQQ", "marketBenchmark": "SPY", "peers": ["QQQ", "XLK", "SPY"], "specialists": ["leveraged_etf", "growth"]},
    "UPRO": {"type": "LEVERAGED_ETF", "leverage": 3, "sector": "Broad U.S. Equity", "sectorCN": "美国大盘", "benchmark": "SPY", "marketBenchmark": "SPY", "peers": ["SPY", "QQQ", "IWM"], "specialists": ["leveraged_etf", "broad_market"]},
    "SPXL": {"type": "LEVERAGED_ETF", "leverage": 3, "sector": "Broad U.S. Equity", "sectorCN": "美国大盘", "benchmark": "SPY", "marketBenchmark": "SPY", "peers": ["SPY", "QQQ", "IWM"], "specialists": ["leveraged_etf", "broad_market"]},
    "NVDA": {"type": "INDIVIDUAL_STOCK", "leverage": 1, "sector": "Semiconductors", "sectorCN": "半导体", "benchmark": "SOXX", "marketBenchmark": "QQQ", "peers": ["AMD", "AVGO", "TSM", "SOXX", "QQQ"], "specialists": ["individual_stock", "semiconductor"]},
    "AAPL": {"type": "INDIVIDUAL_STOCK", "leverage": 1, "sector": "Technology Hardware", "sectorCN": "科技硬件", "benchmark": "XLK", "marketBenchmark": "QQQ", "peers": ["MSFT", "GOOGL", "META", "XLK", "QQQ"], "specialists": ["individual_stock", "technology"]},
    "MSFT": {"type": "INDIVIDUAL_STOCK", "leverage": 1, "sector": "Software / Cloud", "sectorCN": "软件与云计算", "benchmark": "XLK", "marketBenchmark": "QQQ", "peers": ["AAPL", "GOOGL", "AMZN", "XLK", "QQQ"], "specialists": ["individual_stock", "technology"]},
    "SPY": {"type": "BROAD_MARKET_ETF", "leverage": 1, "sector": "Broad U.S. Equity", "sectorCN": "美国大盘", "benchmark": "SPY", "marketBenchmark": "SPY", "peers": ["QQQ", "IWM", "DIA"], "specialists": ["broad_market"]},
    "QQQ": {"type": "BROAD_MARKET_ETF", "leverage": 1, "sector": "Large-Cap Growth", "sectorCN": "大型成长", "benchmark": "QQQ", "marketBenchmark": "SPY", "peers": ["SPY", "XLK", "IWM"], "specialists": ["broad_market", "growth"]},
    "IWM": {"type": "BROAD_MARKET_ETF", "leverage": 1, "sector": "U.S. Small Caps", "sectorCN": "美国小盘", "benchmark": "IWM", "marketBenchmark": "SPY", "peers": ["SPY", "QQQ"], "specialists": ["broad_market", "small_cap"]},
    "SMH": {"type": "SECTOR_ETF", "leverage": 1, "sector": "Semiconductors", "sectorCN": "半导体", "benchmark": "SOXX", "marketBenchmark": "QQQ", "peers": ["SOXX", "NVDA", "AVGO", "TSM"], "specialists": ["sector_etf", "semiconductor"]},
    "SOXX": {"type": "SECTOR_ETF", "leverage": 1, "sector": "Semiconductors", "sectorCN": "半导体", "benchmark": "SOXX", "marketBenchmark": "QQQ", "peers": ["SMH", "NVDA", "AVGO", "AMD"], "specialists": ["sector_etf", "semiconductor"]},
    "XLK": {"type": "SECTOR_ETF", "leverage": 1, "sector": "Technology", "sectorCN": "科技", "benchmark": "XLK", "marketBenchmark": "SPY", "peers": ["QQQ", "AAPL", "MSFT"], "specialists": ["sector_etf", "technology"]},
    "XLE": {"type": "SECTOR_ETF", "leverage": 1, "sector": "Energy", "sectorCN": "能源", "benchmark": "XLE", "marketBenchmark": "SPY", "peers": ["XOM", "CVX", "USO"], "specialists": ["sector_etf", "energy"]},
    "XLF": {"type": "SECTOR_ETF", "leverage": 1, "sector": "Financials", "sectorCN": "金融", "benchmark": "XLF", "marketBenchmark": "SPY", "peers": ["KRE", "KBE", "SPY"], "specialists": ["sector_etf", "financials"]},
}

LEVERAGED = {"SOXL", "TQQQ", "UPRO", "SPXL", "TECL", "FNGU", "SQQQ", "SPXU", "SOXS"}
BROAD = {"SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "VT", "VEA", "VWO"}
SECTOR = {"XLK", "XLE", "XLF", "XLV", "XLY", "XLP", "XLU", "XLI", "XLB", "XLRE", "SMH", "SOXX", "KRE", "XBI", "IBB"}


def _number(value, default=None):
    try:
        value = float(value)
        return value if np.isfinite(value) else default
    except Exception:
        return default


def _r2(value):
    value = _number(value)
    return None if value is None else round(value, 2)


def classify_instrument(ticker: str):
    symbol = str(ticker or "").strip().upper()
    if symbol in PROFILE_REGISTRY:
        profile = copy.deepcopy(PROFILE_REGISTRY[symbol])
        confidence = "HIGH"
    elif symbol in LEVERAGED:
        profile = {"type": "LEVERAGED_ETF", "leverage": 3, "sector": "Unclassified", "sectorCN": "未分类板块", "benchmark": "SPY", "marketBenchmark": "SPY", "peers": ["SPY", "QQQ"], "specialists": ["leveraged_etf"]}
        confidence = "MEDIUM"
    elif symbol in BROAD:
        profile = {"type": "BROAD_MARKET_ETF", "leverage": 1, "sector": "Broad Equity", "sectorCN": "大盘股票", "benchmark": symbol, "marketBenchmark": "SPY", "peers": ["SPY", "QQQ", "IWM"], "specialists": ["broad_market"]}
        confidence = "HIGH"
    elif symbol in SECTOR:
        profile = {"type": "SECTOR_ETF", "leverage": 1, "sector": "Sector Equity", "sectorCN": "行业股票", "benchmark": symbol, "marketBenchmark": "SPY", "peers": ["SPY", "QQQ"], "specialists": ["sector_etf"]}
        confidence = "MEDIUM"
    else:
        profile = {"type": "INDIVIDUAL_STOCK_OR_UNCLASSIFIED", "leverage": 1, "sector": "Unclassified", "sectorCN": "未分类板块", "benchmark": "SPY", "marketBenchmark": "SPY", "peers": ["SPY", "QQQ"], "specialists": ["generic_equity"]}
        confidence = "LOW"
    profile.update({"ticker": symbol, "classificationConfidence": confidence})
    profile["riskLanguageCN"] = (
        f"这是约 {profile['leverage']}× 日度复位杠杆产品；波动损耗与路径依赖必须单独计入。"
        if profile["type"] == "LEVERAGED_ETF"
        else "这是非杠杆标的；仍需按个股或基金自身波动管理风险。"
    )
    profile["riskLanguageEN"] = (
        f"This is an approximately {profile['leverage']}x daily-reset leveraged product; volatility drag and path dependence require explicit treatment."
        if profile["type"] == "LEVERAGED_ETF"
        else "This is not classified as a leveraged product; risk still depends on the instrument's own volatility and structure."
    )
    return profile


def _sector_group(heat, profile):
    role_candidates = {
        "Semiconductors": ["aiSemis"],
        "Technology": ["riskAppetite"],
        "Technology Hardware": ["riskAppetite"],
        "Software / Cloud": ["riskAppetite", "communication"],
        "Large-Cap Growth": ["riskAppetite"],
        "Financials": ["financials"],
        "Energy": ["defense"],
        "Broad U.S. Equity": ["riskAppetite"],
        "U.S. Small Caps": ["riskAppetite"],
    }.get(profile.get("sector"), ["riskAppetite"])
    for group in (heat or {}).get("groups", []):
        if group.get("role") in role_candidates:
            return group
    return {}


def put_call_context(options, price_change=None, structure=None, volume=None):
    pcv = _number((options or {}).get("putCallVolumeRatio"))
    pcoi = _number((options or {}).get("putCallOpenInterestRatio"))
    gex = _number((options or {}).get("netGammaExposureProxy"))
    iv = _number((options or {}).get("averageIVPct"))
    available = bool((options or {}).get("available")) and pcv is not None
    if not available:
        return {
            "available": False,
            "zone": "UNAVAILABLE",
            "summaryCN": "Put/Call 数据不可用；本次不推断期权情绪，也不以缺失数据补足方向结论。",
            "summaryEN": "Put/Call data is unavailable. No options-sentiment or directional conclusion is inferred from missing evidence.",
            "limitationCN": "Put/Call 无法区分 put 是买入还是卖出，也无法区分 call 是买入还是备兑卖出。",
            "limitationEN": "Put/Call cannot distinguish puts bought from puts sold, or calls bought from calls written.",
        }
    if pcv < 1.0:
        zone, zone_cn = "CALL_HEAVY / OPTIMISTIC", "偏乐观 / Call 较多"
    elif pcv < 1.3:
        zone, zone_cn = "NEUTRAL_TO_DEFENSIVE", "中性至防御"
    elif pcv < 1.6:
        zone, zone_cn = "ELEVATED_CAUTION", "谨慎升高"
    else:
        zone, zone_cn = "UNUSUALLY_DEFENSIVE", "异常防御 / 类恐惧"
    position = str(((structure or {}).get("micro") or {}).get("position") or "inside")
    vol_ratio = _number((volume or {}).get("ratio"))
    breaking = position == "provisional_breakdown" or (_number(price_change, 0) < -1.0 and (vol_ratio or 0) >= 1.2)
    holding = position != "provisional_breakdown" and _number(price_change, 0) >= -0.5
    if pcv >= 1.3 and holding:
        interaction_cn = "防御仓位升高但价格仍守住结构，可能形成逆向修复条件；必须等待支撑与量能继续确认。"
        interaction_en = "Defensive positioning is elevated while price holds structure, which may create contrarian repair conditions; support and volume still require confirmation."
    elif pcv >= 1.3 and breaking:
        interaction_cn = "高 Put/Call 与放量破位同向，防御情绪正被价格恶化确认，风险权重应提高。"
        interaction_en = "High Put/Call aligns with a volume-confirmed break, so defensive positioning is being confirmed by price deterioration."
    elif pcv < 1.0 and _number(price_change, 0) > 1.5:
        interaction_cn = "Call 偏重且价格延伸，可能反映拥挤乐观；不能仅凭低 Put/Call 继续追价。"
        interaction_en = "Call-heavy positioning accompanies extended price action, which may reflect crowded optimism; the ratio does not justify chasing."
    else:
        interaction_cn = "期权情绪与价格没有形成强共振；本次只作为背景，不产生单独交易许可。"
        interaction_en = "Options sentiment and price are not strongly aligned; this remains context and does not create standalone permission."
    gamma_cn = "负 Gamma 代理可能放大关键位附近波动。" if gex is not None and gex < 0 else "正 Gamma 代理可能抑制日内波动。" if gex is not None and gex > 0 else "Gamma 方向不可确认。"
    gamma_en = "A negative gamma proxy may amplify moves near key levels." if gex is not None and gex < 0 else "A positive gamma proxy may damp intraday moves." if gex is not None and gex > 0 else "Gamma direction is unconfirmed."
    return {
        "available": True, "putCallVolumeRatio": _r2(pcv), "putCallOpenInterestRatio": _r2(pcoi), "averageIVPct": _r2(iv), "netGammaExposureProxy": _r2(gex),
        "zone": zone, "zoneCN": zone_cn,
        "summaryCN": f"Put/Call Volume={_r2(pcv)}，处于{zone_cn}区。{interaction_cn}{gamma_cn}",
        "summaryEN": f"Put/Call Volume={_r2(pcv)}, in the {zone.replace('_', ' ').lower()} zone. {interaction_en} {gamma_en}",
        "limitationCN": "这是情绪/定位代理，不知道每笔期权是主动买入还是卖出，不能机械映射涨跌。",
        "limitationEN": "This is a sentiment/positioning proxy. It does not reveal whether each option was bought or sold and cannot mechanically predict direction.",
    }


def opex_context(as_of):
    current = pd.to_datetime(as_of).date() if as_of else date.today()
    weeks = monthcalendar(current.year, current.month)
    fridays = [week[4] for week in weeks if week[4]]
    third_friday = date(current.year, current.month, fridays[2])
    delta = (third_friday - current).days
    quarterly = current.month in {3, 6, 9, 12}
    if abs(delta) <= 1:
        level = "HIGH"
    elif -3 <= delta <= 5:
        level = "ELEVATED"
    else:
        level = "NORMAL"
    return {
        "asOf": current.isoformat(), "monthlyExpiration": third_friday.isoformat(), "daysToExpiration": delta,
        "quarterlyWindow": quarterly, "riskLevel": level, "directionalSignal": False,
        "summaryCN": f"本月第三个星期五为 {third_friday.isoformat()}，距离报告日 {delta} 天；{'属于季度到期月。' if quarterly else '不是季度到期月。'}到期可能放大机械对冲流与关键位噪音，但不预测方向。",
        "summaryEN": f"The third Friday is {third_friday.isoformat()}, {delta} days from the report date; {'this is a quarterly expiration month.' if quarterly else 'this is not a quarterly expiration month.'} Expiration may amplify mechanical hedging flows and noise around key levels, but it does not predict direction.",
    }


def geopolitical_context(news, profile):
    titles = " ".join(str(item.get("title") or "") for item in (news or {}).get("items", []))
    lower = titles.lower()
    direct_words = ["taiwan", "tsmc", "export control", "chip ban", "advanced node", "semiconductor equipment", "supply chain"] if "semiconductor" in profile.get("sector", "").lower() else [profile.get("ticker", "").lower(), "sanction", "export control", "supply chain"]
    indirect_words = ["war", "missile", "oil shock", "shipping", "strait", "tariff", "geopolit", "middle east", "ukraine"]
    direct = [word for word in direct_words if word and word in lower]
    indirect = [word for word in indirect_words if word in lower]
    if direct:
        classification, weight = "DIRECT_INSTRUMENT_OR_SECTOR", "HIGH"
        cn = f"新闻标题包含与{profile['sectorCN']}供应链或政策直接相关的线索（{', '.join(direct[:3])}）。这是直接传导候选，但仍需价格、量能和同业反应确认。"
        en = f"Headlines contain possible direct {profile['sector']} supply-chain or policy channels ({', '.join(direct[:3])}). This is a direct-transmission candidate, but price, volume, and peer reaction must confirm it."
    elif indirect:
        classification, weight = "INDIRECT_RISK_AMPLIFIER", "MEDIUM"
        cn = "地缘线索目前主要通过油价、通胀预期、利率和广泛 Risk-Off 传导；除非出现对该标的供应链的直接证据，否则不把它当作首要驱动。"
        en = "The geopolitical signal currently transmits mainly through oil, inflation expectations, yields, and broad risk-off behavior. It is not treated as the primary driver without direct evidence for this instrument's supply chain."
    else:
        classification, weight = "NO_CONFIRMED_GEOPOLITICAL_DRIVER", "LOW"
        cn = "当前新闻样本没有确认地缘事件是主要驱动；该维度保持低权重。"
        en = "The current news sample does not confirm geopolitics as the primary driver; this dimension remains low weight."
    return {"classification": classification, "weight": weight, "directMatches": direct, "indirectMatches": indirect, "summaryCN": cn, "summaryEN": en, "sourceAvailable": bool((news or {}).get("available"))}


def macro_chain(macro, transmission, profile):
    items = {item.get("ticker"): item for item in (macro or {}).get("items", [])}
    tlt = _number((items.get("TLT") or {}).get("changePct"))
    dollar = _number((items.get("UUP") or {}).get("changePct"))
    oil = _number((items.get("USO") or {}).get("changePct"))
    vix = _number(((macro or {}).get("vix") or {}).get("last"))
    rate_pressure = tlt is not None and tlt < -0.35
    dollar_pressure = dollar is not None and dollar > 0.35
    risk_pressure = vix is not None and vix >= 22
    pressure_count = sum([rate_pressure, dollar_pressure, risk_pressure])
    state = "TIGHTENING / HEADWIND" if pressure_count >= 2 else "EASING / TAILWIND" if tlt is not None and tlt > 0.5 and not dollar_pressure else "MIXED / NEUTRAL"
    duration_sensitive = profile.get("sector") in {"Semiconductors", "Technology", "Technology Hardware", "Software / Cloud", "Large-Cap Growth"}
    strength = "HIGH" if duration_sensitive else "MEDIUM" if profile.get("type") == "LEVERAGED_ETF" else "LOW_TO_MEDIUM"
    missing = []
    if tlt is None: missing.append("Treasury-yield proxy")
    if dollar is None: missing.append("USD proxy")
    if vix is None: missing.append("VIX")
    missing += ["live Fed-probability distribution", "economic-surprise consensus", "scheduled-release calendar"]
    chain_en = ["Economic data / inflation / growth", "Fed-path expectations", "Treasury yields and discount rate", f"{profile['sector']} valuation and risk appetite", f"{profile['ticker']} price response"]
    chain_cn = ["经济数据 / 通胀 / 增长", "联储路径预期", "国债收益率与折现率", f"{profile['sectorCN']}估值与风险偏好", f"{profile['ticker']}价格反应"]
    if state.startswith("TIGHTENING"):
        interpretation_cn = f"债券、美元与波动代理中有 {pressure_count} 项显示收紧压力。对{profile['sectorCN']}而言，折现率上升会压低远期现金流估值；但本系统没有实时经济预期差，不能把单一数据与价格下跌机械等同。"
        interpretation_en = f"{pressure_count} of the rates, dollar, and volatility proxies show tightening pressure. For {profile['sector']}, a higher discount rate can compress long-duration valuation, but live surprise data is unavailable, so one release cannot be mechanically equated with a price decline."
    elif state.startswith("EASING"):
        interpretation_cn = f"利率代理边际缓和，对{profile['sectorCN']}估值形成顺风；是否已被定价仍需看价格、相对强弱与成交量。"
        interpretation_en = f"The rates proxy is easing at the margin, supporting {profile['sector']} valuation. Whether that support is already priced still depends on price, relative strength, and volume."
    else:
        interpretation_cn = "宏观代理信号混合，不能提供独立方向许可；它只调整确认门槛和仓位容错。"
        interpretation_en = "Macro proxies are mixed and provide no standalone directional permission; they only modify confirmation requirements and position tolerance."
    return {"state": state, "direction": (transmission or {}).get("status") or state, "transmissionStrength": strength, "chainCN": chain_cn, "chainEN": chain_en, "interpretationCN": interpretation_cn, "interpretationEN": interpretation_en, "missingData": missing, "proxyValues": {"TLTChangePct": _r2(tlt), "USDChangePct": _r2(dollar), "OilChangePct": _r2(oil), "VIX": _r2(vix)}}


def trend_rally_quality(df, quote, volume, heat, profile, options_ctx, macro_ctx):
    close = pd.to_numeric(df.get("Close"), errors="coerce").dropna()
    last = _number((quote or {}).get("close") or (quote or {}).get("last"), _number(close.iloc[-1]) if len(close) else None)
    change = _number((quote or {}).get("prevCloseChangePct"), _number((quote or {}).get("changePct"), 0))
    ma20 = _number(df.iloc[-1].get("EMA20")) if df is not None and not df.empty else None
    ma50 = _number(df.iloc[-1].get("EMA50")) if df is not None and not df.empty else None
    ret20 = (last / _number(close.iloc[-21]) - 1) * 100 if len(close) >= 21 and _number(close.iloc[-21]) else None
    vol_ratio = _number((volume or {}).get("ratio")) if (volume or {}).get("available") is not False else None
    group = _sector_group(heat, profile)
    sector_change = _number(group.get("avgChangePct"))
    benchmark_change = _number(next((item.get("changePct") for g in (heat or {}).get("groups", []) for item in g.get("items", []) if item.get("ticker") == profile.get("benchmark")), None))
    relative = None if change is None or benchmark_change is None else change - benchmark_change
    components = {}
    components["priceDirection"] = 75 if change > 1 and last and ma20 and last > ma20 else 62 if change > 0 else 35 if change < -1 else 48
    if vol_ratio is not None:
        components["volumeConfirmation"] = max(10, min(90, 50 + (vol_ratio - 1) * 55 * (1 if change >= 0 else -1)))
    if sector_change is not None:
        components["breadthParticipation"] = max(10, min(90, 50 + sector_change * 10))
        components["sectorConfirmation"] = max(10, min(90, 50 + (sector_change - (change or 0) * 0.25) * 8))
    if relative is not None:
        components["relativeStrength"] = max(10, min(90, 50 + relative * 10))
    if options_ctx.get("available"):
        components["optionsContext"] = 45 if options_ctx.get("zone") in {"ELEVATED_CAUTION", "UNUSUALLY_DEFENSIVE"} and change > 0 else 55
    components["macroContext"] = 35 if macro_ctx.get("state", "").startswith("TIGHTENING") else 65 if macro_ctx.get("state", "").startswith("EASING") else 50
    weights = {"priceDirection": 20, "volumeConfirmation": 20, "breadthParticipation": 15, "sectorConfirmation": 10, "relativeStrength": 15, "optionsContext": 10, "macroContext": 10}
    available_weight = sum(weights[key] for key in components)
    score = sum(components[key] * weights[key] for key in components) / available_weight if available_weight else 50
    direction_up = change >= 0
    if not direction_up and score < 35:
        classification = "DISTRIBUTION / BREAKDOWN"
    elif not direction_up:
        classification = "DECLINE / REPAIR UNCONFIRMED"
    elif score >= 75:
        classification = "STRONG / BROAD-CONFIRMATION ADVANCE"
    elif score >= 62:
        classification = "HEALTHY ADVANCE"
    elif vol_ratio is not None and vol_ratio < 0.9:
        classification = "LOW-CONSENSUS ADVANCE"
    elif sector_change is not None and change > sector_change + 1.5:
        classification = "NARROW / CONCENTRATED ADVANCE"
    elif last and ma20 and last < ma20:
        classification = "TECHNICAL REBOUND"
    else:
        classification = "WEAKENING / UNCONFIRMED ADVANCE"
    flow_en = "may reflect systematic momentum, trend-following participation, short covering, or dealer hedging rather than broad discretionary accumulation" if direction_up and score < 62 else "is consistent with broader participation, although the available data cannot identify a specific institutional flow source" if direction_up else "may reflect de-risking or distribution, but the available data cannot identify the initiating flow"
    flow_cn = "可能包含系统化动量、趋势跟随、空头回补或做市商对冲，而不一定是广泛主动资金积累" if direction_up and score < 62 else "与较广泛参与一致，但现有数据不能确认具体机构资金来源" if direction_up else "可能包含降风险或派发，但现有数据不能确认最初的资金来源"
    missing = [name for name, present in [("volume confirmation", vol_ratio is not None), ("sector breadth", sector_change is not None), ("benchmark relative strength", relative is not None), ("options positioning", options_ctx.get("available"))] if not present]
    return {"score": _r2(score), "classification": classification, "components": {key: _r2(value) for key, value in components.items()}, "weights": weights, "priceChangePct": _r2(change), "return20dPct": _r2(ret20), "volumeVsAverage": _r2(vol_ratio), "sectorChangePct": _r2(sector_change), "benchmark": profile.get("benchmark"), "benchmarkChangePct": _r2(benchmark_change), "relativeStrength1dPct": _r2(relative), "possibleFlowCN": flow_cn, "possibleFlowEN": flow_en, "missingData": missing}


def _probabilities(quality, macro_ctx, geo_ctx, opex):
    q = _number(quality.get("score"), 50)
    if q >= 70: values = [34, 38, 20, 8]
    elif q >= 55: values = [42, 27, 23, 8]
    elif q >= 40: values = [37, 18, 34, 11]
    else: values = [27, 12, 43, 18]
    if macro_ctx.get("state", "").startswith("TIGHTENING"):
        values[1] -= 5; values[2] += 3; values[3] += 2
    if geo_ctx.get("weight") == "HIGH":
        values[0] -= 2; values[3] += 2
    if opex.get("riskLevel") in {"HIGH", "ELEVATED"}:
        values[0] -= 2; values[2] += 1; values[3] += 1
    values[-1] += 100 - sum(values)
    return values


def four_paths(structure, quality, macro_ctx, geo_ctx, opex, profile):
    micro = (structure or {}).get("micro") or {}
    daily = (structure or {}).get("daily") or {}
    support = micro.get("referenceLow") or daily.get("low") or micro.get("low")
    resistance = micro.get("referenceHigh") or daily.get("high") or micro.get("high")
    probs = _probabilities(quality, macro_ctx, geo_ctx, opex)
    peers = " / ".join(profile.get("peers", [])[:3])
    definitions = [
        ("Scenario A — Constructive Consolidation", "情景A — 建设性盘整", f"Price holds {support} and builds acceptance below {resistance} without deteriorating breadth.", f"价格守住 {support}，在 {resistance} 下方消化，且参与度没有恶化。", "Use time rather than size; retain existing exposure and wait for acceptance.", "用时间替代加仓；维持已有仓位，等待市场接受。"),
        ("Scenario B — Bullish Continuation", "情景B — 上行延续", f"Price clears {resistance} with volume, sector participation, and {peers} confirmation.", f"价格放量突破 {resistance}，所属板块与 {peers} 同步确认。", "Participate in stages; do not chase the first impulse and preserve the next move.", "分批参与，不追第一段冲动，并保留下一个动作。"),
        ("Scenario C — Failed Breakout / Retracement", "情景C — 突破失败 / 回撤", f"Price loses the active range and tests {support}; volume or relative strength weakens.", f"价格失去当前区间并测试 {support}，同时量能或相对强弱恶化。", "Freeze additions, reassess support behavior, and recycle tactical risk if invalidation is accepted.", "冻结新增，重新判断支撑行为；若失效被市场接受，则回收战术风险。"),
        ("Scenario D — Macro / Risk Breakdown", "情景D — 宏观 / 风险破位", "A macro, geopolitical, liquidity, or volatility shock overwhelms instrument-specific strength.", "宏观、地缘、流动性或波动冲击压过标的自身强弱。", "Reduce risk first, preserve liquidity, and rebuild the model after the shock is repriced.", "先降低风险并保留流动性，等冲击重新定价后再建模。"),
    ]
    out = []
    for idx, (name, cn, trigger, trigger_cn, action, action_cn) in enumerate(definitions):
        out.append({"name": name, "nameCN": cn, "probability": probs[idx], "triggerEN": trigger, "conditionCN": trigger_cn, "expectedBehaviorEN": trigger, "expectedBehaviorCN": trigger_cn, "support": support, "resistance": resistance, "confirmationEN": "Price, volume, participation, and relative strength must agree.", "confirmationCN": "价格、量能、参与度与相对强弱必须共同确认。", "invalidationEN": "The trigger fails or the opposite boundary is accepted.", "invalidCN": "触发条件失败，或价格被市场接受在相反边界之外。", "macroSectorEN": f"Macro={macro_ctx.get('state')}; geopolitical channel={geo_ctx.get('classification')}; OPEX={opex.get('riskLevel')}.", "macroSectorCN": f"宏观={macro_ctx.get('state')}；地缘传导={geo_ctx.get('classification')}；到期风险={opex.get('riskLevel')}。", "positionImplicationEN": action, "responseCN": action_cn})
    return out


def build_narrative(profile, quote, volume, quality, macro_ctx, options_ctx, geo_ctx, opex, scenarios, account=None):
    change = _number((quote or {}).get("prevCloseChangePct"), _number((quote or {}).get("changePct")))
    direction_cn = "上涨" if change is not None and change > 0 else "下跌" if change is not None and change < 0 else "横向"
    direction_en = "advanced" if change is not None and change > 0 else "declined" if change is not None and change < 0 else "was broadly unchanged"
    vr = quality.get("volumeVsAverage")
    volume_cn = "成交量数据缺失，无法确认市场接受度" if vr is None else f"成交量约为近期均值的 {vr} 倍"
    volume_en = "volume data is unavailable, so market acceptance cannot be confirmed" if vr is None else f"volume was approximately {vr}x its recent average"
    qclass = quality.get("classification", "UNCONFIRMED")
    headline_cn = f"{profile['ticker']} 当前属于“{qclass}”：价格{direction_cn}，但方向与行情质量必须分开判断。"
    headline_en = f"{profile['ticker']} is classified as {qclass}: price {direction_en}, but direction and move quality must be evaluated separately."
    change_text = f"{abs(change):.2f}%" if change is not None else "--"
    narrative_cn = f"价格行为：{profile['ticker']} 当日{direction_cn} {change_text}。量能：{volume_cn}。参与度与相对强弱共同形成行情质量 {quality.get('score')}/100；当前资金表现{quality.get('possibleFlowCN')}。宏观传导为 {macro_ctx.get('state')}，Put/Call 只作为定位背景，地缘风险为 {geo_ctx.get('classification')}。因此，不能仅凭红绿或单一指标下单。"
    narrative_en = f"Price action: {profile['ticker']} {direction_en} {change_text}. Volume: {volume_en}. Participation and relative strength produce a move-quality score of {quality.get('score')}/100; the observed behavior {quality.get('possibleFlowEN')}. Macro transmission is {macro_ctx.get('state')}; Put/Call remains positioning context, and geopolitical risk is {geo_ctx.get('classification')}. No single red or green indicator authorizes a trade."
    exposure = _number((account or {}).get("currentPositionPct"), 0)
    if qclass in {"STRONG / BROAD-CONFIRMATION ADVANCE", "HEALTHY ADVANCE"}:
        action_cn = "已有仓位可以继续参与；新增只在回踩守住或突破获得广度与量能确认后分批执行，不追第一段。"
        action_en = "Existing positions may continue to participate. Add only in stages after a defended retest or a volume-and-breadth-confirmed break; do not chase the first impulse."
    elif "DISTRIBUTION" in qclass or "DECLINE" in qclass:
        action_cn = "暂停新增；优先检查失效条件与账户风险，等待卖压减弱、支撑收回和相对强弱修复。"
        action_en = "Freeze additions. Review invalidation and account risk first, then wait for selling pressure to weaken, support to be reclaimed, and relative strength to repair."
    else:
        action_cn = "保留现有参与权与现金选择权；不追价，等待量能、板块参与度和相对强弱补上确认。"
        action_en = "Preserve both existing participation and cash optionality. Do not chase; wait for volume, sector participation, and relative strength to confirm."
    if exposure <= 0:
        action_cn += " 当前空仓时，首笔只能是带作废条件的小型观察仓，不是一次性完成部署。"
        action_en += " If currently flat, the first entry can only be a small observation tranche with explicit invalidation, not full deployment."
    return {"headlineCN": headline_cn, "headlineEN": headline_en, "professionalNarrativeCN": narrative_cn, "professionalNarrativeEN": narrative_en, "actionCN": action_cn, "actionEN": action_en, "reasoningChain": ["PRICE_ACTION", "VOLUME_CONFIRMATION", "BREADTH_PARTICIPATION", "RELATIVE_STRENGTH", "POSSIBLE_FLOW", "MACRO_RISK", "TRADING_IMPLICATION"]}


def _missing_data(profile, quote, volume, options_ctx, macro_ctx, news, earnings=None):
    rows = []
    checks = [
        ("Instrument metadata", profile.get("classificationConfidence") != "LOW", "Ticker classification uses a low-confidence fallback."),
        ("Current quote", _number((quote or {}).get("last") or (quote or {}).get("close")) is not None, "Current price is unavailable."),
        ("Volume confirmation", (volume or {}).get("available") is not False and _number((volume or {}).get("ratio")) is not None, "Reliable volume-vs-average evidence is unavailable."),
        ("Options positioning", options_ctx.get("available"), "Options chain / Put-Call context is unavailable."),
        ("News / geopolitics", bool((news or {}).get("available")), "News sample is unavailable; geopolitical classification has low confidence."),
        ("Earnings calendar", bool((earnings or {}).get("available")), "Earnings dates are unconfirmed; no event timing is inferred."),
    ]
    for name, available, note in checks:
        rows.append({"field": name, "available": bool(available), "note": "Available" if available else note})
    for item in macro_ctx.get("missingData", []):
        rows.append({"field": item, "available": False, "note": "Not connected in Beta; no value is fabricated."})
    return rows


def build_beta_analysis(ticker, df, quote, volume, heat, options, macro, macro_transmission, news, structure, account, earnings=None, data_freshness=None):
    profile = classify_instrument(ticker)
    pc = put_call_context(options, (quote or {}).get("prevCloseChangePct", (quote or {}).get("changePct")), structure, volume)
    mc = macro_chain(macro, macro_transmission, profile)
    geo = geopolitical_context(news, profile)
    as_of = str(pd.to_datetime(df.iloc[-1].Date).date()) if df is not None and not df.empty else (quote or {}).get("latestTradingDay")
    opex = opex_context(as_of)
    quality = trend_rally_quality(df, quote, volume, heat, profile, pc, mc)
    scenarios = four_paths(structure, quality, mc, geo, opex, profile)
    narrative = build_narrative(profile, quote, volume, quality, mc, pc, geo, opex, scenarios, account)
    earnings = earnings or {}
    missing = _missing_data(profile, quote, volume, pc, mc, news, earnings)
    scenario_top = max(scenarios, key=lambda item: item["probability"])
    blocks = [
        {"key": "marketRegime", "titleCN": "当前市场环境", "titleEN": "Current Market Regime", "value": mc["state"], "summaryCN": mc["interpretationCN"], "summaryEN": mc["interpretationEN"]},
        {"key": "tickerState", "titleCN": "标的状态 / 行情质量", "titleEN": "Ticker State / Move Quality", "value": quality["classification"], "score": quality["score"], "summaryCN": narrative["headlineCN"], "summaryEN": narrative["headlineEN"]},
        {"key": "participation", "titleCN": "相对强弱与参与度", "titleEN": "Relative Strength & Participation", "value": f"{profile['benchmark']} / {quality.get('relativeStrength1dPct')}", "summaryCN": f"板块变化 {quality.get('sectorChangePct')}%，相对 {profile['benchmark']} 为 {quality.get('relativeStrength1dPct')}%。{quality.get('possibleFlowCN')}。", "summaryEN": f"Sector change {quality.get('sectorChangePct')}%; relative to {profile['benchmark']}: {quality.get('relativeStrength1dPct')}%. The move {quality.get('possibleFlowEN')}."},
        {"key": "riskContext", "titleCN": "风险 / 情绪 / 期权", "titleEN": "Risk / Sentiment / Options", "value": pc.get("zone"), "summaryCN": f"{pc.get('summaryCN')} 财报风险={earnings.get('riskLevel', 'UNCONFIRMED')}：{earnings.get('summaryCN') or earnings.get('reasonCN') or '日期未确认。'} {opex.get('summaryCN')}", "summaryEN": f"{pc.get('summaryEN')} Earnings risk={earnings.get('riskLevel', 'UNCONFIRMED')}: {earnings.get('summaryEN') or earnings.get('reasonEN') or 'dates unconfirmed.'} {opex.get('summaryEN')}"},
        {"key": "scenario", "titleCN": "最高概率路径与关键位", "titleEN": "Top Scenario & Key Levels", "value": f"{scenario_top['probability']}%", "summaryCN": f"{scenario_top['nameCN']}：{scenario_top['conditionCN']} 作废：{scenario_top['invalidCN']}", "summaryEN": f"{scenario_top['name']}: {scenario_top['triggerEN']} Invalidation: {scenario_top['invalidationEN']}"},
        {"key": "action", "titleCN": "行动与仓位解释", "titleEN": "Action / Position Interpretation", "value": "CONDITIONAL", "summaryCN": narrative["actionCN"], "summaryEN": narrative["actionEN"]},
    ]
    return {"version": BETA_VERSION, "asOf": as_of, "generatedAt": datetime.utcnow().isoformat() + "Z", "profile": profile, "decisionBlocks": blocks, "narrative": narrative, "trendRallyQuality": quality, "putCall": pc, "macroChain": mc, "geopoliticalRisk": geo, "opex": opex, "earnings": earnings, "scenarios": scenarios, "probabilityTotal": sum(item["probability"] for item in scenarios), "missingData": missing, "dataFreshness": data_freshness or {}, "reviewMode": {"allSectionsAvailable": True, "exportFormat": "Markdown / text", "missingDataCount": sum(1 for row in missing if not row["available"]), "principleCN": "主页面回答现在最重要的事；Review Mode 展开为什么。", "principleEN": "The primary layer answers what matters now; Review Mode expands why."}}


def _sanitize_value(value, replacements):
    if isinstance(value, str):
        for old, new in replacements:
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [_sanitize_value(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_value(item, replacements) for key, item in value.items()}
    return value


def apply_ticker_aware_overrides(report):
    beta = report.get("betaV110") or {}
    profile = beta.get("profile") or classify_instrument((report.get("meta") or {}).get("ticker"))
    ticker = profile["ticker"]
    report["meta"]["version"] = BETA_VERSION
    report["meta"]["instrumentProfile"] = profile
    report["executiveSummary"]["headlineCN"] = beta.get("narrative", {}).get("headlineCN")
    report["executiveSummary"]["headlineEN"] = beta.get("narrative", {}).get("headlineEN")
    report["executiveSummary"]["strategyCN"] = beta.get("narrative", {}).get("actionCN")
    report["executiveSummary"]["strategyEN"] = beta.get("narrative", {}).get("actionEN")
    report["scenarioEngine"] = copy.deepcopy(beta.get("scenarios", []))
    report["scenarioModel"] = {"scenarios": copy.deepcopy(beta.get("scenarios", [])), "probabilityTotal": beta.get("probabilityTotal"), "source": BETA_VERSION}
    report["tomorrowChecklist"] = [item.get("conditionCN") for item in beta.get("scenarios", [])] + ["任何单一指标都不能独立产生交易许可。"]
    replay = report.get("dailyReplay") or {}
    replay.update({"marketInterpretationCN": beta.get("narrative", {}).get("professionalNarrativeCN"), "marketInterpretationEN": beta.get("narrative", {}).get("professionalNarrativeEN"), "positioningCN": beta.get("narrative", {}).get("actionCN"), "positioningEN": beta.get("narrative", {}).get("actionEN"), "invalidCN": beta.get("scenarios", [{}, {}, {}])[2].get("invalidCN") if len(beta.get("scenarios", [])) > 2 else "等待失效条件。", "tomorrowCN": "按四路径触发条件观察，不用单一路径证明观点。"})
    report["dailyReplay"] = replay
    if "semiconductor" not in profile.get("sector", "").lower():
        peer_text = " / ".join(profile.get("peers", [])[:3]) or profile.get("benchmark", "SPY")
        replacements = [
            ("NVDA / AVGO / SMH", peer_text), ("NVDA/AVGO/SMH", peer_text), ("NVDA/SMH", peer_text),
            ("SOXL/SOXX", f"{ticker}/{profile.get('benchmark')}"), ("SOXX/QQQ", f"{profile.get('benchmark')}/{profile.get('marketBenchmark')}"),
            ("SOXL", ticker), ("半导体权重股", "所属板块与主要同业"), ("半导体领导力", "板块参与度"),
            ("半导体", profile.get("sectorCN", "所属板块")), ("semiconductor leaders", "sector peers"), ("Semiconductor leadership", "Sector participation"),
            ("leveraged semiconductors", profile.get("sector", "this instrument")), ("semiconductors", profile.get("sector", "the selected sector")),
            ("Semiconductors", profile.get("sector", "Selected sector")),
        ]
        beta_copy = copy.deepcopy(beta)
        report = _sanitize_value(report, replacements)
        report["betaV110"] = beta_copy
        report["semiconductorLeadership"] = {"status": "NOT_APPLICABLE", "reasonCN": f"{ticker} 不使用 SOXL 专用半导体领导力模板；请看 {profile.get('sectorCN')} 与 {profile.get('benchmark')} 的参与度。", "reasonEN": f"{ticker} does not use the SOXL semiconductor-leadership template; use {profile.get('sector')} and {profile.get('benchmark')} participation instead."}
        quality = beta.get("trendRallyQuality") or {}
        relative = quality.get("relativeStrength1dPct")
        report["relativeStrengthMatrix"] = {
            "status": "TICKER_AWARE",
            "benchmark": profile.get("benchmark"),
            "rows": [{
                "relationship": f"{ticker} vs {profile.get('benchmark')}",
                "changePct": relative,
                "interpretationCN": f"{ticker} 相对 {profile.get('benchmark')} 的当日强弱为 {relative if relative is not None else '--'} 个百分点；缺失时不补值。",
                "interpretationEN": f"{ticker}'s one-day relative strength versus {profile.get('benchmark')} is {relative if relative is not None else '--'} percentage points; missing values are not fabricated.",
            }],
        }
    return report


def daily_brief(report, lang="cn"):
    """Concise, ticker-aware daily email that mirrors the Beta decision layer."""
    beta = report.get("betaV110") or {}
    if not beta:
        return ""
    en = str(lang).lower().startswith("en")
    profile = beta.get("profile") or {}
    narrative = beta.get("narrative") or {}
    quality = beta.get("trendRallyQuality") or {}
    retirement = report.get("strategic401k") or {}
    lines = [
        (f"MMF {BETA_VERSION} DAILY DECISION BRIEF | {profile.get('ticker', '--')} | {beta.get('asOf', '--')}" if en else f"【MMF {BETA_VERSION} 每日决策简报】{profile.get('ticker', '--')} | {beta.get('asOf', '--')}"),
        (f"Instrument: {profile.get('type', '--')} · Benchmark: {profile.get('benchmark', '--')} · Classification confidence: {profile.get('classificationConfidence', '--')}" if en else f"标的：{profile.get('type', '--')} · 基准：{profile.get('benchmark', '--')} · 分类置信度：{profile.get('classificationConfidence', '--')}"),
        "",
        ("Bottom line: " if en else "一句话结论：") + str(narrative.get("headlineEN" if en else "headlineCN") or "--"),
        "",
        ("1. Decision Layer" if en else "1. 决策层"),
    ]
    for block in beta.get("decisionBlocks", []):
        lines.append(f"• {block.get('titleEN' if en else 'titleCN')}: {block.get('summaryEN' if en else 'summaryCN') or '--'}")
    lines += [
        "",
        ("2. Professional Interpretation" if en else "2. 专业解读"),
        str(narrative.get("professionalNarrativeEN" if en else "professionalNarrativeCN") or "--"),
        "",
        ("3. Conditional Action" if en else "3. 条件行动"),
        str(narrative.get("actionEN" if en else "actionCN") or "--"),
        "",
        ("4. Four-Path Contingency Map" if en else "4. 四路径应对图"),
    ]
    for item in beta.get("scenarios", []):
        lines.append(
            f"• {item.get('name' if en else 'nameCN')} {item.get('probability')}% | "
            f"{'Trigger' if en else '触发'}: {item.get('triggerEN' if en else 'conditionCN')} | "
            f"{'Action' if en else '应对'}: {item.get('positionImplicationEN' if en else 'responseCN')}"
        )
    lines += [
        "",
        ("5. Evidence and Limits" if en else "5. 证据与限制"),
        f"• Put/Call: {(beta.get('putCall') or {}).get('summaryEN' if en else 'summaryCN', '--')}",
        f"• OPEX: {(beta.get('opex') or {}).get('summaryEN' if en else 'summaryCN', '--')}",
        f"• {'Earnings' if en else '财报'}: {(beta.get('earnings') or {}).get('summaryEN' if en else 'summaryCN') or (beta.get('earnings') or {}).get('reasonEN' if en else 'reasonCN') or '--'}",
        f"• {'Move quality' if en else '行情质量'}: {quality.get('classification')} · {quality.get('score')}/100",
    ]
    unavailable = [row.get("field") for row in beta.get("missingData", []) if not row.get("available")]
    lines.append(("• Missing data: " if en else "• 缺失数据：") + (", ".join(unavailable) if unavailable else ("None disclosed" if en else "无已披露缺失")))
    lines += [
        "",
        ("6. 401(k) Strategic Module (separate mandate)" if en else "6. 401(k) 长期战略（独立任务）"),
        str(retirement.get("dailySummaryEN" if en else "dailySummaryCN") or ("No allocation change is inferred from missing data." if en else "不因缺失数据推导配置改变。")),
        "",
        ("Probabilities are planning weights, not forecasts. No single indicator authorizes a trade." if en else "概率是规划权重，不是预测；任何单一指标都不能产生交易许可。"),
    ]
    return "\n".join(lines)


def review_markdown(report, lang="cn"):
    beta = report.get("betaV110") or {}
    en = str(lang).lower().startswith("en")
    profile = beta.get("profile") or {}
    narrative = beta.get("narrative") or {}
    lines = [
        f"# MMF {BETA_VERSION} {'Review Export' if en else '完整审查导出'}",
        "",
        f"- {'Ticker' if en else '标的'}: {profile.get('ticker', '--')}",
        f"- {'Instrument type' if en else '标的类型'}: {profile.get('type', '--')}",
        f"- {'Benchmark' if en else '基准'}: {profile.get('benchmark', '--')}",
        f"- {'Data date' if en else '数据日期'}: {beta.get('asOf', '--')}",
        f"- {'Version' if en else '版本'}: {BETA_VERSION}",
        "",
        f"## {'Primary interpretation' if en else '首要判断'}",
        narrative.get("professionalNarrativeEN" if en else "professionalNarrativeCN", "--"),
        "",
        f"## {'Action' if en else '行动'}",
        narrative.get("actionEN" if en else "actionCN", "--"),
        "",
        f"## {'Six decision blocks' if en else '六个决策块'}",
    ]
    for block in beta.get("decisionBlocks", []):
        lines += [f"### {block.get('titleEN' if en else 'titleCN')}", str(block.get("summaryEN" if en else "summaryCN") or "--"), ""]
    lines += [f"## {'Four-path contingency map' if en else '四路径应对图'}", ""]
    for item in beta.get("scenarios", []):
        lines += [f"### {item.get('name' if en else 'nameCN')} — {item.get('probability')}%", f"- {'Trigger' if en else '触发'}: {item.get('triggerEN' if en else 'conditionCN')}", f"- {'Confirmation' if en else '确认'}: {item.get('confirmationEN' if en else 'confirmationCN')}", f"- {'Invalidation' if en else '作废'}: {item.get('invalidationEN' if en else 'invalidCN')}", f"- {'Position implication' if en else '仓位含义'}: {item.get('positionImplicationEN' if en else 'responseCN')}", ""]
    earnings = beta.get("earnings") or {}
    lines += [f"## {'Evidence modules' if en else '证据模块'}", "", f"### Put/Call", (beta.get("putCall") or {}).get("summaryEN" if en else "summaryCN", "--"), "", f"### {'Macro causal chain' if en else '宏观因果链'}", " → ".join((beta.get("macroChain") or {}).get("chainEN" if en else "chainCN", [])), (beta.get("macroChain") or {}).get("interpretationEN" if en else "interpretationCN", "--"), "", f"### {'Geopolitical transmission' if en else '地缘风险传导'}", (beta.get("geopoliticalRisk") or {}).get("summaryEN" if en else "summaryCN", "--"), "", "### OPEX", (beta.get("opex") or {}).get("summaryEN" if en else "summaryCN", "--"), "", f"### {'Earnings calendar' if en else '财报日历'}", earnings.get("summaryEN" if en else "summaryCN") or earnings.get("reasonEN" if en else "reasonCN") or "--", earnings.get("actionEN" if en else "actionCN") or "--", "", f"## {'Missing-data disclosure' if en else '缺失数据披露'}", ""]
    for row in beta.get("missingData", []):
        lines.append(f"- [{'x' if row.get('available') else ' '}] {row.get('field')}: {row.get('note')}")
    lines += ["", f"> {'Probabilities are planning weights, not forecasts. No single indicator determines a trade.' if en else '概率是规划权重，不是确定预测；任何单一指标都不能决定交易。'}"]
    return "\n".join(lines)
