from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

from charts.chart_engine import (
    candlestick,
    gauge,
    intraday_candlestick,
    intraday_candlestick_proxy,
    line,
    resample_monthly,
    resample_weekly,
)
from mmf_engine.data import fetch_daily, fetch_earnings_calendar, fetch_external_fear_greed, fetch_intraday_5m, fetch_vix_quote, fetch_yahoo_news, fetch_yahoo_options, fmt_big, merge_live_quote, pct, quote, round2, safe_quote
from mmf_engine.revision10 import (
    adaptive_market_structure,
    capital_rotation_layer,
    catalyst_and_risk_regime,
    final_daily_output,
    four_scenario_model,
    intraday_auction_structure,
    macro_transmission,
    market_vacation_state_machine,
    relative_strength_matrix,
    semiconductor_leadership_test,
    structural_change_review,
    systemic_risk_filter,
)
from mmf_engine.strategic_401k import build_401k_strategic_module
from mmf_engine.beta_v110 import BETA_VERSION, apply_ticker_aware_overrides, build_beta_analysis

VERSION = BETA_VERSION
ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = ROOT / "snapshots"
SNAPSHOT_DIR.mkdir(exist_ok=True)

ETF_HOLDINGS = {
    "SOXL": [("NVDA", 22), ("AVGO", 10), ("AMD", 8), ("QCOM", 7), ("TSM", 6), ("ASML", 5), ("AMAT", 5), ("MU", 4)],
    "TQQQ": [("NVDA", 8), ("MSFT", 8), ("AAPL", 7), ("AMZN", 5), ("META", 5), ("AVGO", 4), ("GOOGL", 4)],
    "QQQ": [("NVDA", 8), ("MSFT", 8), ("AAPL", 7), ("AMZN", 5), ("META", 5), ("AVGO", 4), ("GOOGL", 4)],
    "SMH": [("NVDA", 20), ("TSM", 12), ("AVGO", 8), ("ASML", 6), ("AMD", 5), ("QCOM", 5), ("AMAT", 4), ("MU", 4)],
    "SOXX": [("NVDA", 9), ("AVGO", 8), ("AMD", 7), ("QCOM", 6), ("TSM", 5), ("ASML", 5), ("AMAT", 5), ("MU", 4)],
    "SPY": [("NVDA", 7), ("MSFT", 6), ("AAPL", 6), ("AMZN", 4), ("META", 3), ("AVGO", 3), ("GOOGL", 2)],
}

SECTOR_PROXIES = {
    "Semiconductor": ["SOXX", "SMH"],
    "Growth": ["QQQ", "XLK"],
    "Defensive": ["XLU", "XLP", "XLV"],
    "Broad Market": ["SPY", "IWM"],
}

HEATMAP_GROUPS = [
    {"nameCN": "指数 / 成长", "role": "riskAppetite", "items": [("SPY", "S&P 500", 1.1), ("QQQ", "Nasdaq 100", 1.2), ("XLK", "科技", 1.2), ("IWM", "小盘", 1.0)]},
    {"nameCN": "半导体链", "role": "aiSemis", "items": [("SOXX", "半导体ETF", 1.2), ("SMH", "半导体龙头", 1.2), ("NVDA", "AI龙头", 1.4), ("AMD", "GPU/CPU", 1.1), ("AVGO", "AI网络", 1.1), ("MU", "存储", 0.9), ("AMAT", "设备", 0.9)]},
    {"nameCN": "通信服务", "role": "communication", "items": [("XLC", "通信ETF", 1.1), ("META", "社交平台", 1.0), ("GOOGL", "搜索/云", 1.0)]},
    {"nameCN": "可选消费", "role": "consumerCyclical", "items": [("XLY", "可选消费ETF", 1.1), ("AMZN", "电商/云", 1.0), ("TSLA", "汽车/高Beta", 0.9)]},
    {"nameCN": "新能源", "role": "cleanEnergy", "items": [("ICLN", "全球清洁能源", 1.1), ("TAN", "太阳能", 1.0), ("QCLN", "清洁能源科技", 1.0)]},
    {"nameCN": "电动车 / 电池", "role": "evBattery", "items": [("DRIV", "自动驾驶与电动车", 1.1), ("CARZ", "全球汽车", 0.9), ("LIT", "锂电池", 1.0), ("TSLA", "电动车龙头", 1.0)]},
    {"nameCN": "金融", "role": "financials", "items": [("XLF", "金融ETF", 1.1), ("KRE", "区域银行", 1.0), ("KBE", "银行ETF", 1.0), ("SCHW", "券商/财富管理", 0.8)]},
    {"nameCN": "防御 / 价值", "role": "defense", "items": [("XLP", "消费防御", 1.0), ("XLU", "公用事业", 1.0), ("XLV", "医疗", 1.0), ("XLE", "能源", 0.8)]},
    {"nameCN": "工业 / 原材料", "role": "cyclical", "items": [("XLI", "工业", 1.0), ("XLB", "原材料", 1.0)]},
    {"nameCN": "房地产", "role": "rateSensitive", "items": [("XLRE", "房地产ETF", 1.0)]},
    {"nameCN": "宏观 / 避险", "role": "macro", "items": [("TLT", "长债", 1.0), ("HYG", "高收益信用", 1.0), ("UUP", "美元", 1.0), ("GLD", "黄金", 0.9), ("USO", "原油", 0.8)]},
]

MACRO_PROXIES = [("TLT", "Rates proxy"), ("HYG", "Credit proxy"), ("UUP", "Dollar proxy"), ("GLD", "Gold proxy"), ("USO", "Oil proxy")]


def shared_market_data(ticker):
    started = time.perf_counter()
    symbols = {sym for sym, _ in ETF_HOLDINGS.get(ticker.upper(), [])}
    symbols.update(sym for tickers in SECTOR_PROXIES.values() for sym in tickers)
    symbols.update(sym for group in HEATMAP_GROUPS for sym, _, _ in group["items"])
    symbols.update(sym for sym, _ in MACRO_PROXIES)
    symbols.update({"NVDA", "SOXX", "QQQ", "SOXL", "SPY", "IWM", "HYG"})
    quotes = {}
    failures = {}

    def load_quote(symbol):
        return safe_quote(symbol)

    with ThreadPoolExecutor(max_workers=min(12, max(1, len(symbols) + 1)), thread_name_prefix="mmf-market") as pool:
        quote_futures = {pool.submit(load_quote, symbol): symbol for symbol in sorted(symbols)}
        vix_future = pool.submit(fetch_vix_quote)
        for future in as_completed(quote_futures):
            symbol = quote_futures[future]
            try:
                value = future.result()
                quotes[symbol] = value
                if value.get("last") is None:
                    failures[symbol] = value.get("source") or "no quote"
            except Exception as exc:
                failures[symbol] = str(exc)[:120]
                quotes[symbol] = {"source": f"unavailable: {str(exc)[:80]}", "last": None, "changePct": None, "volume": None}
        try:
            vix = vix_future.result()
        except Exception as exc:
            failures["VIX"] = str(exc)[:120]
            vix = {"ticker": "VIX", "name": "VIX volatility index", "source": "unavailable", "last": None, "changePct": None, "volume": None}
    return {
        "quotes": quotes,
        "vix": vix,
        "meta": {
            "requested": len(symbols) + 1,
            "loaded": sum(1 for value in quotes.values() if value.get("last") is not None) + (1 if vix.get("last") is not None else 0),
            "failed": failures,
            "elapsedMs": round((time.perf_counter() - started) * 1000),
            "mode": "parallel-prefetch-once",
        },
    }


def comparison_histories(ticker, target_df):
    """Reuse the daily-data cache populated by shared quotes, then align all pairs to the report date."""
    cutoff = pd.to_datetime(target_df.iloc[-1].Date).tz_localize(None)
    histories = {}
    failures = {}
    for symbol in ("SOXL", "SOXX", "NVDA", "QQQ"):
        try:
            frame = target_df.copy() if symbol == ticker.upper() else fetch_daily(symbol, years=1)
            frame = frame[pd.to_datetime(frame.Date).dt.tz_localize(None) <= cutoff].copy()
            if len(frame) < 25:
                raise RuntimeError("fewer than 25 aligned daily rows")
            histories[symbol] = frame
        except Exception as exc:
            failures[symbol] = str(exc)[:120]
    return histories, failures


def shared_quote(quotes, ticker):
    return (quotes or {}).get(ticker.upper()) or {"source": "shared quote unavailable", "last": None, "changePct": None, "volume": None}


def clip(x, lo=0, hi=100):
    try:
        return max(lo, min(hi, float(x)))
    except Exception:
        return 50


def snapshot_path(ticker, date):
    return SNAPSHOT_DIR / ticker.upper() / f"{date}.json"


def save_snapshot(report):
    p = snapshot_path(report["meta"]["ticker"], report["meta"]["date"])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(p)


def load_snapshot(ticker, date):
    p = snapshot_path(ticker, date)
    if not p.exists():
        raise FileNotFoundError(str(p))
    return json.loads(p.read_text(encoding="utf-8"))


def trend_label(df):
    last = df.iloc[-1]
    if last.Close > last.EMA20 > last.EMA50:
        return "↑ 修复/偏强"
    if last.Close < last.EMA20 < last.EMA50:
        return "↓ 偏弱/下降"
    return "→ 震荡/未确认"


def candle_read(row):
    rng = row.High - row.Low
    if not rng or rng <= 0:
        return "无明显K线信息。"
    body = row.Close - row.Open
    close_pos = (row.Close - row.Low) / rng
    if body < 0 and close_pos < 0.35:
        return "长阴 / 收近低位：卖盘控制更明显。"
    if body > 0 and close_pos > 0.65:
        return "长阳 / 收近高位：买盘控制更明显。"
    if abs(body) / rng < 0.25:
        return "十字 / 小实体：多空分歧大，方向还没确认。"
    return "普通实体K线：需要结合趋势和量能判断。"


def etf_weights(ticker, quotes=None):
    holdings = ETF_HOLDINGS.get(ticker.upper(), [])
    items = []
    for sym, weight in holdings:
        q = shared_quote(quotes, sym) if quotes is not None else safe_quote(sym)
        ch = q.get("changePct")
        impact = round2((ch or 0) * weight / 100) if isinstance(ch, (int, float)) else None
        items.append({"ticker": sym, "weight": weight, "changePct": ch, "impact": impact})
    ranked = sorted([x for x in items if isinstance(x.get("impact"), (int, float))], key=lambda x: abs(x["impact"]), reverse=True)
    drag = [x for x in ranked if x["impact"] < 0]
    support = [x for x in ranked if x["impact"] > 0]
    if ranked:
        summary = f"今天ETF权重影响最明显的是 {ranked[0]['ticker']}。这是解释当天涨跌的核心线索，而不是一个孤立指标。"
    else:
        summary = "个股模式不显示ETF权重影响。"
    return {
        "isETF": bool(holdings),
        "items": items,
        "topImpact": ranked[:5],
        "mainDrag": drag[0] if drag else None,
        "mainSupport": support[0] if support else None,
        "summaryCN": summary,
    }


def sector_rotation(quotes=None):
    groups = {}
    for name, tickers in SECTOR_PROXIES.items():
        vals = [(shared_quote(quotes, t) if quotes is not None else safe_quote(t)).get("changePct") for t in tickers]
        vals = [x for x in vals if isinstance(x, (int, float))]
        groups[name] = round2(np.mean(vals)) if vals else None
    ranked = sorted([(k, v) for k, v in groups.items() if isinstance(v, (int, float))], key=lambda x: x[1], reverse=True)
    strongest = ranked[0] if ranked else ("未知", None)
    weakest = ranked[-1] if ranked else ("未知", None)
    risk_spread = (groups.get("Growth") or 0) - (groups.get("Defensive") or 0)
    if risk_spread > 1:
        mode = "Risk On / Growth Led"
        flow = f"资金偏向进攻：成长股强于防御板块。当前最强是 {strongest[0]}({strongest[1]}%)，最弱是 {weakest[0]}({weakest[1]}%)。"
    elif risk_spread < -1:
        mode = "Risk Off / Defensive"
        flow = f"资金偏向防御：防御板块强于成长股。当前最强是 {strongest[0]}({strongest[1]}%)，最弱是 {weakest[0]}({weakest[1]}%)。"
    else:
        mode = "Mixed / Selective"
        flow = f"板块没有形成单边Risk-On或Risk-Off，资金更像局部切换。当前最强是 {strongest[0]}({strongest[1]}%)，最弱是 {weakest[0]}({weakest[1]}%)。"
    return {
        "groups": groups,
        "mode": mode,
        "strongest": {"name": strongest[0], "changePct": strongest[1]},
        "weakest": {"name": weakest[0], "changePct": weakest[1]},
        "flowCN": flow,
        "interpretationCN": "板块轮动回答的是钱在进攻、防御，还是只在局部腾挪。",
    }


def sector_heatmap(ticker, quotes=None):
    out_groups = []
    all_tiles = []
    for group in HEATMAP_GROUPS:
        tiles = []
        weighted = []
        for sym, label, weight in group["items"]:
            q = shared_quote(quotes, sym) if quotes is not None else safe_quote(sym)
            ch = q.get("changePct")
            tile = {
                "ticker": sym,
                "label": label,
                "changePct": ch,
                "last": q.get("last"),
                "source": q.get("source"),
                "weight": weight,
            }
            tiles.append(tile)
            all_tiles.append(tile)
            if isinstance(ch, (int, float)):
                weighted.append((ch, weight))
        avg = round2(sum(ch * w for ch, w in weighted) / sum(w for _, w in weighted)) if weighted else None
        out_groups.append({"nameCN": group["nameCN"], "role": group["role"], "avgChangePct": avg, "items": tiles})
    semis = next((g.get("avgChangePct") for g in out_groups if g["role"] == "aiSemis"), None)
    growth = next((g.get("avgChangePct") for g in out_groups if g["role"] == "riskAppetite"), None)
    defense = next((g.get("avgChangePct") for g in out_groups if g["role"] == "defense"), None)
    if isinstance(semis, (int, float)) and isinstance(defense, (int, float)) and semis > defense + 1.2:
        mode = "Sector Rotation / Semis Led"
        summary = f"热力图显示半导体链强于防御板块，资金偏向AI/芯片轮动；这比单一反弹更健康，但仍要看指数和权重股是否扩散。"
    elif isinstance(growth, (int, float)) and isinstance(defense, (int, float)) and growth > defense + 1.2:
        mode = "Broad Risk-On"
        summary = "热力图显示成长/指数强于防御板块，资金偏进攻；如果半导体同步，反弹质量更高。"
    elif isinstance(defense, (int, float)) and isinstance(growth, (int, float)) and defense > growth + 1.0:
        mode = "Risk-Off / Defensive"
        summary = "热力图显示防御板块强于成长/指数，资金偏保守；高beta标的反弹需要降低仓位期待。"
    else:
        mode = "Mixed / Selective"
        summary = "热力图没有形成全面Risk-On，资金更像局部轮动；适合看仓位梯子，不适合直接追满。"
    # A ticker may proxy more than one group (for example TSLA).  The group
    # tiles should keep that context, but the leader/laggard list must not
    # repeat the same ticker and imply two independent sources of strength.
    unique_movers = {}
    for tile in all_tiles:
        if isinstance(tile.get("changePct"), (int, float)) and tile.get("ticker") not in unique_movers:
            unique_movers[tile.get("ticker")] = tile
    movers = list(unique_movers.values())
    leaders = sorted(movers, key=lambda x: x["changePct"], reverse=True)[:4]
    laggards = sorted(movers, key=lambda x: x["changePct"])[:4]
    return {
        "mode": mode,
        "summaryCN": summary,
        "groups": out_groups,
        "leaders": leaders,
        "laggards": laggards,
        "focusTicker": ticker.upper(),
        "noteCN": "这是MMF简化热力图，用少量代理判断板块轮动质量；不是全市场股票列表。",
    }


def dynamic_anchor_range(df, q, fib):
    current = q.get("close") or q.get("last")
    try:
        current = float(current)
    except Exception:
        current = None
    clusters = fib.get("clusters") or []
    rows = fib.get("rows") or []
    supports = []
    resistances = []

    def add_level(bucket, price, label, strength=1):
        try:
            price = float(price)
        except Exception:
            return
        if not np.isfinite(price) or price <= 0:
            return
        bucket.append({"price": round2(price), "label": label, "strength": strength})

    for c in clusters:
        count = c.get("count") or 1
        if current and isinstance(c.get("high"), (int, float)) and c["high"] < current:
            add_level(supports, c.get("mid") or c.get("high"), f"Fib共振支撑 {c.get('low')}-{c.get('high')}", count + 2)
        if current and isinstance(c.get("low"), (int, float)) and c["low"] > current:
            add_level(resistances, c.get("mid") or c.get("low"), f"Fib共振压力 {c.get('low')}-{c.get('high')}", count + 2)
    for r in rows:
        price = r.get("price")
        label = f"{r.get('period')} Fib {r.get('nearestFib')}"
        if current and isinstance(price, (int, float)) and price < current:
            add_level(supports, price, label, 1)
        if current and isinstance(price, (int, float)) and price > current:
            add_level(resistances, price, label, 1)

    range_low = range_high = range_period = None
    range_candidates = []
    prev = df.iloc[:-1] if df is not None and len(df) > 1 else None
    if prev is not None and len(prev) >= 20:
        for period in [20, 60, 120]:
            look = prev.tail(min(len(prev), period))
            hi = float(look.High.max())
            lo = float(look.Low.min())
            if current and hi > lo:
                width_ratio = (hi - lo) / current
                range_candidates.append((period, lo, hi, width_ratio))
            if current:
                if lo < current:
                    add_level(supports, lo, f"{period}D swing low", 2)
                if hi > current:
                    add_level(resistances, hi, f"{period}D swing high", 2)
        usable = [x for x in range_candidates if 0.08 <= x[3] <= 0.5]
        chosen = usable[0] if usable else (min(range_candidates, key=lambda x: abs(x[3] - 0.32)) if range_candidates else None)
        if chosen:
            range_period, range_low, range_high, _ = chosen
    if range_low is None or range_high is None:
        row_candidates = []
        for r in rows:
            try:
                lo, hi = float(r.get("low")), float(r.get("high"))
            except Exception:
                continue
            if current and hi > lo:
                row_candidates.append((r.get("period"), lo, hi, (hi - lo) / current))
        usable_rows = [x for x in row_candidates if 0.08 <= x[3] <= 0.5]
        preferred_tuple = usable_rows[0] if usable_rows else (min(row_candidates, key=lambda x: abs(x[3] - 0.32)) if row_candidates else None)
        preferred = {"period": preferred_tuple[0], "low": preferred_tuple[1], "high": preferred_tuple[2]} if preferred_tuple else None
        if preferred:
            range_low = preferred.get("low")
            range_high = preferred.get("high")
            range_period = preferred.get("period")

    supports = sorted(supports, key=lambda x: abs((current or x["price"]) - x["price"]))
    resistances = sorted(resistances, key=lambda x: abs((current or x["price"]) - x["price"]))
    lower = round2(range_low) if range_low else (supports[0]["price"] if supports else None)
    upper = round2(range_high) if range_high else (resistances[0]["price"] if resistances else None)
    mode = "Range / 震荡箱体"
    basis = f"优先选取宽度合理的近期 swing high/low 生成主震荡箱体（当前采用 {range_period or '动态'}）；Fib共振区用于识别箱体内部的短线支撑、压力和流动性测试区。"
    if current and upper and upper > current * 1.35:
        nearby_resistance = next((x for x in resistances if current < x["price"] <= current * 1.35), None)
        if nearby_resistance:
            upper = nearby_resistance["price"]
            basis += f" 原始高点距离现价过远，当前上沿改用更相关的 {nearby_resistance['label']}。"
        else:
            upper = round2(current * 1.25)
            basis += " 原始高点距离现价过远，当前上沿用现价上方25%的临时压力带替代。"
    if current and lower and lower < current * 0.55:
        nearby_support = next((x for x in supports if current * 0.55 <= x["price"] < current), None)
        if nearby_support:
            lower = nearby_support["price"]
            basis += f" 原始低点距离现价过远，当前下沿改用更相关的 {nearby_support['label']}。"

    if prev is not None and current:
        look = prev.tail(min(len(prev), 60))
        prev_high = float(look.High.max())
        prev_low = float(look.Low.min())
        width = max(prev_high - prev_low, current * 0.08)
        if current > prev_high * 1.015:
            lower = round2(prev_high)
            upper = round2(prev_high + width * 0.618)
            mode = "Breakout Rebase / 突破后上移"
            basis = "当前价有效突破前60日高位，原压力转为新支撑，并用前箱体宽度做上方扩展参考。"
        elif current < prev_low * 0.985:
            upper = round2(prev_low)
            lower = round2(prev_low - width * 0.382)
            mode = "Breakdown Rebase / 跌破后下移"
            basis = "当前价有效跌破前60日低位，原支撑转为压力，并用前箱体宽度做下方扩展参考。"
        elif lower is None:
            lower = round2(prev_low)
        elif upper is None:
            upper = round2(prev_high)

    if current and lower is not None and upper is not None and lower > upper:
        lower, upper = upper, lower
    if current and lower is None and upper is None:
        lower, upper = round2(current * 0.9), round2(current * 1.1)
    elif current and lower is None:
        lower = round2(current - max(upper - current, current * 0.08))
    elif current and upper is None:
        upper = round2(current + max(current - lower, current * 0.08))

    if current and lower is not None and current < lower * 0.985:
        old_lower = lower
        nearby_below = next((x for x in supports if x["price"] < current), None)
        lower = nearby_below["price"] if nearby_below else round2(current * 0.92)
        upper = round2(old_lower)
        mode = "Breakdown Rebase / 跌破后下移"
        basis = f"现价已有效跌破原下沿 {old_lower}；旧支撑转为上方压力，新区间下移到现价附近，不再把旧区间称为仍在测试。"

    low_break = round2((lower or 0) * 0.985) if lower else None
    high_break = round2((upper or 0) * 1.015) if upper else None
    return {
        "low": round2(lower),
        "high": round2(upper),
        "mode": mode,
        "basisCN": basis,
        "validUntilCN": "所有数字都会随每次MMF报告重算，不是固定区间；只在当前市场结构有效，有效突破上沿或放量跌破下沿后必须重算。",
        "recalcTriggersCN": [
            f"有效突破上沿 {upper}，下一轮区间上移，原压力可能变支撑。",
            f"放量跌破下沿 {lower}，下一轮区间下移，原支撑可能变压力。",
            "半导体热力图明显转弱、VIX失控、Nasdaq长期结构破坏时重算。",
        ],
        "supportCandidates": supports[:5],
        "resistanceCandidates": resistances[:5],
        "breakoutAbove": high_break,
        "breakdownBelow": low_break,
    }


def capital_behavior_read(q, volume_structure, heat, mac, account=None):
    ch = q.get("changePct") if isinstance(q.get("changePct"), (int, float)) else q.get("prevCloseChangePct")
    close = q.get("close") or q.get("last")
    label = (volume_structure or {}).get("labelCN") or "量价结构待确认"
    score = (volume_structure or {}).get("score")
    read = (volume_structure or {}).get("readCN") or "当前还不能把资金行为解释过满，先等下一次放量方向。"
    evidence = (volume_structure or {}).get("evidenceCN") or "量价证据不足。"
    watch = (volume_structure or {}).get("watchCN") or "继续观察下一次放量方向，以及反弹是否被成交量承认。"
    vix_last = (mac.get("vix") or {}).get("last") if mac else None
    heat_mode = heat.get("mode") if heat else None
    heat_summary = heat.get("summaryCN") if heat else None
    quiet_vix = isinstance(vix_last, (int, float)) and vix_last < 20

    if "慢性派发" in label:
        posture = "Controlled Distribution / 慢性派发"
        summary = "资金更像在逢反弹降低风险：下跌被成交量承认，反弹暂时没有同等买盘承认。"
        implication = "不要把第一根反弹当成底部确认；如果反弹缩量，优先按卖压仍在处理。"
    elif "派发" in label:
        posture = "Distribution Pressure / 派发压力"
        summary = "资金行为偏防守，卖压真实，但还需要后续K线确认是否升级成连续派发。"
        implication = "下一根放量方向更重要；放量站回关键均线才说明有人重新接管。"
    elif "放量风险释放" in label:
        posture = "Controlled Selling / 风险释放"
        summary = "资金在释放风险，卖压真实，但VIX若仍受控，就更像板块内部降杠杆或估值回归。"
        implication = "可以观察赔率，但不要因为价格下跌就自动重仓；先看卖压是否递减。"
    elif "高波动" in label:
        posture = "Price Discovery / 高波动价格发现"
        summary = "买卖双方都在用量表达观点，市场还在重新定价，而不是单边恐慌。"
        implication = "账户要按情景处理，不急着把分歧解释成方向已经确定。"
    elif "吸筹" in label:
        posture = "Constructive Accumulation / 修复吸筹"
        summary = "资金更愿意承认上涨，下跌时卖压相对温和，结构开始比单纯反弹健康。"
        implication = "如果回踩缩量守住关键位，可以把试探条件往前移一点，但仍不能追满。"
    else:
        posture = "Wait For Flow / 等资金表态"
        summary = "资金行为还没有形成压倒性结论，价格变化不能脱离下一次量能确认。"
        implication = "继续等成交量选择方向；没有量，就不要把单日K线解释过满。"

    if quiet_vix and isinstance(ch, (int, float)) and ch <= -5:
        summary += " 但VIX仍低于20，只能说明广泛市场波动尚未失控；不能据此断定半导体卖压可控，也不代表已经恐慌出清。"
    if heat_mode:
        evidence += f" 板块热力：{heat_mode}。{heat_summary or ''}"

    account_pct = account.get("currentPositionPct") if account else None
    if isinstance(account_pct, (int, float)) and account_pct > 0:
        account_line = f"当前账户约 {account_pct}% 仓位，属于参与但保留现金选择权；资金行为未转强前，不用急着把赔率仓升级成趋势仓。"
    else:
        account_line = "当前账户可以把现金视为选择权；资金行为未转强前，等待本身就是仓位。"

    observations = [
        f"价格/收盘：{close if close is not None else '--'}；当日变化：{round2(ch) if isinstance(ch, (int, float)) else '--'}%。",
        f"量价标签：{label}；资金行为分数：{score if score is not None else '--'}/10。",
        f"波动环境：VIX={vix_last if vix_last is not None else 'n/a'}；低VIX只说明广泛市场波动尚未失控，不能单独证明半导体卖压可控，也不等于已经恐慌出清。" if quiet_vix else f"波动环境：VIX={vix_last if vix_last is not None else 'n/a'}。",
    ]
    return {
        "titleCN": "Capital Behavior / 资金行为",
        "postureCN": posture,
        "score": score,
        "summaryCN": summary,
        "readCN": read,
        "evidenceCN": evidence,
        "implicationCN": implication,
        "watchCN": watch,
        "accountCN": account_line,
        "observationsCN": observations,
    }


