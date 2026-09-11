
from __future__ import annotations
import io, base64
import warnings
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D

warnings.filterwarnings("ignore", message=r"Glyph .* missing from font.*")

def _enc(buf):
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

def _nice_dates(dates, max_ticks=6):
    if len(dates) <= max_ticks:
        idx = list(range(len(dates)))
    else:
        step = max(1, len(dates)//max_ticks)
        idx = list(range(0, len(dates), step))
        if idx[-1] != len(dates)-1:
            idx.append(len(dates)-1)
    labels = [pd.to_datetime(dates.iloc[i]).strftime("%b %d") for i in idx]
    return idx, labels

def candlestick(df, title, rows=120, figsize=(12,5.6)):
    """
    v3.0: pure matplotlib candlestick renderer.
    This avoids mplfinance marketcolors validator errors completely.
    Green = up candle, red = down candle, cyan = MA20, gray = MA50.
    """
    d = df.tail(rows).copy().reset_index(drop=True)
    for col in ["Open","High","Low","Close","Volume"]:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    d = d.dropna(subset=["Open","High","Low","Close"]).reset_index(drop=True)
    if d.empty:
        return None

    d["MA20"] = d["Close"].rolling(20).mean()
    d["MA50"] = d["Close"].rolling(50).mean()

    x = list(range(len(d)))
    buf = io.BytesIO()
    fig = plt.figure(figsize=figsize)
    fig.patch.set_facecolor("#0B1020")
    gs = fig.add_gridspec(4, 1, hspace=0.05)
    ax = fig.add_subplot(gs[:3, 0])
    axv = fig.add_subplot(gs[3, 0], sharex=ax)

    for a in (ax, axv):
        a.set_facecolor("#0B1020")
        a.grid(True, color="#273247", alpha=0.62, linewidth=0.8)
        for s in a.spines.values():
            s.set_color("#273247")
        a.tick_params(colors="#AAB4C3")

    width = 0.62
    for i, row in d.iterrows():
        o,h,l,c = row["Open"], row["High"], row["Low"], row["Close"]
        color = "#2ECC71" if c >= o else "#E74C3C"
        ax.vlines(i, l, h, color=color, linewidth=1.1, alpha=0.95)
        y = min(o,c)
        height = abs(c-o)
        if height == 0:
            height = max((h-l)*0.015, 0.01)
        ax.add_patch(Rectangle((i-width/2, y), width, height, facecolor=color, edgecolor=color, alpha=0.9))
        vol = row.get("Volume", 0) or 0
        axv.bar(i, vol, color=color, width=width, alpha=0.72)

    ax.plot(x, d["MA20"], color="#40C7D7", linewidth=1.6, label="MA20")
    ax.plot(x, d["MA50"], color="#A8B1C2", linewidth=1.6, label="MA50")
    ax.set_title(title, color="#E8EEF9", fontsize=14, weight="bold", pad=12)
    ax.set_ylabel("Price", color="#AAB4C3")
    axv.set_ylabel("Volume", color="#AAB4C3")
    axv.ticklabel_format(axis="y", style="sci", scilimits=(6,6))
    axv.yaxis.get_offset_text().set_color("#AAB4C3")

    handles = [
        Line2D([0],[0], color="#2ECC71", lw=6, label="Up Candle"),
        Line2D([0],[0], color="#E74C3C", lw=6, label="Down Candle"),
        Line2D([0],[0], color="#40C7D7", lw=2, label="MA20"),
        Line2D([0],[0], color="#A8B1C2", lw=2, label="MA50"),
    ]
    leg = ax.legend(handles=handles, loc="upper left", fontsize=8, frameon=True)
    leg.get_frame().set_facecolor("#0B1020")
    leg.get_frame().set_edgecolor("#273247")
    for txt in leg.get_texts():
        txt.set_color("#E8EEF9")

    ticks, labels = _nice_dates(d["Date"])
    axv.set_xticks(ticks)
    axv.set_xticklabels(labels, rotation=35, ha="right", color="#AAB4C3")
    plt.setp(ax.get_xticklabels(), visible=False)

    ax.set_xlim(-1, len(d))
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=135, bbox_inches="tight")
    plt.close(fig)
    return _enc(buf)

def line(values, title, figsize=(7,2.8)):
    buf = io.BytesIO()
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("#0B1020")
    ax.set_facecolor("#0B1020")
    ax.plot(values, linewidth=2, color="#40C7D7")
    ax.set_title(title, color="#E8EEF9")
    ax.tick_params(colors="#AAB4C3")
    for s in ax.spines.values():
        s.set_color("#273247")
    ax.grid(True, color="#273247", alpha=.6)
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=135, bbox_inches="tight")
    plt.close(fig)
    return _enc(buf)

