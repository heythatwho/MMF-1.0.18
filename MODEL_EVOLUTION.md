# MMF Model Evolution Log

MMF evolves from live campaigns, but a daily observation enters the model only when it can be expressed as a reusable rule with evidence, invalidation, and an account consequence.

## Update protocol

Every proposed change must record:

1. Field observation — what actually happened.
2. Existing-model failure — what the current model missed or expressed poorly.
3. Generalized rule — a rule that is not tied to one price or one trading day.
4. Counterexample — when the rule should not be used.
5. Account consequence — how the rule changes position size, entry, exit, or cash.
6. Validation — syntax, synthetic scenario, live report, bilingual UI, and email output.

Daily stories must not become permanent rules unless they survive this protocol.

## v3.0.7 — 2026-08-21 — Structural Intelligence / MMF-10 Revision

### Field observations

- SOXL can fall sharply while QQQ, SPX, small caps, or other sectors remain healthy. Semiconductor weakness alone is not proof of broad Risk-Off.
- The direction of relative strength is more useful than a static strong/weak label.
- An old range becomes misleading after price is accepted outside it; micro, daily, and higher-order levels cannot share one label.
- The same daily percentage decline can represent continuous selling or an opening liquidation followed by hours of stabilization.
- Heavy volume near support may show selling absorption, but does not prove institutional accumulation.
- A large catalyst-driven move is event risk until cross-market evidence confirms structural risk.

### Generalized model changes

- Added a relative-strength matrix for NVDA/SOXX, SOXL/SOXX, SOXX/QQQ, and NVDA/QQQ with separate level and change labels.
- Added a capital-rotation layer that explicitly answers whether money is leaving equities, leaving semiconductors, and where it is going.
- Replaced the old four-path set with Range, Bullish Breakout, Healthy Further Correction, and Systemic Risk probabilities totaling 100%.
- Added adaptive regime detection for Trend, Range, and Transition, with separate micro, daily, and higher-order structures.
- Added intraday auction classification and location/time/follow-through volume interpretation.
- Added a cross-market systemic-risk cluster using semiconductors, QQQ, SPX, breadth, VIX, HYG, and rates/dollar shock proxies.
- Added semiconductor leadership status: Expanding, Stable, Weakening, or Recovering.
- Added event-risk versus structural-risk separation and a waiting-regime classifier that does not invent an event calendar.
- Added macro transmission: rates/yields → discount rate → long-duration technology → semiconductors → SOXX → leveraged SOXL.
- Replaced binary Market Vacation with Market Vacation → Observation → Active Management.
- Added a mandatory twelve-question daily output and the explicit conclusion “No material structural change” when the evidence does not change the structure.

### Core rules

> Capital rotation is not capital flight. Systemic risk requires cross-market confirmation.

> A price level triggers evaluation; it is never an automatic buy, sell, or breakout signal.

> Absorption is not accumulation. A micro-range breakout is not automatically a higher-order trend reversal.

### Validation requirement

- Relative-strength probabilities must use aligned dates and sum to 100%.
- Replay reports must cut comparison histories at the replay date.
- Chinese UI, English UI, Chinese email, and English email must expose the same MMF-10 structural layer.
- Every new structural card must include a question-mark explanation.

### 2026-08-21 live refinement

- The displayed micro battlefield now prefers the valid current-session high/low while retaining a prior-session reference band for breakout and breakdown detection. This prevents an obsolete high from remaining inside the active micro range.
- Relative-strength rows now compare today with the previous report state. Persistent weakness remains visible but is not repeatedly presented as new structural information.
- Intraday auction classification is calculated before the four-scenario model and directly reweights the scenario probabilities. Continuous selling, opening-drive failure, balanced auction, and opening liquidation followed by stabilization no longer receive identical weights.
- Systemic risk now reports direction and level separately: increasing/decreasing/unchanged versus low/elevated/high.
- Chinese and English MMF-10 views use the same DOM, row counts, ordering, and question-mark explanations. The English daily email carries the same micro battlefield and systemic-risk direction.

### Refinement validation

- Four synthetic boundary tests passed: active micro range, non-repeated structural change, auction-driven scenario reweighting, and systemic-risk direction.
- Live SOXL output showed a 116.71–128.37 micro battlefield, a 100% four-scenario distribution, and systemic risk `UNCHANGED / INCONCLUSIVE / LOW`.
- Chinese and English MMF-10 each retained five structure rows, five scenario rows, thirteen daily-question rows, and the same expandable explanation system.
- English email preview included the live micro battlefield and systemic-risk direction; browser console reported no warnings or errors.

### 2026-08-23 — Earnings Calendar / 财报风险窗

- Replaced headline-only earnings detection with a confirmed shared earnings calendar from Alpha Vantage. One three-month calendar request is cached and distributed to every MMF module and tracked constituent.
- Added expected report date, days until report, tracked ETF weight, EPS estimate, currency, and report-session status. Pre-market/after-hours timing remains `TIME_NOT_PROVIDED` unless the source explicitly supplies it.
- Added weighted event-risk windows: near-term reports from large constituents can raise earnings risk to `HIGH`, move the catalyst regime to `WAITING`, prevent Active Management, and close trend-position permission before the event.
- Added replay protection: a replay never queries today's future calendar. Only calendar data stored in the original snapshot may enter historical analysis.
- Added the earnings calendar to the shared Chinese/English MMF-10 DOM, question-mark explanations, Copilot context, tomorrow checklist, daily question 6, position risk review, and both email languages.
- Headline mentions of earnings no longer become confirmed event risk by themselves. Without a scheduled date they remain `HEADLINE ONLY / UNCONFIRMED`.