def strategic_behavior_map(ticker, q, fib, heat, mac, scenarios, volume_structure, account=None, df=None):
    current = q.get("close") or q.get("last")
    anchor = dynamic_anchor_range(df, q, fib)
    clusters = fib.get("clusters") or []
    current_num = float(current) if isinstance(current, (int, float)) else None
    support_candidates = [x for x in (anchor.get("supportCandidates") or []) if isinstance(x.get("price"), (int, float)) and (current_num is None or x.get("price") <= current_num)]
    support_candidates.sort(key=lambda x: x.get("price"), reverse=True)
    if support_candidates:
        nearest_price = support_candidates[0].get("price")
        nearby_supports = [x.get("price") for x in support_candidates if nearest_price and abs(x.get("price") - nearest_price) / nearest_price <= 0.025][:3]
        support_low = round2(min(nearby_supports))
        support_high = round2(max(nearby_supports))
        support_mid = round2(sum(nearby_supports) / len(nearby_supports))
    else:
        support_low = anchor.get("low") if current_num is None or (anchor.get("low") or 0) <= current_num else round2(current_num * 0.95)
        support_high = support_low
        support_mid = support_low
    vix_last = (mac.get("vix") or {}).get("last")
    heat_mode = heat.get("mode")
    heat_summary = heat.get("summaryCN")
    leaders = ", ".join([x.get("ticker", "") for x in (heat.get("leaders") or [])[:3] if x.get("ticker")]) or "暂无明确领涨"
    laggards = ", ".join([x.get("ticker", "") for x in (heat.get("laggards") or [])[:3] if x.get("ticker")]) or "暂无明确拖累"
    support_text = f"{support_low}-{support_high}" if support_low is not None and support_high is not None and support_low != support_high else f"{support_low}" if support_low is not None else "当前价下方待确认区域"
    test_zone = None
    if isinstance(support_low, (int, float)) and isinstance(support_high, (int, float)):
        width = max(support_high - support_low, support_high * 0.015)
        test_zone = f"{round2(support_low - width * 0.45)}-{round2(support_low + width * 0.2)}"
    else:
        test_zone = "支撑下沿附近"
    vix_note = f"VIX={vix_last}" if isinstance(vix_last, (int, float)) else "VIX暂不可用"
    volume_label = volume_structure.get("labelCN") if volume_structure else "量价结构待确认"
    capital = capital_behavior_read(q, volume_structure, heat, mac, account)
    account_waiting = bool(account and (account.get("cashPct") == 100 or account.get("previousTrade")))

    consensus = [
        {
            "beliefCN": f"当前动态 Anchor Range 是 {anchor.get('low')}-{anchor.get('high')}，市场大概率先按箱体/再定价结构处理。",
            "confidence": "High" if anchor.get("low") and anchor.get("high") else "Medium",
            "evidenceCN": f"{anchor.get('mode')}。{anchor.get('basisCN')}",
        },
        {
            "beliefCN": f"市场正在把 {support_text} 当成当前战场的关键支撑/共振区。",
            "confidence": "Medium" if support_low is not None else "Low",
            "evidenceCN": fib.get("summaryCN") or "Fib共振区暂时不密集，先看EMA和前低/前高。",
        },
        {
            "beliefCN": "半导体仍是当前风险偏好的主要观察窗口。",
            "confidence": "Medium",
            "evidenceCN": f"{heat_mode}。{heat_summary} 领涨：{leaders}；拖累：{laggards}。",
        },
        {
            "beliefCN": "市场暂时更像在等待确认，而不是无条件进入趋势追涨。",
            "confidence": "Medium",
            "evidenceCN": f"{vix_note}；量价结构：{volume_label}。",
        },
        {
            "beliefCN": f"资金行为当前更接近：{capital.get('postureCN')}。",
            "confidence": "Medium",
            "evidenceCN": capital.get("summaryCN"),
        },
    ]
    if account_waiting:
        consensus.insert(
            0,
            {
                "beliefCN": "账户已经回到等待下一次优势的状态，上一笔交易不再需要被证明。",
                "confidence": "High",
                "evidenceCN": "上一笔交易完成后，新的优势必须重新出现；现金是下一次作战能力。",
            },
        )

    participants = [
        {
            "group": "Technical Traders",
            "groupCN": "技术交易者",
            "likelyActionCN": f"会盯 {support_text}、EMA和前低；接近支撑可能尝试低吸，但跌破后容易触发止损。",
        },
        {
            "group": "Swing Traders",
            "groupCN": "波段资金",
            "likelyActionCN": "更关心回踩是否缩量、反弹是否放量；不会因为单日反弹就直接打满仓位。",
        },
        {
            "group": "Institutional Allocators",
            "groupCN": "机构配置资金",
            "likelyActionCN": f"会看半导体强度是否扩散到指数和权重股；当前领涨线索是 {leaders}。",
        },
        {
            "group": "Options / Hedging Flows",
            "groupCN": "期权/对冲资金",
            "likelyActionCN": "会围绕整数位、前高前低和共识支撑调整gamma与保护仓，容易放大假突破或假跌破。",
        },
        {
            "group": "Liquidity Providers",
            "groupCN": "流动性资金",
            "likelyActionCN": f"会观察 {test_zone} 是否有止损和被动卖盘；资金往往利用已经形成的共识与止损分布，但MMF不假设任何一方能凭空制造全部共识。",
        },
    ]

    liquidity_scenarios = [
        {
            "scenario": "Support Holds",
            "scenarioCN": "支撑守住",
            "pathCN": f"{support_text} 附近承接增强，买盘愿意接住回踩，反弹可能延续。",
            "accountResponseCN": "只允许按计划小仓试探；不因为支撑守住一天就追满。",
        },
        {
            "scenario": "False Breakdown",
            "scenarioCN": "假跌破 / 流动性测试",
            "pathCN": f"价格刺穿共识支撑，测试 {test_zone} 后快速收回，说明止损被消化后仍有真实需求。",
            "accountResponseCN": "可按Entry Zone重新评估试仓；必须同时看到量能和板块质量没有恶化。",
        },
        {
            "scenario": "Consensus Failure",
            "scenarioCN": "共识失效",
            "pathCN": f"跌破 {support_text} 后放量下行，半导体热力图转弱或VIX升高，说明支撑共识不再有买盘兑现。",
            "accountResponseCN": "减速或冻结加仓，重跑MMF；不要把便宜误认为高赔率。",
        },
    ]
    if scenarios:
        liquidity_scenarios.append(
            {
                "scenario": "Base Path",
                "scenarioCN": scenarios[0].get("name", "Base / 震荡消化"),
                "pathCN": scenarios[0].get("whyCN", "市场仍在选择路径，等待下一次放量表态。"),
                "accountResponseCN": scenarios[0].get("responseCN", "继续观察，不急着证明方向。"),
            }
        )

    summary = f"指标不是答案，指标是市场行为留下的脚印。当前动态区间是 {anchor.get('low')}-{anchor.get('high')}；共识焦点在 {support_text}，真正要观察的是价格到那里时谁愿意买、谁被迫卖。"
    if current:
        summary = f"当前价格约 {current}。{summary}"
    return {
        "titleCN": "市场行为分析",
        "subtitle": "Strategic Behavior Map",
        "principleCN": "多算多胜，少算少胜。",
        "coreIdeaCN": "分析市场，不是为了预测价格，而是为了预判参与者下一步最可能怎么行动。",
        "dynamicAnchorRange": anchor,
        "capitalBehavior": capital,
        "consensusCardCN": f"动态区间 {anchor.get('low')}-{anchor.get('high')}；市场正在把 {support_text} 当作共识测试区。若该处形成拥挤的支撑共识，价格可能先扫过 {test_zone}，测试止损与真实承接。",
        "consensusNow": consensus,
        "participantMap": participants,
        "liquidityScenarios": liquidity_scenarios,
        "pathMeta": {
            "asOfDate": str(pd.to_datetime(df.iloc[-1].Date).date()) if df is not None and not df.empty else q.get("latestTradingDay"),
            "timeFrameCN": "日线 / 当前MMF报告",
            "currentPrice": round2(current_num),
            "basisCN": "路径每次运行都会按当前收盘、当前价下方最近支撑、量价结构和板块环境重算；已被有效跌破的旧支撑会转为上方压力，不再继续显示为支撑守住情景。",
        },
        "accountResponseCN": "先为上涨、下跌、横盘和假动作设计账户应对，不用靠单一路径证明观点。",
        "summaryCN": summary,
    }


def ensure_strategic_behavior_map(report):
    if report.get("strategicBehaviorMap") and (report.get("strategicBehaviorMap") or {}).get("dynamicAnchorRange") and (report.get("strategicBehaviorMap") or {}).get("capitalBehavior"):
        return report
    ticker = ((report.get("meta") or {}).get("ticker") or "SOXL").upper()
    q = (report.get("dailyBattlefield") or {}).get("quote") or {}
    fib = report.get("fibonacci") or {}
    heat = report.get("sectorHeatmap") or {}
    mac = report.get("macro") or {}
    scenarios = report.get("scenarioEngine") or []
    volume_structure = report.get("volumeStructure") or (report.get("intradayDecision") or {}).get("volumeStructure") or {}
    account = report.get("accountState") or {}
    report["strategicBehaviorMap"] = strategic_behavior_map(ticker, q, fib, heat, mac, scenarios, volume_structure, account)
    return report


def macro_panel(quotes=None, vix_quote=None):
    items = []
    for t, name in MACRO_PROXIES:
        q = shared_quote(quotes, t) if quotes is not None else safe_quote(t)
        items.append({"ticker": t, "name": name, "last": q.get("last"), "changePct": q.get("changePct")})
    vix = vix_quote or fetch_vix_quote()
    items.append({"ticker": "VIX", "name": "Volatility index", "last": vix.get("last"), "changePct": vix.get("changePct"), "source": vix.get("source")})
    pressure = sum(
        [
            1
            for x in items
            if (x["ticker"] == "UUP" and isinstance(x.get("changePct"), (int, float)) and x["changePct"] > 0)
            or (x["ticker"] == "USO" and isinstance(x.get("changePct"), (int, float)) and x["changePct"] > 1)
            or (x["ticker"] == "TLT" and isinstance(x.get("changePct"), (int, float)) and x["changePct"] < 0)
            or (x["ticker"] == "VIX" and isinstance(x.get("last"), (int, float)) and x["last"] >= 22)
            or (x["ticker"] == "VIX" and isinstance(x.get("changePct"), (int, float)) and x["changePct"] >= 5)
        ]
    )
    status = "Macro Pressure" if pressure >= 2 else "Macro Neutral"
    vix_last = vix.get("last")
    if isinstance(vix_last, (int, float)):
        if vix_last >= 30:
            vix_note = f"VIX={vix_last}，市场处在高波动/恐慌区，仓位要先考虑活下来。"
        elif vix_last >= 22:
            vix_note = f"VIX={vix_last}，波动压力偏高，反弹更容易被波动打断。"
        elif vix_last <= 15:
            vix_note = f"VIX={vix_last}，波动环境偏安静，但太安静也可能让资金低估风险。"
        else:
            vix_note = f"VIX={vix_last}，波动环境中性，暂时不是主要压制。"
    else:
        vix_note = "VIX暂时不可用，波动风险用价格和量能替代判断。"
    fed_policy = {
        "asOf": "2026-07-01",
        "currentTargetRange": "3.50%-3.75%",
        "expectedCuts2026": "0次左右，市场已经从等降息转向维持高利率/甚至小幅升息风险",
        "officialBiasCN": "政策层面仍以压通胀和观察就业为主，降息不是已经兑现的顺风。",
        "expectationCheckCN": "如果市场原本期待年内多次降息，但现实是继续维持3.50%-3.75%，那就是预期落空；对高估值科技、半导体和杠杆ETF来说，这会压低估值倍数，也会让反弹更依赖业绩和真实资金承接。",
        "semiconductorImpactCN": "半导体属于久期更长、估值更敏感的成长资产：利率越高，未来现金流折现越重；如果降息预期延后，SOXL这类杠杆半导体ETF会同时承受估值压缩和波动放大的压力。",
    }
    rate_note = f"利率口径截至{fed_policy['asOf']}：联邦基金目标区间约{fed_policy['currentTargetRange']}；2026年市场降息预期约{fed_policy['expectedCuts2026']}。{fed_policy['expectationCheckCN']}"
    return {
        "items": items,
        "status": status,
        "vix": vix,
        "vixNoteCN": vix_note,
        "fedPolicy": fed_policy,
        "rateNoteCN": rate_note,
        "interpretationCN": f"宏观面看利率、美元、避险、通胀和VIX波动是否共同压制风险资产。{vix_note} {rate_note}",
    }


def fibonacci_resonance(df):
    current = float(df.iloc[-1].Close)
    levels = [0.236, 0.382, 0.5, 0.618, 0.786]
    rows = []
    all_prices = []
    for period in [20, 60, 120, 180, 252]:
        d = df.tail(min(len(df), period))
        hi = float(d.High.max())
        lo = float(d.Low.min())
        prices = {lv: hi - (hi - lo) * lv for lv in levels}
        nearest = min(levels, key=lambda lv: abs(current - prices[lv]))
        price = prices[nearest]
        all_prices.extend(prices.values())
        rows.append(
            {
                "period": f"{period}D",
                "high": round2(hi),
                "low": round2(lo),
                "nearestFib": nearest,
                "price": round2(price),
                "distance": round2(current - price),
                "isClose": abs(current - price) / current <= 0.035,
            }
        )
    hi = float(df.High.max())
    lo = float(df.Low.min())
    ath_prices = {lv: hi - (hi - lo) * lv for lv in levels}
    nearest = min(levels, key=lambda lv: abs(current - ath_prices[lv]))
    all_prices.extend(ath_prices.values())
    rows.append(
        {
            "period": "ATH",
            "high": round2(hi),
            "low": round2(lo),
            "nearestFib": nearest,
            "price": round2(ath_prices[nearest]),
            "distance": round2(current - ath_prices[nearest]),
            "isClose": abs(current - ath_prices[nearest]) / current <= 0.035,
        }
    )

    prices = sorted([p for p in all_prices if np.isfinite(p)])
    clusters = []
    used = set()
    for i, price in enumerate(prices):
        if i in used:
            continue
        group = [price]
        used.add(i)
        for j in range(i + 1, len(prices)):
            if abs(prices[j] - price) / max(price, 1) <= 0.045:
                group.append(prices[j])
                used.add(j)
        if len(group) >= 3:
            lo_g = round2(min(group))
            hi_g = round2(max(group))
            mid = np.mean(group)
            distance = round2(current - mid)
            zone = "red" if lo_g <= current <= hi_g else "orange" if abs(current - mid) / current <= 0.06 else "yellow"
            role = "support" if hi_g < current else "resistance" if lo_g > current else "active"
            role_cn = "支撑" if role == "support" else "压力" if role == "resistance" else "现价战场"
            clusters.append({"low": lo_g, "high": hi_g, "count": len(group), "mid": round2(mid), "distance": distance, "zone": zone, "role": role, "roleCN": role_cn})
    clusters = sorted(clusters, key=lambda x: abs(x["distance"] or 0))[:5]
    if clusters:
        c = clusters[0]
        distance = c["distance"]
        if distance < 0:
            distance_read = f"现价低于中心 {abs(distance)}，该区位于上方，当前按压力观察"
        elif distance > 0:
            distance_read = f"现价高于中心 {distance}，该区位于下方，当前按支撑观察"
        else:
            distance_read = "现价正在该区中心附近"
        summary = f"Fib共振区不是单个点，而是一段战场。离现价最近的是{c['roleCN']}区 {c['low']} - {c['high']}，中心 {c['mid']}；{distance_read}。"
    else:
        summary = "没有形成足够密集的Fib共振区，当前更应看EMA和前低/前高。"
    return {"rows": rows, "clusters": clusters, "summaryCN": summary}


def intraday_battle(df, q, intraday_df=None):
    if intraday_df is not None and not intraday_df.empty:
        first = intraday_df.iloc[0]
        last = intraday_df.iloc[-1]
        day_change = pct(last.Close, first.Open) or 0
        vwap = round2(last.get("VWAP"))
        ema20 = round2(last.get("EMA20"))
        above_vwap = last.Close >= last.get("VWAP", last.Close)
        above_ema20 = last.Close >= last.get("EMA20", last.Close)
        title = "买盘掌控VWAP上方" if above_vwap and above_ema20 and day_change > 0 else "卖盘压制VWAP下方" if (not above_vwap) and (not above_ema20) and day_change < 0 else "多空围绕VWAP拉扯"

        phase_specs = [
            ("开盘阶段", 0.25, "开盘阶段看第一波方向有没有被量能承认。"),
            ("上午中段", 0.50, "上午中段看价格能否站稳VWAP/EMA20，而不是只看反弹幅度。"),
            ("午盘震荡", 0.75, "午盘看横盘位置：横在VWAP上方是承接，横在下方是压力。"),
            ("尾盘决战", 1.00, "尾盘决定资金是否愿意带仓过夜。"),
        ]
        phases = []
        n = len(intraday_df)
        start_idx = 0
        for phase, frac, fallback_read in phase_specs:
            end_idx = max(start_idx + 1, min(n, int(round(n * frac))))
            part = intraday_df.iloc[start_idx:end_idx]
            if part.empty:
                part = intraday_df.iloc[[min(start_idx, n - 1)]]
            p_first = part.iloc[0]
            p_last = part.iloc[-1]
            phase_change = pct(p_last.Close, p_first.Open) or 0
            vol_raw = float(part.Volume.fillna(0).sum()) if "Volume" in part else 0
            relation = "VWAP上方" if p_last.Close >= p_last.get("VWAP", p_last.Close) else "VWAP下方"
            read = f"{fallback_read} 本段变化 {phase_change:+.2f}%，收在{relation}，阶段成交量 {round2(vol_raw/1_000_000)}M。"
            phases.append({"phase": phase, "readCN": read, "changeProxy": round2(phase_change), "volume": f"{round2(vol_raw/1_000_000)}M"})
            start_idx = end_idx
        summary = f"已接入常规交易时段5分钟OHLCV数据。常规盘日内变化 {day_change:+.2f}%，最后一根5分钟K收于 {round2(last.Close)}，VWAP {vwap}，EMA20 {ema20}；它可能与盘前/盘后最新价不同。判断重点是价格是否持续在VWAP/EMA20同侧运行。"
        bars = []
        for _, row in intraday_df.iterrows():
            bars.append({
                "time": pd.to_datetime(row.Date, utc=True).tz_convert("America/New_York").strftime("%H:%M"),
                "open": round2(row.Open),
                "high": round2(row.High),
                "low": round2(row.Low),
                "close": round2(row.Close),
                "volume": round2(row.Volume),
                "vwap": round2(row.get("VWAP")),
                "ema20": round2(row.get("EMA20")),
            })
        return {
            "title": title,
            "source": "Tiingo IEX real 5-minute OHLCV",
            "phases": phases,
            "summaryCN": summary,
            "bars": bars,
            "vwap": vwap,
            "ema20": ema20,
            "latestTime": str(pd.to_datetime(last.Date, utc=True).tz_convert("America/New_York")),
            "mode": "real_5m",
        }
    ch = q.get("changePct") or 0
    title = "卖盘主导" if ch < -2 else "买盘主导" if ch > 2 else "多空拉扯"
    phases = [
        ("开盘阶段", "看跳空后是否快速回补；不能回补，说明第一波卖压被市场承认。", 0.25),
        ("上午中段", "看反弹能否站回VWAP/EMA20；站不回，多数只是空头回补。", 0.35),
        ("午盘震荡", "看价格能否横住；横住代表卖压放缓，横不住代表继续派发。", 0.15),
        ("尾盘决战", "尾盘决定资金是否愿意带仓过夜；弱收盘代表机构不急着接。", 0.25),
    ]
    out = [{"phase": p, "readCN": r, "changeProxy": round2(ch * m), "volume": "n/a"} for p, r, m in phases]
    return {
        "title": title,
        "source": "Daily-derived intraday proxy until true 5m OHLCV is connected",
        "phases": out,
        "summaryCN": "当前暂未拿到稳定的5分钟OHLCV数据，先用日线变化拆成四段代理路径；等数据稳定后，会切换为基于VWAP/EMA20的真实日内节奏图。",
        "mode": "proxy",
    }


def volume_context(df, q):
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    vol = q.get("volumeRaw") if isinstance(q.get("volumeRaw"), (int, float, np.integer, np.floating)) else last.Volume
    avg20 = last.VOL20 if pd.notna(last.VOL20) else None
    volume_available = isinstance(vol, (int, float, np.integer, np.floating)) and float(vol) > 0
    ratio = round2((float(vol) / float(avg20)) if volume_available and avg20 and avg20 > 0 else None)
    vs_avg = round2((ratio - 1) * 100) if isinstance(ratio, (int, float)) else None
    ch = q.get("changePct") if isinstance(q.get("changePct"), (int, float)) else pct(last.Close, prev.Close) or 0

    if not volume_available or ratio is None:
        headline = "当前交易时段没有可靠成交量字段；这是数据缺失，不是缩量信号。"
        action = "量价结论暂不可用，不能据此判断观望、吸筹或派发。"
        next_move = "等待常规时段成交量或可靠的盘前/盘后量能后再判断资金行为。"
    elif ratio >= 1.5 and ch < -1:
        headline = f"今天成交量约 {fmt_big(vol)}，比20日均量高 {vs_avg}%。这是放量下跌，卖盘不是轻轻按一下，而是在主动降低风险。"
        action = "资金更像是在撤、在降杠杆，或者至少不愿意马上接回去。第一根反弹容易只是空头回补。"
        next_move = "如果明天反弹缩量，资金大概率继续卖强不卖弱；只有放量站回关键均线，才说明有人真正回来接。"
    elif ratio >= 1.5 and ch > 1:
        headline = f"今天成交量约 {fmt_big(vol)}，比20日均量高 {vs_avg}%。这是放量上涨，买盘愿意付价，但不能自动等于可以追。"
        action = "资金在试图抢回主动权；接下来要看回踩时量能是否缩下来，价格是否还能守住。"
        next_move = "大资金更可能等回踩确认，而不是连续追高；若回踩缩量守住VWAP/EMA20，才会更像真实加仓。"
    elif ratio >= 1.25:
        headline = f"今天成交量约 {fmt_big(vol)}，比20日均量高 {vs_avg}%。量明显出来了，但价格只动了 {round2(ch)}%，说明多空都在用力。"
        action = "资金不是没来，而是分歧很大：有人卖，有人接，最后要看收盘位置和次日延续。"
        next_move = "资金大概率先观察这根量能后的第二天：能放量延续就跟，不能延续就会把今天当成换手而不是突破。"
    elif ratio <= 0.75:
        headline = f"今天成交量约 {fmt_big(vol)}，只有20日均量的 {ratio} 倍。价格变化 {round2(ch)}%，但量没有配合。"
        action = "资金更像在观望，不像大规模进攻或恐慌撤退。缩量上涨容易虚，缩量下跌也未必是真砸盘。"
        next_move = "大资金大概率继续等量能表态；下一次放量的方向，比今天这根K线更重要。"
    else:
        headline = f"今天成交量约 {fmt_big(vol)}，约为20日均量 {ratio} 倍，基本属于正常换手。"
        action = "资金没有强烈表态，价格变化更多是短线供需和权重股扰动，不像一边倒的机构行动。"
        next_move = "资金大概率继续挑位置，不会急着证明方向；明天重点看是否突然放量突破或放量跌破。"

    return {
        "volume": fmt_big(vol),
        "volumeRaw": round2(vol),
        "avg20": fmt_big(avg20) if avg20 else "--",
        "ratio": ratio,
        "available": volume_available and ratio is not None,
        "qualityCN": "可用" if volume_available and ratio is not None else "缺失/不可用于量价推断",
        "vsAvgPct": vs_avg,
        "headlineCN": headline,
        "moneyActionCN": action,
        "nextMoveCN": next_move,
    }


