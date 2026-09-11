# MMF v1.0.18 — Master Refactor & UAT Specification

**Status:** Beta / UAT  
**Purpose:** Codex implementation specification  
**Rule:** Do **NOT** overwrite the current stable MMF version.  
**Source of truth:** This document should become the master specification for the v1.0.18 refactor.

---

## 1. Core Objective

MMF has accumulated a large amount of useful information, but the current problems are:

1. Too much information is presented at the same level, increasing review time and cognitive load.
2. Some analysis is still hard-coded around **SOXL**, even when the user enters another ticker.
3. Some indicators overlap or repeat the same information.
4. MMF often gives a label or conclusion without explaining the underlying market mechanism professionally.
5. Scenario analysis, macro interpretation, options positioning, and market-structure interpretation should be more systematic.
6. UAT is difficult because many sections are collapsed and cannot be reviewed as a complete output.

The Beta should **reduce noise without removing useful evidence**.

The philosophy is:

> Keep the evidence rich in the backend, but make the primary decision layer concise, dynamic, professional, and explainable.

---

# 2. Version / Safety Requirement

## 2.1 Do not overwrite production

The current working MMF must remain intact.

Create the new implementation as:

`MMF v1.0.18`

The Beta should run independently from the current stable version so that outputs can be compared side-by-side.

Do not:

- delete current logic;
- silently replace existing calculations;
- overwrite the stable application;
- change existing production behavior without an explicit Beta equivalent and comparison.

Where practical, use separate branches / directories / configuration flags.

Recommended future Git structure:

- `main` — stable version
- `beta` — current UAT candidate
- `dev` — active development

---

# 3. Make MMF Ticker-Aware

This is one of the highest-priority changes.

## Current problem

When the user changes the ticker away from SOXL, multiple sections still speak as though the security is SOXL or a leveraged semiconductor ETF.

That makes the application appear hard-coded and can produce logically incorrect analysis.

## Required behavior

The analysis engine must first identify the instrument being analyzed.

At minimum distinguish:

- Individual stock
- Standard ETF
- Leveraged ETF
- Broad-market ETF/index proxy
- Sector ETF
- Semiconductor/security-specific instruments
- Retirement / long-horizon fund where applicable

Then dynamically determine:

- relevant benchmark;
- relevant sector;
- important constituent stocks, if applicable;
- leverage characteristics;
- volatility expectations;
- suitable technical interpretation;
- appropriate macro sensitivity;
- relevant peer comparison;
- wording and risk language.

### Example

If ticker = `SOXL`:

Use semiconductor-specific logic, leveraged-ETF risk, SOXX/SMH/NVDA/AMD/QQQ context where relevant.

If ticker = `NVDA`:

Do **not** describe it as a leveraged semiconductor ETF. Analyze NVDA as an individual semiconductor stock, with appropriate sector and market benchmarks.

If ticker = `AAPL`:

Do not retain SOXL/NVDA/AMD-specific narrative unless they are genuinely relevant to market context.

### Architecture requirement

SOXL-specific logic should become a **specialized module/plugin**, not the universal analysis template.

General engine first → identify asset → load applicable specialized modules.

---

# 4. Dashboard Information Hierarchy

Do **not** compress the dashboard to only three items.

Target approximately **5–6 high-level decision blocks**.

The exact UI can evolve during Beta, but the primary page should approximately answer:

1. **Current Market Regime**
2. **Ticker State / Trend Quality**
3. **Relative Strength & Participation**
4. **Risk / Sentiment / Options Context**
5. **Scenario Probability & Key Levels**
6. **Action / Position Interpretation**

Detailed evidence remains available underneath through expandable sections.

## Principle

The main page answers:

> “What matters right now?”

Expanded sections answer:

> “Why does MMF think that?”

Do not delete useful underlying data simply to make the front page shorter.

---

# 5. Professional Narrative / Interpretation Layer

This is a major upgrade.