Validation: eight synthetic tests passed. The live calendar confirmed NVDA for 2026-08-26 (tracked SOXL weight 22%, EPS estimate 2.01 USD, session timing not provided) and AVGO for 2026-09-02. The current earnings regime became `HIGH / WAITING`; trend permission became `NO`; Chinese and English email briefs both included the event.

## v3.0.6 — 2026-07-28 — Field Learning 1.0

### Field observations

- Several individually defensible entries can accumulate into an inefficient or overweight combined position.
- Ordinary fear was using capital that should have been reserved for extreme fear plus selling-pressure failure.
- A visible support sweep and rapid reclaim can be a stop hunt or inventory transfer, but a V-shaped rebound alone cannot prove institutional accumulation.
- A low probability of systemic crisis does not imply low downside risk for a daily-reset 3× ETF.
- Fixed exit prices are incomplete. The path into the target, sector breadth, volume, momentum, and structure determine how much to sell.
- Time and price symmetry can describe trend maturity but cannot predict the end date.
- A fixed tactical Reward/Risk number becomes stale as price, ATR, EMA20, and the 20-day range change.

### Generalized model changes

- Added Market Phase: trend, compression, transition, and range/price discovery.
- Added Liquidity Assessment: accumulation candidate, distribution, rotation, stop hunt, and unresolved.
- Added Emotion–Reaction Divergence: fear alone does not authorize risk; fear plus selling-pressure failure may raise the deployment class.
- Added Tail Risk as probability × impact, with explicit 3× path-risk language.
- Added Exit Quality (A–E) from trend, structure, breadth, volume, and momentum.
- Added Time/Price Symmetry as tertiary evidence only.
- Added Capital Efficiency and a rising evidence threshold for every additional layer.
- Added position-layer missions: structure, odds, liquidity, trend, core, trading, rebuild, and probe.
- Added 3×-equivalent exposure in the Position War Room.
- Added mandatory post-campaign review questions.
- Replaced fixed tactical Reward/Risk 1.8 with a daily calculation based on a dynamic first-rebound target and a risk distance using the greater of ATR14 or 10%.
- Removed the stale hard-coded SOXL 177→200 completed-trade state. The report and email now receive the saved Position War Room exposure.

### Core rules

> An entry must be efficient, not merely cheap. Every tranche can make sense while the combined position no longer has optimal odds.

> Do not size up merely because others are afraid. Size up only when fear is extreme and the market stops falling the way panic should.

> Price supplies the exit plan; the path into the target and the quality of confirmation determine how much to sell.

### Counterexamples and limits

- A support sweep followed by a reclaim is not automatically accumulation; failure to hold the transaction core downgrades the interpretation.
- Symmetry cannot authorize a trade.
- Low VIX does not remove leveraged ETF path risk.
- A high Exit Quality grade is not permission to ignore a tranche’s original invalidation.
- A deep discount does not override a failed systemic risk gate.

### Validation

- Python modules compile.
- Frontend JavaScript parses with Node.
- No duplicate static HTML IDs.
- Synthetic stop-hunt scenario returns the expected liquidity classification.
- Live SOXL report generated for 2026-07-28 with an explicitly supplied 42% exposure.
- Chinese and English email renderers include Field Learning.

## 401K_STRATEGIC_V1 — 2026-09-03 — Long-Term Retirement Portfolio

### Separation and mandate

- Added a dedicated 401(k) strategic module that shares market intelligence with MMF but never inherits SOXL execution logic.
- The module uses daily, weekly, and monthly evidence only. Intraday and five-minute inputs are explicitly excluded.
- The permanent strategic baseline remains 60% Vanguard Institutional 500, 25% Vanguard Extended Market, and 15% Vanguard Total International. The model does not alter this baseline automatically.

### Independent engines

- Portfolio Drift compares entered current holdings with the baseline using a ±5 percentage-point band. Missing balances remain `CURRENT ALLOCATION NOT AVAILABLE` rather than being guessed.
- Opportunity evaluates the three asset buckets independently using valuation 25%, drawdown 20%, macro 20%, relative trend 15%, breadth 10%, and systemic risk 10%.
- Confirmation is calculated separately. Drawdown alone cannot authorize accumulation, and high systemic risk overrides opportunity with `CAUTION`.
- Temporary new-contribution tilts are bounded at 5, 10, or 15 percentage points for mild, moderate, or rare qualified opportunities. Existing holdings remain `HOLD`; no automatic trade or allocation change is generated.

### Delivery and explainability

- Added one compact daily 401(k) status to the battlefield, one dedicated strategic page, and one monthly review block.
- Chinese and English use the same DOM, module order, data fields, and question-mark explanations.
- Chinese and English daily emails now carry the matching 401(k) status, new-contribution mix, and drift state.
- Valuation is exposed as a configurable normalized input. V1 breadth is labeled as a fund-price participation proxy rather than fabricated constituent breadth.
- The approximate incoming Principal rollover remains processing context only and is explicitly excluded from permanent portfolio value.

### Validation

- Synthetic tests verify drift independence, dual opportunity/confirmation thresholds, drawdown-only rejection, new-contribution-only changes, and bounded moderate/rare tilts.
- Python sources compile without writing bytecode; the 401(k) and unified bilingual JavaScript bundles pass syntax checks.