def volume_structure_read(df, q, vol_ctx, sec, mac):
    if not (vol_ctx or {}).get("available"):
        return {
            "labelCN": "当期量能缺失",
            "score": None,
            "readCN": "当前时段没有可靠成交量，不能把0解释成缩量，也不能用它确认吸筹或派发。",
            "evidenceCN": "历史日线量价结构仍可参考，但当前时段的量价确认暂时冻结。",
            "scenarioCN": "先按价格快照处理，等待常规时段或可靠扩展时段成交量。",
            "watchCN": "成交量恢复前，不使用量价结构调整情景概率或扩大仓位。",
            "available": False,
        }
    rows = df.tail(min(len(df), 8)).copy()
    if len(rows) < 3:
        return {
            "labelCN": "量价结构样本不足",
            "score": 5,
            "readCN": "最近K线数量不够，暂时不把单日放量或缩量解释过满。",
            "evidenceCN": "需要至少3根以上日线才能判断放量跌、缩量涨是否连续出现。",
            "watchCN": "继续看下一次放量选择方向。",
        }

    events = []
    high_down = low_up = high_up = low_down = 0
    latest_date = rows.iloc[-1].Date
    for i in range(1, len(rows)):
        prev = rows.iloc[i - 1]
        row = rows.iloc[i]
        ret = pct(row.Close, prev.Close) or 0
        volr = row.VOL_RATIO if pd.notna(row.VOL_RATIO) else None
        if row.Date == latest_date:
            ret = q.get("changePct") if isinstance(q.get("changePct"), (int, float)) else ret
            volr = vol_ctx.get("ratio") if isinstance(vol_ctx.get("ratio"), (int, float)) else volr
        volr = float(volr or 1)
        if ret <= -1 and volr >= 1.15:
            high_down += 1
            events.append("放量跌")
        elif ret >= 1 and volr <= 1.05:
            low_up += 1
            events.append("缩量涨")
        elif ret >= 1 and volr >= 1.15:
            high_up += 1
            events.append("放量涨")
        elif ret <= -1 and volr <= 1.05:
            low_down += 1
            events.append("缩量跌")
        else:
            events.append("普通换手")

    semis = (sec.get("groups") or {}).get("Semiconductor")
    defensive = (sec.get("groups") or {}).get("Defensive")
    vix_last = (mac.get("vix") or {}).get("last")
    ch = q.get("changePct") if isinstance(q.get("changePct"), (int, float)) else 0
    sector_split = isinstance(semis, (int, float)) and isinstance(defensive, (int, float)) and semis < defensive - 1
    quiet_vix = isinstance(vix_last, (int, float)) and vix_last < 20

    if high_down >= 2 and low_up >= 1 and high_up == 0:
        label = "慢性派发警报"
        score = 2
        read = "最近结构接近放量跌、缩量涨、再放量跌：有人愿意用更大的成交量卖，但反弹暂时没有同等量能承认。"
        scenario = "这更像卖压主导，不能把第一根反弹当成底部确认。"
    elif high_down >= 2 and high_up >= 1:
        label = "高波动价格发现"
        score = 4
        read = "下跌有量，但反弹也曾经有量，说明不是单纯聪明钱卖给散户，更像AI/半导体内部在重新定价。"
        scenario = "核心问题不是谁在卖，而是同样价格为什么同时吸引买盘和卖盘。"
    elif high_down >= 1 and low_up >= 1:
        label = "派发压力观察"
        score = 3
        read = "已经出现放量跌配缩量涨的组合，但样本还不够判定为连续派发。"
        scenario = "下一根放量方向会决定这是换手消化，还是慢性派发升级。"
    elif high_up >= 1 and low_down >= 1:
        label = "吸筹式修复观察"
        score = 6
        read = "量能更愿意承认上涨，下跌时反而缩量，这比单纯反弹健康。"
        scenario = "如果回踩继续缩量守住，才更接近可加仓结构。"
    elif high_down >= 1:
        label = "放量风险释放"
        score = 4
        read = "当前主要证据是放量下跌，说明卖压真实，但还不能仅凭一根K线定义为派发。"
        scenario = "先看卖压是否递减，再判断是释放风险还是趋势破坏。"
    else:
        label = "量价分歧不强"
        score = 5
        read = "最近量价没有形成压倒性结构，市场还在等下一次放量表态。"
        scenario = "方向还没被成交量正式承认。"

    if quiet_vix and abs(ch) >= 5 and sector_split:
        read += " 同时VIX不高但半导体弱于防御，说明更像板块内部轮动/杠杆出清，而不是全市场恐慌。"
    evidence = (
        f"最近{len(events)}段：{' → '.join(events)}；"
        f"放量跌={high_down}，缩量涨={low_up}，放量涨={high_up}，缩量跌={low_down}；"
        f"VIX={vix_last if vix_last is not None else 'n/a'}，Semiconductor={semis}%，Defensive={defensive}%。"
    )
    watch = "最怕继续出现放量跌、缩量涨；更好的结构是下探缩量，或放量站回关键均线后回踩缩量守住。"
    return {"labelCN": label, "score": score, "readCN": read, "evidenceCN": evidence, "scenarioCN": scenario, "watchCN": watch}


def reconcile_quote_volume(q, df):
    out = dict(q or {})
    if df is None or df.empty:
        return out
    last = df.iloc[-1]
    daily_volume = float(last.Volume or 0)
    quote_volume = out.get("volumeRaw") if isinstance(out.get("volumeRaw"), (int, float, np.integer, np.floating)) else None
    if daily_volume > 0 and (quote_volume is None or daily_volume > float(quote_volume) * 5):
        out["volume"] = fmt_big(daily_volume)
        out["volumeRaw"] = daily_volume
        out["volumeSource"] = "Tiingo daily volume preferred over partial IEX volume"
    if out.get("prevCloseChangePct") is None and isinstance(out.get("last"), (int, float)) and isinstance(out.get("prevClose"), (int, float)):
        out["prevCloseChangePct"] = pct(out.get("last"), out.get("prevClose"))
    return out


def factor_interpret(name, score):
    level = "偏热/强" if score >= 80 else "偏积极" if score >= 60 else "中性" if score >= 40 else "偏冷" if score >= 20 else "极冷"
    mp = {
        "Momentum": "趋势动能",
        "Breadth": "板块广度",
        "Volume": "量能",
        "ETF Flow": "ETF资金/权重贡献",
        "Volatility": "波动环境",
        "Macro": "宏观环境",
        "Positioning": "价格位置",
    }
    return f"{mp.get(name, name)}：{level}。"


def fear_greed_score_at(df, idx, sec, mac, etf):
    row = df.iloc[idx]
    prev = df.iloc[idx - 1] if idx > 0 else row
    ret1 = pct(row.Close, prev.Close) or 0
    ret5 = pct(row.Close, df.iloc[max(0, idx - 5)].Close) or 0
    ret20 = pct(row.Close, df.iloc[max(0, idx - 20)].Close) or 0
    ret60 = pct(row.Close, df.iloc[max(0, idx - 60)].Close) or 0
    dev20 = pct(row.Close, row.EMA20) or 0
    vol_ratio = float(row.VOL_RATIO or 1)
    etf_impact = sum([(x.get("impact") or 0) for x in etf.get("items", [])])
    momentum = clip(50 + ret20 * 1.2 + ret60 * 0.35 + ret5 * 1.6 + ret1 * 1.1)
    breadth = clip(50 + ((sec["groups"].get("Semiconductor") or 0) * 7) + ((sec["groups"].get("Growth") or 0) * 4))
    volume = clip(50 + ret1 * 2.2 - max(0, -ret1) * min(vol_ratio, 2.5) * 4 + (vol_ratio - 1) * 10)
    etf_flow = clip(50 + etf_impact * 18 + ret1 * 1.5)
    vix = (mac.get("vix") or {}).get("last")
    vix_penalty = 0
    if isinstance(vix, (int, float)):
        vix_penalty = max(0, vix - 18) * 1.6
    volatility = clip(65 - abs(vol_ratio - 1) * 22 - abs(ret1) * 2.8 - vix_penalty)
    macro_score = clip((42 if mac.get("status") == "Macro Pressure" else 58) - vix_penalty * 0.35)
    positioning = clip(50 + dev20 * 2.4 - max(0, -ret1) * 1.6)
    return {
        "Momentum": momentum,
        "Breadth": breadth,
        "Volume": volume,
        "ETF Flow": etf_flow,
        "Volatility": volatility,
        "Macro": macro_score,
        "Positioning": positioning,
    }


def fear_greed_attribution(df, sec, mac, etf):
    weights = [("Momentum", 20, "趋势动能"), ("Breadth", 15, "板块广度"), ("Volume", 15, "量能压力"), ("ETF Flow", 20, "ETF权重贡献"), ("Volatility", 10, "波动环境"), ("Macro", 10, "宏观压力"), ("Positioning", 10, "价格位置")]
    scores = fear_greed_score_at(df, len(df) - 1, sec, mac, etf)
    rows = []
    total = 0
    for name, weight, cn in weights:
        score = scores[name]
        contribution = round2(weight * score / 100)
        total += contribution
        rows.append({"factor": name, "nameCN": cn, "weight": weight, "score": round2(score), "contribution": contribution, "interpretationCN": factor_interpret(name, score)})
    model_total = round2(total)
    external_raw = os.getenv("FEAR_GREED_OVERRIDE", "auto").strip()
    external_score = None
    external_info = None
    try:
        if external_raw.lower() in ("", "auto", "external", "feargreedmeter"):
            external_info = fetch_external_fear_greed()
            external_score = clip(external_info["score"]) if external_info else None
        else:
            external_score = clip(float(external_raw))
            external_info = {"score": external_score, "label": None, "source": "manual FEAR_GREED_OVERRIDE", "url": None}
    except Exception:
        external_score = None
        external_info = None
    if external_score is not None and model_total:
        scale = external_score / model_total
        for row in rows:
            row["modelContribution"] = row["contribution"]
            row["contribution"] = round2(row["contribution"] * scale)
    total = round2(external_score if external_score is not None else model_total)
    label = "Extreme Fear" if total < 20 else "Fear" if total < 40 else "Neutral" if total < 60 else "Greed" if total < 80 else "Extreme Greed"
    ranked = sorted(rows, key=lambda x: abs((x["score"] or 50) - 50), reverse=True)
    trend = []
    for i in range(max(61, len(df) - 60), len(df)):
        score_map = fear_greed_score_at(df, i, sec, mac, etf)
        model_trend_score = round2(sum([w * score_map[name] / 100 for name, w, _ in weights]))
        trend.append(model_trend_score)
    yesterday = trend[-2] if len(trend) > 1 else None
    trend_note = "60D趋势为MMF内部模型；当前仪表总分优先使用外部Fear & Greed读数。" if external_score is not None else "60D趋势和当前仪表都来自MMF内部模型。"
    external_source = external_info.get("source") if external_info else None
    external_text = f"外部Fear & Greed={round2(external_score)}" if external_score is not None else "外部Fear & Greed暂不可用"
    model_gap = round2((external_score or 0) - model_total) if external_score is not None else None
    gap_text = f"两者差值约 {model_gap} 分。" if model_gap is not None else ""
    explanation = (
        f"{external_text}，MMF内部模型={model_total}。{gap_text}"
        "差异正常：外部指数通常看更宽的美股市场，并会纳入VIX、期权Put/Call、避险资产、债券信用利差、市场宽度等跨资产指标；"
        "MMF内部模型更偏向当前标的和战场结构，重点看趋势、板块、权重股、量能、ETF贡献和价格位置。"
        "所以外部读数更像全市场天气，MMF读数更像这一个战场的火力图。"
    )
    return {
        "score": total,
        "label": label,
        "modelScore": model_total,
        "externalScore": round2(external_score) if external_score is not None else None,
        "source": external_source or "MMF internal attribution model",
        "externalUrl": external_info.get("url") if external_info else None,
        "rows": rows,
        "mainDrivers": ranked[:3],
        "yesterday": yesterday,
        "delta": round2(model_total - yesterday) if yesterday is not None else None,
        "deltaBasis": "MMF model vs prior MMF model",
        "trend": trend,
        "chart": line(trend, "MMF Fear & Greed 60D") if trend else None,
        "gauge": gauge(total, "MMF Fear & Greed"),
        "formulaCN": "总分优先对齐外部Fear & Greed读数；内部归因仍按 Momentum 20% + Breadth 15% + Volume 15% + ETF Flow 20% + Volatility 10% + Macro 10% + Positioning 10% 拆解原因。设置 FEAR_GREED_OVERRIDE=auto 会自动抓 feargreedmeter；设置数字则手动锁定。",
        "explanationCN": explanation,
        "interpretationCN": f"当前情绪为 {label}。外部读数={round2(external_score) if external_score is not None else '--'}，MMF模型读数={model_total}。主要异常项是 {ranked[0]['factor']}、{ranked[1]['factor']}。{trend_note}",
    }


def options_context(ticker, q):
    spot = q.get("last") or q.get("close")
    try:
        raw = fetch_yahoo_options(ticker, spot=spot)
    except Exception as e:
        return {
            "available": False,
            "source": "unavailable",
            "score": 4.5,
            "summaryCN": "期权链暂时不可用，短线Gamma和Dealer定位仍要打折。",
            "observationCN": "Put/Call、Gamma、dealer positioning 本次抓取失败，继续用价格、量能和尾盘承接替代。",
            "evidenceCN": f"Options fetch error: {str(e)[:120]}",
            "riskCN": "缺少期权维度时，不能对盘中反转信号太自信。",
            "actionCN": "暂时降低短线结论权重。",
        }
    pcv = raw.get("putCallVolumeRatio")
    pcoi = raw.get("putCallOpenInterestRatio")
    net_gex = raw.get("netGammaExposureProxy")
    avg_iv = raw.get("averageIVPct")
    if isinstance(pcv, (int, float)) and pcv >= 1.25:
        tone = "put需求明显高于call，短线保护/看跌需求偏强。"
        score = 3.5
    elif isinstance(pcv, (int, float)) and pcv <= 0.75:
        tone = "call需求高于put，短线追涨或反弹押注更活跃。"
        score = 5.5
    else:
        tone = "Put/Call没有明显单边，期权市场更像分歧而不是一致押注。"
        score = 4.8
    if isinstance(net_gex, (int, float)) and net_gex < 0:
        dealer = "净Gamma proxy偏负，价格波动更容易被对冲放大；跌破关键位时要防加速。"
        score -= 0.8
    elif isinstance(net_gex, (int, float)) and net_gex > 0:
        dealer = "净Gamma proxy偏正，理论上更容易压低日内波动，但这只是OI/IV近似，不等于真实dealer book。"
        score += 0.4
    else:
        dealer = "Gamma proxy接近中性或不可判定，暂时不把期权当主导因素。"
    score = round2(max(1, min(8, score)))
    evidence = (
        f"到期日={raw.get('expiration')}（{raw.get('daysToExpiry')}天）；"
        f"Put/Call Volume={pcv}；Put/Call OI={pcoi}；Avg IV={avg_iv}%；"
        f"Net Gamma Exposure proxy={net_gex}。"
    )
    return {
        **raw,
        "available": True,
        "score": score,
        "summaryCN": f"期权链已接入：{tone} {dealer}",
        "observationCN": f"{tone} {dealer}",
        "evidenceCN": evidence,
        "riskCN": "公开期权链能给OI/IV/成交量，但Gamma和Dealer positioning仍是proxy；真实做市商库存无法从公开链条完全还原。",
        "actionCN": "如果Put/Call升高且净Gamma偏负，反弹先当减压；如果站回关键位且Put/Call降温，再提高短线信号权重。",
    }


def news_context(ticker, q, sec, etf, vol_ctx):
    symbols = [ticker]
    if ticker.upper() == "SOXL":
        symbols += ["SOXX", "SMH", "NVDA", "AMAT", "LRCX", "KLAC", "META"]
    items = []
    errors = []
    seen = set()
    for sym in symbols:
        try:
            data = fetch_yahoo_news(sym, count=5)
            for item in data.get("items", []):
                title = item.get("title") or ""
                key = title.lower()
                if title and key not in seen:
                    seen.add(key)
                    item["querySymbol"] = sym
                    items.append(item)
        except Exception as e:
            errors.append(f"{sym}: {str(e)[:80]}")
    def relevance(item):
        title = (item.get("title") or "").lower()
        score = 0
        for word in ["semiconductor", "chip", "chips", "ai", "meta", "cloud", "capex", "compute", "nvidia", "applied materials", "lam", "kla", "sox", "selloff", "plunge", "collapse", "rotation"]:
            if word in title:
                score += 2
        for word in ["league tables", "adds", "etf"]:
            if word in title:
                score -= 1
        return score
    items = sorted(items, key=relevance, reverse=True)[:8]
    titles = "；".join([x.get("title", "") for x in items])
    semis = (sec.get("groups") or {}).get("Semiconductor")
    defensive = (sec.get("groups") or {}).get("Defensive")
    ch = q.get("changePct") if isinstance(q.get("changePct"), (int, float)) else None
    ratio = vol_ctx.get("ratio") if isinstance(vol_ctx.get("ratio"), (int, float)) else None
    keywords = {
        "AI capex / overbuild": ["AI", "cloud", "Meta", "capex", "compute", "spending", "infrastructure"],
        "Semiconductor selloff": ["chip", "semiconductor", "SOX", "Nvidia", "Micron", "Applied Materials", "Lam", "KLA"],
        "Rotation / defensives": ["rotation", "defensive", "software", "health care", "consumer staples"],
        "Macro / jobs / rates": ["jobs", "payroll", "Fed", "rates", "yield", "Treasury"],
    }
    matched = []
    for label, words in keywords.items():
        if any(w.lower() in titles.lower() for w in words):
            matched.append(label)
    if not matched and isinstance(semis, (int, float)) and isinstance(defensive, (int, float)) and semis < defensive - 1:
        matched.append("Rotation / defensives")
    if not matched:
        matched.append("Ticker-specific news sparse")
    if isinstance(ch, (int, float)) and ch < -5 and isinstance(semis, (int, float)) and semis < -2:
        impact = "价格和板块已经承认负面叙事：半导体被卖，防御板块相对强。"
        score = 3.8
    elif isinstance(ch, (int, float)) and ch > 3:
        impact = "价格暂时没有承认负面叙事，或市场正在交易利空钝化/反弹修复。"
        score = 5.5
    else:
        impact = "市场反应仍需结合量能和尾盘位置确认，不能只凭标题判断。"
        score = 5
    main_story = " / ".join(matched[:3])
    top_titles = [x.get("title") for x in items[:3] if x.get("title")]
    if top_titles:
        evidence = "主要新闻：" + "；".join(top_titles)
    elif errors:
        evidence = "新闻抓取失败：" + "；".join(errors[:3])
    else:
        evidence = "新闻源没有返回足够标题；本维度退回价格、量能、板块反应。"
    read = f"今天主消息线索：{main_story}。{impact}"
    return {
        "available": bool(items),
        "source": "Yahoo Finance search news",
        "score": score,
        "mainStoryCN": main_story,
        "summaryCN": read,
        "observationCN": f"{read} 量能比={ratio}，Semiconductor={semis}%，Defensive={defensive}%。",
        "evidenceCN": evidence,
        "riskCN": "新闻标题本身不等于交易信号；只有价格、量能和权重股共同承认，新闻才真正进入战场。",
        "actionCN": "先看市场是否继续承认这条叙事：半导体能否止跌、权重股能否修复、反弹是否放量。",
        "items": items,
        "errors": errors,
    }


def earnings_calendar_context(ticker, mode="live"):
    """Translate one shared provider calendar into the ETF's earnings-risk window."""
    symbol=ticker.upper()
    holdings=ETF_HOLDINGS.get(symbol) or [(symbol, 100)]
    weight_map={str(item).upper():float(weight) for item,weight in holdings}
    tracked_symbols=list(weight_map)
    if mode == "replay":
        return {
            "available":False,
            "source":"Replay safety rule",
            "asOf":None,
            "riskLevel":"UNCONFIRMED",
            "events":[],
            "trackedSymbols":tracked_symbols,
            "reasonCN":"Replay不调用今天的未来财报日历，避免把后来才知道的日期泄漏进历史判断；只有原快照保存的日历才可使用。",
            "reasonEN":"Replay does not query today's future earnings calendar; only calendar data stored in the original snapshot may be used.",
        }
    raw=fetch_earnings_calendar(tracked_symbols, horizon="3month")
    today=datetime.now(ZoneInfo("America/New_York")).date()
    enriched=[]
    for item in raw.get("events", []):
        try:
            report_date=pd.to_datetime(item.get("reportDate")).date()
        except Exception:
            continue
        days=(report_date-today).days
        if days < 0:
            continue
        weight=weight_map.get(str(item.get("symbol") or "").upper(), 0)
        enriched.append({**item,"daysUntil":days,"trackedWeightPct":round2(weight)})
    enriched.sort(key=lambda x:(x.get("daysUntil",9999),-float(x.get("trackedWeightPct") or 0),x.get("symbol") or ""))
    next_event=enriched[0] if enriched else None
    next_7_weight=round2(sum(float(item.get("trackedWeightPct") or 0) for item in enriched if item.get("daysUntil",9999) <= 7))
    next_3_weight=round2(sum(float(item.get("trackedWeightPct") or 0) for item in enriched if item.get("daysUntil",9999) <= 3))
    if not raw.get("available"):
        risk="UNCONFIRMED"
    elif next_event is None:
        risk="NO EVENT IN 3-MONTH WINDOW"
    elif next_event["daysUntil"] <= 2 or next_3_weight >= 10:
        risk="HIGH"
    elif next_event["daysUntil"] <= 7 or next_7_weight >= 15:
        risk="ELEVATED"
    elif next_event["daysUntil"] <= 14:
        risk="WATCH"
    else:
        risk="LOW"
    critical=risk == "HIGH"
    if next_event:
        next_cn=f"最近事件：{next_event['symbol']}，预计 {next_event['reportDate']}，距今 {next_event['daysUntil']} 个日历日，跟踪权重约 {next_event['trackedWeightPct']}%。"
        next_en=f"Next event: {next_event['symbol']} on {next_event['reportDate']} in {next_event['daysUntil']} calendar days; tracked weight {next_event['trackedWeightPct']}%."
    elif raw.get("available"):
        next_cn="未来3个月的已连接日历没有返回这些关键权重股的预定财报。"
        next_en="The connected three-month calendar returned no scheduled event for the tracked constituents."
    else:
        next_cn=f"财报日期未确认：{raw.get('reason') or '数据源不可用'}"
        next_en=f"Earnings dates are unconfirmed: {raw.get('reason') or 'provider unavailable'}"
    action_cn=(
        "进入财报高风险窗：禁止把事件前波动当趋势确认；新增仓位必须降级为观察，保留财报跳空风险预算。"
        if critical else
        "未来一周存在关键财报：方向仓位需要更强确认，避免在结果公布前消耗全部现金纵深。"
        if risk == "ELEVATED" else
        "财报风险处于观察层；继续按价格、量能、领导力和账户风险执行。"
    )
    action_en=(
        "High-risk earnings window: do not treat pre-event movement as trend confirmation. Downgrade additions to observation and preserve gap-risk capacity."
        if critical else
        "A key report is due within one week. Require stronger confirmation and preserve cash depth before the release."
        if risk == "ELEVATED" else
        "Earnings risk remains a watch layer; execute from price, volume, leadership, and account risk."
    )
    return {
        "available":bool(raw.get("available")),
        "source":raw.get("source"),
        "asOf":raw.get("asOf"),
        "horizon":raw.get("horizon"),
        "riskLevel":risk,
        "isCriticalWindow":critical,
        "requiresWaiting":critical,
        "nextEvent":next_event,
        "events":enriched[:12],
        "trackedSymbols":tracked_symbols,
        "trackedWeightCoveragePct":round2(sum(weight_map.values())),
        "weightReportingWithin3DaysPct":next_3_weight,
        "weightReportingWithin7DaysPct":next_7_weight,
        "summaryCN":next_cn,
        "summaryEN":next_en,
        "actionCN":action_cn,
        "actionEN":action_en,
        "timeNoteCN":"盘前/盘后只有在数据源明确提供时才显示；否则标记为未提供，不推测。",
        "timeNoteEN":"Pre-market/after-hours timing is shown only when the provider supplies it; otherwise it remains unconfirmed.",
        "reasonCN":None if raw.get("available") else next_cn,
        "reasonEN":None if raw.get("available") else next_en,
    }