MMF currently tends to produce simplified labels such as “Market Vacation.” Labels can remain useful, but a label alone is not enough.

MMF should translate raw indicators into a **professional market interpretation**.

## Required reasoning chain

Whenever sufficient data exists, narrative should follow:

**Price Action  
→ Volume Confirmation  
→ Breadth / Participation  
→ Relative Strength  
→ Possible Flow Characteristics  
→ Macro / Risk Context  
→ Trading Implication**

### Example

Instead of only:

> Market Vacation

or:

> Bullish

MMF should be capable of producing something like:

> Price continues to advance, but participation and volume have not expanded proportionally. The move therefore has price confirmation but weaker consensus confirmation. Part of the advance may be consistent with systematic momentum, CTA/trend-following participation, or dealer hedging flows rather than broad discretionary accumulation. The trend remains constructive, but conviction is lower until volume and breadth improve.

Then translate that into an actionable interpretation:

> Existing positions can continue to participate, but the move does not justify chasing price. Confirmation should come from stronger participation, volume expansion, or a successful retest of support.

## Important language concepts MMF should understand

Where supported by evidence, MMF should be able to describe:

- low-consensus rally;
- high-consensus rally;
- distribution;
- accumulation;
- short covering;
- systematic momentum;
- CTA / trend-following participation;
- dealer hedging / gamma-related flows;
- narrow leadership;
- broad participation;
- price confirmation without volume confirmation;
- breadth divergence;
- relative-strength confirmation;
- failed breakout;
- technical repair;
- structural repair;
- risk-on / risk-off transition.

### Critical caution

Do **not** state a specific flow source as fact unless MMF actually has data proving it.

Use probabilistic language:

- “consistent with”
- “may reflect”
- “suggests”
- “cannot confirm, but…”

Do not hallucinate institutional flow.

---

# 6. Trend / Rally Quality Module

MMF should distinguish **price direction** from **quality of the move**.

A stock rising does not automatically mean the market broadly accepts the thesis.

Evaluate:

- price direction;
- absolute volume;
- volume vs recent average;
- breadth;
- sector confirmation;
- benchmark-relative strength;
- major constituent confirmation where applicable;
- options sentiment;
- volatility;
- macro backdrop.

Possible classifications:

- Strong / broad-confirmation advance
- Healthy advance
- Low-consensus advance
- Narrow / concentrated advance
- Technical rebound
- Short-covering-like rebound
- Weakening advance
- Distribution / breakdown

For leveraged products such as SOXL, this module should receive additional weight because low-quality rallies can reverse violently.

---

# 7. Avoid Duplicate Indicators

Do **not** add all seven CNN Fear & Greed components simply because they exist.

MMF already contains overlapping information.

Examples discussed:

- Put/Call is already represented.
- Sector/constituent views already provide useful breadth information.
- VIX already covers volatility.
- Fear & Greed composite can remain as a high-level sentiment indicator.

The goal is:

> **No indicator should be added unless it contributes incremental decision information.**

Credit-market indicators such as HYG/LQD or high-yield spreads should **not** become a core SOXL signal merely to add another dimension.

They may be used as low-priority macro/risk context where appropriate, because the transmission to semiconductor prices is indirect.

---

# 8. Put/Call Interpretation

Retain Put/Call, but improve interpretation.

## Important limitation

Put/Call ratio alone does **not** tell MMF whether puts were bought or sold, nor whether calls were bought or written.

Therefore:

> Put/Call must be treated as a sentiment/positioning proxy, not a deterministic directional signal.

For the current SOXL-oriented workflow, use approximate alert zones as contextual thresholds rather than mechanical trade triggers:

- `< 1.0` — relatively optimistic / call-heavy
- `1.0–1.3` — neutral to defensive
- `1.3–1.6` — elevated caution
- `> 1.6` — unusually defensive / fear-like positioning

These thresholds must **not** automatically generate buy/sell orders.

Interpret jointly with price:

