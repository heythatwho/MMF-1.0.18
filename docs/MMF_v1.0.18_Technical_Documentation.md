# MMF v1.0.18 — Model Development & Technical Documentation

## 1. Status and safety boundary

This document describes the code packaged in the isolated `MMF-1.0.18` directory. It is intended to run independently on port 8005 and does not require modifying an older local service.

Implemented version: `v1.0.18`.

## 2. Runtime architecture

1. `api/app.py` exposes the authenticated HTML application, report API, email preview/send APIs, and the Beta review-export endpoint.
2. `mmf_engine/data.py` acquires and caches market data.
3. `mmf_engine/engine.py` prefetches shared market data once, builds the existing evidence report, then invokes the Beta analysis.
4. `mmf_engine/beta_v110.py` classifies the ticker, selects relevant context, evaluates move quality, builds mechanism-based narrative, and produces four conditional paths.
5. `frontend/beta_v110.js` adds the six-block primary layer, evidence disclosure, Review Mode, and Markdown download to the existing shared bilingual DOM.
6. `mailer/email_engine.py` uses the Beta bilingual decision brief when `betaV110` is present.

The decision hierarchy is `Data → Evidence → Interpretation → Scenario → Action`.

## 3. Data sources and pipeline

The inherited data layer currently supports:

- Tiingo daily prices and Tiingo IEX five-minute OHLCV when configured;
- Yahoo chart/extended quote and news fallbacks;
- Yahoo or Cboe delayed option-chain data;
- Alpha Vantage quote and earnings-calendar data when configured;
- Cboe VIX history and external Fear & Greed context;
- Stooq fallback for selected cross-asset proxies.

`shared_market_data()` fetches the cross-market quote universe once per report and redistributes it to ETF, heatmap, macro, relative-strength, leadership, systemic-risk, and flow modules. This avoids repeated requests for the same symbol. Data date, source, session, staleness, comparison-history failures, and missing Beta inputs are retained in the report.

## 4. Ticker classification and benchmark selection

`classify_instrument()` returns:

- instrument type;
- leverage multiple where known;
- sector in English and Chinese;
- sector benchmark and broad-market benchmark;
- relevant peers;
- applicable specialists;
- classification confidence and risk language.

Explicit profiles cover SOXL, TQQQ, UPRO, SPXL, NVDA, AAPL, MSFT, SPY, QQQ, IWM, SMH, SOXX, XLK, XLE, and XLF. Known broad, sector, and leveraged ETF sets provide medium/high-confidence fallbacks. Unknown symbols use a low-confidence generic-equity fallback; the UI discloses that limitation.

SOXL loads `soxl`, `leveraged_etf`, and `semiconductor` specialists. Non-semiconductor tickers receive a ticker-aware relative-strength row and the semiconductor-leadership module is marked `NOT_APPLICABLE` rather than silently reused.

## 5. Move-quality calculation

`trend_rally_quality()` separates direction from quality. It uses only available components and renormalizes their weights:

| Component | Nominal weight |
|---|---:|
| Price direction / EMA20 relationship | 20 |
| Volume versus recent average | 20 |
| Sector breadth / participation | 15 |
| Sector confirmation | 10 |
| Relative strength versus selected benchmark | 15 |
| Options context | 10 |
| Macro context | 10 |

Missing components are omitted from the denominator rather than treated as zero. Output classes include broad-confirmation advance, healthy advance, low-consensus advance, narrow/concentrated advance, technical rebound, weakening/unconfirmed advance, decline/repair unconfirmed, and distribution/breakdown.

Possible-flow descriptions are explicitly probabilistic. Public price/volume/options data cannot prove which institution initiated a move.

## 6. Put/Call interpretation

Put/Call Volume is classified into contextual zones:

- below 1.0: call-heavy / optimistic;
- 1.0–1.3: neutral to defensive;
- 1.3–1.6: elevated caution;
- above 1.6: unusually defensive.

The engine combines this context with support behavior, price change, volume ratio, IV, and a gamma proxy. It never converts the ratio directly into an order. It also states that public aggregate ratios cannot distinguish options bought from options sold or calls bought from calls written.

## 7. Macro, geopolitics, and OPEX