def smart_money(df, q, vol_ctx=None):
    ch = q.get("changePct") or 0
    vol = float(df.iloc[-1].VOL_RATIO or 1)
    vol_ctx = vol_ctx or {}
    if ch < -2 and vol > 1.1:
        smart = "聪明钱在降风险，不急着接飞刀；它更像先把仓位缩小，等恐慌释放后再看有没有便宜筹码。"
        institution = "机构在做两件事：卖掉弹性太大的仓位，保留核心仓位观察板块是否继续破位。"
        retail = "散户更容易在下跌里恐慌割肉，或者在第一根急反弹里冲进去想抄底。"
        funds = "主动基金倾向先降 beta，被动资金只按指数权重流动，所以不会主动救场。"
        dealer = "做市商会顺着波动调仓，盘中容易把跌势或反抽都放大。"
        leveraged = "杠杆资金最危险，很多不是想卖，而是被波动和保证金逼着卖。"
        etf_flow = "ETF资金如果继续净流出，会让权重股压力传导到整个篮子；这时不是个股问题，是篮子被卖。"
    elif ch > 2 and vol > 1.1:
        smart = "聪明钱开始试探性回补，但通常不是一口气打满；它会先看回踩能不能缩量守住。"
        institution = "机构更像在做选择性加仓：买回强权重，暂时不碰还没修复的弱票。"
        retail = "散户容易被上涨带出FOMO，越涨越想追，但真正好的信号是回踩不破。"
        funds = "主动基金会追相对强弱，被动资金若遇到指数买盘，会把权重股继续往上推。"
        dealer = "做市商可能在突破时被迫对冲，短线会放大上涨，但也会让回落更快。"
        leveraged = "杠杆资金会回来试仓，但只要波动一放大，撤得也会很快。"
        etf_flow = "ETF资金如果同步流入，说明不是单一股票自救，而是板块级资金回补。"
    elif vol <= 0.8:
        smart = "聪明钱大多在等，没有明显抢筹，也没有明显砸盘；这是一种观望，不是确认。"
        institution = "机构像是在等下一个放量方向：不急着买，也不急着把牌全摊开。"
        retail = "散户容易被盘中小波动带节奏，看见红就追，看见绿就怕。"
        funds = "主动基金更多是在调结构，被动资金没有给出强方向。"
        dealer = "做市商主要跟随波动做库存管理，方向感不强。"
        leveraged = "杠杆资金会轻仓试探，但还没有形成集体进攻。"
        etf_flow = "ETF资金更像局部腾挪，暂时看不出大规模流入或撤退。"
    else:
        smart = "聪明钱没有强烈表态，更多是在等结构确认：等价格、量能和尾盘位置给出同一个答案。"
        institution = "机构在观察承接质量，不会只因为一根K线就改变仓位级别。"
        retail = "散户容易被短线噪音牵着走，今天的核心不是情绪，而是纪律。"
        funds = "主动基金看相对强弱，被动基金跟随指数权重，整体更像选择性调仓。"
        dealer = "做市商更关心波动和期权仓位，容易放大短线波动，但不代表真实趋势。"
        leveraged = "杠杆资金还没形成一致进攻，更多是在等待低风险的方向确认。"
        etf_flow = "ETF资金需要看权重股是否同步，如果只是一两个权重撑住，板块质量仍然有限。"
    return {
        "smartMoney": smart,
        "nextMove": (vol_ctx or {}).get("nextMoveCN", "资金大概率继续等价格、量能和尾盘位置给出同一个方向。"),
        "institution": institution,
        "retail": retail,
        "funds": funds,
        "dealerMM": dealer,
        "leveraged": leveraged,
        "etfFlow": etf_flow,
    }


def weekly_analysis(wdf):
    last = wdf.iloc[-1]
    ema20 = round2(last.EMA20)
    ema50 = round2(last.EMA50)
    if last.Close < last.EMA20:
        level_text = f"周线EMA20约 {ema20}、EMA50约 {ema50}。当前已经低于EMA20，属于中期结构警报；后续重点是能否重新收回，而不是继续使用‘仍在均线上方’的条件句。"
    else:
        level_text = f"周线EMA20约 {ema20}、EMA50约 {ema50}。当前仍在EMA20上方，属于趋势测试；跌破后不能收回才升级为结构警报。"
    return {
        "trend": trend_label(wdf),
        "analysisCN": f"本周截至当前价格为 {round2(last.Close)}（本周K线尚未收盘），趋势暂定为 {trend_label(wdf)}。这部分主要用于判断中期结构是否遭到破坏，不用于预测下一周涨跌。",
        "keyLevelsCN": level_text,
        "riskCN": "如果日线反弹但周线继续放量下跌，说明中期资金在松动。",
        "conclusionCN": "周线继续保留，但不允许用周线替代入场确认。",
    }


def monthly_analysis(mdf):
    last = mdf.iloc[-1]
    return {
        "trend": trend_label(mdf),
        "analysisCN": f"本月截至当前价格为 {round2(last.Close)}（本月K线尚未收盘），大周期暂定为 {trend_label(mdf)}。月线负责判断牛熊大结构是否结束。",
        "keyLevelsCN": f"月线EMA20约 {round2(last.EMA20)}，EMA50约 {round2(last.EMA50)}。大周期仍强时，短线暴跌更多是风险重定价；月线转弱时，才是战略级降仓。",
        "riskCN": "月线上涨斜率越陡，回撤时越要检查长期资金是否继续承接。",
        "conclusionCN": "月线不是买点工具，是判断战场是否换时代的工具。",
    }


def dimensions(df, q, fg, mac, sec, smart, fib, vol_ctx, options_ctx=None, news_ctx=None):
    last = df.iloc[-1]
    ch = q.get("changePct") or 0
    vol_ratio = round2(last.VOL_RATIO)
    technical_score = 5 + (1 if last.Close > last.EMA20 else -1) + (1 if last.Close > last.EMA50 else -1)
    technical_score += 0.5 if last.MACD > last.MACD_SIGNAL else -0.5
    fg_score = fg["score"] or 50
    macd_state = "MACD在Signal上方，说明动能线已经重新压过慢线，短线修复更有可信度。" if last.MACD > last.MACD_SIGNAL else "MACD仍在Signal下方，说明价格虽然可能反弹，但动能还没有完全夺回主动权。"
    if last.Close > last.EMA20 and last.Close > last.EMA50 and last.MACD > last.MACD_SIGNAL and isinstance(vol_ctx.get("ratio"), (int, float)) and vol_ctx.get("ratio") >= 1:
        technical_picture = "画面上更像买盘重新组织进攻：价格站在线上，动能配合，量能至少不拖后腿。"
    elif last.Close > last.EMA20 and last.Close > last.EMA50:
        technical_picture = "画面上是价格先冲到有利位置，但动能和量能还没有完全跟上；这更像修复中的战场，不是已经确认的总攻。"
    elif last.Close > last.EMA20:
        technical_picture = "画面上是短线先修复，但中期结构仍要观察；价格只是夺回前沿阵地，还没拿下纵深。"
    else:
        technical_picture = "画面上仍偏防守：价格还没有夺回关键均线，反弹容易被当成降低风险的机会。"

    name_cn = {
        "Technical": "技术面",
        "Sentiment": "情绪面",
        "Money Flow": "资金流",
        "Fundamentals": "基本面",
        "Sector Rotation": "板块轮动",
        "Macro": "宏观",
        "Smart Money": "聪明钱",
        "Retail": "散户",
        "Options": "期权",
        "News Interpretation": "消息解读",
    }

    def d(name, score, observation, evidence, risk, action):
        clipped = round2(max(0, min(10, score)))
        state = "support" if clipped >= 7 else "defense" if clipped <= 4 else "watch"
        insight = dimension_insight(name, clipped, state)
        return {
            "name": name,
            "nameCN": name_cn.get(name, name),
            "score": clipped,
            "insightCN": insight,
            "observationCN": observation,
            "evidenceCN": evidence,
            "riskCN": risk,
            "actionCN": action,
        }

    def dimension_insight(name, score, state):
        close = round2(last.Close)
        ema20 = round2(last.EMA20)
        ema50 = round2(last.EMA50)
        macd_gap = round2(last.MACD - last.MACD_SIGNAL)
        volume_state = "放量" if isinstance(vol_ctx.get("ratio"), (int, float)) and vol_ctx.get("ratio") >= 1.15 else "缩量/正常量"
        sector_mode = sec.get("mode", "Unknown")
        macro_status = mac.get("status", "Unknown")
        fg_delta = fg.get("delta")
        rate_range = (mac.get("fedPolicy") or {}).get("currentTargetRange", "待确认")
        rate_expect = (mac.get("fedPolicy") or {}).get("expectedCuts2026", "待确认")
        templates = {
            "Technical": {
                "support": f"技术面结论：价格已经重新站到关键均线体系上方，Close={close}，EMA20={ema20}，EMA50={ema50}，MACD差值={macd_gap}；这说明短线承接开始被市场接受，但仍要用回踩不破和成交量确认，不适合因为一根修复K线直接满仓。",
                "watch": f"技术面结论：结构还在修复和防守之间，Close={close}，EMA20={ema20}，EMA50={ema50}，MACD差值={macd_gap}；现在最重要的不是猜方向，而是看价格能不能重新站稳EMA20，并且回落时不再放量。",
                "defense": f"技术面结论：价格仍没有夺回关键均线，Close={close}，EMA20={ema20}，EMA50={ema50}，MACD差值={macd_gap}；这类结构里反弹更像减压，不是确认反转，除非后续出现放量站回和尾盘承接。",
            },
            "Sentiment": {
                "support": f"情绪面结论：Fear & Greed={fg_score}/{fg.get('label')}，Delta={fg_delta}；情绪如果从低位修复，说明恐慌在降温，但修复初期常常只是空头回补，需要价格和量能证明资金真的回来。",
                "watch": f"情绪面结论：Fear & Greed={fg_score}/{fg.get('label')}，Delta={fg_delta}；情绪没有强到能单独支持进攻，也没有坏到只能防守，重点看它接下来是继续恶化，还是在坏消息里不再下探。",
                "defense": f"情绪面结论：Fear & Greed={fg_score}/{fg.get('label')}，Delta={fg_delta}；市场温度偏冷时，第一根反弹很容易来自恐慌后的技术修复，不代表风险已经解除，仓位要先轻后重。",
            },
            "Money Flow": {
                "support": f"资金流结论：当天变化={ch}%，量能状态={volume_state}，量能比={vol_ratio}；如果上涨伴随有效放量，说明资金愿意重新付价，但仍要确认不是单日抢反弹。",
                "watch": f"资金流结论：当天变化={ch}%，量能状态={volume_state}，量能比={vol_ratio}；现在资金没有给出压倒性答案，必须继续看后续1-2天是否放量修复，或下跌时量能是否继续扩大。",
                "defense": f"资金流结论：当天变化={ch}%，量能状态={volume_state}，量能比={vol_ratio}；如果下跌有量、反弹无量，说明主动买盘还没回来，不能只因为价格便宜就提前进攻。",
            },
            "Fundamentals": {
                "support": "基本面结论：长期叙事没有被单日波动推翻，但当前版本还未接入PE、盈利修正和财报预期；因此基本面只能作为背景支持，不能当作今天的入场许可。",
                "watch": "基本面结论：公司/行业长期逻辑仍需要和估值、盈利修正一起看；在数据未接入前，这一维只能提醒不要把短线K线误读成基本面已经改变。",
                "defense": "基本面结论：高估值资产在风险重定价时会先被压估值，再慢慢找理由；没有盈利上修或估值缓冲时，基本面不能抵消技术和资金面的压力。",
            },
            "Sector Rotation": {
                "support": f"板块轮动结论：Sector mode={sector_mode}；如果半导体和成长股强于大盘，SOXL的反弹质量会更好，因为资金不是只救一个ticker，而是在扩散到整条进攻线。",
                "watch": f"板块轮动结论：Sector mode={sector_mode}；目前还不能确认资金全面Risk-On，需要继续比较SMH/SOXX、QQQ、SPY以及防御板块的相对强弱。",
                "defense": f"板块轮动结论：Sector mode={sector_mode}；如果半导体弱于大盘，即使SOXL出现单日反弹，也更像杠杆波动，不像板块主线重新拿回主动权。",
            },
            "Macro": {
                "support": f"宏观结论：宏观状态={macro_status}，当前联邦基金目标区间约{rate_range}，2026降息预期={rate_expect}；如果利率和美元没有继续施压，科技和半导体的估值压力会减轻，但高利率环境仍要求反弹必须有真实业绩和资金承接。",
                "watch": f"宏观结论：宏观状态={macro_status}，当前联邦基金目标区间约{rate_range}，2026降息预期={rate_expect}；这不是强顺风，只能算暂时没有继续恶化。半导体对利率敏感，所以要观察TLT、美元和VIX是否再次同时压上来。",
                "defense": f"宏观结论：宏观状态={macro_status}，当前联邦基金目标区间约{rate_range}，2026降息预期={rate_expect}；如果降息预期落空或利率重新上行，SOXL会同时承受估值压缩和杠杆波动放大，仓位必须更保守。",
            },
            "Smart Money": {
                "support": "聪明钱结论：真正有耐心的资金不会只看一根反弹K线，它会等权重股、板块、尾盘承接和成交量同时改善；如果这些线索共振，才说明机构资金开始重新组织进攻。",
                "watch": "聪明钱结论：现在更像等待确认的阶段，大资金会先观察卖压是否减弱，而不是急着替市场证明底部；重点看尾盘是否有人接、回踩是否缩量。",
                "defense": "聪明钱结论：如果权重股拖累、尾盘走弱、反弹缩量同时出现，说明大资金仍在降低风险；这种环境里散户越急，越容易接到二次下杀。",
            },
            "Retail": {
                "support": "散户结论：即使环境改善，也不能把FOMO当成信号；散户最该做的是等清单确认后分批，而不是在第一根强反弹里一次性追满。",
                "watch": "散户结论：现在最容易犯的错是跌的时候想割、弹的时候想追；这一维提醒你把情绪延迟一拍，用观察清单替代即时冲动。",
                "defense": "散户结论：当前更容易出现恐慌割肉或冲动抄底，两边都可能错；如果没有明确作废条件和仓位上限，就不该行动。",
            },
            "Options": {
                "support": f"期权结论：{(options_ctx or {}).get('summaryCN', '期权链暂不可用，短线Gamma和Dealer定位仍要打折。')}",
                "watch": f"期权结论：{(options_ctx or {}).get('summaryCN', '期权链暂不可用，短线Gamma和Dealer定位仍要打折。')}",
                "defense": f"期权结论：{(options_ctx or {}).get('summaryCN', '期权链暂不可用，短线Gamma和Dealer定位仍要打折。')}",
            },
            "News Interpretation": {
                "support": f"消息解读结论：{(news_ctx or {}).get('summaryCN', '新闻源暂不可用，先用价格、量能和板块反应判断市场是否承认叙事。')}",
                "watch": f"消息解读结论：{(news_ctx or {}).get('summaryCN', '新闻源暂不可用，先用价格、量能和板块反应判断市场是否承认叙事。')}",
                "defense": f"消息解读结论：{(news_ctx or {}).get('summaryCN', '新闻源暂不可用，先用价格、量能和板块反应判断市场是否承认叙事。')}",
            },
        }
        return templates.get(name, {}).get(state, f"{name_cn.get(name, name)}结论：当前分数为{score}/10，需要结合观察、证据、风险和动作一起判断。")

    return [
        d("Technical", technical_score, f"技术面现在不是给买点，而是在回答承接有没有被市场接受。Close={round2(last.Close)}，EMA20={round2(last.EMA20)}，EMA50={round2(last.EMA50)}；价格离EMA20约 {pct(last.Close, last.EMA20)}%，说明短线位置已经接近关键战壕。{macd_state} {technical_picture} {vol_ctx.get('headlineCN')}", f"RSI7={round2(last.RSI7)}；RSI14={round2(last.RSI14)}；MACD={round2(last.MACD)}；Signal={round2(last.MACD_SIGNAL)}；MACD差值={round2(last.MACD - last.MACD_SIGNAL)}；{fib.get('summaryCN')}", "如果价格站上均线但MACD不跟、成交量不跟，容易变成假修复；如果反弹不能重新站回EMA20，容易横盘消化或二次下杀。", "先看EMA20、成交量、MACD方向和权重股是否同步确认；不是第一根不能做，而是条件没齐就不急着承担新风险。"),
        d("Sentiment", fg_score / 10, f"情绪读数 {fg_score} / {fg['label']}。重点不是Fear或Greed这个标签，而是分数为什么被压低、有没有继续恶化、以及市场是否已经对坏情绪麻木。", f"主要异常项：{', '.join([x['factor'] for x in fg.get('mainDrivers', [])[:3]])}；Delta={fg.get('delta')}", "情绪快速降温时，第一根反弹经常只是空头回补。", "等情绪不再恶化，再考虑从Market Vacation切到Tactical。"),
        d("Money Flow", 5 + min(1.5, max(-1.5, ch / 4)), f"{vol_ctx.get('headlineCN')} {vol_ctx.get('moneyActionCN')}", f"Volume={vol_ctx.get('volume')}；20D Avg={vol_ctx.get('avg20')}；Volume ratio={vol_ratio}；Price change={ch}%；{smart.get('smartMoney')}", "如果反弹缩量，说明资金没有真正回来；如果下跌放量，说明卖盘还没释放干净。", "观察后续1-2天是否放量修复，并检查资金是否按预期选择方向。"),
        d("Fundamentals", 5, "基本面没有被单日K线直接推翻，但高估值资产遇到风险重定价时，市场会先砍估值，再慢慢找理由。这个维度今天更多是背景，不是入场许可。", "当前未接PE/PEG/earnings revision，基本面只作为背景层。", "基本面空白会让长周期判断偏保守。", "不把基本面当作当天入场理由。"),
        d("Sector Rotation", 5.5, f"{sec.get('flowCN')} 这说明今天不是只看一个ticker，而要看进攻资金有没有在板块里扩散。", f"板块模式：{sec['mode']}；最强：{sec['strongest']['name']} {sec['strongest']['changePct']}%；最弱：{sec['weakest']['name']} {sec['weakest']['changePct']}%。", "如果半导体弱于大盘，SOXL的反弹质量会下降。", "确认SMH/SOXX是否重新强于QQQ/SPY。"),
        d("Macro", 5 if mac["status"] == "Macro Neutral" else 4, f"宏观状态：{mac['status']}。宏观不是今天唯一矛盾，但它决定风险资产有没有顺风；如果利率、美元、油价和VIX一起施压，技术修复会明显更吃力。{mac.get('vixNoteCN')} {mac.get('rateNoteCN')}", f"观察TLT/UUP/GLD/USO/VIX是否同步给压力。利率层面：{(mac.get('fedPolicy') or {}).get('officialBiasCN')} 当前目标区间={(mac.get('fedPolicy') or {}).get('currentTargetRange')}；2026降息预期={(mac.get('fedPolicy') or {}).get('expectedCuts2026')}。", f"美元、利率、油和VIX同时压上来时，技术反弹容易失败。{(mac.get('fedPolicy') or {}).get('semiconductorImpactCN')}", "宏观没有转好前，仓位保持轻；如果降息预期继续落空，半导体反弹要更重视量能、权重股和尾盘承接。"),
        d("Smart Money", 5, f"聪明钱没有必要抢第一根反弹，它会等权重股、板块、量能和尾盘承接共同确认。{smart.get('nextMove')}", smart["smartMoney"], "真正有耐心的资金不会急着替市场证明底部。", "等板块共振和尾盘承接。"),
        d("Retail", 5, "散户在这种大波动日最容易两边犯错：跌的时候恐慌，弹的时候FOMO。越是看起来快要错过，越要回到清单。", smart["retail"], "过早抄底容易被第二波杀伤。", "用清单交易，不用情绪交易。"),
        d("Options", (options_ctx or {}).get("score", 4.5), (options_ctx or {}).get("observationCN", "期权链暂时不可用，短线Gamma和Dealer定位仍要打折。"), (options_ctx or {}).get("evidenceCN", "Options data unavailable."), (options_ctx or {}).get("riskCN", "缺少期权维度时，不能对盘中反转信号太自信。"), (options_ctx or {}).get("actionCN", "暂时降低短线结论权重。")),
        d("News Interpretation", (news_ctx or {}).get("score", 5), (news_ctx or {}).get("observationCN", "新闻源暂不可用，先用价格、量能和板块反应判断市场是否承认叙事。"), (news_ctx or {}).get("evidenceCN", "News data unavailable."), (news_ctx or {}).get("riskCN", "新闻标题本身不等于交易信号；只有价格、量能和权重股共同承认，新闻才真正进入战场。"), (news_ctx or {}).get("actionCN", "先看盘，再解读，最后布局。")),
    ]


def warrior_doctrine(df, q, fg, mac, smart, fib, vol_ctx, reward_risk, vacation):
    last = df.iloc[-1]
    ch = q.get("changePct") or 0
    vol_ratio = (vol_ctx or {}).get("ratio")
    vol_ratio = vol_ratio if isinstance(vol_ratio, (int, float)) else float(last.VOL_RATIO or 1)
    vix = (mac.get("vix") or {}).get("last")
    terrain_ok = last.Close > last.EMA20 and last.Close > last.EMA50
    support_text = fib.get("summaryCN", "关键地形需要继续观察。")

    dao_score = 7 if not vacation else 4.5
    tian_score = 6 if mac.get("status") == "Macro Neutral" else 4
    if isinstance(vix, (int, float)) and vix < 18:
        tian_score += 0.8
    di_score = 6.5 if terrain_ok else 4.5 if last.Close > last.EMA20 else 3.8
    jiang_score = 6 if ch > 0 and vol_ratio >= 0.8 else 4.5
    fa_score = 7 if reward_risk and reward_risk >= 1.35 and not vacation else 5 if reward_risk and reward_risk >= 1 else 4

    items = [
        {
            "nameCN": "道",
            "nameEN": "Doctrine",
            "score": round2(dao_score),
            "readCN": "道是这一仗的核心原则：我们是否顺着市场真实状态，而不是顺着自己的愿望。"
            + (" 当前允许战术参与，但新增风险仍要服从确认条件。" if not vacation else " 当前仍偏Market Vacation，先求不输，再谈进攻。"),
            "evidenceCN": f"MMF Score={fg.get('score')}；Market Vacation={'YES' if vacation else 'NO'}；Reward/Risk={reward_risk}。",
            "actionCN": "先解读，再布局；只在市场承认方向时加仓。",
        },
        {
            "nameCN": "天",
            "nameEN": "Weather",
            "score": round2(tian_score),
            "readCN": f"天是宏观天气和时间窗口。{mac.get('interpretationCN')} {mac.get('vixNoteCN')}",
            "evidenceCN": f"Macro={mac.get('status')}；VIX={vix if vix is not None else '--'}。",
            "actionCN": "宏观不逆风时才扩大动作；遇到事件风险先降节奏。",
        },
        {
            "nameCN": "地",
            "nameEN": "Terrain",
            "score": round2(di_score),
            "readCN": "地是价格地形：均线、支撑、阻力和Fib共振区决定进退路线。" + support_text,
            "evidenceCN": f"Close={round2(last.Close)}；EMA20={round2(last.EMA20)}；EMA50={round2(last.EMA50)}。",
            "actionCN": "上方压力区不追，回踩防线不破再考虑试仓。",
        },
        {
            "nameCN": "将",
            "nameEN": "Commanders",
            "score": round2(jiang_score),
            "readCN": "将是各路资金主将：聪明钱、机构、散户、杠杆和ETF资金谁在掌控节奏。" + smart.get("smartMoney", ""),
            "evidenceCN": f"{vol_ctx.get('headlineCN')} {smart.get('nextMove')}",
            "actionCN": "跟随有纪律的资金，不跟随散户FOMO。",
        },
        {
            "nameCN": "法",
            "nameEN": "Discipline",
            "score": round2(fa_score),
            "readCN": "法是交易纪律：仓位、作废条件、现金比例和明日清单。没有纪律，方向看对也可能输。",
            "evidenceCN": f"Reward/Risk={reward_risk}；量能比={round2(vol_ratio)}；当日变化={ch}%。",
            "actionCN": "仓位服从赔率和作废条件；条件不成熟就保留现金。",
        },
    ]
    avg = round2(sum(x["score"] for x in items) / len(items))
    if avg >= 6.5:
        summary = "五事整体偏顺，可以保持战术观察，但进攻仍要等价格、量能和资金角色同向。"
    elif avg >= 5:
        summary = "五事参差，适合小仓侦察或继续等待，不适合重仓证明观点。"
    else:
        summary = "五事未齐，当前更像保存兵力的阶段；现金是下一次作战能力。"
    return {"title": "战争五事 · 道天地将法", "summaryCN": summary, "score": avg, "items": items}