### High Put/Call + support holds

Potential fear extreme / hedging demand. Could become contrarian bullish if structure stabilizes.

### High Put/Call + price breaks support + volume expands

More serious risk signal. Defensive positioning is being confirmed by price deterioration.

### Low Put/Call + extended price

Potential complacency / crowded optimism.

The dashboard should explain the interaction rather than displaying the ratio in isolation.

---

# 9. Macro Chain

Macro analysis needs to be restored as an explicit causal chain rather than a collection of headlines.

At minimum monitor:

- Federal Reserve expectations;
- rate-cut / hold / hike expectations;
- Treasury yields;
- inflation data;
- labor-market data;
- growth/activity data;
- liquidity/risk environment;
- scheduled high-impact releases.

## Required causal interpretation

For semiconductor / high-duration growth exposure:

**Economic data  
→ inflation/growth interpretation  
→ expected Fed path  
→ Treasury yields / discount rate  
→ growth-stock valuation pressure/support  
→ semiconductor / ticker impact**

Do not jump directly from:

> CPI higher → SOXL down

without explaining the transmission mechanism and whether the market had already priced the result.

Macro should be classified by:

- current state;
- direction of change;
- surprise vs expectations;
- whether already priced;
- likely transmission strength to the selected ticker.

---

# 10. Geopolitical Risk

Geopolitics should generally be treated as a **risk amplifier**, not automatically as the primary semiconductor driver.

Possible transmission channels:

1. Oil / energy shock
2. Inflation expectations
3. Treasury yields / Fed expectations
4. Broad risk-off behavior
5. Semiconductor supply-chain disruption
6. Taiwan / advanced-node manufacturing risk
7. Export-control / China-related semiconductor policy
8. Shipping/logistics disruption

MMF should distinguish:

### Indirect geopolitical event

Main effect is market sentiment, oil, inflation, or risk premium.

### Semiconductor-direct event

Affects fabrication, Taiwan, export controls, advanced chips, equipment, supply chain, or a major constituent.

Direct semiconductor events deserve materially greater weighting.

Historical geopolitical reactions can be used as context, but MMF must not assume identical future price responses.

---

# 11. OPEX / Expiration Risk Module

Add explicit awareness of major options/futures expiration windows, especially the **third Friday of the month** and major quarterly expiration periods.

Purpose:

- identify potentially elevated mechanical flow;
- recognize dealer hedging effects;
- recognize unusually high volume;
- warn that key technical levels may experience greater intraday noise.

OPEX is primarily a **volatility/flow amplifier**, not a directional predictor.

MMF should never say:

> “OPEX means the market will fall.”

Instead:

> “Expiration-related positioning may increase mechanical flows and intraday volatility around existing key levels; direction still requires price/volume confirmation.”

---

# 12. Four-Path Probability Engine

This remains a core MMF feature and must not disappear during simplification.

Each daily review should produce the **four highest-probability forward paths**.

Probabilities should sum to approximately 100%.

Each scenario should include:

- probability;
- trigger;
- expected price behavior;
- key support/resistance;
- confirmation signals;
- invalidation;
- likely macro/sector conditions;
- position implication.

Example structure:

### Scenario A — Constructive consolidation
**Probability:** XX%

Price holds support, digests the prior move, and builds acceptance.

### Scenario B — Bullish continuation
**Probability:** XX%

Breakout receives volume, breadth, sector, and constituent confirmation.

### Scenario C — Failed breakout / retracement
**Probability:** XX%

Price loses the breakout zone and retests lower support.

### Scenario D — Macro/risk-driven breakdown
**Probability:** XX%

External shock overwhelms ticker-specific strength and produces structural deterioration.

## Important

The four paths are **not predictions presented as certainty**.

They are contingency maps.

The purpose is:

> Whatever the market does, the user already has a next move.

---

# 13. Position / Action Philosophy

Preserve the existing MMF philosophy:

> Always leave a next move.