The macro chain is explicit: economic data → Fed-path expectations → Treasury yields/discount rate → selected-sector valuation/risk appetite → ticker response. TLT, UUP, USO, and VIX are proxies. Live Fed-probability distribution, surprise-versus-consensus data, and scheduled-release calendar are currently not connected and are disclosed as missing.

Geopolitical news is classified as direct instrument/sector transmission, indirect risk amplification, or no confirmed geopolitical driver. Headline matching only produces a candidate channel; price, volume, and peer response still have to confirm it.

OPEX is computed from the third Friday of the month and identifies quarterly expiration months. It changes volatility/hedging-risk context only; `directionalSignal` is always false.

## 8. Scenario engine

The Beta always emits exactly four paths:

1. Constructive consolidation;
2. Bullish continuation;
3. Failed breakout / retracement;
4. Macro / risk breakdown.

Planning weights respond to move quality, macro headwind, direct geopolitical risk, and elevated OPEX risk, then normalize to exactly 100%. Every path contains activation, confirmation, invalidation, macro/sector context, and position implication. These weights are planning aids, not calibrated price forecasts.

## 9. Narrative and action logic

The professional narrative follows price action, volume, breadth/participation, relative strength, possible flows, macro/options/geopolitical risk, and trading implication. Direction is never treated as equivalent to quality. Actions remain conditional:

- strong/healthy move: participate with existing exposure; add only after defended retest or confirmed break;
- decline/distribution: freeze additions and reassess invalidation/account risk;
- mixed/unconfirmed: preserve both exposure and cash optionality;
- flat account: any initial participation is a small observation tranche with explicit invalidation, not full deployment.

The inherited account-risk and position-engineering controls remain available in the complete evidence library.

## 10. UI and bilingual behavior

The primary MMF page presents six equally weighted blocks: regime, ticker state/move quality, relative strength/participation, risk/options, scenario/key levels, and action/position interpretation. Professional narrative and next action follow the blocks. Detailed Beta calculations and all inherited evidence remain expandable.

Chinese and English use the same DOM. Dynamic Beta values select the corresponding language field; no separate English page template is used. Every decision block has a question-mark explanation. Review Mode opens all details and page sections for UAT. The export endpoint returns complete Chinese or English Markdown including version, date, profile, six blocks, four paths, evidence, and missing-data disclosure.

## 11. Email behavior

When a Beta report is present, both preview and send paths use `daily_brief()`. The selected UI language is passed as `lang=cn` or `lang=en`. The email mirrors the six-block decision layer, professional interpretation, conditional action, four paths, evidence limits, and the separate 401(k) mandate without repeating the old SOXL-centric sections.

## 12. Missing-data policy

Unavailable inputs are represented as unavailable and listed explicitly. The engine does not infer zero, neutral, or directional meaning from absence. Current explicit gaps include live Fed probabilities, economic surprise consensus, scheduled economic-release calendar, and any unavailable quote/volume/options/news input.

## 13. UAT methodology

Automated unit and synthetic-matrix tests cover SOXL, NVDA, AAPL, QQQ, and XLE. They verify classification, specialist selection, contextual Put/Call thresholds, non-directional OPEX, exactly six blocks, exactly four paths totaling 100%, probabilistic flow language, non-semiconductor sanitization, bilingual email, and complete Review export. Existing earnings, structural, and 401(k) regression tests are also run.

Browser UAT verifies live report loading, shared bilingual layout, Review Mode, help controls, and export on the independent Beta server.

## 14. Known limitations / future work

- Classification is registry/set based, not yet backed by a live security-master service.
- Scenario probabilities are deterministic planning heuristics, not statistically calibrated forecasts.
- Breadth uses available group proxies rather than full constituent advance/decline data.
- Gamma exposure is a proxy derived from public option-chain fields, not dealer inventory.
- Headline keyword classification does not perform entity-resolution or causal proof.
- Live Fed probabilities, economic-surprise consensus, and a scheduled macro calendar are not connected.
- Beta remains local/private; remote private repository and CI/CD are intentionally outside this analytical refactor.

## 15. Version history

- `v1.0.0`: frozen stable baseline imported into local Git.
- `v1.0.18`: ticker-aware decision/narrative/scenario layer, contextual risk modules, shared bilingual UI, Review Mode/export, and concise bilingual mail.