def scenario_engine(df, q, vol_ctx=None):
    last = df.iloc[-1]
    ema20 = round2(last.EMA20)
    low20 = round2(df.tail(20).Low.min())
    current = float(q.get("close") or q.get("last") or last.Close)
    near_reclaim = round2(current * 1.045)
    trend_reference = f"先收复近端反弹确认位 {near_reclaim}；日线EMA20 {ema20} 仅是中期趋势修复参考" if ema20 and ema20 > current * 1.2 else f"放量站回EMA20附近 {ema20}"
    ch = q.get("changePct") if isinstance(q.get("changePct"), (int, float)) else 0
    volume_available = bool((vol_ctx or {}).get("available"))
    ratio = (vol_ctx or {}).get("ratio") if volume_available else None
    ratio = ratio if isinstance(ratio, (int, float)) else None
    base_prob, bull_prob, bear_prob, tail_prob = 45, 25, 20, 10
    volume_note = (vol_ctx or {}).get("headlineCN", "量能线索还不完整，先看价格是否被后续K线确认。")

    if not volume_available:
        base_why = "当前时段缺少可靠成交量，情景概率不使用缩量/放量信号；先等待常规时段确认。"
        bull_why = "价格反弹仍需常规时段量能与权重股确认。"
        bear_why = "价格破位需要有效成交量确认，当前不能用0成交量降低风险判断。"
    elif isinstance(ratio, (int, float)) and ratio >= 1.35 and ch > 1:
        bull_prob += 8
        base_prob -= 5
        bear_prob -= 3
        base_why = "放量上涨让趋势修复概率上升，但仍需要回踩确认，不能把第一天直接当成胜利。"
        bull_why = "买盘愿意付价，量能也承认了方向；下一步看回踩是否缩量守住EMA20/VWAP。"
        bear_why = "二次下杀概率下降，但如果放量后无法延续，今天可能只是高位换手。"
    elif isinstance(ratio, (int, float)) and ratio >= 1.35 and ch < -1:
        bear_prob += 10
        base_prob -= 6
        bull_prob -= 4
        base_why = "放量下跌说明卖盘被市场承认，震荡消化仍可能发生，但要先看到卖压放缓。"
        bull_why = "趋势修复需要更高门槛：不仅要站回EMA20，还要看到权重股和量能一起反转。"
        bear_why = "卖盘带量出现，说明二次下杀不是尾部风险，而是需要认真防守的主路径之一。"
    elif isinstance(ratio, (int, float)) and ratio <= 0.8:
        base_prob += 8
        bull_prob -= 3
        bear_prob -= 3
        tail_prob -= 2
        base_why = "缩量说明大资金还没有强表态，最常见路径是继续震荡，等下一次放量选择方向。"
        bull_why = "缺少量能配合，趋势修复即使出现也需要更多确认，不能追着小波动跑。"
        bear_why = "缩量下跌未必是真砸盘，但跌破关键位后仍要立刻防守。"
    else:
        base_why = "低点暂未破，但反弹也没有放量突破。"
        bull_why = "需要EMA20、权重股和板块同步确认。"
        bear_why = "如果卖盘继续被量能承认，会触发二次下杀。"

    return [
        {"name": "Base / 震荡消化", "probability": base_prob, "whyCN": f"{base_why} {volume_note}", "conditionCN": "守住低点，量能不继续恶化。", "invalidCN": "放量跌破近期低点，或放量站回EMA20并守住。", "watchCN": f"守住 {low20} 上方，反弹有没有量。", "responseCN": "继续观察，不急着证明方向。"},
        {"name": "Bull / 趋势修复", "probability": bull_prob, "whyCN": bull_why, "conditionCN": f"{trend_reference}，同时板块和权重股同步修复。", "invalidCN": "站上近端确认位后马上缩量跌回。", "watchCN": "NVDA/AVGO/SMH是否同步修复，回踩是否缩量。", "responseCN": "先确认近端结构，再谈中期均线；不是要求一天拉回EMA20。"},
        {"name": "Bear / 二次下杀", "probability": bear_prob, "whyCN": bear_why, "conditionCN": f"跌破近期低点 {low20} 且无法快速收回。", "invalidCN": "跌不动、量缩、尾盘有人接。", "watchCN": "是否放量下跌、广度恶化，以及反弹是否无量。", "responseCN": "继续Market Vacation，等恐慌释放。"},
        {"name": "Tail / 消息驱动异动", "probability": tail_prob, "whyCN": "政策、财报、利率或地缘可能突然改变市场定价；只有量能承认的消息才算真正进入战场。", "conditionCN": "出现跳空或新闻驱动，并且量能承认。", "invalidCN": "缺口快速回补，消息没有被资金承认。", "watchCN": "缺口是否守住，量能是否跟上。", "responseCN": "先别追，消息行情最容易让人忘记仓位纪律。"},
    ]


def intraday_decision(df, q, fg, sec, mac, fib, reward_risk, mmf_score, vacation, volume_structure=None):
    last = df.iloc[-1]
    current = float(q.get("close") or q.get("last") or last.Close)
    ch = q.get("changePct") if isinstance(q.get("changePct"), (int, float)) else 0
    prev_close = q.get("prevClose") if isinstance(q.get("prevClose"), (int, float)) else None
    semis = (sec.get("groups") or {}).get("Semiconductor")
    growth = (sec.get("groups") or {}).get("Growth")
    defensive = (sec.get("groups") or {}).get("Defensive")
    vix_last = (mac.get("vix") or {}).get("last")
    trend_score = 3 if last.Close < last.EMA20 and last.MACD < last.MACD_SIGNAL else 5 if last.Close < last.EMA20 else 6.5
    if last.Close > last.EMA20 and last.MACD > last.MACD_SIGNAL:
        trend_score = 7
    breadth_score = 5
    if isinstance(semis, (int, float)) and isinstance(defensive, (int, float)):
        breadth_score = 3.5 if semis < defensive - 1 else 6 if semis > defensive + 1 else 4.5
    fear_val = fg.get("score") if isinstance(fg.get("score"), (int, float)) else 50
    fear_score = 8 if fear_val <= 20 else 6 if fear_val <= 25 else 4 if fear_val <= 35 else 3
    rr_score = round2(max(1, min(10, reward_risk * 2.2 if isinstance(reward_risk, (int, float)) else 4)))
    if trend_score <= 4 and breadth_score <= 4 and rr_score >= 6:
        rating = "★★☆☆☆"
        suggested = "5%-10%"
        state = "PARTIAL MARKET VACATION"
        decision = "可以试探性小仓，但不是抄底确认点。"
    elif trend_score >= 6 and breadth_score >= 5 and mmf_score >= 50:
        rating = "★★★☆☆"
        suggested = "10%-20%"
        state = "TACTICAL"
        decision = "可以小仓参与，但仍要等回踩确认后再加。"
    elif rr_score >= 5 and fear_score >= 5:
        rating = "★★☆☆☆"
        suggested = "5%"
        state = "PARTIAL MARKET VACATION"
        decision = "只适合观察仓，先验证承接，不把第一笔当成确认。"
    else:
        rating = "★☆☆☆☆"
        suggested = "0%-5%"
        state = "MARKET VACATION"
        decision = "暂时不急着建仓，先等趋势、广度或情绪至少有一项明显改善。"
    if vacation:
        rating = "★☆☆☆☆"
        suggested = "0%"
        state = "MARKET VACATION"
        decision = "当前风险闸门不允许新增仓位；先更新数据或等待确认，不执行试探仓。"

    lookback = df.tail(min(len(df), 252))
    hi = float(lookback.High.max())
    lo = float(lookback.Low.min())
    fib_levels = {lv: round2(hi - (hi - lo) * lv) for lv in [0.236, 0.382, 0.5, 0.618, 0.786]}
    nearest_lv = min(fib_levels, key=lambda lv: abs(current - fib_levels[lv])) if fib_levels else None
    if ch <= -12:
        nearest_text = f"最近Fib约 {nearest_lv} = {fib_levels.get(nearest_lv)}；" if nearest_lv is not None else ""
        fib_read = f"单日跌幅已经进入panic zone。{nearest_text}这类位置可以开始准备计划，但panic zone不等于趋势买点，必须等待承接和小周期结构确认。"
    elif nearest_lv is None:
        fib_read = "关键Fib区域暂时不足，先看EMA20和近20日低点。"
    elif nearest_lv >= 0.786 or current <= fib_levels.get(0.786, current) * 1.03:
        fib_read = f"价格已经靠近深度回撤区：0.786约 {fib_levels.get(0.786)}。这开始进入panic zone，但panic zone不等于趋势反转。"
    elif nearest_lv >= 0.618:
        fib_read = f"价格靠近0.618深回撤区，0.618约 {fib_levels.get(0.618)}，说明风险已经释放一部分，但还需要承接确认。"
    else:
        fib_read = f"当前最近Fib约 {nearest_lv} = {fib_levels.get(nearest_lv)}，还没有进入足够深的恐慌折价区。"

    if ch <= -12:
        event = "这不是普通回调，更像一次半导体/AI高弹性资产的risk-off冲击。"
    elif ch <= -5:
        event = "这是明显的风险释放，不宜按普通小回调处理。"
    elif ch >= 5:
        event = "这是强反弹日，但强反弹不自动等于趋势确认。"
    else:
        event = "今天更像常规波动，重点看量能和板块是否给出确认。"

    if isinstance(vix_last, (int, float)) and abs(ch) >= 8 and vix_last < 20:
        vol_note = f"VIX={vix_last}，但标的波动很大，说明这更像板块内部去杠杆/轮动，而不是全市场系统性恐慌。"
    elif isinstance(vix_last, (int, float)) and vix_last >= 22:
        vol_note = f"VIX={vix_last}，系统波动压力偏高，任何小仓都要更保守。"
    else:
        vol_note = f"VIX={vix_last if vix_last is not None else 'n/a'}，暂时没有显示系统性恐慌。"

    if isinstance(semis, (int, float)) and isinstance(defensive, (int, float)) and semis < defensive:
        breadth_note = f"板块广度偏Risk-Off：Semiconductor {semis}%，Defensive {defensive}%。资金从高beta/AI/半导体流出，防御板块相对更强。"
    else:
        breadth_note = f"板块广度仍需确认：Semiconductor {semis}%，Growth {growth}%，Defensive {defensive}%。"

    down_step = round2(current * 0.96)
    deep_step = round2(current * 0.91)
    rebound_1 = round2(current * 1.045)
    rebound_2 = round2(current * 1.075)
    action = [
        f"如果已经有观察仓，先把它当成信息仓；新增仓位仍只允许小：{suggested}，不要把试探仓当成抄底确认。",
        f"如果现价附近守住，并且反弹站回 {rebound_1}-{rebound_2} 区间，同时半导体权重股同步修复，再考虑加仓。",
        f"如果跌到 {down_step} 附近仍无承接，只观察；到 {deep_step} 附近才重新评估第二笔，而不是机械补仓。",
        "量价上最想看到：下探缩量，或放量站回关键均线后回踩缩量守住。",
        "无论哪种路径，都不要为了证明观点而急着参与第一根反弹；第一天可以参与，但必须由确认条件和账户风险允许。",
    ]
    scenarios = [
        {"name": "Scenario 1 / 继续探底后反弹", "probability": 50, "pathCN": f"{current} → {down_step} → {deep_step} 附近，随后尝试反弹到 {rebound_1}-{rebound_2}。", "responseCN": "只保留观察仓，等反弹质量确认。"},
        {"name": "Scenario 2 / 盘中投降式低点", "probability": 30, "pathCN": f"{current} 附近横住，随后回到 {rebound_1}-{rebound_2}。", "responseCN": "确认量能和权重股同步后再加，不提前满仓。"},
        {"name": "Scenario 3 / 真正破位", "probability": 20, "pathCN": f"跌破 {down_step} 后无法收回，继续向 {deep_step} 或更低区域释放。", "responseCN": "回到Market Vacation，停止加仓，等下一次确认。"},
    ]
    return {
        "title": "MMF-10 Intraday Review",
        "decisionCN": decision,
        "rating": rating,
        "suggestedPosition": suggested,
        "marketState": state,
        "scores": {
            "Trend": round2(trend_score),
            "Breadth": round2(breadth_score),
            "Fear": round2(fear_score),
            "RiskReward": rr_score,
            "MMF": mmf_score,
        },
        "eventCN": event,
        "volumeStructure": volume_structure or {},
        "breadthCN": breadth_note,
        "fibCN": fib_read,
        "volatilityCN": vol_note,
        "whyCN": f"核心问题不是单一价格便宜，而是市场正在重新回答AI/半导体的合理价格。趋势仍弱、板块广度偏防守、情绪还没到极端恐慌；但价格已经接近更值得准备的风险收益区域。",
        "actionCN": action,
        "scenarios": scenarios,
        "current": round2(current),
        "prevClose": round2(prev_close) if prev_close is not None else None,
        "changePct": round2(ch),
    }


def account_state(ticker, df, q, reward_risk, mmf_score, vacation, current_position_pct=0):
    current = float(q.get("close") or q.get("last") or 0)
    last = df.iloc[-1]
    ema20 = round2(last.EMA20)
    low20 = round2(df.tail(20).Low.min())
    pullback_7 = round2(current * 0.93) if current else None
    pullback_12 = round2(current * 0.88) if current else None
    current_position_pct = round2(clip(float(current_position_pct or 0), 0, 100))
    cash_pct = max(0, 100 - current_position_pct)
    max_new_exposure = 0 if vacation else 5
    previous_trade = None
    if current_position_pct > 0:
        state = "HOLDING"
        state_cn = "持仓观察"
        summary = f"账户已录入 {current_position_pct}% 本标的仓位；今天的问题不是继续证明买点，而是组合仓位、退出质量和剩余主动权是否仍符合计划。"
        recommendation = "先审查仓位堆叠、3×等效风险、各层使命与退出条件；达到上限后停止新增，转入退出管理。"
    else:
        state = "CASH_WAITING"
        state_cn = "现金等待"
        summary = "当前为空仓等待状态，市场分析必须转化为下一笔交易的触发条件。"
        recommendation = "先等待确认条件完成，再用小仓位启动下一笔计划。"
    triggers = [
        {"name": "回踩重新定价", "level": pullback_7, "actionCN": "只观察承接质量，不机械买回。"},
        {"name": "深回撤观察区", "level": pullback_12, "actionCN": "若缩量止跌并横住，才重新评估观察仓。"},
        {"name": "EMA20确认", "level": ema20, "actionCN": "放量站回并回踩不破，才说明第一层确认完成。"},
        {"name": "20日低点防线", "level": low20, "actionCN": "跌破后无法收回则继续现金等待。"},
    ]
    scenarios = [
        {"name": "Account Scenario 1 / 继续等待", "probability": 45, "accountCN": f"现金 {cash_pct}%，新风险 0%。", "responseCN": "保留完整选择权，等待下一次高质量机会。"},
        {"name": "Account Scenario 2 / 突破确认", "probability": 25, "accountCN": f"最多重新启动 {max_new_exposure}% 观察仓。", "responseCN": "只有放量站回关键均线、板块同步、回踩不破时才考虑。"},
        {"name": "Account Scenario 3 / 回踩给价", "probability": 20, "accountCN": "现金仍是主仓位，观察是否出现缩量承接。", "responseCN": "若风险闸门重新打开、回踩到计划区且承接真实，再按当时允许的上限设计观察仓；闸门关闭时仍为0%。"},
        {"name": "Account Scenario 4 / 暴跌释放", "probability": 10, "accountCN": "账户不受伤，现金变成进攻能力。", "responseCN": "不急着接第一刀，等恐慌释放和结构稳定。"},
    ]
    return {
        "title": "Account State / 账户状态",
        "state": state,
        "stateCN": state_cn,
        "cashPct": cash_pct,
        "currentPositionPct": current_position_pct,
        "previousTrade": previous_trade,
        "currentCampaignCN": "当前战役进行中。" if current_position_pct > 0 else "等待下一笔计划。",
        "suggestedMode": "Market Vacation / Risk Management" if vacation and current_position_pct > 0 else "Market Vacation / Waiting Next Campaign" if vacation else "Tactical Position Management" if current_position_pct > 0 else "Tactical Watch",
        "maxNewExposurePct": max_new_exposure,
        "summaryCN": summary,
        "recommendationCN": recommendation,
        "notFirstDayCN": "不要为了证明观点而急着参与第一天。第一天不是禁令，真正的问题是确认条件是否完成、账户是否需要承担新风险。",
        "triggers": triggers,
        "scenarios": scenarios,
        "rewardRisk": reward_risk,
        "mmfScore": mmf_score,
    }


def position_regime(ticker, df, q, reward_risk, mmf_score, sec, mac, volume_structure=None):
    current = float(q.get("close") or q.get("last") or 0)
    lookback = df.tail(min(len(df), 252)) if df is not None and not df.empty else None
    high_252 = float(lookback.High.max()) if lookback is not None and len(lookback) else current
    low_252 = float(lookback.Low.min()) if lookback is not None and len(lookback) else current
    discount_pct = round2((1 - current / high_252) * 100) if current and high_252 else 0
    rebound_from_low_pct = round2((current / low_252 - 1) * 100) if current and low_252 else 0
    vix_last = (mac.get("vix") or {}).get("last") if mac else None
    semis = (sec.get("groups") or {}).get("Semiconductor") if sec else None
    growth = (sec.get("groups") or {}).get("Growth") if sec else None
    defensive = (sec.get("groups") or {}).get("Defensive") if sec else None
    vol_label = (volume_structure or {}).get("labelCN") or "量价结构待确认"
    vol_score = (volume_structure or {}).get("score")

    systemic_breaks = []
    risk_warnings = []
    if isinstance(vix_last, (int, float)) and vix_last >= 25:
        systemic_breaks.append(f"VIX={vix_last}，进入系统性高波动区。")
    elif isinstance(vix_last, (int, float)) and vix_last >= 22:
        risk_warnings.append(f"VIX={vix_last}，接近系统风险警戒区，扩仓需要更严格确认。")
    if isinstance(semis, (int, float)) and isinstance(growth, (int, float)) and isinstance(defensive, (int, float)) and semis < -4 and growth < -3 and defensive < -2:
        systemic_breaks.append("半导体、成长和防御板块同步走弱，可能不只是板块去拥挤。")
    if "慢性派发" in vol_label and isinstance(vol_score, (int, float)) and vol_score <= 2:
        if isinstance(vix_last, (int, float)) and vix_last >= 22:
            systemic_breaks.append("慢性派发与系统波动警戒同时出现，扩仓需要暂停。")
        else:
            risk_warnings.append("量价结构接近连续派发；当前先视为板块风险警告，需等待卖压递减或承接确认。")

    gate_pass = not systemic_breaks
    deep_discount = discount_pct >= 45
    normal_discount = discount_pct >= 25 or (isinstance(reward_risk, (int, float)) and reward_risk >= 1.5)
    constructive_flow = isinstance(vol_score, (int, float)) and vol_score >= 5
    trend_ok = mmf_score >= 55 and constructive_flow

    if not gate_pass:
        tier = "Risk Gate Closed / 风险闸门关闭"
        default_cap, dynamic_low, dynamic_high, extension_cap = 5, 0, 15, 20
        thesis = "价格便宜不等于风险下降；系统风险或连续派发出现时，折扣可能是旧模型失效后的新价格。"
        permission = "只允许观察或降风险，不允许把赔率仓扩成深度赔率仓。"
    elif trend_ok and mmf_score >= 65:
        tier = "Trend Position / 趋势仓"
        default_cap, dynamic_low, dynamic_high, extension_cap = 35, 25, 50, 60
        thesis = "趋势和资金重新改善，仓位可以按新的风险预算计算；这已经不只是抢折扣。"
        permission = "允许从赔率仓切换为趋势仓，但必须重新设置作废条件和回撤预算。"
    elif deep_discount:
        tier = "Deep Odds Position / 深度赔率仓"
        default_cap, dynamic_low, dynamic_high, extension_cap = 25, 35, 45, 50
        thesis = "市场质量仍弱，但价格质量明显提高；当前买的不是趋势，而是市场已经支付出来的深度折扣和反弹赔率。"
        permission = "允许把普通赔率仓扩成深度赔率仓；最高50%只是条件扩展上限，不是必须打满。"
    elif normal_discount:
        tier = "Odds Position / 普通赔率仓"
        default_cap, dynamic_low, dynamic_high, extension_cap = 25, 10, 25, 35
        thesis = "赔率开始出现，但折扣还不足以把弱市场中的上限永久提高。"
        permission = "以试探和分批为主；25%是默认赔率仓上限。"
    else:
        tier = "Observation Position / 观察仓"
        default_cap, dynamic_low, dynamic_high, extension_cap = 5, 0, 5, 10
        thesis = "价格折扣和资金行为都还不够，仓位的任务是收集信息，不是证明观点。"
        permission = "只允许观察仓，等待价格、量能或风险收益重新定价。"

    gate_status = "FAIL" if not gate_pass else "CAUTION" if risk_warnings else "PASS"
    risk_gate = {
        "status": gate_status,
        "statusCN": "关闭" if gate_status == "FAIL" else "谨慎通过" if gate_status == "CAUTION" else "通过",
        "checksCN": [
            f"VIX={vix_last if vix_last is not None else 'n/a'}；22-25以上会压低扩仓许可。",
            f"Semiconductor={semis}%，Growth={growth}%，Defensive={defensive}%；判断是板块去拥挤还是全市场失控。",
            f"量价结构：{vol_label}（{vol_score if vol_score is not None else '--'}/10）。",
            "若出现行业级基本面下修、政策/出口限制、信用恶化或流动性事件，必须重算仓位层级。",
        ],
        "failReasonsCN": systemic_breaks,
        "warningsCN": risk_warnings,
    }
    return {
        "tier": tier,
        "defaultOddsCapPct": default_cap,
        "dynamicSuggestedRangePct": {"low": dynamic_low, "high": dynamic_high},
        "extensionCapPct": extension_cap,
        "trendPermission": "YES" if tier.startswith("Trend") else "NO",
        "priceDiscount": {
            "current": round2(current),
            "high252": round2(high_252),
            "low252": round2(low_252),
            "discountFrom252HighPct": discount_pct,
            "reboundFrom252LowPct": rebound_from_low_pct,
            "qualityCN": "高" if deep_discount else "中" if normal_discount else "低",
        },
        "riskRegimeGate": risk_gate,
        "thesisCN": thesis,
        "permissionCN": permission,
        "reviewQuestionsCN": [
            "为什么修改策略：因为风险收益重新定价，而不是因为亏损或怕错过。",
            "市场假设有没有变：AI/半导体基本面、系统风险和流动性事件必须持续检查。",
            "赔率有没有提高：看价格相对高点的折扣、Fib/情绪/量能，而不是主观感觉。",
            "风险有没有同步提高：SOXL波动会变大，50%不是安全仓位，只是保留一半现金后的风险预算。",
            "Plan B是否存在：若风险闸门关闭，停止扩仓并重跑MMF。",
        ],
    }


def position_engineering(ticker, df, q, reward_risk, mmf_score, sec, mac, volume_structure=None, current_position_pct=15):
    regime = position_regime(ticker, df, q, reward_risk, mmf_score, sec, mac, volume_structure)
    max_position_pct = regime["dynamicSuggestedRangePct"]["high"]
    current = float(q.get("close") or q.get("last") or 0)
    cash_pct = max(0, 100 - current_position_pct)
    volume_score = (volume_structure or {}).get("score")
    market_quality = round2((mmf_score / 10) * 0.6 + (volume_score if isinstance(volume_score, (int, float)) else 5) * 0.4)
    position_risk_score = 9 if max_position_pct <= 20 and cash_pct >= 80 else 7 if max_position_pct <= 35 else 6 if max_position_pct <= 50 and cash_pct >= 50 else 4
    rr_score = 8 if isinstance(reward_risk, (int, float)) and reward_risk >= 3 else 7 if isinstance(reward_risk, (int, float)) and reward_risk >= 1.5 else 5
    psychology_score = 10 if current_position_pct <= 20 else 8 if current_position_pct <= 35 else 5
    trade_quality = round2(position_risk_score * 0.35 + rr_score * 0.25 + psychology_score * 0.25 + min(7, market_quality) * 0.15)
    discount_pct = (regime.get("priceDiscount") or {}).get("discountFrom252HighPct") or 0
    gate_status = (regime.get("riskRegimeGate") or {}).get("status")
    gate_pass = gate_status != "FAIL"
    trend_confirmation = 4.5 if regime["trendPermission"] == "YES" else 3.0 if mmf_score >= 55 else 2.0 if mmf_score >= 40 else 1.0
    if isinstance(volume_score, (int, float)):
        trend_confirmation = clip(trend_confirmation + (0.5 if volume_score >= 6 else -0.5 if volume_score <= 3 else 0), 1, 5)
    discount_quality = 5.0 if discount_pct >= 45 else 4.0 if discount_pct >= 35 else 3.0 if discount_pct >= 25 else 2.0 if discount_pct >= 12 else 1.0
    reward_risk_quality = 5.0 if reward_risk >= 5 else 4.5 if reward_risk >= 3 else 4.0 if reward_risk >= 2 else 3.5 if reward_risk >= 1.5 else 2.0 if reward_risk >= 1 else 1.0
    flow_quality = clip((volume_score or 5) / 2, 1, 5)
    risk_regime_quality = 4.5 if gate_status == "PASS" else 3.5 if gate_status == "CAUTION" else 1.0
    entry_timing = round2(clip(trend_confirmation * 0.55 + flow_quality * 0.25 + reward_risk_quality * 0.20, 1, 5))
    deployment_quality = round2(clip(discount_quality * 0.35 + reward_risk_quality * 0.25 + risk_regime_quality * 0.25 + trend_confirmation * 0.15, 1, 5))
    if not gate_pass:
        deployment_quality = min(deployment_quality, 2.0)

    def stars(score):
        filled = max(1, min(5, int(round(score))))
        return "★" * filled + "☆" * (5 - filled)

    deployment_metrics = {
        "trendConfirmation": {"score": round2(trend_confirmation), "stars": stars(trend_confirmation), "labelCN": "趋势确认"},
        "entryTiming": {"score": entry_timing, "stars": stars(entry_timing), "labelCN": "入场时机"},
        "priceDiscount": {"score": discount_quality, "stars": stars(discount_quality), "labelCN": "价格折扣"},
        "rewardRisk": {"score": reward_risk_quality, "stars": stars(reward_risk_quality), "labelCN": "赔率质量"},
        "riskRegime": {"score": risk_regime_quality, "stars": stars(risk_regime_quality), "labelCN": "风险环境"},
        "deploymentQuality": {"score": deployment_quality, "stars": stars(deployment_quality), "labelCN": "部署质量"},
        "methodCN": "部署质量综合价格折扣、Reward/Risk、风险闸门与趋势确认；入场时机独立反映技术确认和量价结构。",
    }

    downside_steps = [(-10, "常规二次下探"), (-15, "支撑下沿/扫止损"), (-32, "深度风险释放")]
    upside_steps = [(18, "局部低点反弹"), (30, "均线修复反弹"), (47, "重新挑战上方结构")]
    downside = []
    upside = []
    for move, label in downside_steps:
        target = round2(current * (1 + move / 100)) if current else None
        downside.append({
            "name": label,
            "target": target,
            "movePct": move,
            "impactCurrentPct": round2(current_position_pct * move / 100),
            "impactMaxPct": round2(max_position_pct * move / 100),
        })
    for move, label in upside_steps:
        target = round2(current * (1 + move / 100)) if current else None
        upside.append({
            "name": label,
            "target": target,
            "movePct": move,
            "impactCurrentPct": round2(current_position_pct * move / 100),
            "impactMaxPct": round2(max_position_pct * move / 100),
        })

    read = (
        f"这不是在赌方向，而是在做仓位工程：当前仓位层级为{regime['tier']}。"
        f"默认赔率仓上限{regime['defaultOddsCapPct']}%，动态建议区间{regime['dynamicSuggestedRangePct']['low']}%-{regime['dynamicSuggestedRangePct']['high']}%，"
        f"条件扩展上限{regime['extensionCapPct']}%。当前按{current_position_pct}%实际仓位评估，账户仍有约{cash_pct}%现金/其它资产缓冲。"
    )
    conclusion = (
        "这笔交易买的不是趋势，而是折扣和赔率；目标是反弹兑现，不是长期证明观点。"
        if trade_quality >= 7
        else "仓位工程尚可，但交易质量还需要更好的支撑、量能或趋势确认。"
    )
    return {
        "title": "Position Engineering / 仓位工程学",
        "tradeQualityScore": trade_quality,
        "marketQualityScore": market_quality,
        "positionRiskScore": position_risk_score,
        "riskRewardScore": rr_score,
        "psychologyScore": psychology_score,
        "currentPositionPct": current_position_pct,
        "maxTacticalPositionPct": max_position_pct,
        "positionTier": regime["tier"],
        "defaultOddsCapPct": regime["defaultOddsCapPct"],
        "dynamicSuggestedRangePct": regime["dynamicSuggestedRangePct"],
        "extensionCapPct": regime["extensionCapPct"],
        "trendPermission": regime["trendPermission"],
        "priceDiscount": regime["priceDiscount"],
        "riskRegimeGate": regime["riskRegimeGate"],
        "decisionReviewCN": regime["reviewQuestionsCN"],
        "deploymentMetrics": deployment_metrics,
        "cashBufferPct": cash_pct,
        "readCN": read,
        "notPredictionCN": f"问题不是现价{round2(current)}是不是最低点，而是市场质量、价格折扣、风险类型和账户纵深是否共同允许这个仓位。",
        "supportCN": "支撑不是一个精确点。市场经常会先刺穿支撑、扫止损、测试真实需求，再决定是否修复。",
        "patternCN": "不需要吃完整个pattern。拿到局部20%-30%的可控反弹，也可以是一笔高质量交易。",
        "downside": downside,
        "upside": upside,
        "addPlanCN": f"参考路径：{regime['permissionCN']} 若下探但卖压递减、支撑附近横住，可在动态区间内分批；若风险闸门关闭，则停止扩仓，保留现金重新评估。",
        "invalidCN": "如果VIX快速突破22-25、QQQ同步连续放量破位、信用/流动性恶化、行业基本面下修，或低位无反弹地持续单边抛售，深度折扣假设作废。",
        "conclusionCN": conclusion,
    }


