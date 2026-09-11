from __future__ import annotations

import json
import os
import re
import smtplib
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "config" / "config.env")
REPORT_DIR = ROOT / "reports"
REPORT_DIR.mkdir(exist_ok=True)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
EMAIL_LANGUAGE_FILE = ROOT / "config" / "email_language.json"


def normalize_email_language(lang=None):
    return "en" if str(lang or "").strip().lower().startswith("en") else "cn"


def get_email_language_preference():
    env_lang = os.getenv("EMAIL_LANGUAGE", "").strip()
    if env_lang:
        return normalize_email_language(env_lang)
    try:
        payload = json.loads(EMAIL_LANGUAGE_FILE.read_text(encoding="utf-8"))
        return normalize_email_language(payload.get("language"))
    except (OSError, ValueError, TypeError):
        return "cn"


def set_email_language_preference(lang):
    language = normalize_email_language(lang)
    EMAIL_LANGUAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    EMAIL_LANGUAGE_FILE.write_text(
        json.dumps({"language": language}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return language


def _english_label(value):
    text = str(value or "--")
    exact = {
        "指数 / 成长": "Index / Growth",
        "半导体链": "Semiconductors",
        "通信服务": "Communication Services",
        "可选消费": "Consumer Discretionary",
        "新能源": "Clean Energy",
        "电动车 / 电池": "EV / Battery",
        "金融": "Financials",
        "防御 / 价值": "Defensive / Value",
        "工业 / 原材料": "Industrials / Materials",
        "房地产": "Real Estate",
        "宏观 / 避险": "Macro / Safe Havens",
    }
    if text in exact:
        return exact[text]
    return (
        text.replace("↑ 修复/偏强", "Repair / Bullish")
        .replace("↓ 偏弱/下降", "Weak / Bearish")
        .replace("→ 震荡/未确认", "Range / Unconfirmed")
        .replace(" / 深度赔率仓", "")
        .replace(" / 普通赔率仓", "")
        .replace(" / 趋势仓", "")
        .replace(" / 观察仓", "")
        .replace("Extreme / 极高", "Extreme")
        .replace("High / 高", "High")
        .replace("Weak / 弱", "Weak")
        .replace("Strong / 强", "Strong")
    )


def _render_email_cn_legacy(report):
    m = report["meta"]
    ex = report["executiveSummary"]
    r = report["dailyReplay"]
    vac = report["marketVacation"]
    version = m.get("version", "v3.0")
    lines = [
        f"【MMF每日复盘 {version}】{m['ticker']} | {m['date']} | 16:00 PST",
        "",
        "Miao Market Framework · 孙子计划",
        "交易不是预测，而是解析和布局。",
        "市场不是用来预测的，而是用来解读的。",
        "",
        "━━━━━━━━━━━━━━━━━━━",
        "今日结论",
        "━━━━━━━━━━━━━━━━━━━",
        f"MMF评分：{ex['mmfScore']} / 100",
        f"市场温度：{ex['marketTemperature']} / 100",
        f"市场状态：{ex['marketStatus']}",
        f"是否继续Market Vacation：{vac['status']}",
        f"Reward/Risk：{ex.get('rewardRisk', ex.get('riskReward'))}（上方空间/下方风险）",
        f"趋势确认：{(ex.get('trendConfirmation') or {}).get('stars')}（{(ex.get('trendConfirmation') or {}).get('score')}/5）",
        f"入场时机：{(ex.get('entryTiming') or {}).get('stars')}（{(ex.get('entryTiming') or {}).get('score')}/5）",
        f"价格折扣：{(ex.get('priceDiscountQuality') or {}).get('stars')}（{(ex.get('priceDiscountQuality') or {}).get('score')}/5）",
        f"部署质量：{(ex.get('deploymentQuality') or {}).get('stars')}（{(ex.get('deploymentQuality') or {}).get('score')}/5）",
        "",
        ex["headlineCN"],
        "",
        "核心要点：",
    ]
    for b in ex.get("bulletsCN", []):
        lines.append("• " + b)
    rs = report.get("relativeStrengthMatrix") or {}
    rotation = report.get("capitalRotation") or {}
    structure = report.get("adaptiveMarketStructure") or {}
    auction = report.get("intradayAuctionStructure") or {}
    systemic = report.get("systemicRiskFilter") or {}
    leadership = report.get("semiconductorLeadership") or {}
    catalyst = report.get("catalystRegime") or {}
    state_machine = report.get("marketVacationStateMachine") or {}
    scenario_model = report.get("scenarioModel") or {}
    daily_output = report.get("mmf10DailyOutput") or {}
    if rs or rotation or structure:
        lines += [
            "", "━━━━━━━━━━━━━━━━━━━", "MMF-10 结构与资金总判", "━━━━━━━━━━━━━━━━━━━",
            f"状态机：{state_machine.get('state')}；结构：{structure.get('regime')}；半导体领导力：{leadership.get('status')}；系统风险：{systemic.get('direction')} / {systemic.get('status')}",
            f"资金性质：{rotation.get('classification')}。{rotation.get('summaryCN', '')}",
            f"资金去向：{rotation.get('whereMoneyWentCN', '')}",
            f"微观区间：{(structure.get('micro') or {}).get('low')} - {(structure.get('micro') or {}).get('high')}；日线区间：{(structure.get('daily') or {}).get('low')} - {(structure.get('daily') or {}).get('high')}",
            f"事件风险：{catalyst.get('eventRisk')}；结构风险：{catalyst.get('structuralRisk')}；{catalyst.get('eventDataStatus', '')}",
            f"盘中拍卖：{auction.get('classification')}。{auction.get('summaryCN', '')}",
            "相对强弱矩阵（静态强弱 / 最近变化）：",
        ]
        for row in rs.get("rows", []):
            lines.append(f"• {row.get('relationship')}：{row.get('status')} / {row.get('change')}；20D {row.get('relative20dPct')}%；5D {row.get('recent5dPct')}%")
        lines.append(f"四情景概率合计：{scenario_model.get('probabilityTotal')}%（证据权重，不是预测）")
        for scenario in scenario_model.get("scenarios", []):
            lines.append(f"• {scenario.get('nameCN')}：{scenario.get('probability')}%；确认：{scenario.get('conditionCN')}；作废：{scenario.get('invalidCN')}")
        lines.append("每日12问：")
        for item in daily_output.get("answers", []):
            lines.append(f"• {item.get('question')} {item.get('answerCN')}")
    quote = (report.get("dailyBattlefield") or {}).get("quote") or {}
    tech = (report.get("dailyBattlefield") or {}).get("technicalIndicators") or {}
    candle = (report.get("dailyBattlefield") or {}).get("candleCN")
    if quote:
        lines += [
            "",
            "━━━━━━━━━━━━━━━━━━━",
            "每日战场概括",
            "━━━━━━━━━━━━━━━━━━━",
            f"价格：现价/收盘 {quote.get('close') or quote.get('last')}；当日变化 {quote.get('prevCloseChangePct', quote.get('changePct'))}%；区间 {quote.get('low')} - {quote.get('high')}。",
            f"成交量：{quote.get('volume')}；数据源：{quote.get('source')} / {quote.get('volumeSource')}",
        ]
        if candle:
            lines.append(f"K线：{candle}")
        if tech:
            lines.append(f"技术：RSI7 {tech.get('rsi7')} / RSI14 {tech.get('rsi14')}；EMA20 {tech.get('ema20')}；EMA50 {tech.get('ema50')}；MACD {tech.get('macd')} / Signal {tech.get('macdSignal')}")

    dec = report.get("intradayDecision") or {}
    if dec:
        lines += [
            "",
            "━━━━━━━━━━━━━━━━━━━",
            "盘中决策 MMF-10 概括",
            "━━━━━━━━━━━━━━━━━━━",
            f"状态：{dec.get('marketState')}；评级：{dec.get('rating')}；建议仓位：{dec.get('suggestedPosition')}",
            dec.get("decisionCN", ""),
            dec.get("whyCN", ""),
        ]
        vs = dec.get("volumeStructure") or {}
        if vs:
            lines.append(f"量价结构：{vs.get('labelCN')}（{vs.get('score')}/10）。{vs.get('readCN')}")
        for action in (dec.get("actionCN") or [])[:4]:
            lines.append("• " + action)

    behavior = report.get("strategicBehaviorMap") or {}
    if behavior:
        anchor = behavior.get("dynamicAnchorRange") or {}
        capital = behavior.get("capitalBehavior") or {}
        lines += [
            "",
            "━━━━━━━━━━━━━━━━━━━",
            behavior.get("titleCN", "市场行为分析"),
            "━━━━━━━━━━━━━━━━━━━",
            behavior.get("coreIdeaCN", ""),
            behavior.get("summaryCN", ""),
        ]
        if capital:
            lines += [
                "",
                "Capital Behavior / 资金行为",
                f"状态：{capital.get('postureCN')}；评分：{capital.get('score')}/10",
                capital.get("summaryCN", ""),
                capital.get("implicationCN", ""),
                capital.get("watchCN", ""),
                capital.get("accountCN", ""),
            ]
            for obs in (capital.get("observationsCN") or [])[:3]:
                lines.append("• " + obs)
        if anchor:
            lines += [
                f"动态区间：{anchor.get('low')} - {anchor.get('high')}；模式：{anchor.get('mode')}",
                f"上破重算：{anchor.get('breakoutAbove')}；下破重算：{anchor.get('breakdownBelow')}",
                anchor.get("basisCN", ""),
                anchor.get("validUntilCN", ""),
            ]
            for c in (anchor.get("supportCandidates") or [])[:3]:
                tag = "（强支撑）" if c.get("strength", 0) >= 3 else ""
                lines.append(f"• 支撑 {c.get('price')}：{c.get('label')}；强度 {c.get('strength')}{tag}")
            for c in (anchor.get("resistanceCandidates") or [])[:3]:
                lines.append(f"• 压力 {c.get('price')}：{c.get('label')}；强度 {c.get('strength')}")
        for c in (behavior.get("consensusNow") or [])[:3]:
            lines.append(f"• 共识：{c.get('beliefCN')} 证据：{c.get('evidenceCN')}")

    heat = report.get("sectorHeatmap") or {}
    if heat:
        leaders = "，".join([f"{x.get('ticker')} {x.get('changePct')}%" for x in (heat.get("leaders") or [])[:4]])
        laggards = "，".join([f"{x.get('ticker')} {x.get('changePct')}%" for x in (heat.get("laggards") or [])[:4]])
        lines += [
            "",
            "━━━━━━━━━━━━━━━━━━━",
            "板块轮动热力图概括",
            "━━━━━━━━━━━━━━━━━━━",
            f"模式：{heat.get('mode')}",
            heat.get("summaryCN", ""),
            f"主支撑：{leaders or '--'}",
            f"主拖累：{laggards or '--'}",
        ]

    fib = report.get("fibonacci") or {}
    if fib:
        lines += ["", "━━━━━━━━━━━━━━━━━━━", "Fibonacci 共振区概括", "━━━━━━━━━━━━━━━━━━━", fib.get("summaryCN", "")]
        for c in (fib.get("clusters") or [])[:4]:
            lines.append(f"• {c.get('low')} - {c.get('high')}；中心 {c.get('mid')}；次数 {c.get('count')}；距离 {c.get('distance')}")

    macro = report.get("macro") or {}
    sector = report.get("sectorRotation") or {}
    if macro or sector:
        lines += [
            "",
            "━━━━━━━━━━━━━━━━━━━",
            "宏观 / 板块概括",
            "━━━━━━━━━━━━━━━━━━━",
            f"宏观状态：{macro.get('status')}",
            macro.get("vixNoteCN", ""),
            f"板块模式：{sector.get('mode')}",
            sector.get("flowCN", ""),
        ]

    smart = report.get("smartMoney") or {}
    if smart:
        lines += ["", "━━━━━━━━━━━━━━━━━━━", "资金角色概括", "━━━━━━━━━━━━━━━━━━━"]
        for key in ["smartMoney", "nextMove", "institution", "retail", "funds", "dealerMM", "leveraged", "etfFlow"]:
            if smart.get(key):
                lines.append(f"• {key}: {smart.get(key)}")

    opt = report.get("optionsContext") or {}
    news = report.get("newsContext") or {}
    if opt or news:
        lines += ["", "━━━━━━━━━━━━━━━━━━━", "期权 / 新闻概括", "━━━━━━━━━━━━━━━━━━━"]
        for x in [opt.get("summaryCN"), opt.get("riskCN"), opt.get("actionCN"), news.get("summaryCN"), news.get("riskCN"), news.get("actionCN")]:
            if x:
                lines.append(x)

    pe = report.get("positionEngineering") or {}
    if pe:
        lines += [
            "",
            "━━━━━━━━━━━━━━━━━━━",
            "仓位工程概括（非作战室输入）",
            "━━━━━━━━━━━━━━━━━━━",
            f"交易质量：{pe.get('tradeQualityScore')}/10；市场质量：{pe.get('marketQualityScore')}/10；模型战术上限：{pe.get('maxTacticalPositionPct')}%；现金缓冲：{pe.get('cashBufferPct')}%",
            f"仓位层级：{pe.get('positionTier')}；默认赔率仓上限：{pe.get('defaultOddsCapPct')}%；动态建议：{(pe.get('dynamicSuggestedRangePct') or {}).get('low')}%-{(pe.get('dynamicSuggestedRangePct') or {}).get('high')}%；条件扩展上限：{pe.get('extensionCapPct')}%；趋势仓许可：{pe.get('trendPermission')}",
            f"价格折扣：相对252日高点 {(pe.get('priceDiscount') or {}).get('discountFrom252HighPct')}%；风险闸门：{(pe.get('riskRegimeGate') or {}).get('statusCN') or (pe.get('riskRegimeGate') or {}).get('status')}",
            f"分项评分：趋势确认 {((pe.get('deploymentMetrics') or {}).get('trendConfirmation') or {}).get('score')}/5；入场时机 {((pe.get('deploymentMetrics') or {}).get('entryTiming') or {}).get('score')}/5；价格折扣 {((pe.get('deploymentMetrics') or {}).get('priceDiscount') or {}).get('score')}/5；赔率质量 {((pe.get('deploymentMetrics') or {}).get('rewardRisk') or {}).get('score')}/5；部署质量 {((pe.get('deploymentMetrics') or {}).get('deploymentQuality') or {}).get('score')}/5",
            pe.get("readCN", ""),
            pe.get("conclusionCN", ""),
        ]
        for q in (pe.get("decisionReviewCN") or [])[:5]:
            lines.append("• 决策审查：" + q)

    enemy = report.get("enemyIntentReview") or {}
    if enemy:
        lines += [
            "",
            "━━━━━━━━━━━━━━━━━━━",
            enemy.get("titleCN", "敌谋预判"),
            "━━━━━━━━━━━━━━━━━━━",
            enemy.get("coreIdeaCN", ""),
            enemy.get("enemyQuestionCN", ""),
            enemy.get("summaryCN", ""),
        ]
        for ctx in (enemy.get("contextCN") or [])[:3]:
            lines.append("• " + ctx)
        for c in (enemy.get("challenges") or [])[:5]:
            lines.append(f"• {c.get('nameCN')}（置信 {c.get('confidence')}）：{c.get('challengeCN')} 回答：{c.get('answerCN')}")

    dims = report.get("dimensions") or []
    if dims:
        lines += ["", "━━━━━━━━━━━━━━━━━━━", "MMF-10 维度概括", "━━━━━━━━━━━━━━━━━━━"]
        for d in dims:
            lines.append(f"• {d.get('nameCN')} / {d.get('name')}：{d.get('score')}/10。{d.get('insightCN')}")
    acct = report.get("accountState") or {}
    if acct:
        lines += [
            "",
            "━━━━━━━━━━━━━━━━━━━",
            acct.get("title", "Account State / 账户状态"),
            "━━━━━━━━━━━━━━━━━━━",
            f"状态：{acct.get('stateCN')}",
            f"现金：{acct.get('cashPct')}%",
            f"当前仓位：{acct.get('currentPositionPct')}%",
            f"建议模式：{acct.get('suggestedMode')}",
            acct.get("summaryCN", ""),
            acct.get("recommendationCN", ""),
            acct.get("notFirstDayCN", ""),
        ]
        prev = acct.get("previousTrade")
        if prev:
            lines.append(f"上一笔交易：{prev.get('entry')} → {prev.get('exit')}，仓位 {prev.get('positionPct')}%，交易收益约 {prev.get('tradeReturnPct')}%，账户贡献约 {prev.get('accountContributionPct')}%。")
        for trigger in acct.get("triggers", []):
            lines.append(f"• {trigger.get('name')}：{trigger.get('level')}；{trigger.get('actionCN')}")
    for title, body in [
        ("今天发生了什么", r["whatHappenedCN"]),
        ("为什么发生", r["whyCN"]),
        ("谁造成的", r["whoCausedCN"]),
        ("市场如何解读", r["marketInterpretationCN"]),
        ("应该怎么布局", r["positioningCN"]),
        ("什么情况作废", r["invalidCN"]),
        ("明天看什么", r["tomorrowCN"]),
        ("MMF结论", r["conclusionCN"]),
    ]:
        lines += ["", "━━━━━━━━━━━━━━━━━━━", title, "━━━━━━━━━━━━━━━━━━━", body]

    doctrine = report.get("warriorDoctrine")
    if doctrine:
        lines += ["", "━━━━━━━━━━━━━━━━━━━", doctrine.get("title", "战争五事 · 道天地将法"), "━━━━━━━━━━━━━━━━━━━", doctrine.get("summaryCN", "")]
        for item in doctrine.get("items", []):
            lines.append(f"• {item.get('nameCN')} / {item.get('nameEN')}：{item.get('score')}/10")
            lines.append(f"  解读：{item.get('readCN')}")
            lines.append(f"  证据：{item.get('evidenceCN')}")
            lines.append(f"  动作：{item.get('actionCN')}")

    fg = report["fearGreed"]
    lines += ["", "━━━━━━━━━━━━━━━━━━━", "Fear & Greed Attribution", "━━━━━━━━━━━━━━━━━━━", f"总分：{fg['score']} / 100 · {fg['label']}", fg["interpretationCN"], fg["formulaCN"]]
    for row in fg.get("rows", []):
        lines.append(f"• {row['factor']} | 权重 {row['weight']}% | 分数 {row['score']} | 贡献 {row['contribution']} | {row['interpretationCN']}")

    lines += ["", "━━━━━━━━━━━━━━━━━━━", "未来推演", "━━━━━━━━━━━━━━━━━━━"]
    for s in report["scenarioEngine"]:
        lines += [f"{s['name']}：{s['probability']}%", f"为什么：{s['whyCN']}", f"成立：{s['conditionCN']}", f"失效：{s['invalidCN']}", f"观察：{s['watchCN']}", f"应对：{s['responseCN']}", ""]

    lines += ["━━━━━━━━━━━━━━━━━━━", "明日观察清单", "━━━━━━━━━━━━━━━━━━━"]
    for x in report["tomorrowChecklist"]:
        lines.append("□ " + x)

    initiative = report.get("initiativeManagement") or {}
    if initiative:
        lines += [
            "", "━━━━━━━━━━━━━━━━━━━", "主动权管理 Initiative Management", "━━━━━━━━━━━━━━━━━━━",
            f"主动权指数：{initiative.get('score')} / 100 · {initiative.get('labelCN', '')}",
            initiative.get("principleCN", ""),
            initiative.get("accountReadCN", ""),
            "", "信息区域（价格只是坐标，资金行为才是触发器）：",
        ]
        for zone in initiative.get("informationZones", []):
            level = zone.get("range") or zone.get("levels") or "—"
            lines += [
                f"• {zone.get('roleCN')} / {zone.get('roleEN')}：{level}；默认部署 {zone.get('defaultSizePct')}%",
                f"  触发：{zone.get('triggerCN')}",
                f"  含义：{zone.get('meaningCN')}",
                f"  失效：{zone.get('invalidationCN')}",
            ]
        follow = initiative.get("liquidityFollowThrough") or {}
        lines += ["", "流动性后续验证：", follow.get("summaryCN", "")]
        for item in follow.get("checksCN", []):
            lines.append("• " + item)
        lines += ["", "竞争性结构假设："]
        for model in initiative.get("structureHypotheses", []):
            lines.append(f"• {model.get('nameCN')}：{model.get('confidence')}%｜证据：{model.get('evidenceCN')}｜失效：{model.get('invalidationCN')}｜行动：{model.get('actionCN')}")
        lines += ["", "重新庙算触发条件："]
        for trigger in initiative.get("templeRecalculationTriggersCN", []):
            lines.append("• " + trigger)
        feasibility = initiative.get("executionFeasibility") or {}
        lines += [
            "", "执行可行性：",
            f"• 默认模式：{feasibility.get('defaultModeCN', '')}",
            f"• 主动模式：{feasibility.get('activeModeCN', '')}",
            f"• 约束：{feasibility.get('constraintCN', '')}",
        ]
    field = report.get("fieldEvolution") or {}
    if field:
        phase = field.get("marketPhase") or {}
        liquidity = field.get("liquidityAssessment") or {}
        emotion = field.get("emotionReaction") or {}
        symmetry = field.get("symmetry") or {}
        exit_quality = field.get("exitQuality") or {}
        tail = field.get("tailRisk") or {}
        capital = field.get("capitalEfficiency") or {}
        post = field.get("postMortem") or {}
        lines += [
            "", "━━━━━━━━━━━━━━━━━━━", "实战迭代 Field Learning", "━━━━━━━━━━━━━━━━━━━",
            field.get("coreLessonCN", ""),
            f"市场阶段：{phase.get('labelCN')}；ATR压缩比 {phase.get('atrCompressionRatio')}；区间压缩比 {phase.get('rangeCompressionRatio')}。",
            phase.get("readCN", ""),
            f"流动性事件：{liquidity.get('labelCN')}；置信度 {liquidity.get('confidence')}%。",
            liquidity.get("readCN", ""),
            f"情绪部署级别：{emotion.get('deploymentClass')}；进攻仓许可：{'YES' if emotion.get('attackAuthorized') else 'NO'}。",
            emotion.get("ruleCN", ""),
            emotion.get("readCN", ""),
            f"退出质量：{exit_quality.get('grade')} · {exit_quality.get('score')}/5。",
            exit_quality.get("ruleCN", ""),
            exit_quality.get("actionCN", ""),
            f"尾部风险：概率 {tail.get('probabilityPct')}% · 冲击 {tail.get('impact')}。",
            tail.get("readCN", ""),
            f"时间/空间对称：{symmetry.get('strength')} · {symmetry.get('score')}/100。",
            symmetry.get("readCN", ""),
            "", "每层加仓审查：",
        ]
        for item in capital.get("addAuditCN", []):
            lines.append("• " + item)
        lines += ["", post.get("titleCN", "战役结束后复盘") + "："]
        for item in post.get("questionsCN", []):
            lines.append("□ " + item)
    ph = report["philosophy"]
    lines += ["", "━━━━━━━━━━━━━━━━━━━", ph.get("titleCN", "MMF Philosophy"), "━━━━━━━━━━━━━━━━━━━", ph["mottoCN"], ph["marketCN"], ph["survivalCN"], ph["finalCN"]]
    if ph.get("missionCN"):
        lines.append(ph["missionCN"])
    for x in ph.get("processCN", []):
        lines.append("• " + x)
    return "\n".join(lines)


def _render_email_en_legacy(report):
    m = report["meta"]
    ex = report.get("executiveSummary") or {}
    q = (report.get("dailyBattlefield") or {}).get("quote") or {}
    pe = report.get("positionEngineering") or {}
    gate = pe.get("riskRegimeGate") or {}
    wa = report.get("weeklyAnalysis") or {}
    ma = report.get("monthlyAnalysis") or {}
    intra = report.get("intradayBattle") or {}
    heat = report.get("sectorHeatmap") or {}
    opt = report.get("optionsContext") or {}
    rs = report.get("relativeStrengthMatrix") or {}
    rotation = report.get("capitalRotation") or {}
    structure = report.get("adaptiveMarketStructure") or {}
    auction = report.get("intradayAuctionStructure") or {}
    systemic = report.get("systemicRiskFilter") or {}
    leadership = report.get("semiconductorLeadership") or {}
    catalyst = report.get("catalystRegime") or {}
    state_machine = report.get("marketVacationStateMachine") or {}
    scenario_model = report.get("scenarioModel") or {}
    lines = [
        f"MMF Daily Battlefield {m.get('version', 'v3.0')} | {m['ticker']} | {m['date']}", "",
        "Miao Market Framework · Project Sun Tzu",
        "Trading is not prediction. It is intelligence, deployment, and position engineering.", "",
        "====================", "COMMAND BRIEF", "====================",
        f"MMF Score: {ex.get('mmfScore')} / 100",
        f"Market Temperature: {ex.get('marketTemperature')} / 100",
        f"Market State: {ex.get('marketStatus')}",
        f"Tactical Reward/Risk: {ex.get('executableRewardRisk', ex.get('rewardRisk'))}",
        f"Recovery Reward/Risk: {ex.get('recoveryRewardRisk')}",
        f"Trend Confirmation: {(ex.get('trendConfirmation') or {}).get('score')}/5",
        f"Entry Timing: {(ex.get('entryTiming') or {}).get('score')}/5",
        f"Price Discount: {(ex.get('priceDiscountQuality') or {}).get('score')}/5",
        f"Deployment Quality: {(ex.get('deploymentQuality') or {}).get('score')}/5", "",
        "====================", "MARKET FACTS", "====================",
        f"Last/Close: {q.get('close') or q.get('last')} | Change: {q.get('prevCloseChangePct', q.get('changePct'))}%",
        f"Range: {q.get('low')} - {q.get('high')} | Volume: {q.get('volume')}", "",
        "====================", "MMF-10 STRUCTURAL & CAPITAL REGIME", "====================",
        f"State Machine: {state_machine.get('state')} | Regime: {structure.get('regime')} | Semiconductor Leadership: {leadership.get('status')} | Systemic Risk: {systemic.get('direction')} / {systemic.get('status')}",
        f"Capital Classification: {rotation.get('classification')} | Leaving equities: {rotation.get('isMoneyLeavingEquities')} | Leaving semiconductors: {rotation.get('isMoneyLeavingSemiconductors')}",
        f"Micro Range: {(structure.get('micro') or {}).get('low')} - {(structure.get('micro') or {}).get('high')} | Daily Range: {(structure.get('daily') or {}).get('low')} - {(structure.get('daily') or {}).get('high')}",
        f"Event Risk: {catalyst.get('eventRisk')} | Structural Risk: {catalyst.get('structuralRisk')} | {catalyst.get('eventDataStatus')}",
        f"Intraday Auction: {auction.get('classification')}",
        "Relative strength (level / change):",
        *[f"- {row.get('relationship')}: {row.get('status')} / {row.get('change')} | 20D {row.get('relative20dPct')}% | 5D {row.get('recent5dPct')}%" for row in rs.get('rows', [])],
        "Four scenarios (evidence weights, not predictions):",
        *[f"- {item.get('name')}: {item.get('probability')}%" for item in scenario_model.get('scenarios', [])], "",
        "====================", "TIMEFRAME ANALYSIS", "====================",
        f"Monthly regime: {_english_label(ma.get('trend'))}. Monthly structure determines the strategic era; it is not an entry trigger.",
        f"Weekly structure: {_english_label(wa.get('trend'))}. Weekly structure determines whether medium-term sponsorship remains intact.",
        f"Daily battlefield: close {q.get('close') or q.get('last')}; use daily structure for deployment conditions.",
        f"Intraday execution: {intra.get('mode')} / {intra.get('source')}. Lower timeframes choose execution timing, not the strategic thesis.", "",
        "====================", "POSITION ENGINEERING", "====================",
        f"Trade Quality: {pe.get('tradeQualityScore')}/10 | Market Quality: {pe.get('marketQualityScore')}/10",
        f"Maximum Tactical Size: {pe.get('maxTacticalPositionPct')}% | Cash Buffer: {pe.get('cashBufferPct')}%",
        f"Position Tier: {_english_label(pe.get('positionTier'))} | Risk Gate: {gate.get('status')}",
        "The maximum size is a ceiling, not a requirement to deploy fully.", "",
        "====================", "SECTOR ROTATION", "====================",
        f"Mode: {heat.get('mode')}",
    ]
    for group in (heat.get("groups") or []):
        lines.append(f"- {_english_label(group.get('nameEN') or group.get('nameCN'))}: {group.get('avgChangePct')}%")
    lines += ["", "====================", "OPTIONS POSITIONING", "====================",
              f"Put/Call Volume: {opt.get('putCallVolumeRatio')}",
              f"Put/Call Open Interest: {opt.get('putCallOpenInterestRatio')}",
              f"Average IV: {opt.get('averageIVPct')}%",
              f"Net Gamma Exposure Proxy: {opt.get('netGammaExposureProxy')}", "",
              "Execution must remain governed by activation, invalidation, and account risk capacity."]
    initiative = report.get("initiativeManagement") or {}
    if initiative:
        lines += [
            "", "====================", "INITIATIVE MANAGEMENT", "====================",
            f"Initiative Index: {initiative.get('score')} / 100 · {initiative.get('labelEN', '')}",
            initiative.get("principleEN", ""),
            initiative.get("accountReadEN", ""),
            "", "Information zones (price is a coordinate; capital behavior is the trigger):",
        ]
        for zone in initiative.get("informationZones", []):
            level = zone.get("range") or zone.get("levels") or "—"
            lines += [
                f"- {zone.get('roleEN')}: {level}; default deployment {zone.get('defaultSizePct')}%",
                f"  Trigger: {zone.get('triggerEN')}",
                f"  Meaning: {zone.get('meaningEN')}",
                f"  Invalidation: {zone.get('invalidationEN')}",
            ]
        follow = initiative.get("liquidityFollowThrough") or {}
        lines += ["", "Liquidity follow-through:", follow.get("summaryEN", "")]
        for item in follow.get("checksEN", []):
            lines.append("- " + item)
        lines += ["", "Competing structure hypotheses:"]
        for model in initiative.get("structureHypotheses", []):
            lines.append(f"- {model.get('nameEN')}: {model.get('confidence')}% | Evidence: {model.get('evidenceEN')} | Invalidation: {model.get('invalidationEN')} | Action: {model.get('actionEN')}")
        lines += ["", "Temple recalculation triggers:"]
        for trigger in initiative.get("templeRecalculationTriggersEN", []):
            lines.append("- " + trigger)
        feasibility = initiative.get("executionFeasibility") or {}
        lines += [
            "", "Execution feasibility:",
            f"- Default mode: {feasibility.get('defaultModeEN', '')}",
            f"- Active mode: {feasibility.get('activeModeEN', '')}",
            f"- Constraint: {feasibility.get('constraintEN', '')}",
        ]
    field = report.get("fieldEvolution") or {}
    if field:
        phase = field.get("marketPhase") or {}
        liquidity = field.get("liquidityAssessment") or {}
        emotion = field.get("emotionReaction") or {}
        symmetry = field.get("symmetry") or {}
        exit_quality = field.get("exitQuality") or {}
        tail = field.get("tailRisk") or {}
        capital = field.get("capitalEfficiency") or {}
        post = field.get("postMortem") or {}
        lines += [
            "", "====================", "FIELD LEARNING", "====================",
            field.get("coreLessonEN", ""),
            f"Market Phase: {phase.get('labelEN')} | ATR compression {phase.get('atrCompressionRatio')} | Range compression {phase.get('rangeCompressionRatio')}.",
            phase.get("readEN", ""),
            f"Liquidity Event: {liquidity.get('labelEN')} | Confidence {liquidity.get('confidence')}%.",
            liquidity.get("readEN", ""),
            f"Sentiment Budget: {str(emotion.get('deploymentClass') or '').split('/')[0].strip()} | Attack authorized: {'YES' if emotion.get('attackAuthorized') else 'NO'}.",
            emotion.get("ruleEN", ""),
            emotion.get("readEN", ""),
            f"Exit Quality: {exit_quality.get('grade')} · {exit_quality.get('score')}/5.",
            exit_quality.get("ruleEN", ""),
            exit_quality.get("actionEN", ""),
            f"Tail Risk: {tail.get('probabilityPct')}% probability · {_english_label(tail.get('impact'))}.",
            tail.get("readEN", ""),
            f"Time/Price Symmetry: {_english_label(symmetry.get('strength'))} · {symmetry.get('score')}/100.",
            symmetry.get("readEN", ""),
            "", "Add-layer audit:",
        ]
        for item in capital.get("addAuditEN", []):
            lines.append("- " + item)
        lines += ["", post.get("titleEN", "Post-campaign Review") + ":"]
        for item in post.get("questionsEN", []):
            lines.append("- " + item)
    return "\n".join(lines)


def _display(value, fallback="--"):
    if value is None or value == "":
        return fallback
    return str(value)


def _metric_text(metric):
    metric = metric or {}
    stars = metric.get("stars") or "--"
    score = metric.get("score")
    return f"{stars} ({_display(score)}/5)"


def _data_stamp(meta):
    quote_time = str(meta.get("quoteTime") or "").strip()
    quote_date = str(meta.get("quoteDate") or "").strip()
    stamp = quote_time if quote_time and quote_date and quote_date in quote_time else " ".join(x for x in [quote_date, quote_time] if x)
    return stamp or "--"


def _without_action_prefix(text):
    return re.sub(r"^(建议行动|行动建议|Recommended action)\s*[：:]\s*", "", str(text or "").strip(), flags=re.I)


def _volume_label_en(volume):
    label = str((volume or {}).get("labelCN") or "")
    labels = {
        "当期量能缺失": "Current Volume Unavailable",
        "量价结构样本不足": "Insufficient Price/Volume Sample",
        "慢性派发警报": "Chronic Distribution Alert",
        "高波动价格发现": "High-Volatility Price Discovery",
        "派发压力观察": "Distribution Pressure Watch",
        "吸筹式修复观察": "Constructive Accumulation Watch",
        "放量风险释放": "High-Volume Risk Release",
        "量价分歧不强": "No Decisive Price/Volume Signal",
    }
    return labels.get(label, "Price/Volume Unconfirmed")


def _unique_strings(items, limit=None):
    out = []
    seen = set()
    for item in items or []:
        text = re.sub(r"\s+", " ", str(item or "")).strip()
        key = re.sub(r"[\s，。；：、,.!?:;·•□\-]+", "", text).lower()
        if not text or not key or key in seen:
            continue
        seen.add(key)
        out.append(text)
        if limit and len(out) >= limit:
            break
    return out


def _finalize_brief(lines):
    """Remove accidental duplicate prose while keeping the section structure intact."""
    out = []
    seen = set()
    for raw in lines:
        text = str(raw or "").strip()
        if not text:
            if out and out[-1] != "":
                out.append("")
            continue
        is_structure = text.startswith(("【", "MMF DAILY", "1.", "2.", "3.", "4.", "5.", "6.", "7."))
        key = re.sub(r"[\s，。；：、,.!?:;·•□\-]+", "", text).lower()
        if not is_structure and len(key) >= 18 and key in seen:
            continue
        if not is_structure and len(key) >= 18:
            seen.add(key)
        out.append(text)
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out)


def _compact_context(report):
    ex = report.get("executiveSummary") or {}
    battlefield = report.get("dailyBattlefield") or {}
    pe = report.get("positionEngineering") or {}
    behavior = report.get("strategicBehaviorMap") or {}
    return {
        "meta": report.get("meta") or {},
        "ex": ex,
        "replay": report.get("dailyReplay") or {},
        "quote": battlefield.get("quote") or {},
        "tech": battlefield.get("technicalIndicators") or {},
        "candle": battlefield.get("candleCN") or "--",
        "pe": pe,
        "gate": pe.get("riskRegimeGate") or {},
        "account": report.get("accountState") or {},
        "volume": report.get("volumeStructure") or (report.get("intradayDecision") or {}).get("volumeStructure") or {},
        "behavior": behavior,
        "capital": behavior.get("capitalBehavior") or {},
        "anchor": behavior.get("dynamicAnchorRange") or {},
        "sector": report.get("sectorRotation") or {},
        "heat": report.get("sectorHeatmap") or {},
        "options": report.get("optionsContext") or {},
        "macro": report.get("macro") or {},
        "weights": report.get("etfWeights") or {},
        "structure": report.get("adaptiveMarketStructure") or {},
        "rotation": report.get("capitalRotation") or {},
        "leadership": report.get("semiconductorLeadership") or {},
        "systemic": report.get("systemicRiskFilter") or {},
        "earnings": report.get("earningsCalendar") or {},
        "strategic401k": report.get("strategic401k") or {},
        "initiative": report.get("initiativeManagement") or {},
        "field": report.get("fieldEvolution") or {},
        "scenarios": report.get("scenarioEngine") or [],
        "checklist": report.get("tomorrowChecklist") or [],
        "betaV110": report.get("betaV110") or {},
    }


def _retirement_cn(value):
    return {
        "NO 401(k) ACTION REQUIRED": "无需 401(k) 行动",
        "REVIEW CONTRIBUTION TILT": "审查新缴款倾斜",
        "NORMAL": "正常",
        "MILD_RISK_ON": "温和风险偏进攻",
        "STRONG_RISK_ON": "强风险偏进攻",
        "MILD_RISK_OFF": "温和风险偏防守",
        "STRONG_RISK_OFF": "强风险偏防守",
        "RECOVERY": "修复期",
        "SYSTEMIC_STRESS": "系统压力",
        "HOLD": "维持",
        "CURRENT ALLOCATION NOT AVAILABLE": "当前持仓比例未录入",
        "REBALANCE WATCH": "再平衡观察",
        "NORMAL / NO REBALANCE REQUIRED": "正常 / 无需再平衡",
    }.get(str(value), _display(value))


def render_email_cn(report):
    if report.get("betaV110"):
        from mmf_engine.beta_v110 import daily_brief
        return daily_brief(report, "cn")
    c = _compact_context(report)
    m, ex, r, q = c["meta"], c["ex"], c["replay"], c["quote"]
    pe, gate, account = c["pe"], c["gate"], c["account"]
    tech, volume, sector = c["tech"], c["volume"], c["sector"]
    structure, rotation, earnings = c["structure"], c["rotation"], c["earnings"]
    anchor, capital = c["anchor"], c["capital"]
    retirement = c["strategic401k"]
    main_drag, main_support = c["weights"].get("mainDrag") or {}, c["weights"].get("mainSupport") or {}
    current = q.get("close") or q.get("last")
    change = q.get("prevCloseChangePct", q.get("changePct"))
    suggested = pe.get("dynamicSuggestedRangePct") or {}
    action = _without_action_prefix(r.get("positioningCN") or ex.get("strategyCN") or "等待价格、量能与风险闸门共同确认。")

    lines = [
        f"【MMF每日决策简报 {m.get('version', 'v3.0')}】{m.get('ticker', '--')} | {m.get('date', '--')}",
        f"数据：{m.get('quoteSource', '--')} · {_data_stamp(m)}",
        "",
        f"一句话结论：{ex.get('headlineCN') or r.get('marketInterpretationCN') or '--'}",
        "",
        "1. 战场速览",
        f"• MMF {ex.get('mmfScore')}/100 · 温度 {ex.get('marketTemperature')}/100 · 状态 {_display(ex.get('marketStatus'))}",
        f"• 现价 {_display(current)} · 当日 {_display(change)}% · 区间 {_display(q.get('low'))}-{_display(q.get('high'))} · 成交量 {_display(q.get('volume'))}",
        f"• 战术赔率 {_display(ex.get('executableRewardRisk', ex.get('rewardRisk')))} · 恢复潜力赔率 {_display(ex.get('recoveryRewardRisk'))}；执行以战术赔率为准。",
        f"• 趋势 {_metric_text(ex.get('trendConfirmation'))} · 时机 {_metric_text(ex.get('entryTiming'))} · 折扣 {_metric_text(ex.get('priceDiscountQuality'))} · 部署 {_metric_text(ex.get('deploymentQuality'))}",
        "",
        "2. 今日事实与解读",
        f"• K线：{c['candle']} EMA20={_display(tech.get('ema20'))}，EMA50={_display(tech.get('ema50'))}，RSI14={_display(tech.get('rsi14'))}，MACD={_display(tech.get('macd'))}。",
        f"• 量价：{_display(volume.get('labelCN'), '待确认')}（{_display(volume.get('score'))}/10）；{_display(volume.get('readCN') or volume.get('moneyActionCN') or volume.get('interpretationCN'))}",
        f"• 驱动：主要拖累 {_display(main_drag.get('ticker'))}（影响 {_display(main_drag.get('impact'))}）；主要支撑 {_display(main_support.get('ticker'))}（影响 {_display(main_support.get('impact'))}）。",
        f"• 解释：{_display(r.get('marketInterpretationCN'))}",
        "",
        "3. 结构与资金",
        f"• 结构：{_display(structure.get('regime'))} · 半导体领导力 {_display(c['leadership'].get('status'))} · 系统风险 {_display(c['systemic'].get('direction'))} / {_display(c['systemic'].get('status'))}。",
        f"• 资金：{_display(rotation.get('classification'))}；{_display(capital.get('postureCN') or capital.get('summaryCN'))}",
        f"• 微观战场：{_display((structure.get('micro') or {}).get('low'))}-{_display((structure.get('micro') or {}).get('high'))}；当前时段区间与日线/高阶结构分开，价位只触发复核。",
        f"• 财报日历：风险 {_display(earnings.get('riskLevel'))}；{_display(earnings.get('summaryCN') or earnings.get('reasonCN'))} 未来7天预计披露权重约 {_display(earnings.get('weightReportingWithin7DaysPct'))}%。",
        f"• 板块：{_display(sector.get('mode'))}；最强 {_display((sector.get('strongest') or {}).get('name'))} {_display((sector.get('strongest') or {}).get('changePct'))}%，最弱 {_display((sector.get('weakest') or {}).get('name'))} {_display((sector.get('weakest') or {}).get('changePct'))}%。",
        f"• 波动/期权：VIX {_display((c['macro'].get('vix') or {}).get('last'))}；Put/Call成交量 {_display(c['options'].get('putCallVolumeRatio'))}，Put/Call OI {_display(c['options'].get('putCallOpenInterestRatio'))}，平均IV {_display(c['options'].get('averageIVPct'))}%，Gamma proxy {_display(c['options'].get('netGammaExposureProxy'))}。",
        "",
        "4. 仓位与行动",
        f"• 账户：当前仓位 {_display(account.get('currentPositionPct', pe.get('currentPositionPct')))}% · 现金/其他资产 {_display(account.get('cashPct', pe.get('cashBufferPct')))}%。",
        f"• 模型：{_display(pe.get('positionTier'))} · 动态区间 {_display(suggested.get('low'))}%-{_display(suggested.get('high'))}% · 条件扩展上限 {_display(pe.get('extensionCapPct'))}% · 风险闸门 {_display(gate.get('status'))}。",
        f"• 建议行动：{action}",
        "",
        "5. 情景地图（证据权重，不是价格预测）",
    ]
    for scenario in c["scenarios"][:4]:
        lines.append(
            f"• {scenario.get('name', '--')} {scenario.get('probability', '--')}%｜成立：{scenario.get('conditionCN', '--')}｜应对：{scenario.get('responseCN', '--')}｜作废：{scenario.get('invalidCN', '--')}"
        )
    lines += ["", "6. 下一交易日"]
    for item in _unique_strings(c["checklist"], limit=5):
        lines.append("□ " + item.lstrip("□ "))
    lines += [
        f"• 总作废条件：{_display(r.get('invalidCN') or pe.get('invalidCN'))}",
        "",
        "7. 实战迭代",
        f"• 主动权：{_display(c['initiative'].get('score'))}/100 · {_display(c['initiative'].get('labelCN'))}。",
        f"• 今日学习：{_display(c['field'].get('coreLessonCN'))}",
        "",
        "8. 401(k) 长期战略（独立于 SOXL 执行）",
        f"• {_display(retirement.get('dailySummaryCN'), '长期模块数据暂不可用；维持60/25/15基线，不据缺失数据调仓。')}",
        f"• 当前动作：{_retirement_cn(retirement.get('action') or 'NO 401(k) ACTION REQUIRED')} · 市场环境 {_retirement_cn(retirement.get('marketRegime'))} · 现有持仓 {_retirement_cn(retirement.get('existingHoldingsAction') or 'HOLD')}。",
        f"• 新缴款建议：标普500 {_display((retirement.get('recommendedContributionPct') or {}).get('SP500'))}% · 扩展市场 {_display((retirement.get('recommendedContributionPct') or {}).get('EXTENDED_MARKET'))}% · 国际股票 {_display((retirement.get('recommendedContributionPct') or {}).get('INTERNATIONAL'))}%。",
        f"• 漂移审查：{_retirement_cn((retirement.get('portfolioDrift') or {}).get('status'))}。只优先调整新缴款，不自动卖出现有退休资产。",
        "",
        "完整原始指标、计算字段与证据链保留在随附 JSON；本邮件只保留决策所需的唯一版本。",
    ]
    return _finalize_brief(lines)


def _english_action(c):
    pe, gate, account = c["pe"], c["gate"], c["account"]
    suggested = pe.get("dynamicSuggestedRangePct") or {}
    position = account.get("currentPositionPct", pe.get("currentPositionPct")) or 0
    if gate.get("status") == "FAIL":
        return "Do not add risk. Preserve cash and rerun the framework after the failed gate is resolved."
    if float(position or 0) <= 0:
        probe = min(float(suggested.get("high") or 10), 10)
        return f"A staged probe of up to {probe:g}% is permitted only after price, volume, and semiconductor leadership confirm; do not deploy it all at once."
    remaining = max(0, float(pe.get("maxTacticalPositionPct") or suggested.get("high") or 0) - float(position or 0))
    return f"Manage the existing {position}% position inside the {suggested.get('low', '--')}%-{suggested.get('high', '--')}% model range. At most {remaining:g}% remains available, and only after confirmation; stop adding when the risk gate closes."


def render_email_en(report):
    if report.get("betaV110"):
        from mmf_engine.beta_v110 import daily_brief
        return daily_brief(report, "en")
    c = _compact_context(report)
    m, ex, q = c["meta"], c["ex"], c["quote"]
    pe, gate, account = c["pe"], c["gate"], c["account"]
    tech, volume, sector = c["tech"], c["volume"], c["sector"]
    structure, rotation, earnings = c["structure"], c["rotation"], c["earnings"]
    anchor, capital = c["anchor"], c["capital"]
    retirement = c["strategic401k"]
    main_drag, main_support = c["weights"].get("mainDrag") or {}, c["weights"].get("mainSupport") or {}
    suggested = pe.get("dynamicSuggestedRangePct") or {}
    current = q.get("close") or q.get("last")
    change = q.get("prevCloseChangePct", q.get("changePct"))
    state = ex.get("marketStatus") or "Unconfirmed"
    lines = [
        f"MMF DAILY DECISION BRIEF {m.get('version', 'v3.0')} | {m.get('ticker', '--')} | {m.get('date', '--')}",
        f"Data: {m.get('quoteSource', '--')} · {_data_stamp(m)}",
        "",
        f"Bottom line: Market state is {state}. Execution is governed by confirmation, invalidation, and account risk capacity.",
        "",
        "1. Battlefield Snapshot",
        f"• MMF {ex.get('mmfScore')}/100 · Temperature {ex.get('marketTemperature')}/100 · State {state}",
        f"• Last {_display(current)} · Change {_display(change)}% · Range {_display(q.get('low'))}-{_display(q.get('high'))} · Volume {_display(q.get('volume'))}",
        f"• Tactical R/R {_display(ex.get('executableRewardRisk', ex.get('rewardRisk')))} · Recovery-potential R/R {_display(ex.get('recoveryRewardRisk'))}; tactical R/R governs execution.",
        f"• Trend {_metric_text(ex.get('trendConfirmation'))} · Timing {_metric_text(ex.get('entryTiming'))} · Discount {_metric_text(ex.get('priceDiscountQuality'))} · Deployment {_metric_text(ex.get('deploymentQuality'))}",
        "",
        "2. Facts and Interpretation",
        f"• Candle/technicals: close {_display(current)}, EMA20 {_display(tech.get('ema20'))}, EMA50 {_display(tech.get('ema50'))}, RSI14 {_display(tech.get('rsi14'))}, MACD {_display(tech.get('macd'))}.",
        f"• Price/volume: {_volume_label_en(volume)} ({_display(volume.get('score'))}/10). Volume is evidence only after follow-through confirms its intent.",
        f"• Drivers: main drag {_display(main_drag.get('ticker'))} ({_display(main_drag.get('impact'))}); main support {_display(main_support.get('ticker'))} ({_display(main_support.get('impact'))}).",
        "",
        "3. Structure and Capital",
        f"• Regime {_display(structure.get('regime'))} · Semiconductor leadership {_display(c['leadership'].get('status'))} · Systemic risk {_display(c['systemic'].get('direction'))} / {_display(c['systemic'].get('status'))}.",
        f"• Capital classification {_display(rotation.get('classification'))} · Equities outflow {_display(rotation.get('isMoneyLeavingEquities'))} · Semiconductor outflow {_display(rotation.get('isMoneyLeavingSemiconductors'))}.",
        f"• Micro battlefield {_display((structure.get('micro') or {}).get('low'))}-{_display((structure.get('micro') or {}).get('high'))}; current-session terrain is kept separate from daily and higher-order structure, and a level triggers review rather than an order.",
        f"• Earnings calendar: risk {_display(earnings.get('riskLevel'))}; {_display(earnings.get('summaryEN') or earnings.get('reasonEN'))} Weight expected to report within seven days: {_display(earnings.get('weightReportingWithin7DaysPct'))}%.",
        f"• Sector mode {_display(sector.get('mode'))}; strongest {_display((sector.get('strongest') or {}).get('name'))} {_display((sector.get('strongest') or {}).get('changePct'))}%, weakest {_display((sector.get('weakest') or {}).get('name'))} {_display((sector.get('weakest') or {}).get('changePct'))}%.",
        f"• Volatility/options: VIX {_display((c['macro'].get('vix') or {}).get('last'))}; Put/Call volume {_display(c['options'].get('putCallVolumeRatio'))}, Put/Call OI {_display(c['options'].get('putCallOpenInterestRatio'))}, average IV {_display(c['options'].get('averageIVPct'))}%, gamma proxy {_display(c['options'].get('netGammaExposureProxy'))}.",
        "",
        "4. Position and Action",
        f"• Account: position {_display(account.get('currentPositionPct', pe.get('currentPositionPct')))}% · cash/other assets {_display(account.get('cashPct', pe.get('cashBufferPct')))}%.",
        f"• Model: {_english_label(pe.get('positionTier'))} · range {_display(suggested.get('low'))}%-{_display(suggested.get('high'))}% · conditional cap {_display(pe.get('extensionCapPct'))}% · risk gate {_display(gate.get('status'))}.",
        f"• Recommended action: {_english_action(c)}",
        "",
        "5. Scenario Map (evidence weights, not forecasts)",
    ]
    for scenario in c["scenarios"][:4]:
        name = str(scenario.get("name") or "Scenario")
        if "Scenario A" in name or "Range" in name or name.startswith("Base"):
            condition, response = "Price remains accepted inside the active range without worsening breadth.", "Wait for directional confirmation."
        elif "Scenario B" in name or "Bullish" in name or name.startswith("Bull"):
            condition, response = "Price reclaims the confirmation level with volume and semiconductor leadership.", "Add in stages; do not chase the first impulse."
        elif "Scenario C" in name or "Orderly" in name or name.startswith("Bear"):
            condition, response = "Price tests or breaks the active low while broad-market volatility remains controlled.", "Recalculate the odds; do not buy mechanically."
        elif "Scenario D" in name or "Systemic" in name or name.startswith("Tail"):
            condition, response = "Semiconductors, broad indexes, volatility, and credit deteriorate together.", "Freeze additions and reassess systemic risk."
        else:
            condition, response = "New evidence changes the active range.", "Recalculate before acting."
        lines.append(f"• {name} {scenario.get('probability', '--')}% | Trigger: {condition} | Response: {response}")
    field = c["field"]
    phase, liquidity, tail = field.get("marketPhase") or {}, field.get("liquidityAssessment") or {}, field.get("tailRisk") or {}
    lines += [
        "",
        "6. Next Session",
        "□ Confirm whether price is accepted above the active reclaim level.",
        "□ Require volume and NVDA/AVGO/SMH leadership to agree with the move.",
        "□ Treat a high-volume break of the active defense level as invalidation, not as automatic value.",
        "□ Recalculate the plan after a structural break or a systemic-risk escalation.",
        "",
        "7. Field Learning",
        f"• Initiative {_display(c['initiative'].get('score'))}/100 · {_display(c['initiative'].get('labelEN'))}.",
        f"• Phase {_display(phase.get('labelEN'))} · {_display(liquidity.get('labelEN'))} · Tail risk {_display(tail.get('probabilityPct'))}%.",
        f"• Lesson: {_display(field.get('coreLessonEN'))}",
        "",
        "8. 401(k) Long-Term Strategy (separate from SOXL execution)",
        f"• {_display(retirement.get('dailySummaryEN'), 'Long-term module data is unavailable; keep the 60/25/15 baseline and do not reallocate on missing evidence.')}",
        f"• Current action: {_display(retirement.get('action'), 'NO 401(k) ACTION REQUIRED')} · regime {_display(retirement.get('marketRegime'))} · existing holdings {_display(retirement.get('existingHoldingsAction'), 'HOLD')}.",
        f"• New-contribution mix: S&P 500 {_display((retirement.get('recommendedContributionPct') or {}).get('SP500'))}% · Extended Market {_display((retirement.get('recommendedContributionPct') or {}).get('EXTENDED_MARKET'))}% · International {_display((retirement.get('recommendedContributionPct') or {}).get('INTERNATIONAL'))}%.",
        f"• Drift review: {_display((retirement.get('portfolioDrift') or {}).get('status'))}. Adjust new contributions first; never auto-sell existing retirement holdings.",
        "",
        "The attached JSON retains the complete raw metrics, calculations, and evidence chain; this email carries only the authoritative decision brief.",
    ]
    return _finalize_brief(lines)


def save_report_files(report, lang="cn"):
    folder = REPORT_DIR / report["meta"]["date"] / report["meta"]["ticker"]
    folder.mkdir(parents=True, exist_ok=True)
    version = report["meta"].get("version", "v3_0").replace(".", "_")
    jp = folder / f"MMF_{version}_{report['meta']['ticker']}_{report['meta']['date']}_snapshot.json"
    suffix = "en" if lang == "en" else "cn"
    mp = folder / f"MMF_{version}_{report['meta']['ticker']}_{report['meta']['date']}_review_{suffix}.md"
    jp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    mp.write_text(render_email_en(report) if lang == "en" else render_email_cn(report), encoding="utf-8")
    return {"json": str(jp), "markdown": str(mp)}


def _send_email_report(report, recipient=None, lang="cn"):
    files = save_report_files(report, lang=lang)
    if os.getenv("EMAIL_ENABLED", "false").lower() != "true":
        return {
            "sent": False,
            "reason": "EMAIL_ENABLED=false. Preview and report files were generated, but SMTP sending is disabled in config/config.env.",
            "files": files,
        }
    user = os.getenv("SMTP_USER", "").strip()
    pw = os.getenv("SMTP_APP_PASSWORD", "").strip()
    to_email = (recipient or os.getenv("EMAIL_TO", user)).strip()
    if not EMAIL_RE.match(to_email):
        return {
            "sent": False,
            "reason": "Invalid recipient email address.",
            "files": files,
        }
    if not user or not pw:
        return {
            "sent": False,
            "reason": "Missing SMTP_USER or SMTP_APP_PASSWORD in config/config.env. Gmail requires an App Password, not the normal login password.",
            "files": files,
        }
    try:
        msg = EmailMessage()
        msg["Subject"] = (f"MMF Daily Decision Brief {report['meta'].get('version','v3.0')} | {report['meta']['ticker']} | {report['meta']['date']}" if lang == "en" else f"【MMF每日决策简报 {report['meta'].get('version','v3.0')}】{report['meta']['ticker']} | {report['meta']['date']}")
        msg["From"] = os.getenv("EMAIL_FROM", user)
        msg["To"] = to_email
        msg.set_content(render_email_en(report) if lang == "en" else render_email_cn(report))
        for path in files.values():
            p = Path(path)
            msg.add_attachment(p.read_bytes(), maintype="application", subtype="octet-stream", filename=p.name)
        with smtplib.SMTP(os.getenv("SMTP_SERVER", "smtp.gmail.com"), int(os.getenv("SMTP_PORT", "587")), timeout=30) as s:
            s.starttls()
            s.login(user, pw)
            s.send_message(msg)
        return {"sent": True, "recipient": to_email, "files": files}
    except smtplib.SMTPAuthenticationError as e:
        return {
            "sent": False,
            "reason": "SMTP authentication failed. Gmail usually requires a 16-character App Password with 2-Step Verification enabled, not the normal Gmail password.",
            "smtp_error": str(e),
            "files": files,
        }
    except Exception as e:
        return {
            "sent": False,
            "reason": f"SMTP send failed: {type(e).__name__}: {e}",
            "files": files,
        }


def send_email_report(report, lang="cn"):
    return _send_email_report(report, lang=lang)


def send_email_report_to(report, recipient, lang="cn"):
    recipient = (recipient or "").strip()
    if not EMAIL_RE.match(recipient):
        return {"sent": False, "reason": "Invalid recipient email address."}
    return _send_email_report(report, recipient=recipient, lang=lang)
