import os
import json
from typing import Any

import requests


SYSTEM_PROMPT = """你是 MMF 平台内的战场问答官。
你只能解释用户提供的 MMF report/context，不能联网，不能编造外部新闻，不能声称确定预测。
MMF 是交易决策支持系统，不是自动交易系统，也不是投资顾问。
回答时必须区分市场层结论和账户层仓位，不要把建议仓位写成必须买满。
如果数据不足，直接说缺少哪项数据。默认用中文，交易台风格，简洁、克制，控制在 300 个中文字符以内。"""


def _pick(data: dict[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = data
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def compact_report_context(report: dict[str, Any], account: dict[str, Any] | None = None) -> dict[str, Any]:
    ex = _pick(report, "executiveSummary", {}) or {}
    quote = _pick(report, "dailyBattlefield.quote", {}) or {}
    tech = _pick(report, "dailyBattlefield.technicalIndicators", {}) or {}
    decision = _pick(report, "intradayDecision", {}) or {}
    volume = decision.get("volumeStructure") if isinstance(decision, dict) else {}
    pe = _pick(report, "positionEngineering", {}) or {}
    fib = _pick(report, "fibonacci", {}) or {}
    warrior = _pick(report, "warriorDoctrine", {}) or {}
    vacation = _pick(report, "marketVacation", {}) or {}
    news = _pick(report, "newsContext", {}) or {}
    options = _pick(report, "optionsContext", {}) or {}
    macro = _pick(report, "macro", {}) or {}

    return {
        "meta": _pick(report, "meta", {}),
        "accountInput": account or {},
        "market": {
            "headlineCN": ex.get("headlineCN"),
            "bulletsCN": (ex.get("bulletsCN") or [])[:5],
            "strategyCN": ex.get("strategyCN"),
            "marketStatus": ex.get("marketStatus"),
            "mmfScore": ex.get("mmfScore"),
            "marketTemperature": ex.get("marketTemperature"),
            "entryQuality": ex.get("entryQuality"),
            "entryTiming": ex.get("entryTiming"),
            "trendConfirmation": ex.get("trendConfirmation"),
            "priceDiscountQuality": ex.get("priceDiscountQuality"),
            "deploymentQuality": ex.get("deploymentQuality"),
            "rewardRiskQuality": ex.get("rewardRiskQuality"),
            "rewardRisk": ex.get("rewardRisk") or ex.get("riskReward"),
        },
        "quote": {
            "source": quote.get("source"),
            "last": quote.get("last"),
            "close": quote.get("close"),
            "prevClose": quote.get("prevClose"),
            "prevCloseChangePct": quote.get("prevCloseChangePct"),
            "open": quote.get("open"),
            "high": quote.get("high"),
            "low": quote.get("low"),
            "volume": quote.get("volume"),
        },
        "technical": {
            "rsi7": tech.get("rsi7"),
            "rsi14": tech.get("rsi14"),
            "macd": tech.get("macd"),
            "macdSignal": tech.get("macdSignal"),
            "ema20": tech.get("ema20"),
            "ema50": tech.get("ema50"),
        },
        "intradayDecision": {
            "marketState": decision.get("marketState"),
            "decisionCN": decision.get("decisionCN"),
            "rating": decision.get("rating"),
            "suggestedPosition": decision.get("suggestedPosition"),
            "whyCN": decision.get("whyCN"),
            "actionCN": (decision.get("actionCN") or [])[:5],
            "volumeStructure": volume,
            "scenarios": (decision.get("scenarios") or [])[:3],
        },
        "positionEngineering": {
            "tradeQualityScore": pe.get("tradeQualityScore"),
            "marketQualityScore": pe.get("marketQualityScore"),
            "maxTacticalPositionPct": pe.get("maxTacticalPositionPct"),
            "cashBufferPct": pe.get("cashBufferPct"),
            "deploymentMetrics": pe.get("deploymentMetrics"),
            "readCN": pe.get("readCN"),
            "supportCN": pe.get("supportCN"),
            "conclusionCN": pe.get("conclusionCN"),
        },
        "warriorDoctrine": {
            "score": warrior.get("score"),
            "summaryCN": warrior.get("summaryCN"),
            "items": (warrior.get("items") or [])[:5],
        },
        "fibonacci": {
            "summaryCN": fib.get("summaryCN"),
            "clusters": (fib.get("clusters") or [])[:4],
        },
        "macro": {
            "status": macro.get("status"),
            "interpretationCN": macro.get("interpretationCN"),
        },
        "optionsContext": {
            "summaryCN": options.get("summaryCN"),
            "riskCN": options.get("riskCN"),
            "actionCN": options.get("actionCN"),
        },
        "newsContext": {
            "summaryCN": news.get("summaryCN"),
            "riskCN": news.get("riskCN"),
            "items": (news.get("items") or [])[:3],
        },
        "marketVacation": vacation,
    }


def ask_ollama(question: str, report: dict[str, Any], account: dict[str, Any] | None = None) -> dict[str, Any]:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    timeout = float(os.getenv("OLLAMA_TIMEOUT", "45"))
    context = compact_report_context(report, account)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "下面是当前 MMF 精简报告 JSON。请只基于它回答用户问题。\n"
                    f"MMF_CONTEXT:\n{json.dumps(context, ensure_ascii=False)}\n\n"
                    f"用户问题：{question}"
                ),
            },
        ],
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 360},
    }
    resp = requests.post(f"{base_url}/api/chat", json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    answer = ((data.get("message") or {}).get("content") or "").strip()
    return {
        "provider": "ollama",
        "model": model,
        "answer": answer,
        "done": data.get("done", True),
    }