def initiative_management(df, q, pe, account, behavior, intra, market_session, volume_structure=None):
    """Turn position engineering into an explicit optionality and information plan."""
    current = float(q.get("close") or q.get("last") or 0)
    exposure = float((account or {}).get("currentPositionPct") or 0)
    cash = max(0.0, 100.0 - exposure)
    cap = float((pe or {}).get("maxTacticalPositionPct") or 0)
    gate = ((pe or {}).get("riskRegimeGate") or {}).get("status") or "FAIL"
    anchor = (behavior or {}).get("dynamicAnchorRange") or {}
    volume_score = (volume_structure or {}).get("score")

    cash_optionality = round2(min(25, cash * 0.25))
    participation = round2(20 if 5 <= exposure <= max(35, cap) else 12 if 0 < exposure < 60 else 5 if exposure == 0 else 2)
    reentry_capacity = round2(min(20, cash * 0.20))
    exit_capacity = round2(15 if exposure <= max(cap, 35) else 8 if exposure <= 60 else 3)
    plan_readiness = 20 if gate == "PASS" else 15 if gate == "CAUTION" else 6
    concentration_penalty = max(0, round2((exposure - max(cap, 35)) * 0.45))
    initiative_score = round2(max(0, min(100, cash_optionality + participation + reentry_capacity + exit_capacity + plan_readiness - concentration_penalty)))
    initiative_label = "High / 主动权高" if initiative_score >= 75 else "Balanced / 主动权均衡" if initiative_score >= 55 else "Constrained / 主动权受限" if initiative_score >= 35 else "Low / 主动权低"

    anchor_low = anchor.get("low")
    anchor_high = anchor.get("high")
    confirmation_mid = current * 0.94 if current else None
    confirmation_low = round2(confirmation_mid * 0.99) if confirmation_mid else None
    confirmation_high = round2(confirmation_mid * 1.01) if confirmation_mid else None
    if isinstance(anchor_high, (int, float)) and current and anchor_high > current * 0.90:
        confirmation_low = round2(max(confirmation_low, anchor_high * 0.985))
        confirmation_high = round2(max(confirmation_high, anchor_high * 1.015))
    odds_low = round2(anchor_low) if isinstance(anchor_low, (int, float)) else round2(current * 0.86)
    odds_high = round2(anchor_high) if isinstance(anchor_high, (int, float)) else round2(current * 0.90)
    if odds_low and odds_high and odds_low > odds_high:
        odds_low, odds_high = odds_high, odds_low
    if confirmation_low and odds_high:
        odds_high = round2(min(odds_high, confirmation_low * 0.95))
        if not odds_low or odds_low >= odds_high:
            odds_low = round2(odds_high * 0.93)

    supports = [x.get("price") for x in (anchor.get("supportCandidates") or []) if isinstance(x.get("price"), (int, float))]
    deep_candidates = sorted([x for x in supports if not odds_low or x < odds_low * 0.97], reverse=True)
    temple_levels = deep_candidates[:2]
    if len(temple_levels) < 2 and current:
        temple_levels = list(dict.fromkeys(temple_levels + [round2(current * 0.80), round2(current * 0.74)]))[:2]

    zones = [
        {
            "role": "Confirmation Zone / 确认位",
            "roleCN": "确认位",
            "roleEN": "Confirmation Zone",
            "low": confirmation_low,
            "high": confirmation_high,
            "range": f"{confirmation_low}-{confirmation_high}",
            "defaultSizePct": 5,
            "triggerCN": "回踩后缩量守住，且半导体权重与板块广度没有同步恶化。",
            "triggerEN": "A pullback holds on lighter volume while semiconductor leaders and breadth remain stable.",
            "meaningCN": "这里买的是新战场的承接确认，不是价格折扣。",
            "meaningEN": "This zone buys confirmation that the new battlefield is being defended, not deep discount.",
            "invalidationCN": "放量跌穿并无法快速收回，取消确认仓。",
            "invalidationEN": "Cancel the confirmation tranche if price breaks on volume and cannot reclaim the zone.",
        },
        {
            "role": "Odds Zone / 赔率位",
            "roleCN": "赔率位",
            "roleEN": "Odds Zone",
            "low": odds_low,
            "high": odds_high,
            "range": f"{odds_low}-{odds_high}",
            "defaultSizePct": 10,
            "triggerCN": "重新进入折扣区后出现卖压递减、止跌或流动性测试后的快速收回。",
            "triggerEN": "Price re-enters the discount zone and selling pressure fades, stabilizes, or quickly reclaims a liquidity sweep.",
            "meaningCN": "这里买的是折扣和风险收益重新改善。",
            "meaningEN": "This zone buys renewed discount and improved asymmetry.",
            "invalidationCN": "风险闸门关闭，或跌破后持续放量单边下行。",
            "invalidationEN": "Suspend deployment if the risk gate closes or downside becomes persistent and one-sided.",
        },
        {
            "role": "Temple Recalculation / 重新庙算位",
            "roleCN": "重新庙算位",
            "roleEN": "Temple Recalculation",
            "levels": temple_levels,
            "defaultSizePct": 0,
            "triggerCN": "进入深回撤区时暂停机械挂单，重新验证放量阳线、箱体/通道和基本面假设。",
            "triggerEN": "At a deep drawdown, pause mechanical orders and re-test the volume impulse, range/channel, and fundamental thesis.",
            "meaningCN": "更低价格可能提高赔率，也可能证明旧模型已经失效。",
            "meaningEN": "A lower price may improve odds or prove that the prior model has failed.",
            "invalidationCN": "庙算未完成前不预设买点。",
            "invalidationEN": "No preset purchase is authorized before the adversarial review is complete.",
        },
    ]

    tail = df.tail(min(25, len(df))).copy()
    x = np.arange(len(tail), dtype=float)
    high_slope = float(np.polyfit(x, tail.High.astype(float), 1)[0]) if len(tail) >= 5 else 0
    low_slope = float(np.polyfit(x, tail.Low.astype(float), 1)[0]) if len(tail) >= 5 else 0
    ema20 = float(tail.iloc[-1].EMA20) if len(tail) and pd.notna(tail.iloc[-1].EMA20) else current
    macd_ok = bool(len(tail) and tail.iloc[-1].MACD > tail.iloc[-1].MACD_SIGNAL)
    descending_score = round2(clip(55 + (-high_slope / current * 1000 if current and high_slope < 0 else -20) + (-low_slope / current * 700 if current and low_slope < 0 else -10), 10, 85))
    range_width = (float(tail.High.max()) - float(tail.Low.min())) / current * 100 if current and len(tail) else 0
    range_score = round2(clip(65 - abs(high_slope - low_slope) / current * 1200 - max(0, range_width - 45) * 0.6, 10, 80)) if current else 40
    reversal_score = round2(clip(25 + (25 if current > ema20 else -5) + (20 if macd_ok else 0) + (10 if isinstance(volume_score, (int, float)) and volume_score >= 6 else 0), 5, 80))
    hypotheses = [
        {"name": "Horizontal Range", "nameEN": "Horizontal Range", "nameCN": "水平箱体", "confidence": range_score, "evidenceCN": f"近25日高低点斜率差为 {round2(high_slope-low_slope)}；箱体宽度约 {round2(range_width)}%。", "evidenceEN": f"The 25-session high/low slope spread is {round2(high_slope-low_slope)} and the observed range is about {round2(range_width)}% wide.", "invalidationCN": "有效突破箱体边界并连续站稳后，水平箱体权重下降。", "invalidationEN": "Reduce the range model's weight after a confirmed boundary break with sustained acceptance.", "actionCN": "在上下沿按资金行为分批，不在箱体中部追价。", "actionEN": "Stage by capital behavior near the boundaries; do not chase the middle of the range."},
        {"name": "Descending Channel", "nameEN": "Descending Channel", "nameCN": "下降通道", "confidence": descending_score, "evidenceCN": f"近25日高点斜率 {round2(high_slope)}、低点斜率 {round2(low_slope)}。", "evidenceEN": f"The 25-session high slope is {round2(high_slope)} and the low slope is {round2(low_slope)}.", "invalidationCN": "放量突破通道上轨并连续站稳，停止通道内高卖低接。", "invalidationEN": "Stop channel trading after a volume-backed upper-boundary break that holds.", "actionCN": "只用交易库存做梯，核心/趋势仓不因通道噪音频繁切换。", "actionEN": "Use only trading inventory for channel ladders; do not churn the trend tranche on channel noise."},
        {"name": "Trend Reversal", "nameEN": "Trend Reversal", "nameCN": "趋势反转", "confidence": reversal_score, "evidenceCN": f"现价 {round2(current)}，EMA20 {round2(ema20)}；MACD确认={'是' if macd_ok else '否'}。", "evidenceEN": f"Price is {round2(current)} versus EMA20 at {round2(ema20)}; MACD confirmation is {'present' if macd_ok else 'absent'}.", "invalidationCN": "重新跌回关键结构下方且量能承认下跌，反转假设失效。", "invalidationEN": "Invalidate the reversal if price falls back below the key structure and volume accepts the decline.", "actionCN": "只有价格、量能和板块共振后，赔率仓才升级为趋势仓。", "actionEN": "Upgrade an odds tranche to a trend tranche only after price, volume, and sector breadth confirm together."},
    ]
    hypotheses.sort(key=lambda z: z["confidence"], reverse=True)

    if len(df) >= 3:
        last3 = df.tail(3)
        latest = last3.iloc[-1]
        prior = last3.iloc[-2]
        follow_state = "Constructive Follow-through / 建设性延续" if latest.Close >= prior.Close and latest.VOL_RATIO >= 0.8 else "Liquidity Test / 流动性测试待确认" if latest.Close >= latest.Low * 1.04 else "Failed Follow-through / 延续失败"
        follow_cn = "放量之后价格继续被接受。" if follow_state.startswith("Constructive") else "放量本身保持中性，未来1-3个交易日重点看是否守住、缩量整理或立即跌回。" if follow_state.startswith("Liquidity") else "放量后价格未能延续，需提高换手、派发或流动性收集的权重。"
        follow_en = "Price continues to be accepted after the volume expansion." if follow_state.startswith("Constructive") else "Volume remains neutral by itself; use the next 1–3 sessions to test acceptance, quiet consolidation, or immediate failure." if follow_state.startswith("Liquidity") else "Price failed to follow through after the volume event; raise the weight of turnover, distribution, or liquidity collection."
    else:
        follow_state, follow_cn, follow_en = "Pending", "历史数据不足，等待后续K线。", "History is insufficient; wait for follow-through bars."

    session_name = (market_session or {}).get("session") or "unknown"
    real_intraday = (intra or {}).get("mode") == "real_5m"
    active_ready = real_intraday and session_name in {"pre-market", "regular", "after-hours"}
    feasibility_score = 90 if active_ready else 78 if session_name == "closed" else 68
    execution = {
        "score": feasibility_score,
        "defaultModeCN": "默认模式：使用预设的信息区域、条件单和仓位上限；适合无法全天盯盘。",
        "defaultModeEN": "Default mode uses information zones, conditional orders, and position ceilings when continuous monitoring is unavailable.",
        "activeModeCN": "主动模式：只有能盯盘且真实五分钟数据可用时，才允许量能、NVDA/SMH和VIX覆盖默认价位。",
        "activeModeEN": "Active mode may override default levels only when live monitoring and reliable five-minute data are available.",
        "currentMode": "Active" if active_ready else "Default",
        "constraintCN": "理论最优不等于执行最优；无法监控时不得依赖临场判断。",
        "constraintEN": "The theoretically best plan is not executable if it depends on monitoring that is unavailable.",
    }

    temple_triggers = [
        "放量阳线被完全否定，或关键支撑跌破后无法收回。",
        "创新低、箱体转为下降通道，或下降通道被有效突破。",
        "风险从半导体扩散至QQQ、信用、流动性或防御板块。",
        "行业基本面、政策、出口限制或估值锚发生变化。",
        "价格进入重新庙算位；在复核完成前取消机械加仓。",
    ]
    temple_triggers_en = [
        "A high-volume up bar is fully rejected, or a key support break cannot be reclaimed.",
        "Price makes a new low, a range becomes a descending channel, or that channel is decisively broken.",
        "Risk spreads from semiconductors to QQQ, credit, liquidity, or defensive sectors.",
        "Industry fundamentals, policy, export restrictions, or the valuation anchor change.",
        "Price enters the temple-recalculation zone; cancel mechanical adds until the review is complete.",
    ]
    return {
        "title": "Initiative Management / 主动权管理",
        "score": initiative_score,
        "label": initiative_label,
        "labelCN": initiative_label.split("/")[-1].strip(),
        "labelEN": initiative_label.split("/")[0].strip(),
        "components": {"cashOptionality": cash_optionality, "participationOptionality": participation, "reentryCapacity": reentry_capacity, "exitCapacity": exit_capacity, "planReadiness": plan_readiness, "concentrationPenalty": concentration_penalty},
        "principleCN": "主动权比方向更重要。仓位工程的目的不是最大化单次收益，而是最大化未来选择权。",
        "principleEN": "Initiative matters more than direction. Position engineering should maximize future choices, not a single trade's theoretical return.",
        "accountReadCN": f"当前仓位 {round2(exposure)}%、现金/其它资产约 {round2(cash)}%、模型上限 {round2(cap)}%；上涨参与、下跌回补和退出能力共同形成主动权。",
        "accountReadEN": f"Current exposure is {round2(exposure)}%, cash/other assets about {round2(cash)}%, and the model ceiling {round2(cap)}%. Initiative comes from participation, re-entry capacity, and exit capacity together.",
        "informationZones": zones,
        "templeRecalculationTriggersCN": temple_triggers,
        "templeRecalculationTriggersEN": temple_triggers_en,
        "liquidityFollowThrough": {"state": follow_state, "readCN": follow_cn, "summaryCN": follow_cn, "readEN": follow_en, "summaryEN": follow_en, "window": "1-3 trading days", "checksCN": ["守住放量K线的核心成交区。", "回调时量能收缩而非继续放大。", "再次上攻时板块广度与权重股同步。"], "checksEN": ["Hold the core transaction area of the volume bar.", "Contract volume on pullbacks instead of expanding it.", "Require sector breadth and leaders to confirm the next advance."]},
        "structureHypotheses": hypotheses,
        "executionFeasibility": execution,
    }