def gauge(score, title="MMF Fear & Greed Gauge", figsize=(6.8,3.4)):
    import numpy as np
    from matplotlib.patches import Wedge, Circle
    import matplotlib.patheffects as pe
    score = 50 if score is None else max(0, min(100, float(score)))
    buf = io.BytesIO()
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("#0B1020")
    ax.set_facecolor("#0B1020")
    ax.set_xlim(-1.25, 1.25)
    ax.set_ylim(-0.35, 1.2)
    ax.axis("off")

    bg = Circle((0, 0), 1.08, facecolor="#111A2B", edgecolor="#263247", linewidth=1.0, alpha=0.78)
    bg.set_path_effects([pe.SimplePatchShadow(offset=(0, -3), alpha=0.35, rho=0.95), pe.Normal()])
    ax.add_patch(bg)

    bands = [("#C0392B",0,20),("#E67E22",20,40),("#D7B56D",40,60),("#7CB342",60,80),("#2ECC71",80,100)]
    for color, lo, hi in bands:
        start = 180 - hi * 1.8
        end = 180 - lo * 1.8
        wedge = Wedge((0, 0), 1.0, start, end, width=0.23, facecolor=color, edgecolor="#0B1020", linewidth=2, alpha=0.96)
        wedge.set_path_effects([pe.SimplePatchShadow(offset=(0, -1.8), alpha=0.26), pe.Normal()])
        ax.add_patch(wedge)
        shine = Wedge((0, 0), 1.0, start, end, width=0.08, facecolor="#FFFFFF", edgecolor="none", alpha=0.08)
        ax.add_patch(shine)

    theta = np.deg2rad(180 - score * 1.8)
    needle_len = 0.84
    x = np.cos(theta) * needle_len
    y = np.sin(theta) * needle_len
    needle = ax.plot([0, x], [0, y], color="#FFFFFF", linewidth=4.5, solid_capstyle="round")[0]
    needle.set_path_effects([pe.SimpleLineShadow(offset=(0, -2), alpha=0.45), pe.Normal()])
    ax.add_patch(Circle((0, 0), 0.085, facecolor="#E8EEF9", edgecolor="#FFFFFF", linewidth=1.4))

    label = "Extreme Fear" if score < 20 else "Fear" if score < 40 else "Neutral" if score < 60 else "Greed" if score < 80 else "Extreme Greed"
    ax.text(0, 0.35, f"{score:.0f}", ha="center", va="center", color="#E8EEF9", fontsize=34, fontweight="bold")
    ax.text(0, 0.16, label, ha="center", va="center", color="#D7B56D", fontsize=13, fontweight="bold")
    ax.text(0, -0.12, title, ha="center", va="center", color="#AAB4C3", fontsize=10)
    ax.text(-1.04, -0.04, "恐惧", ha="center", va="center", color="#AAB4C3", fontsize=9)
    ax.text(1.04, -0.04, "贪婪", ha="center", va="center", color="#AAB4C3", fontsize=9)
    ax.text(0, 1.03, "中性", ha="center", va="center", color="#AAB4C3", fontsize=9)
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=135, bbox_inches="tight")
    plt.close(fig)
    return _enc(buf)

def intraday_candlestick_proxy(phases, start_price, title="Intraday 5m Battle Proxy", figsize=(10,4.2)):
    """
    Draws a candlestick-style proxy for the intraday battle.
    It uses numeric time labels instead of Chinese labels to avoid font glyph issues.
    """
    labels = ["09:30", "10:30", "13:00", "15:30"][:len(phases)]
    rows = []
    price = float(start_price or 100)
    for i, p in enumerate(phases):
        change = float(p.get("changeProxy") or 0) / 100
        o = price
        c = max(0.01, o * (1 + change))
        wiggle = max(abs(c - o) * 0.45, o * 0.004)
        h = max(o, c) + wiggle
        l = min(o, c) - wiggle
        rows.append({"Open": o, "High": h, "Low": l, "Close": c, "Volume": 1 + i * 0.2})
        price = c
    if not rows:
        return None
    d = pd.DataFrame(rows)
    d["EMA20"] = d["Close"].ewm(span=3, adjust=False).mean()
    typical = (d["High"] + d["Low"] + d["Close"]) / 3
    d["VWAP"] = (typical * d["Volume"]).cumsum() / d["Volume"].cumsum()
    buf = io.BytesIO()
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("#0B1020")
    ax.set_facecolor("#0B1020")
    width = 0.55
    for i, row in d.iterrows():
        o,h,l,c = row["Open"], row["High"], row["Low"], row["Close"]
        color = "#2ECC71" if c >= o else "#E74C3C"
        ax.vlines(i, l, h, color=color, linewidth=1.3)
        body_y = min(o, c)
        body_h = abs(c - o) or max((h-l)*0.02, 0.01)
        ax.add_patch(Rectangle((i-width/2, body_y), width, body_h, facecolor=color, edgecolor=color, alpha=0.92))
    ax.plot(range(len(d)), d["VWAP"], color="#D7B56D", linewidth=1.8, label="VWAP")
    ax.plot(range(len(d)), d["EMA20"], color="#40C7D7", linewidth=1.8, label="EMA20")
    ax.set_title(title, color="#E8EEF9", fontsize=14, weight="bold")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, color="#AAB4C3")
    ax.tick_params(colors="#AAB4C3")
    ax.set_ylabel("Proxy Price", color="#AAB4C3")
    for s in ax.spines.values():
        s.set_color("#273247")
    ax.grid(True, color="#273247", alpha=.6)
    leg = ax.legend(loc="upper left", fontsize=8, frameon=True)
    leg.get_frame().set_facecolor("#0B1020")
    leg.get_frame().set_edgecolor("#273247")
    for txt in leg.get_texts():
        txt.set_color("#E8EEF9")
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=135, bbox_inches="tight")
    plt.close(fig)
    return _enc(buf)