Do not assume that every analysis requires a trade.

For the user's SOXL workflow:

- layered entries;
- layered exits;
- preserve liquidity;
- do not chase;
- use support zones for planned entries;
- lower-position entries can be exited above their own cost basis as part of tactical recycling;
- distinguish tactical lots from structural/core lots;
- a trade does not need to maximize profit to be successful;
- maintaining optionality is valuable.

The system should not become more aggressive merely because the narrative layer becomes more sophisticated.

---

# 14. Review / UAT Mode

Add a dedicated:

`Review Mode` / `UAT Mode`

This is required because normal dashboard sections may be collapsed, causing reviewers to miss information.

When enabled:

1. Expand **all collapsible sections**.
2. Show all tabs/sections needed for review.
3. Disable UI behavior that hides analysis from export where practical.
4. Produce a complete Markdown/text export of the analysis.
5. Allow full-page screenshots or equivalent review output.
6. Include ticker, timestamp/data date, version number, and data freshness.
7. Clearly identify missing data rather than silently omitting sections.

The goal is to let an external reviewer inspect the **entire MMF output**, not only the visible top-level dashboard.

---

# 15. UAT Requirements

UAT should explicitly test:

### Ticker switching

Run at least several structurally different instruments.

Examples:

- SOXL
- NVDA
- AAPL
- QQQ / SPY
- a non-semiconductor sector ETF

Verify that SOXL-specific wording does not leak into unrelated assets.

### Narrative quality

Check whether:

- conclusions explain *why*;
- professional terminology is understandable;
- causal claims are supported;
- probabilistic language is used appropriately;
- price and market acceptance are distinguished.

### Information duplication

Identify:

- repeated indicators;
- repeated conclusions;
- multiple panels saying essentially the same thing.

Prefer one primary interpretation with supporting evidence beneath it.

### Scenario engine

Verify:

- exactly four meaningful paths;
- probabilities are coherent;
- triggers differ;
- scenarios are not cosmetic rewrites of one another.

### Missing-data behavior

MMF must say when evidence is unavailable.

Do not fabricate an interpretation merely to fill the dashboard.

---

# 16. User-Safety / Interpretation Design

MMF contains enough information that inexperienced users may overreact to one panel or one indicator.

Therefore the interface should make clear:

- no single indicator determines a trade;
- Put/Call is contextual;
- Fear & Greed is contextual;
- OPEX is not directional;
- geopolitical headlines require transmission analysis;
- probability scenarios are not forecasts with certainty;
- the final interpretation should synthesize multiple dimensions.

The high-level page should reduce the chance that a user sees one red/green signal and immediately treats it as a standalone buy/sell instruction.

---

# 17. English Narrative Quality

After the functional Beta is stable, review the English output separately.

English should sound like professional market research, not literal translation or repetitive template language.

Avoid excessive use of:

- bullish / bearish without explanation;
- “market vacation” as the only conclusion;
- generic “risk remains” statements;
- deterministic causal language.

Prefer:

> “Price action remains constructive, but declining participation weakens conviction.”

rather than:

> “Bullish. Market is good.”

The English and Chinese versions should convey the same analytical meaning even if wording differs.

---

# 18. Documentation Requirement

After implementing the Beta, Codex should generate a **Model Development Document / Technical Documentation** based on the actual codebase.

It should document:

- system architecture;
- data sources;
- data pipeline;
- calculations;
- indicator definitions;
- ticker classification;
- benchmark selection;
- scoring logic;
- narrative logic;
- scenario engine;
- position logic;
- missing-data handling;
- UI structure;
- UAT methodology;
- known limitations;
- version history.

Do not document intended behavior that is not actually implemented without labeling it as planned/future work.

This document will be reviewed separately after Codex generates it.

---

# 19. Git / Version Management

Stop using dozens of copied local folders as the primary version-control system.

The current stable application can become:

`v1.0.0`

This refactor becomes:

`v1.0.18`

Suggested future versioning:

- `v1.1.1-beta` — small Beta fix
- `v1.1.2-beta` — subsequent Beta fix
- `v1.1.0` — stable release after UAT
- `v1.2.0-beta` — next feature release

Use a **private Git repository**.

Recommended branches:

- `main`
- `beta`
- `dev`

Every meaningful change should have:

- commit message;
- affected files;
- short change summary;
- known limitations;
- UAT status.

---

# 20. Deployment — Not Part of Core Refactor

Do not mix infrastructure migration with analytical refactoring unless necessary.

Current priority:

1. Put project under Git/version control.
2. Preserve `v1.0.0`.
3. Build `v1.0.18`.
4. Run local UAT.
5. Run Review Mode.
6. Fix analytical/UI issues.
7. Only then stabilize external Beta deployment.

For a small private UAT group, remote-access/deployment architecture can remain lightweight.

Do not redesign the entire analytical application merely to accommodate deployment.

Eventually Git-based CI/CD can deploy the Beta environment to a cloud host.

---

# 21. Implementation Priority

## P0 — Must not regress

- Preserve current stable version.
- Create isolated Beta.
- No loss of existing useful calculations/data.
- Correct ticker awareness.
- Remove SOXL hard-coding from universal logic.

## P1 — Core Beta work

- 5–6 block information hierarchy.
- Professional narrative layer.
- Trend/rally quality.
- Four-path probability engine.
- Improved macro causal chain.
- Put/Call contextual interpretation.
- Geopolitical risk transmission.
- OPEX awareness.

## P2 — Reviewability

- Review/UAT Mode.
- Full expanded export.
- Data freshness/version labeling.
- Missing-data disclosure.

## P3 — Engineering hygiene

- Private Git repository.
- `main` / `beta` / `dev`.
- semantic-ish versioning.
- Codex-generated Model Development Document.

## P4 — Later

- External Beta deployment / CI/CD.
- broader subscription/account infrastructure.

---

# 22. Codex Completion Checklist

Before declaring `v1.0.18` complete, Codex should report:

- [ ] Stable MMF was not overwritten.
- [ ] Beta launches independently.
- [ ] Ticker classification is implemented.
- [ ] Non-SOXL tickers no longer receive inappropriate SOXL narrative.
- [ ] SOXL-specific analysis still works when SOXL is selected.
- [ ] Main dashboard contains approximately 5–6 decision blocks.
- [ ] Detailed evidence remains accessible.
- [ ] Narrative layer explains price + volume + breadth + relative strength.
- [ ] Flow language is probabilistic rather than fabricated.
- [ ] Put/Call interpretation is contextual.
- [ ] Macro chain explains transmission mechanism.
- [ ] Geopolitical risk distinguishes direct vs indirect semiconductor impact.
- [ ] OPEX is treated as a volatility/flow amplifier, not a directional forecast.
- [ ] Four forward scenarios are generated with probabilities and triggers.
- [ ] Review Mode expands hidden/collapsed information.
- [ ] Complete Markdown/text review export works.
- [ ] Missing data is explicitly identified.
- [ ] Version and data freshness are visible.
- [ ] English narrative has been checked for professional wording.
- [ ] No obvious duplicate panels/signals remain.
- [ ] Codex outputs a list of modified files and a concise change log.
- [ ] Model Development Document is generated from the implemented system.

---

# 23. Final Design Principle

MMF should not become a larger collection of indicators.

It should become a better **reasoning system**.

The intended hierarchy is:

> **Data → Evidence → Interpretation → Scenario → Action**

not:

> **Indicator → Indicator → Indicator → Indicator → Buy/Sell**

The user should be able to understand the high-level market state in a few minutes, while still being able to open the underlying evidence when deeper investigation is necessary.

And the core trading philosophy remains:

> **Do not predict one future. Prepare for the highest-probability futures, preserve optionality, and always leave a next move.**