def field_evolution_review(ticker, df, q, fg, sec, mac, volume_structure, pe, scenario_ctx, initiative_ctx):
    """Convert recent field observations into reusable, evidence-gated model rules."""
    current = float(q.get("close") or q.get("last") or 0)
    latest = df.iloc[-1]
    work = df.tail(min(180, len(df))).reset_index(drop=True).copy()
    tail30 = work.tail(min(30, len(work)))
    tail10 = work.tail(min(10, len(work)))
    prior10 = work.iloc[-20:-10] if len(work) >= 20 else work.iloc[:-10]
    x30 = np.arange(len(tail30), dtype=float)
    high_slope = float(np.polyfit(x30, tail30.High.astype(float), 1)[0]) if len(tail30) >= 5 else 0.0
    low_slope = float(np.polyfit(x30, tail30.Low.astype(float), 1)[0]) if len(tail30) >= 5 else 0.0
    ema20 = float(latest.EMA20) if pd.notna(latest.EMA20) else current
    ema50 = float(latest.EMA50) if pd.notna(latest.EMA50) else ema20
    macd_ok = bool(pd.notna(latest.MACD) and pd.notna(latest.MACD_SIGNAL) and latest.MACD > latest.MACD_SIGNAL)
    rsi14 = float(latest.RSI14) if hasattr(latest, "RSI14") and pd.notna(latest.RSI14) else 50.0

    true_range = pd.concat(
        [(work.High - work.Low), (work.High - work.Close.shift()).abs(), (work.Low - work.Close.shift()).abs()],
        axis=1,
    ).max(axis=1)
    recent_atr = float(true_range.tail(min(10, len(true_range))).mean()) if len(true_range) else 0
    prior_atr = float(true_range.iloc[-30:-10].mean()) if len(true_range) >= 30 else float(true_range.mean()) if len(true_range) else 0
    atr_ratio = recent_atr / prior_atr if prior_atr else 1.0
    recent_range = float(tail10.High.max() - tail10.Low.min()) if len(tail10) else 0
    prior_range = float(prior10.High.max() - prior10.Low.min()) if len(prior10) else recent_range
    range_ratio = recent_range / prior_range if prior_range else 1.0
    downtrend = (current < ema20 <= ema50) or (high_slope < 0 and low_slope < 0)
    uptrend = (current > ema20 >= ema50) and high_slope > 0
    compressed = atr_ratio <= 0.88 or range_ratio <= 0.78
    transition = (downtrend and macd_ok and current >= ema20 * 0.97) or (uptrend and not macd_ok)
    if downtrend and compressed:
        phase_en, phase_cn = "Downtrend → Compression", "下降趋势 → 波动压缩"
        phase_code = "COMPRESSION"
    elif transition:
        phase_en, phase_cn = "Transition / Decision Point", "过渡期 / 方向选择"
        phase_code = "TRANSITION"
    elif downtrend:
        phase_en, phase_cn = "Trend / Downtrend", "趋势期 / 下跌趋势"
        phase_code = "DOWNTREND"
    elif uptrend:
        phase_en, phase_cn = "Trend / Uptrend", "趋势期 / 上涨趋势"
        phase_code = "UPTREND"
    else:
        phase_en, phase_cn = "Range / Price Discovery", "震荡 / 价格发现"
        phase_code = "RANGE"
    phase = {
        "code": phase_code,
        "labelCN": phase_cn,
        "labelEN": phase_en,
        "highSlope30": round2(high_slope),
        "lowSlope30": round2(low_slope),
        "atrCompressionRatio": round2(atr_ratio),
        "rangeCompressionRatio": round2(range_ratio),
        "readCN": f"近30日高点斜率 {round2(high_slope)}、低点斜率 {round2(low_slope)}；近10日ATR相对前段为 {round2(atr_ratio)}，区间宽度比为 {round2(range_ratio)}。阶段判断只说明行情处于趋势、压缩还是过渡，不等于反转确认。",
        "readEN": f"The 30-session high/low slopes are {round2(high_slope)} and {round2(low_slope)}. The recent ATR ratio is {round2(atr_ratio)} and range-width ratio {round2(range_ratio)}. Phase classification describes maturity and compression; it does not confirm a reversal.",
    }

    prior_floor = float(work.iloc[-21:-1].Low.min()) if len(work) >= 21 else float(work.iloc[:-1].Low.min()) if len(work) > 1 else float(latest.Low)
    bar_range = max(float(latest.High - latest.Low), current * 0.001 if current else 0.001)
    close_location = clip((float(latest.Close) - float(latest.Low)) / bar_range, 0, 1)
    volume_ratio = float(latest.VOL_RATIO) if hasattr(latest, "VOL_RATIO") and pd.notna(latest.VOL_RATIO) else None
    swept_floor = bool(float(latest.Low) < prior_floor * 0.995)
    reclaimed_floor = bool(float(latest.Close) >= prior_floor)
    daily_change = float(q.get("prevCloseChangePct") if q.get("prevCloseChangePct") is not None else q.get("changePct") or 0)
    sector_groups = (sec or {}).get("groups") or {}
    semis = sector_groups.get("Semiconductor")
    growth = sector_groups.get("Growth")
    defensive = sector_groups.get("Defensive")
    mixed_rotation = all(isinstance(x, (int, float)) for x in [semis, growth, defensive]) and max(semis, growth, defensive) - min(semis, growth, defensive) >= 1.5
    if swept_floor and reclaimed_floor and close_location >= 0.55:
        liquidity_code, liquidity_cn, liquidity_en, liquidity_conf = "STOP_HUNT", "流动性清扫 / 止损猎杀", "Liquidity Sweep / Stop Hunt", 85 if (volume_ratio or 0) >= 1.2 else 72
        liquidity_read_cn = "价格刺穿可见前低后重新收回，说明低位流动性被交易，但不能仅凭V形反弹断言机构吸筹。后续必须验证成交核心区能否守住。"
        liquidity_read_en = "Price swept a visible prior low and reclaimed it. Liquidity was transacted, but a V-shaped rebound alone does not prove institutional accumulation; the transaction core must hold."
    elif (volume_ratio or 0) >= 1.2 and close_location >= 0.68 and daily_change >= 0:
        liquidity_code, liquidity_cn, liquidity_en, liquidity_conf = "ACCUMULATION", "建设性承接 / 吸筹候选", "Constructive Demand / Accumulation Candidate", 72
        liquidity_read_cn = "成交量放大且收在日内区间上部，主动买盘较强；仍要看下一次回踩是否缩量。"
        liquidity_read_en = "Volume expanded and price closed in the upper part of the range. Demand was active, but the next pullback must contract in volume."
    elif (volume_ratio or 0) >= 1.2 and close_location <= 0.32 and daily_change < 0:
        liquidity_code, liquidity_cn, liquidity_en, liquidity_conf = "DISTRIBUTION", "派发 / 风险释放", "Distribution / Risk Release", 78
        liquidity_read_cn = "下跌得到成交量承认且收盘靠近日内低位；在卖压失效前，不把更低价格自动解释成更高赔率。"
        liquidity_read_en = "Volume confirmed the decline and price closed near the low. A lower price is not automatically better odds until selling pressure fails."
    elif (volume_ratio or 0) >= 1.0 and mixed_rotation:
        liquidity_code, liquidity_cn, liquidity_en, liquidity_conf = "ROTATION", "换手 / 板块轮动", "Rotation / Inventory Transfer", 66
        liquidity_read_cn = "成交活跃但板块并未一面倒，更像筹码换手和局部轮动；方向仍需后续价格接受度确认。"
        liquidity_read_en = "Trading was active without one-sided sector breadth, which is more consistent with rotation and inventory transfer than a clean directional move."
    else:
        liquidity_code, liquidity_cn, liquidity_en, liquidity_conf = "UNRESOLVED", "流动性意图待确认", "Liquidity Intent Unresolved", 45
        liquidity_read_cn = "成交量本身保持中性；下一步看价格是否守住成交核心、回调是否缩量，以及权重股是否同步。"
        liquidity_read_en = "Volume is neutral by itself. Watch whether price holds the transaction core, pullbacks contract, and leaders confirm."
    liquidity = {
        "code": liquidity_code,
        "labelCN": liquidity_cn,
        "labelEN": liquidity_en,
        "confidence": liquidity_conf,
        "priorVisibleLow": round2(prior_floor),
        "sweptPriorLow": swept_floor,
        "reclaimedPriorLow": reclaimed_floor,
        "closeLocationPct": round2(close_location * 100),
        "volumeRatio": round2(volume_ratio) if volume_ratio is not None else None,
        "readCN": liquidity_read_cn,
        "readEN": liquidity_read_en,
        "questionsCN": ["今天是谁在主动成交？", "成交量是在建仓、换手、派发，还是清扫止损？", "放量之后，价格是否继续被接受？"],
        "questionsEN": ["Who initiated today's trading?", "Was volume accumulation, rotation, distribution, or a stop sweep?", "Was price accepted after the volume event?"],
    }

    fear_score = float(fg.get("score") or 50)
    vix_last = (mac.get("vix") or {}).get("last") if mac else None
    gate_status = ((pe or {}).get("riskRegimeGate") or {}).get("status") or "FAIL"
    selling_failure = bool((swept_floor and reclaimed_floor) or (daily_change < 0 and close_location >= 0.68))
    extreme_fear = fear_score <= 20 or (isinstance(vix_last, (int, float)) and vix_last >= 28)
    moderate_fear = fear_score <= 40
    attack_authorized = bool(extreme_fear and selling_failure and gate_status != "FAIL")
    if attack_authorized:
        deployment_class = "Attack / 进攻仓"
        reaction_cn = "情绪已接近极端，同时价格不再按恐慌逻辑继续下跌；只有在风险闸门未关闭时，才允许使用进攻级预算。"
        reaction_en = "Fear is extreme while price no longer behaves as panic should. Attack-level risk is permitted only while the systemic risk gate remains open."
    elif moderate_fear and selling_failure:
        deployment_class = "Odds / 赔率仓"
        reaction_cn = "情绪偏冷且卖压出现失效迹象，但尚未达到极端恐慌；只允许赔率仓，不提前使用进攻仓预算。"
        reaction_en = "Fear is elevated and selling shows signs of failure, but panic is not extreme. Use odds-level risk, not an attack budget."
    elif moderate_fear:
        deployment_class = "Probe / 试探仓"
        reaction_cn = "情绪属于普通到中度恐惧，价格尚未证明卖压失效；只允许试探或等待。"
        reaction_en = "Fear is ordinary to moderate and price has not proved that selling is failing. Only probe-level risk or waiting is justified."
    else:
        deployment_class = "Wait / 等待"
        reaction_cn = "情绪没有提供逆向部署优势；必须依赖趋势、折扣和资金确认。"
        reaction_en = "Sentiment provides no contrarian deployment edge. Trend, discount, and capital confirmation must carry the decision."
    emotion_reaction = {
        "fearScore": round2(fear_score),
        "vix": vix_last,
        "sellingPressureFailure": selling_failure,
        "attackAuthorized": attack_authorized,
        "deploymentClass": deployment_class,
        "readCN": reaction_cn,
        "readEN": reaction_en,
        "ruleCN": "不是“别人恐慌就重仓”，而是“别人恐慌，但市场开始不再按照恐慌应有的方式继续下跌”时，才提高部署级别。",
        "ruleEN": "Do not size up merely because others are afraid. Size up only when fear is extreme and the market stops falling the way panic should.",
    }

    peak_pos = int(work.High.astype(float).idxmax()) if len(work) else 0
    before_peak = work.iloc[: peak_pos + 1]
    trough_pos = int(before_peak.Low.astype(float).idxmin()) if len(before_peak) else 0
    peak_price = float(work.iloc[peak_pos].High) if len(work) else current
    trough_price = float(work.iloc[trough_pos].Low) if len(work) else current
    advance_days = max(1, peak_pos - trough_pos)
    decline_days = max(0, len(work) - 1 - peak_pos)
    advance_pct = (peak_price / trough_price - 1) * 100 if trough_price else 0
    decline_pct = (1 - current / peak_price) * 100 if peak_price else 0
    time_ratio = decline_days / advance_days if advance_days else 0
    price_ratio = decline_pct / advance_pct if advance_pct else 0
    time_closeness = max(0, 1 - abs(time_ratio - 1))
    price_closeness = max(0, 1 - abs(price_ratio - 1))
    symmetry_score = round2((time_closeness * 0.55 + price_closeness * 0.45) * 100)
    symmetry_strength = "Strong / 强" if symmetry_score >= 75 else "Medium / 中" if symmetry_score >= 45 else "Weak / 弱"
    symmetry = {
        "strength": symmetry_strength,
        "score": symmetry_score,
        "advanceDays": advance_days,
        "declineDays": decline_days,
        "advancePct": round2(advance_pct),
        "declinePct": round2(decline_pct),
        "timeRatio": round2(time_ratio),
        "priceRatio": round2(price_ratio),
        "readCN": "对称性只用于判断趋势成熟度和边际收益递减，属于三级证据。它不能预测结束日期，也不能单独授权买入。",
        "readEN": "Symmetry is tertiary evidence for trend maturity and diminishing marginal downside. It cannot predict an end date or independently authorize a trade.",
    }

    trend_component = float((((pe or {}).get("deploymentMetrics") or {}).get("trendConfirmation") or {}).get("score") or 1)
    volume_component = clip(float((volume_structure or {}).get("score") or 5) / 2, 1, 5)
    if all(isinstance(x, (int, float)) for x in [semis, growth, defensive]):
        breadth_component = clip(3 + (semis - defensive) * 0.35 + (growth - defensive) * 0.15, 1, 5)
    else:
        breadth_component = 3
    momentum_component = clip(2.5 + (1 if macd_ok else -0.75) + (0.75 if rsi14 >= 50 else -0.25), 1, 5)
    structure_component = 4.5 if current >= ema20 and high_slope >= 0 else 3 if compressed else 1.5
    exit_score = round2((trend_component + volume_component + breadth_component + momentum_component + structure_component) / 5)
    exit_grade = "A" if exit_score >= 4.2 else "B" if exit_score >= 3.4 else "C" if exit_score >= 2.6 else "D" if exit_score >= 1.8 else "E"
    if exit_grade == "A":
        exit_action_cn, exit_action_en = "到达计划区时只部分兑现或上移保护线，保留趋势参与权。", "At a planned target, take only a partial exit or trail protection while preserving trend participation."
    elif exit_grade == "B":
        exit_action_cn, exit_action_en = "到达计划区时分批兑现；若共振继续，可保留一部分。", "Scale out at a planned target; retain a portion only while confirmation persists."
    elif exit_grade == "C":
        exit_action_cn, exit_action_en = "按原计划兑现目标仓位，不因单日上涨临时取消卖出。", "Execute the planned tranche at target; do not cancel the exit because of one strong bar."
    else:
        exit_action_cn, exit_action_en = "反弹质量弱，到达目标区优先释放对应仓位和风险。", "Rebound quality is weak; prioritize releasing the assigned tranche and risk at the target zone."
    exit_quality = {
        "score": exit_score,
        "grade": exit_grade,
        "components": {
            "trend": round2(trend_component),
            "structure": round2(structure_component),
            "breadth": round2(breadth_component),
            "volume": round2(volume_component),
            "momentum": round2(momentum_component),
        },
        "actionCN": exit_action_cn,
        "actionEN": exit_action_en,
        "ruleCN": "固定价格提供预案；价格到达的方式、板块共振和资金质量决定最终卖多少。低位仓按反弹质量出，高位仓按结构修复出。",
        "ruleEN": "Price supplies the plan; the path into the target, sector confirmation, and capital quality determine how much to sell. Exit low-cost tranches by rebound quality and high-cost tranches by structural repair.",
    }

    leveraged = ticker.upper() in {"SOXL", "TQQQ", "SPXL", "UPRO", "TECL", "FNGU"}
    tail_probability = 5
    if gate_status == "CAUTION":
        tail_probability += 5
    elif gate_status == "FAIL":
        tail_probability += 12
    if liquidity_code == "DISTRIBUTION":
        tail_probability += 5
    if downtrend and not compressed:
        tail_probability += 3
    tail_probability = min(30, tail_probability)
    tail_risk = {
        "probabilityPct": tail_probability,
        "impact": "Extreme / 极高" if leveraged else "High / 高",
        "leveragedPathRisk": leveraged,
        "readCN": "系统性风险概率低，不等于3×ETF继续大跌的概率低。权重股再下一层、QQQ技术回调和每日复位/波动损耗，都可能在没有金融危机的情况下放大损失。",
        "readEN": "Low systemic-risk probability does not mean low downside probability for a 3× ETF. Another leg lower in leaders, a QQQ correction, and daily reset/volatility drag can amplify losses without a financial crisis.",
        "recalcCN": ["风险闸门转为FAIL。", "流动性清扫后无法守住成交核心。", "板块风险扩散至成长、防御和信用。", "时间压缩向下破位而不是向上转换。"],
        "recalcEN": ["The risk gate turns FAIL.", "A liquidity sweep cannot hold its transaction core.", "Risk spreads into growth, defensive sectors, or credit.", "Compression resolves downward rather than transitioning upward."],
    }

    capital_efficiency = {
        "principleCN": "每一笔都有逻辑，不代表组合后的整体仓位仍然有最优赔率。每增加一层，下一层的证据要求必须更高。",
        "principleEN": "Every tranche can be individually logical while the combined position is still inefficient. Each additional layer requires stronger evidence than the one before it.",
        "sentimentBudgetCN": [
            {"stage": "Fear 40附近", "permission": "试探仓", "rule": "不使用极端恐慌预算。"},
            {"stage": "Fear 25–35", "permission": "赔率仓", "rule": "必须同时看到折扣扩大或卖压递减。"},
            {"stage": "Extreme Fear + 卖压失效", "permission": "进攻仓候选", "rule": "风险闸门必须保持开启。"},
        ],
        "sentimentBudgetEN": [
            {"stage": "Fear near 40", "permission": "Probe", "rule": "Do not spend an extreme-panic budget."},
            {"stage": "Fear 25–35", "permission": "Odds tranche", "rule": "Require deeper discount or fading selling pressure."},
            {"stage": "Extreme Fear + selling failure", "permission": "Attack candidate", "rule": "The systemic risk gate must remain open."},
        ],
        "addAuditCN": ["新增后总仓位和3×等效敞口是多少？", "均价改善是否足以补偿新增风险？", "下一层还剩多少现金和非线性应对能力？", "这一层的任务和退出条件是否不同于上一层？", "如果未来两周横盘，这层仓位是否仍值得持有？"],
        "addAuditEN": ["What are total exposure and 3×-equivalent exposure after the add?", "Does cost improvement compensate for added risk?", "How much cash and nonlinear response capacity remain?", "Does this layer have a distinct mission and exit condition?", "Is the tranche still worth holding if price is flat for two weeks?"],
    }

    post_mortem = {
        "required": True,
        "titleCN": "战役结束后复盘",
        "titleEN": "Post-campaign Review",
        "questionsCN": [
            "入场是否提前？最终承担多少风险，换来多少成本改善？",
            "多次局部正确是否累积成整体过重？",
            "是否在普通恐惧阶段提前使用了极端恐慌预算？",
            "到达目标时是否按反弹/共振质量执行，而不是临场改口？",
            "横盘和3×路径损耗是否被计入机会成本？",
            "这次决策是否提高了下一次决策的质量？",
        ],
        "questionsEN": [
            "Was entry early, and how much risk purchased how much cost improvement?",
            "Did several locally correct decisions accumulate into an overweight position?",
            "Was an extreme-panic budget spent during ordinary fear?",
            "Were exits executed by rebound/confirmation quality rather than rewritten at the target?",
            "Were time and 3× path drag included as opportunity costs?",
            "Did this campaign improve the quality of the next decision?",
        ],
    }

    return {
        "title": "Field Evolution / 实战迭代",
        "modelVersion": "Field Learning 1.0",
        "asOf": str(pd.to_datetime(latest.Date).date()),
        "marketPhase": phase,
        "liquidityAssessment": liquidity,
        "emotionReaction": emotion_reaction,
        "symmetry": symmetry,
        "exitQuality": exit_quality,
        "tailRisk": tail_risk,
        "capitalEfficiency": capital_efficiency,
        "postMortem": post_mortem,
        "scenarioCount": len(scenario_ctx or []),
        "initiativeScore": (initiative_ctx or {}).get("score"),
        "coreLessonCN": "买点不只要便宜，还要高效；每一笔都有逻辑，不代表整体仓位仍然有最优赔率。",
        "coreLessonEN": "An entry must be efficient, not merely cheap. Every tranche can make sense while the combined position no longer has optimal odds.",
    }


def enemy_intent_review(q, mac, sec, heat, volume_structure, position_engineering_ctx, behavior_ctx=None):
    pe = position_engineering_ctx or {}
    gate = pe.get("riskRegimeGate") or {}
    discount = pe.get("priceDiscount") or {}
    tier = pe.get("positionTier") or "待判断"
    dynamic_range = pe.get("dynamicSuggestedRangePct") or {}
    vix_last = (mac.get("vix") or {}).get("last") if mac else None
    semis = (sec.get("groups") or {}).get("Semiconductor") if sec else None
    growth = (sec.get("groups") or {}).get("Growth") if sec else None
    defensive = (sec.get("groups") or {}).get("Defensive") if sec else None
    vol_label = (volume_structure or {}).get("labelCN") or "量价结构待确认"
    cap = ((behavior_ctx or {}).get("capitalBehavior") or {}).get("postureCN")
    current = q.get("close") or q.get("last")
    range_low = dynamic_range.get("low")
    range_high = dynamic_range.get("high")
    extension_cap = pe.get("extensionCapPct")

    def item(name, assumption, challenge, alternative, confidence, what_changes, answer):
        return {
            "nameCN": name,
            "assumptionCN": assumption,
            "challengeCN": challenge,
            "alternativeCN": alternative,
            "confidence": confidence,
            "whatWouldChangeCN": what_changes,
            "answerCN": answer,
        }

    fail_reasons = gate.get("failReasonsCN") or []
    system_conf = "75%" if gate.get("status") == "PASS" else "45%"
    institution_conf = "55%" if cap and ("Accumulation" in cap or "Price Discovery" in cap or "Selling" in cap) else "45%"
    cheap_conf = "70%" if (discount.get("discountFrom252HighPct") or 0) >= 45 else "55%"
    odds_conf = "70%" if tier.startswith("Deep Odds") else "55%"

    challenges = [
        item(
            "系统风险是否被低估",
            "当前更像板块去拥挤，而不是全市场系统性风险。",
            "有没有可能系统风险已经开始，只是VIX和指数还没有完全反映？",
            "半导体先跌只是第一波，后面可能扩散到QQQ、信用、流动性和防御板块。",
            system_conf,
            "VIX快速上破22-25、QQQ连续放量破位、Growth和Defensive同步走弱、信用或流动性指标恶化。",
            "目前按Risk Gate处理：通过时允许深度赔率仓推演；关闭时不允许把便宜解释成机会。",
        ),
        item(
            "叙事偏见",
            "低位承接可能来自更有耐心的资金。",
            "我们是不是把散户割肉、机构吸筹、洗盘、拉升拼成了一个太完整的故事？",
            "成交可能只是ETF再平衡、空头回补、做市商Gamma对冲、被动资金流入或短线基金抢反弹。",
            institution_conf,
            "反弹持续缩量、尾盘无人承接、低位成交后不能横住，或权重股继续同步派发。",
            "MMF只把这写成当前最符合证据的解释，不写成真相；仓位用概率和作废条件约束叙事。",
        ),
        item(
            "估值锚是否改变",
            f"相对252日高点折扣约{discount.get('discountFrom252HighPct')}%，价格质量提高。",
            f"现价 {current if current is not None else '附近'} 相对旧锚显得便宜；有没有可能AI/半导体估值锚已经整体下移？",
            "如果利润率、CapEx预期、出口限制或利率假设改变，旧高点不再是有效锚。",
            cheap_conf,
            "行业级EPS/CapEx预期下修、政策限制升级、主要权重股指引恶化、长期利率重新上行。",
            "价格折扣只提高赔率，不自动证明底部；所以Deep Odds不是Trend Position。",
        ),
        item(
            "赔率是否只是跌很多",
            "价格下跌后Risk/Reward改善。",
            "这是赔率好，还是只是因为跌了很多所以看起来便宜？",
            "杠杆ETF可能因为每日复位、波动损耗和连续下跌，让反弹需求高于表面跌幅。",
            odds_conf,
            "下跌继续放量、反弹无法站回关键均线、动态区间下破后不能快速收回。",
            "赔率必须同时通过价格折扣、非系统风险、承接质量和账户现金纵深；单独跌很多不算。",
        ),
        item(
            "为什么是这个仓位范围",
            f"当前仓位层级为{tier}，动态建议{dynamic_range.get('low')}%-{dynamic_range.get('high')}%，扩展上限{pe.get('extensionCapPct')}%。",
            f"如果 {range_low}%-{range_high}% 合理，为什么不是更低；如果赔率好，为什么不超过 {extension_cap}%？",
            "更低仓位会保留更多纵深但参与不足；超过扩展上限会显著压缩战略预备队，并可能把深度赔率仓误用成趋势仓。",
            "70%",
            f"如果资金重新流入、趋势修复，可进入趋势仓另算；如果Risk Gate关闭，降到 {range_low}% 以下或冻结新增。",
            f"{extension_cap}%是条件扩展上限，不是目标仓位；它只在风险闸门通过、承接改善且账户仍有纵深时开放。",
        ),
    ]
    summary = (
        "庙算，不为证明自己正确，而为寻找自己可能错误之处。"
        f" 当前最需要防的不是市场波动，而是叙事过满、替代解释被忽略、以及把赔率仓误认为趋势仓。"
    )
    if fail_reasons:
        summary += " 当前风险闸门已有警告：" + " ".join(fail_reasons)
    return {
        "titleCN": "敌谋预判",
        "subtitle": "Enemy Intent",
        "principleCN": "未战而庙算胜者，得算多也。",
        "coreIdeaCN": "庙算，不为证明自己正确，而为寻找自己可能错误之处。",
        "enemyQuestionCN": "如果我是市场，我会怎样利用你现在的想法？",
        "summaryCN": summary,
        "contextCN": [
            f"仓位层级：{tier}；动态建议：{dynamic_range.get('low')}-{dynamic_range.get('high')}%；扩展上限：{pe.get('extensionCapPct')}%。",
            f"VIX={vix_last if vix_last is not None else 'n/a'}；Semiconductor={semis}%，Growth={growth}%，Defensive={defensive}%。",
            f"量价结构：{vol_label}；资金行为：{cap or '待确认'}。",
        ],
        "challenges": challenges,
        "finalQuestionCN": "只有当主要反对意见都有可验证的控制条件，且最坏路径不会破坏账户，计划才通过庙算。",
    }


def executive_summary(ticker, q, mmf_score, fg, vacation, etf, sec, account=None):
    status = "Market Vacation" if vacation else "Tactical"
    if account and account.get("previousTrade"):
        headline = "Account Waiting：上一笔高质量交易已完成，当前100%现金，等待下一次Risk/Reward。"
    else:
        headline = f"{status}：市场尚未给出足够确认。" if vacation else f"{status}：可以观察机会，但确认条件仍需完成。"
    points = [
        f"作战姿态：{status}，MMF Score {mmf_score}/100。",
        f"{ticker} 当日变化 {q.get('changePct')}%，收盘 {q.get('close')}。",
        f"Fear & Greed {fg['score']} / {fg['label']}，主要异常项：{', '.join([x['factor'] for x in fg['mainDrivers'][:2]])}。",
        f"板块轮动：{sec['mode']}。{sec.get('flowCN')}",
    ]
    if account:
        points.insert(0, f"账户状态：{account.get('stateCN')}；当前仓位 {account.get('currentPositionPct')}%，现金/其它资产约 {account.get('cashPct')}%。")
    if etf.get("mainDrag"):
        points.append(f"权重拖累最大：{etf['mainDrag']['ticker']}，影响约 {etf['mainDrag']['impact']}。")
    if etf.get("mainSupport"):
        points.append(f"权重支撑最大：{etf['mainSupport']['ticker']}，影响约 {etf['mainSupport']['impact']}。")
    if account and account.get("previousTrade"):
        strategy = f"Portfolio策略：{account.get('recommendationCN')}"
    else:
        position_pct = (account or {}).get("currentPositionPct")
        cash_pct = (account or {}).get("cashPct")
        if isinstance(position_pct, (int, float)) and position_pct > 0:
            strategy = f"策略：持仓管理优先。当前仓位 {position_pct}%，现金/其它资产约 {cash_pct}%；未获得新确认前暂停新增，先审查各层仓位使命、退出条件与账户风险。"
        elif vacation:
            strategy = "策略：空仓以现金等待为主；是否启动5%-10%观察仓，由下一常规交易时段的执行许可决定。"
        else:
            strategy = "策略：保持战术模式，不满仓；只有确认条件完成后才分批部署。"
    return {"headlineCN": headline, "bulletsCN": points, "strategyCN": strategy}


def mmf_score_from_fear_greed(fg):
    return round2(sum([row["contribution"] for row in fg.get("rows", [])]))


def quote_freshness(q, mode="live", market_session=None):
    raw = q.get("latestTime") or q.get("latestTradingDay")
    if mode != "live":
        return {"status": "REPLAY", "isStale": False, "asOf": raw, "ageMinutes": None, "noteCN": "历史回放数据，不按实时标准判断。"}
    try:
        ts = pd.to_datetime(raw, utc=True)
        now = pd.Timestamp.now(tz="UTC")
        age_minutes = max(0, round((now - ts).total_seconds() / 60, 1))
        session = (market_session or {}).get("session")
        stale_limit = 180 if session in {"pre-market", "regular", "after-hours"} else 1080
        stale = age_minutes > stale_limit
    except Exception:
        age_minutes = None
        stale = True
    status = "STALE" if stale else "LIVE"
    note = (
        f"行情截至 {raw}，距当前约 {age_minutes} 分钟；已冻结可执行仓位与旧价格路径。"
        if stale else f"行情截至 {raw}，当前可用于实时决策。"
    )
    return {"status": status, "isStale": stale, "asOf": raw, "ageMinutes": age_minutes, "noteCN": note}


def quote_data_quality(q, mode="live"):
    if mode != "live":
        return {"status": "REPLAY", "isUsableForExecution": True, "issuesCN": [], "noteCN": "历史回放按已完成K线处理。"}
    issues = []
    warnings = []
    volume = q.get("volumeRaw")
    if not isinstance(volume, (int, float, np.integer, np.floating)) or float(volume) <= 0:
        issues.append("当前时段成交量缺失；0不代表真实缩量。")
    if q.get("prevClose") is None:
        issues.append("缺少前收盘，日涨跌幅口径不完整。")
    session = q.get("session")
    if session == "extended":
        warnings.append("当前属于扩展/夜间时段，不能与常规时段OHLCV混成完整日线；量价确认需等待常规时段。")
    usable = not issues
    return {
        "status": "PASS" if usable else "LIMITED",
        "isUsableForExecution": usable,
        "issuesCN": issues + warnings,
        "noteCN": ("；".join(warnings) + " 可用于赔率与价格位置判断，但不能确认盘中量价。" if warnings else "数据可用于执行判断。") if usable else "；".join(issues) + " 已冻结量价确认和可执行仓位。",
    }


def us_market_session(mode="live"):
    if mode != "live":
        return {"isTradingWindow": True, "session": "replay", "labelCN": "历史报告"}
    now_et = datetime.now(ZoneInfo("America/New_York"))
    minute = now_et.hour * 60 + now_et.minute
    weekday = now_et.weekday() < 5
    if weekday and 240 <= minute < 570:
        session, label = "pre-market", "盘前"
    elif weekday and 570 <= minute < 960:
        session, label = "regular", "常规交易"
    elif weekday and 960 <= minute < 1200:
        session, label = "after-hours", "盘后"
    else:
        session, label = "closed", "休市时段"
    return {
        "isTradingWindow": session != "closed",
        "session": session,
        "labelCN": label,
        "asOfET": now_et.isoformat(),
        "windowCN": "美东工作日 04:00-20:00（盘前、常规、盘后）",
    }