def intraday_candlestick(df, title="Intraday 5m Battle", rows=96, figsize=(10,4.2)):
    d = df.tail(rows).copy().reset_index(drop=True)
    for col in ["Open","High","Low","Close","Volume","VWAP","EMA20"]:
        if col in d:
            d[col] = pd.to_numeric(d[col], errors="coerce")
    d = d.dropna(subset=["Open","High","Low","Close"]).reset_index(drop=True)
    if d.empty:
        return None

    x = list(range(len(d)))
    buf = io.BytesIO()
    fig = plt.figure(figsize=figsize)
    fig.patch.set_facecolor("#0B1020")
    gs = fig.add_gridspec(4, 1, hspace=0.05)
    ax = fig.add_subplot(gs[:3, 0])
    axv = fig.add_subplot(gs[3, 0], sharex=ax)

    for a in (ax, axv):
        a.set_facecolor("#0B1020")
        a.grid(True, color="#273247", alpha=0.62, linewidth=0.8)
        for s in a.spines.values():
            s.set_color("#273247")
        a.tick_params(colors="#AAB4C3")

    width = 0.58
    for i, row in d.iterrows():
        o,h,l,c = row["Open"], row["High"], row["Low"], row["Close"]
        color = "#2ECC71" if c >= o else "#E74C3C"
        ax.vlines(i, l, h, color=color, linewidth=1.0, alpha=0.95)
        body_y = min(o, c)
        body_h = abs(c - o) or max((h-l)*0.02, 0.01)
        ax.add_patch(Rectangle((i-width/2, body_y), width, body_h, facecolor=color, edgecolor=color, alpha=0.92))
        axv.bar(i, row.get("Volume", 0) or 0, color=color, width=width, alpha=0.66)

    if "VWAP" in d:
        ax.plot(x, d["VWAP"], color="#D7B56D", linewidth=1.7, label="VWAP")
    if "EMA20" in d:
        ax.plot(x, d["EMA20"], color="#40C7D7", linewidth=1.7, label="EMA20")

    ax.set_title(title, color="#E8EEF9", fontsize=14, weight="bold", pad=12)
    ax.set_ylabel("Price", color="#AAB4C3")
    axv.set_ylabel("Vol", color="#AAB4C3")
    axv.ticklabel_format(axis="y", style="sci", scilimits=(6,6))
    axv.yaxis.get_offset_text().set_color("#AAB4C3")

    if "Date" in d:
        if len(d) <= 6:
            ticks = list(range(len(d)))
        else:
            step = max(1, len(d)//6)
            ticks = list(range(0, len(d), step))
            if ticks[-1] != len(d)-1:
                ticks.append(len(d)-1)
        labels = [pd.to_datetime(d.loc[i, "Date"]).strftime("%H:%M") for i in ticks]
        axv.set_xticks(ticks)
        axv.set_xticklabels(labels, rotation=0, ha="center", color="#AAB4C3")

    handles = [
        Line2D([0],[0], color="#2ECC71", lw=6, label="Up Candle"),
        Line2D([0],[0], color="#E74C3C", lw=6, label="Down Candle"),
        Line2D([0],[0], color="#D7B56D", lw=2, label="VWAP"),
        Line2D([0],[0], color="#40C7D7", lw=2, label="EMA20"),
    ]
    leg = ax.legend(handles=handles, loc="upper left", fontsize=8, frameon=True)
    leg.get_frame().set_facecolor("#0B1020")
    leg.get_frame().set_edgecolor("#273247")
    for txt in leg.get_texts():
        txt.set_color("#E8EEF9")

    plt.setp(ax.get_xticklabels(), visible=False)
    ax.set_xlim(-1, len(d))
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=135, bbox_inches="tight")
    plt.close(fig)
    return _enc(buf)

def resample_weekly(df):
    return df.set_index("Date").resample("W").agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}).dropna().reset_index()

def resample_monthly(df):
    return df.set_index("Date").resample("ME").agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}).dropna().reset_index()
