# MMF v1.0.18 — UAT Report

## Scope

UAT covers the new Beta layer and regressions inherited from the stable MMF. Test instruments: SOXL, NVDA, AAPL, QQQ, and XLE (a non-semiconductor sector ETF).

## Automated results

- Ticker profiles correctly distinguish leveraged ETF, individual stock, broad-market ETF, and sector ETF.
- SOXL loads the SOXL specialist; NVDA/AAPL/QQQ/XLE do not.
- AAPL selects XLK; NVDA selects SOXX; QQQ selects QQQ; XLE selects XLE.
- Put/Call thresholds produce the four specified context zones and retain the non-directional limitation.
- Quarterly third-Friday OPEX is high volatility context with no directional signal.
- All five instruments produce six decision blocks and four distinct paths totaling 100%.
- Flow language remains probabilistic.
- AAPL does not inherit the SOXL semiconductor-leadership conclusion.
- Chinese and English daily briefs include the same Beta structure.
- Review exports include decision blocks, four paths, version/date, and missing-data disclosure.
- Existing earnings-calendar, structural-revision, and 401(k) tests pass.

Result at implementation: **19 tests passed** (13 inherited `unittest` tests plus 6 Beta UAT tests).

## Browser checks

Completed against an isolated local QA process, then the final authenticated Beta service was restarted on port 8005:

- SOXL live report loaded and displayed six decision blocks.
- AAPL was classified as `INDIVIDUAL_STOCK` with XLK as benchmark; SOXL specialist and ETF-weight cards were hidden as not applicable.
- Chinese/English switching preserved the same six blocks and changed the analytical narrative without changing layout.
- All six blocks exposed question-mark explanations.
- Review Mode opened all 96 currently rendered detail panels and all seven page views.
- English Review export produced 6,136 characters and included version, four paths, and missing-data disclosure.
- English email preview for AAPL used the Beta decision brief and did not fall back to the Chinese title.
- A 390 × 844 mobile viewport rendered a single-column decision grid with no horizontal overflow.
- The existing 8004 stable tab remained available and titled `MMF v3.0.7 全球战场`.

## Acceptance caveats

This is a Beta/UAT candidate, not a stable promotion. Missing live data must remain disclosed, scenario weights are not forecast calibration, and unknown instruments should be reviewed when classification confidence is low.