def build_report(ticker, mode="live", replay_date=None, current_position_pct=0):
    ticker = ticker.upper()
    df = fetch_daily(ticker)
    if mode == "replay" and replay_date:
        cutoff = pd.to_datetime(replay_date).date()
        df = df[pd.to_datetime(df.Date).dt.date <= cutoff].copy()
        if len(df) < 80:
            raise RuntimeError("Not enough historical data for replay.")
    elif mode == "live":
        df = merge_live_quote(df, ticker)
    q = reconcile_quote_volume(quote(df, ticker=ticker if mode == "live" else None), df)
    market_session = us_market_session(mode)
    freshness = quote_freshness(q, mode, market_session)
    data_quality = quote_data_quality(q, mode)
    shared_market = shared_market_data(ticker)
    shared_quotes = shared_market["quotes"]
    etf = etf_weights(ticker, shared_quotes)
    sec = sector_rotation(shared_quotes)
    heat = sector_heatmap(ticker, shared_quotes)
    mac = macro_panel(shared_quotes, shared_market["vix"])
    comparison_frames, comparison_failures = comparison_histories(ticker, df)
    relative_strength_ctx = relative_strength_matrix(comparison_frames)
    capital_rotation_ctx = capital_rotation_layer(heat, relative_strength_ctx)
    fg = fear_greed_attribution(df, sec, mac, etf)
    fib = fibonacci_resonance(df)
    vol_ctx = volume_context(df, q)
    if q.get("session") == "extended":
        regular_volume_note = vol_ctx.get("headlineCN")
        vol_ctx.update({
            "available": False,
            "ratio": None,
            "qualityCN": "扩展时段缺少独立增量成交量",
            "headlineCN": f"最近常规时段量能仅作背景参考：{regular_volume_note} 扩展时段没有独立增量成交量，不能用它确认当前价格。",
            "moneyActionCN": "当前扩展时段量价关系不可判断。",
            "nextMoveCN": "等待下一常规时段的价格与成交量共同确认。",
        })
    volume_structure = volume_structure_read(df, q, vol_ctx, sec, mac)
    intraday_df = None
    intraday_error = None
    if mode == "live":
        try:
            intraday_df = fetch_intraday_5m(ticker)
        except Exception as e:
            intraday_error = str(e)[:140]
    intra = intraday_battle(df, q, intraday_df)
    auction_ctx = intraday_auction_structure(intra, q, vol_ctx)
    opt_ctx = options_context(ticker, q)
    news_ctx = news_context(ticker, q, sec, etf, vol_ctx)
    earnings_ctx = earnings_calendar_context(ticker, mode=mode)
    market_structure_ctx = adaptive_market_structure(df, q, fib)
    systemic_risk_ctx = systemic_risk_filter(heat, relative_strength_ctx, mac)
    semiconductor_leadership_ctx = semiconductor_leadership_test(relative_strength_ctx, heat)
    catalyst_ctx = catalyst_and_risk_regime(news_ctx, market_structure_ctx, volume_structure, systemic_risk_ctx, earnings_ctx)
    macro_transmission_ctx = macro_transmission(mac, heat)
    structural_change_ctx = structural_change_review(market_structure_ctx, relative_strength_ctx, systemic_risk_ctx, volume_structure)
    smart = smart_money(df, q, vol_ctx)
    dims = dimensions(df, q, fg, mac, sec, smart, fib, vol_ctx, opt_ctx, news_ctx)
    mmf_score = mmf_score_from_fear_greed(fg)
    last = df.iloc[-1]
    current_price = float(q.get("close") or q.get("last") or last.Close)
    high20 = float(df.tail(20).High.max())
    low20 = float(df.tail(20).Low.min())
    true_range = pd.concat([(df.High-df.Low), (df.High-df.Close.shift()).abs(), (df.Low-df.Close.shift()).abs()], axis=1).max(axis=1)
    atr14 = float(true_range.tail(14).mean()) if len(true_range.dropna()) else current_price * 0.08
    rr_up = max(0, high20 - current_price)
    rr_down = max(current_price - low20, atr14 * 1.5, current_price * 0.08)
    reward_risk = min(8.0, round2(rr_up / rr_down)) if rr_down > 0 else 1.0
    risk_reward = round2(rr_down / rr_up) if rr_up and rr_up > 0 else None
    reward_risk_note = f"Reward/Risk={reward_risk}：上方参考为20日高点，下方风险至少取1.5×ATR14或现价8%，并封顶8倍，避免靠近前低时分母失真。"
    ema20_value = float(last.EMA20) if pd.notna(last.EMA20) else current_price
    first_rebound_up = min(rr_up, max(0, ema20_value - current_price, atr14 * 1.2))
    tactical_down = max(atr14, current_price * 0.10)
    tactical_reward_risk = round2(clip(first_rebound_up / tactical_down if tactical_down else 0, 0, 5))
    tactical_target = round2(current_price + first_rebound_up)
    recovery_reward_risk = reward_risk
    vacation = freshness["isStale"] or not data_quality["isUsableForExecution"] or mmf_score < 45 or tactical_reward_risk < 1.35
    execution_blocked = freshness["isStale"] or not data_quality["isUsableForExecution"]
    account_state_ctx = account_state(ticker, df, q, tactical_reward_risk, mmf_score, vacation, current_position_pct=current_position_pct)
    intraday_decision_ctx = intraday_decision(df, q, fg, sec, mac, fib, tactical_reward_risk, mmf_score, vacation, volume_structure)
    position_engineering_ctx = position_engineering(ticker, df, q, tactical_reward_risk, mmf_score, sec, mac, volume_structure, current_position_pct=account_state_ctx.get("currentPositionPct", 15))
    if systemic_risk_ctx["status"] == "HIGH":
        position_engineering_ctx["positionTier"] = "Systemic Defense / 系统防御"
        position_engineering_ctx["maxTacticalPositionPct"] = 0
        position_engineering_ctx["dynamicSuggestedRangePct"] = {"low": 0, "high": 0}
        position_engineering_ctx["extensionCapPct"] = 0
        position_engineering_ctx["trendPermission"] = "NO"
        position_engineering_ctx["riskRegimeGate"] = {
            **(position_engineering_ctx.get("riskRegimeGate") or {}),
            "status": "FAIL",
            "statusCN": "关闭：跨市场系统风险确认",
            "failReasonsCN": systemic_risk_ctx.get("signals", []),
        }
        position_engineering_ctx["deploymentMetrics"]["riskRegime"] = {"score": 1.0, "stars": "★☆☆☆☆", "labelCN": "风险环境（系统防御）"}
        position_engineering_ctx["deploymentMetrics"]["deploymentQuality"] = {"score": 1.0, "stars": "★☆☆☆☆", "labelCN": "部署质量（系统风险关闭）"}
    elif systemic_risk_ctx["status"] == "ELEVATED" and (position_engineering_ctx.get("riskRegimeGate") or {}).get("status") == "PASS":
        position_engineering_ctx["riskRegimeGate"] = {
            **position_engineering_ctx["riskRegimeGate"],
            "status": "CAUTION",
            "statusCN": "谨慎：部分跨市场风险确认",
            "warningsCN": systemic_risk_ctx.get("signals", []),
        }
    if earnings_ctx.get("isCriticalWindow"):
        position_engineering_ctx["trendPermission"] = "NO"
        position_engineering_ctx["riskRegimeGate"] = {
            **(position_engineering_ctx.get("riskRegimeGate") or {}),
            "status": "CAUTION",
            "statusCN": "谨慎：关键权重股进入财报高风险窗",
            "warningsCN": [earnings_ctx.get("summaryCN"), earnings_ctx.get("actionCN")],
        }
        position_engineering_ctx.setdefault("decisionReviewCN", []).append("财报高风险窗覆盖趋势仓许可；事件公布前保留跳空风险预算。")
    position_engineering_ctx["earningsRisk"] = earnings_ctx
    if execution_blocked:
        theoretical_range = dict(position_engineering_ctx.get("dynamicSuggestedRangePct") or {})
        theoretical_cap = position_engineering_ctx.get("extensionCapPct")
        position_engineering_ctx["theoreticalPositionTier"] = position_engineering_ctx.get("positionTier")
        position_engineering_ctx["theoreticalSuggestedRangePct"] = theoretical_range
        position_engineering_ctx["theoreticalExtensionCapPct"] = theoretical_cap
        block_reason = freshness["noteCN"] if freshness["isStale"] else data_quality["noteCN"] if not data_quality["isUsableForExecution"] else "Market Vacation生效：MMF环境尚未达到执行门槛。"
        position_engineering_ctx["positionTier"] = "Execution Frozen / 当前不可执行"
        position_engineering_ctx["maxTacticalPositionPct"] = 0
        position_engineering_ctx["dynamicSuggestedRangePct"] = {"low": 0, "high": 0}
        position_engineering_ctx["extensionCapPct"] = 0
        position_engineering_ctx["trendPermission"] = "NO"
        position_engineering_ctx["riskRegimeGate"] = {**(position_engineering_ctx.get("riskRegimeGate") or {}), "status": "FAIL", "statusCN": "关闭：当前不可执行", "failReasonsCN": [block_reason]}
        position_engineering_ctx["readCN"] = block_reason + f" 理论层级为{position_engineering_ctx['theoreticalPositionTier']}、理论区间{theoretical_range.get('low')}%-{theoretical_range.get('high')}%，但当前执行上限为0%。"
        position_engineering_ctx["deploymentMetrics"]["deploymentQuality"] = {"score": 1.0, "stars": "★☆☆☆☆", "labelCN": "部署质量（当前不可执行）"}
    vacation_state_ctx = market_vacation_state_machine(
        vacation,
        market_structure_ctx,
        semiconductor_leadership_ctx,
        systemic_risk_ctx,
        catalyst_ctx,
        vol_ctx,
        execution_blocked=execution_blocked,
    )
    scenario_model_ctx = four_scenario_model(
        market_structure_ctx,
        semiconductor_leadership_ctx,
        capital_rotation_ctx,
        systemic_risk_ctx,
        catalyst_ctx,
        vol_ctx,
        auction_ctx,
    )
    scenario_ctx = scenario_model_ctx["scenarios"]
    behavior_ctx = strategic_behavior_map(ticker, q, fib, heat, mac, scenario_ctx, volume_structure, account_state_ctx, df)
    enemy_review_ctx = enemy_intent_review(q, mac, sec, heat, volume_structure, position_engineering_ctx, behavior_ctx)
    candle = candle_read(last)
    high_low_change = q.get("highLowChangePct")
    open_close_change = q.get("openCloseChangePct")
    extended_session = q.get("session") == "extended"
    range_note = ("当前为扩展/夜间价格快照；数据源未提供可靠的独立时段成交量，常规时段与夜间OHLC不合并解读。" if extended_session else f"高低区间：最高 {q.get('high')}，最低 {q.get('low')}，从最高到最低回撤 {high_low_change}%。")
    prev_close_change = q.get("prevCloseChangePct")
    open_close_note = f"价格变化：前收→当前 {prev_close_change if prev_close_change is not None else '--'}%；Open→Close {open_close_change if open_close_change is not None else q.get('changePct')}%。前者用于判断当日损益冲击，后者用于判断盘内资金行为。"
    summary = f"{'夜间快照' if extended_session else '今天'} {ticker} 当前/收盘 {q['close']}，前收→当前变化 {prev_close_change if prev_close_change is not None else '--'}%。{range_note} {'' if extended_session else 'K线为：'+candle+' '}{vol_ctx['headlineCN']}"
    if etf.get("mainDrag"):
        summary += f" 权重影响上，{etf['mainDrag']['ticker']} 是主要拖累。"
    wdf = resample_weekly(df)
    mdf = resample_monthly(df)
    for dfx in (wdf, mdf):
        dfx["EMA20"] = dfx["Close"].ewm(span=20, adjust=False).mean()
        dfx["EMA50"] = dfx["Close"].ewm(span=50, adjust=False).mean()
    ex = executive_summary(ticker, q, mmf_score, fg, vacation, etf, sec, account_state_ctx)
    intraday_chart = None if intra.get("mode") == "real_5m" else intraday_candlestick_proxy(intra["phases"], q.get("open") or q.get("close"), f"{ticker} Intraday 5m Proxy Candles")
    charts = {
        "daily": candlestick(df, f"{ticker} Daily Candlestick", rows=120, figsize=(12, 5.8)),
        "weekly": candlestick(wdf, f"{ticker} Weekly Trend", rows=90, figsize=(8, 4)),
        "monthly": candlestick(mdf, f"{ticker} Monthly Trend", rows=72, figsize=(8, 4)),
        "intraday": intraday_chart,
    }
    ema20 = round2(last.EMA20)
    near_reclaim = round2(current_price * 1.045)
    near_defense = round2(current_price * 0.96)
    checklist = [
        freshness["noteCN"],
        f"近端收复位：{near_reclaim}；先看能否站回并守住，不要求一天拉回EMA20。",
        f"近端风险线：{near_defense}；跌破且无法快速收回则继续等待。",
        f"日线EMA20 {ema20} 属于中期趋势修复参考，不是明日必须触发的目标。",
        "NVDA / AVGO / SMH 是否同步修复",
        "量能是否真正承认方向，前收跌幅与盘内跌幅必须分开解读",
        "Risk Regime Gate 是否重新打开；未打开时新增仓位仍为0%",
        f"财报日历：{earnings_ctx.get('summaryCN') or earnings_ctx.get('reasonCN')} 风险级别={earnings_ctx.get('riskLevel')}。",
    ]
    executable_cap = float(position_engineering_ctx.get("maxTacticalPositionPct") or 0)
    current_position = float(account_state_ctx.get("currentPositionPct") or 0)
    if executable_cap <= 0:
        recommended_action = f"建议行动：当前已有 {round2(current_position)}% 仓位；新增仓位维持0%。先等价格站回 {near_reclaim} 并守住，同时 NVDA / AVGO / SMH 同步修复；若跌破 {near_defense} 后无法快速收回，优先降低风险。" if current_position > 0 else f"建议行动：新增仓位维持0%；先等价格站回 {near_reclaim} 并守住，同时 NVDA / AVGO / SMH 同步修复。若跌破 {near_defense} 后无法快速收回，继续等待。"
    elif current_position > 0:
        remaining_room = round2(max(0, executable_cap - current_position))
        position_state = "已接近模型上限" if remaining_room <= 3 else "仍保留少量模型空间"
        recommended_action = f"建议行动：当前已有 {round2(current_position)}% 仓位，{position_state}；先管理现有仓位，不再按空仓逻辑建观察仓。只有站回 {near_reclaim} 且量能与半导体权重同步时，才讨论最多 {remaining_room}% 的剩余空间；跌破 {near_defense} 且无法收回则停止新增并降低风险。"
    elif vacation:
        probe_high = round2(min(executable_cap, 10))
        probe_low = round2(min(5, probe_high))
        session_name = (market_session or {}).get("session")
        timing_prefix = "计划层：空仓者可在下一常规交易时段考虑" if session_name != "regular" else "计划层：空仓者当前可考虑"
        recommended_action = f"{timing_prefix}{probe_low}%-{probe_high}%观察仓，不一次买满；当前时段能否立刻执行，以盘中执行许可为准。站回 {near_reclaim} 且量能与半导体权重同步后才使用下一档仓位，跌破 {near_defense} 则停止新增。"
    else:
        recommended_action = f"建议行动：按0%-{round2(executable_cap)}%上限分批部署，不一次买满；第一批只在 {near_reclaim} 上方获得价格与量能确认后执行，跌破 {near_defense} 后无法收回则暂停计划。"
    if earnings_ctx.get("isCriticalWindow"):
        recommended_action = f"建议行动：{earnings_ctx.get('actionCN')} 当前已有 {round2(current_position)}% 仓位；财报公布前暂停新增方向仓，先确认可承受的隔夜跳空风险。"
    initiative_ctx = initiative_management(df, q, position_engineering_ctx, account_state_ctx, behavior_ctx, intra, market_session, volume_structure)
    field_evolution_ctx = field_evolution_review(ticker, df, q, fg, sec, mac, volume_structure, position_engineering_ctx, scenario_ctx, initiative_ctx)
    final_daily_ctx = final_daily_output(
        capital_rotation_ctx,
        relative_strength_ctx,
        semiconductor_leadership_ctx,
        market_structure_ctx,
        auction_ctx,
        systemic_risk_ctx,
        scenario_model_ctx,
        structural_change_ctx,
        vacation_state_ctx,
        vol_ctx,
        catalyst_ctx,
        earnings_ctx,
    )
    strategic_401k_ctx = build_401k_strategic_module(
        macro_context=macro_transmission_ctx,
        systemic_context=systemic_risk_ctx,
        as_of=str(pd.to_datetime(last.Date).date()),
    )
    report = {
        "meta": {"project": "Miao Market Framework", "codename": "Project Sun Tzu", "edition": "Global Battlefield Edition", "version": VERSION, "ticker": ticker, "date": str(pd.to_datetime(last.Date).date()), "mode": mode, "quoteSource": q.get("source"), "quoteDate": q.get("latestTradingDay"), "quoteTime": q.get("latestTime"), "dataFreshness": freshness, "dataQuality": data_quality, "marketSession": market_session},
        "executiveSummary": {"headlineCN": ex["headlineCN"], "bulletsCN": ex["bulletsCN"], "strategyCN": ex["strategyCN"], "mmfScore": mmf_score, "marketTemperature": fg["score"], "entryQuality": position_engineering_ctx["deploymentMetrics"]["entryTiming"]["stars"], "entryTiming": position_engineering_ctx["deploymentMetrics"]["entryTiming"], "trendConfirmation": position_engineering_ctx["deploymentMetrics"]["trendConfirmation"], "priceDiscountQuality": position_engineering_ctx["deploymentMetrics"]["priceDiscount"], "deploymentQuality": position_engineering_ctx["deploymentMetrics"]["deploymentQuality"], "rewardRiskQuality": position_engineering_ctx["deploymentMetrics"]["rewardRisk"], "rewardRisk": tactical_reward_risk, "executableRewardRisk": tactical_reward_risk, "recoveryRewardRisk": recovery_reward_risk, "riskReward": tactical_reward_risk, "riskOverReward": round2(1/tactical_reward_risk) if tactical_reward_risk else None, "rewardRiskNoteCN": f"战术赔率={tactical_reward_risk}：现价 {round2(current_price)} 至首个动态反弹目标 {tactical_target}，风险距离取 ATR14 与现价10%的较大值；恢复潜力赔率={recovery_reward_risk}（20日高点/ATR框架）。两者每天重算，执行优先使用战术赔率。", "marketVacation": "YES" if vacation_state_ctx["state"] == "MARKET VACATION" else "NO", "marketStatus": vacation_state_ctx["state"]},
        "accountState": account_state_ctx,
        "dailyBattlefield": {"dailyChart": None, "quote": q, "candleCN": candle, "fibSummaryCN": fib["summaryCN"], "technicalIndicators": {"rsi7": round2(last.get("RSI7")), "rsi14": round2(last.get("RSI14")), "macd": round2(last.get("MACD")), "macdSignal": round2(last.get("MACD_SIGNAL")), "ema20": round2(last.get("EMA20")), "ema50": round2(last.get("EMA50"))}},
        "intradayDecision": intraday_decision_ctx,
        "positionEngineering": position_engineering_ctx,
        "initiativeManagement": initiative_ctx,
        "fieldEvolution": field_evolution_ctx,
        "relativeStrengthMatrix": relative_strength_ctx,
        "capitalRotation": capital_rotation_ctx,
        "adaptiveMarketStructure": market_structure_ctx,
        "intradayAuctionStructure": auction_ctx,
        "systemicRiskFilter": systemic_risk_ctx,
        "semiconductorLeadership": semiconductor_leadership_ctx,
        "catalystRegime": catalyst_ctx,
        "earningsCalendar": earnings_ctx,
        "strategic401k": strategic_401k_ctx,
        "macroTransmission": macro_transmission_ctx,
        "structuralChange": structural_change_ctx,
        "marketVacationStateMachine": vacation_state_ctx,
        "mmf10DailyOutput": final_daily_ctx,
        "dailyReplay": {
            "title": f"{ticker} Daily Replay",
            "summary": summary,
            "whatHappenedCN": summary,
            "rangeMoveCN": range_note,
            "openCloseMoveCN": open_close_note,
            "marketInterpretationCN": (
                "当前仍是休战等待：价格尚未获得趋势、量能与板块领导力的共同确认，单日反弹或下跌都不足以单独改变部署级别。"
                if vacation_state_ctx["state"] == "MARKET VACATION"
                else "当前属于观察或战术阶段：可以依据确认条件管理仓位，但不能把单日波动直接升级为趋势结论。"
            ),
            "whyCN": f"技术位置上，现价 {round2(current_price)}、EMA20 {round2(last.EMA20)}、RSI14 {round2(last.get('RSI14'))}；量价证据：{vol_ctx['headlineCN']} 这些数据解释当前结构，不预测下一根K线。",
            "whoCausedCN": f"权重层面主要拖累为 {(etf.get('mainDrag') or {}).get('ticker') or '待确认'}，主要支撑为 {(etf.get('mainSupport') or {}).get('ticker') or '待确认'}；板块处于 {sec.get('mode')}，后续是否扩散决定这次波动能否延续。",
            "positioningCN": recommended_action,
            "invalidCN": f"若放量跌破 {near_defense} 且无法快速收回，停止新增并重跑MMF；若站回 {near_reclaim} 后量能与NVDA/AVGO/SMH同步修复，则下调防御级别。",
            "tomorrowCN": f"下一常规交易时段只确认四件事：{near_reclaim} 能否被接受、{near_defense} 能否守住、量能是否承认方向、半导体权重是否同步。",
            "conclusionCN": "复盘结论以“盘面含义—原因—行动—作废条件”四段为唯一版本。",
            "strategic401kCN": strategic_401k_ctx["dailySummaryCN"],
            "strategic401kEN": strategic_401k_ctx["dailySummaryEN"],
        },
        "charts": charts,
        "etfWeights": etf,
        "intradayBattle": intra,
        "weeklyAnalysis": weekly_analysis(wdf),
        "monthlyAnalysis": monthly_analysis(mdf),
        "fearGreed": fg,
        "fibonacci": fib,
        "macro": mac,
        "sectorRotation": sec,
        "sectorHeatmap": heat,
        "smartMoney": smart,
        "optionsContext": opt_ctx,
        "newsContext": news_ctx,
        "volumeRead": vol_ctx,
        "volumeStructure": volume_structure,
        "warriorDoctrine": warrior_doctrine(df, q, fg, mac, smart, fib, vol_ctx, tactical_reward_risk, vacation),
        "dimensions": dims,
        "scenarioEngine": scenario_ctx,
        "scenarioModel": scenario_model_ctx,
        "strategicBehaviorMap": behavior_ctx,
        "enemyIntentReview": enemy_review_ctx,
        "tomorrowChecklist": checklist,
        "marketVacation": {"status": vacation_state_ctx["state"], "cashSuggestion": "70%-90%" if vacation_state_ctx["state"] == "MARKET VACATION" else "50%-80%" if vacation_state_ctx["state"] == "OBSERVATION" else "30%-70%", "reasonCN": vacation_state_ctx["reasonCN"], "transitions": vacation_state_ctx["transitions"]},
        "philosophy": {
            "titleCN": "MMF Philosophy v2.0 / Sun Tzu Market Philosophy",
            "mottoCN": "交易的目标不是预测市场。交易的目标是：无论市场怎么走，我都不会输。",
            "marketCN": "先为不可胜，以待敌之可胜。先确保自己不会输，再等待市场犯错。",
            "survivalCN": "不败，由我决定；赚钱，交给市场决定。",
            "invincibleCN": "不败由我决定。",
            "profitCN": "赚钱交给市场决定。",
            "finalCN": "不可胜在己，可胜在敌。",
            "missionCN": "MMF不是一个预测市场的系统。MMF是在无法预测市场的情况下，依然能够长期生存、等待机会，并在市场犯错时获利的决策框架。",
            "processCN": [
                "第一原则：不败。先确保自己不会输，再等待市场犯错。",
                "市场不是预测游戏，而是Scenario游戏；MMF不问市场一定怎么走，只问如果这样走我怎么办。",
                "仓位比观点重要。判断正确可以赚钱，判断错误也必须继续有资格参加下一局。",
                "Market Vacation不是失败，而是主动放弃负EV游戏。",
                "技术分析不是预言工具，而是观察市场参与者行为：谁在买，谁在卖，谁更着急，谁更痛苦。",
                "市场是情报战。道是叙事，天是宏观，地是结构，将是参与者，法是纪律和仓位。",
                "不需要抄到底，只需要参与高赔率区间；风险有限，收益开放。",
                "不存在完美交易，只存在高质量交易：即使看错，仍然能够继续玩。",
                "最大的优势不是聪明，而是耐心；机会永远比资金多。",
                "不可胜在己，可胜在敌：不败由我决定，赚钱交给市场决定。",
                "Own Your Slice：市场永远会留下最后一段利润。MMF不追求吃完整个趋势，只追求赚到属于自己计划的那一段，然后离开；见好就收不是胆小，而是系统纪律。",
            ],
        },
        "dataIntegrity": {"tiingo": bool(os.getenv("TIINGO_API_KEY", "").strip()), "intraday5m": "real Tiingo IEX 5m OHLCV" if intraday_df is not None and not intraday_df.empty else "proxy fallback", "intradayError": intraday_error, "snapshot": "ok", "quoteVolumeSource": q.get("volumeSource") or "quote/daily source", "sharedMarketData": shared_market["meta"], "comparisonHistoryFailures": comparison_failures, "notes": "Shared quotes are prefetched once and reused across ETF, rotation, heatmap, macro, relative-strength, leadership, systemic-risk, and capital-flow modules. MMF v1.0.18 adds ticker-aware classification, a six-block decision layer, professional mechanism-based narrative, contextual Put/Call, explicit macro/geopolitical/OPEX transmission, four conditional paths, and complete review export."},
    }
    report["betaV110"] = build_beta_analysis(
        ticker=ticker,
        df=df,
        quote=q,
        volume=vol_ctx,
        heat=heat,
        options=opt_ctx,
        macro=mac,
        macro_transmission=macro_transmission_ctx,
        news=news_ctx,
        structure=market_structure_ctx,
        account=account_state_ctx,
        earnings=earnings_ctx,
        data_freshness=freshness,
    )
    report = apply_ticker_aware_overrides(report)
    if mode in ("snapshot", "replay"):
        save_snapshot(report)
    return ensure_strategic_behavior_map(report)


def analyze_ticker(ticker, mode="live", replay_date=None, current_position_pct=0):
    if mode == "snapshot":
        date = replay_date or str(pd.Timestamp.now(tz="America/Los_Angeles").date())
        try:
            r = load_snapshot(ticker, date)
            r["meta"]["replaySource"] = "snapshot"
            return ensure_strategic_behavior_map(r)
        except FileNotFoundError:
            r = build_report(ticker, mode="snapshot", replay_date=replay_date, current_position_pct=current_position_pct)
            r["meta"]["replaySource"] = "auto-generated"
            return r
    if mode == "replay" and replay_date:
        try:
            r = load_snapshot(ticker, replay_date)
            r["meta"]["replaySource"] = "snapshot"
            return ensure_strategic_behavior_map(r)
        except FileNotFoundError:
            r = build_report(ticker, mode="replay", replay_date=replay_date, current_position_pct=current_position_pct)
            r["meta"]["replaySource"] = "auto-generated"
            return r
    return build_report(ticker, mode=mode, replay_date=replay_date, current_position_pct=current_position_pct)
