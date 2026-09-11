(function () {
  'use strict';

  const VERSION = 'v1.0.18';
  let reviewMode = false;

  function byId(id) { return document.getElementById(id); }
  function safe(value) {
    return String(value == null || value === '' ? '--' : value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
  function isEnglish() { return document.documentElement.lang === 'en' || document.body.classList.contains('lang-en'); }
  function text(cn, en) { return isEnglish() ? en : cn; }
  function languageKey(cn, en) { return isEnglish() ? en : cn; }

  function help(linesCN, linesEN) {
    const lines = isEnglish() ? linesEN : linesCN;
    return `<details class="sectionHelp betaHelp"><summary aria-label="${text('说明','Explanation')}">?</summary><div class="note">${lines.map(x => `<p>${safe(x)}</p>`).join('')}</div></details>`;
  }

  function ensureShell() {
    const page = byId('mmfPage');
    if (!page || byId('betaDecisionLayer')) return;
    const controls = page.querySelector(':scope > .controls');
    const beta = document.createElement('section');
    beta.id = 'betaDecisionLayer';
    controls.insertAdjacentElement('afterend', beta);

    const legacy = document.createElement('details');
    legacy.id = 'betaLegacyEvidence';
    legacy.className = 'card betaLegacyEvidence';
    legacy.innerHTML = `<summary><span data-zh="完整证据库（稳定版模块，按需展开）" data-en="Complete Evidence Library (stable modules, expand as needed)">完整证据库（稳定版模块，按需展开）</span></summary><div id="betaLegacyContent"></div>`;
    beta.insertAdjacentElement('afterend', legacy);
    const content = byId('betaLegacyContent');
    [...page.children].forEach(node => {
      if (node !== controls && node !== beta && node !== legacy) content.appendChild(node);
    });

    const style = document.createElement('style');
    style.textContent = `
      .betaHero{border-color:rgba(64,199,215,.48);background:linear-gradient(135deg,rgba(8,27,39,.98),rgba(19,23,37,.98));padding:18px;border-radius:8px;margin:16px 0}
      .betaHeroTop{display:flex;justify-content:space-between;gap:16px;align-items:flex-start}.betaIdentity{display:flex;gap:7px;flex-wrap:wrap;margin-top:10px}
      .betaDecisionGrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:14px 0}.betaDecisionCard{position:relative;border:1px solid var(--line);background:#0b1422;border-radius:8px;padding:15px;min-height:190px}.betaDecisionCard h3{font-size:14px;color:var(--muted);margin:0 38px 10px 0}.betaDecisionCard .betaValue{font-size:clamp(16px,1.3vw,20px);font-weight:900;color:var(--gold);line-height:1.25;overflow-wrap:anywhere;padding-right:2px}.betaDecisionCard .betaScore{display:block;font-size:13px;color:var(--cyan);margin-top:5px}.betaDecisionCard .betaSummary{font-size:13px;line-height:1.55;color:#ced7e4;margin-top:10px}.betaDecisionCard .betaHelp{position:absolute;right:12px;top:12px}
      .betaNarrative{border-left:4px solid var(--cyan);padding:14px 16px;background:rgba(64,199,215,.07);border-radius:0 8px 8px 0}.betaNarrative h2{margin:0 0 8px}.betaAction{border-left-color:var(--gold);background:rgba(215,181,109,.08);margin-top:10px}
      .betaEvidenceGrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.betaEvidenceGrid>details{margin:0}.betaScenario{border-left:3px solid var(--cyan);padding:10px 12px;margin:9px 0;background:rgba(64,199,215,.06)}.betaScenario b{color:var(--gold)}
      .betaMissing{color:#ffb2aa}.betaReviewOutput{max-height:70vh}.betaLegacyEvidence>summary{font-size:18px}.betaReviewMode .pageView{display:block!important}.betaReviewMode #englishPage{display:none!important}.betaReviewMode .navRow{position:sticky;top:0;z-index:90;background:rgba(8,16,24,.96);padding:8px}.betaReviewMode #betaLegacyEvidence{display:block}.betaReviewMode #betaLegacyContent{display:block}
      @media(max-width:1000px){.betaDecisionGrid,.betaEvidenceGrid{grid-template-columns:1fr}.betaHeroTop{flex-direction:column}.betaDecisionCard{min-height:0}}
    `;
    document.head.appendChild(style);
  }

  function renderDecisionBlocks(beta) {
    return (beta.decisionBlocks || []).map(block => {
      const title = block[languageKey('titleCN','titleEN')];
      const summary = block[languageKey('summaryCN','summaryEN')];
      const score = block.score == null ? '' : `<span class="betaScore">${safe(block.score)}/100</span>`;
      return `<article class="betaDecisionCard"><h3>${safe(title)}</h3>${help(
        ['这里是决策层摘要；它压缩相关证据，但不会隐藏数据缺失。展开下方证据库可核对计算。','卡片结论必须与其他证据共同使用，不能单独产生交易许可。'],
        ['This is a decision-layer summary. It compresses related evidence without hiding missing data; expand the evidence layer to audit the calculation.','Use this card with the other evidence. It cannot create trading permission by itself.']
      )}<div class="betaValue">${safe(block.value)}${score}</div><div class="betaSummary">${safe(summary)}</div></article>`;
    }).join('');
  }

  function renderEvidence(beta) {
    const quality = beta.trendRallyQuality || {};
    const putCall = beta.putCall || {};
    const macro = beta.macroChain || {};
    const geo = beta.geopoliticalRisk || {};
    const opex = beta.opex || {};
    const earnings = beta.earnings || {};
    const componentRows = Object.entries(quality.components || {}).map(([k,v]) => `<tr><td>${safe(k)}</td><td>${safe(v)}</td></tr>`).join('');
    const paths = (beta.scenarios || []).map(s => `<div class="betaScenario"><b>${safe(s[languageKey('nameCN','name')])} · ${safe(s.probability)}%</b><div>${safe(s[languageKey('conditionCN','triggerEN')])}</div><div class="small">${text('确认','Confirmation')}: ${safe(s[languageKey('confirmationCN','confirmationEN')])}</div><div class="small">${text('作废','Invalidation')}: ${safe(s[languageKey('invalidCN','invalidationEN')])}</div><div class="small">${text('应对','Response')}: ${safe(s[languageKey('responseCN','positionImplicationEN')])}</div></div>`).join('');
    const missing = (beta.missingData || []).map(x => `<li class="${x.available ? '' : 'betaMissing'}">${x.available ? '✓' : '○'} ${safe(x.field)} — ${safe(x.note)}</li>`).join('');
    return `<details class="card" id="betaEvidenceLayer"><summary>${text('Beta 证据层：计算、机制与限制 ▾','Beta Evidence Layer: Calculations, Mechanisms & Limits ▾')}</summary>
      <div class="betaEvidenceGrid">
        <details><summary>${text('趋势 / 行情质量','Trend / Move Quality')}</summary><p class="note">${safe(quality.classification)} · ${safe(quality.score)}/100</p><table><tr><th>${text('组成','Component')}</th><th>${text('分数','Score')}</th></tr>${componentRows}</table><p class="small">${safe(quality[languageKey('possibleFlowCN','possibleFlowEN')])}</p></details>
        <details><summary>Put/Call</summary><p class="note">${safe(putCall[languageKey('summaryCN','summaryEN')])}</p><p class="small">${safe(putCall[languageKey('limitationCN','limitationEN')])}</p></details>
        <details><summary>${text('宏观因果链','Macro Causal Chain')}</summary><p class="note">${(macro[languageKey('chainCN','chainEN')] || []).map(safe).join(' → ')}</p><p class="small">${safe(macro[languageKey('interpretationCN','interpretationEN')])}</p></details>
        <details><summary>${text('地缘传导与到期风险','Geopolitical Transmission & OPEX')}</summary><p class="note">${safe(geo[languageKey('summaryCN','summaryEN')])}</p><p class="small">${safe(opex[languageKey('summaryCN','summaryEN')])}</p></details>
        <details><summary>${text('财报日历','Earnings Calendar')}</summary><p class="note"><b>${text('风险','Risk')} ${safe(earnings.riskLevel)}</b> · ${safe(earnings[languageKey('summaryCN','summaryEN')] || earnings[languageKey('reasonCN','reasonEN')])}</p><p class="small">${safe(earnings[languageKey('actionCN','actionEN')])}</p></details>
      </div>
      <details><summary>${text('四路径完整应对图（概率合计','Complete Four-Path Map (probability total')} ${safe(beta.probabilityTotal)}%）</summary>${paths}</details>
      <details><summary>${text('数据新鲜度与缺失披露','Freshness & Missing-Data Disclosure')}</summary><p class="small">${text('缺失不会被零值或推测填补。','Missing evidence is never replaced with zeroes or invented values.')}</p><ul>${missing}</ul></details>
    </details>`;
  }

  function renderBeta(report) {
    ensureShell();
    const beta = report && report.betaV110;
    if (!beta || !byId('betaDecisionLayer')) return;
    const p = beta.profile || {};
    const n = beta.narrative || {};
    const fresh = beta.dataFreshness || {};
    const semiconductorRelevant = (p.specialists || []).includes('semiconductor');
    const specialistCard = byId('mmf10StructureCard');
    if (specialistCard) specialistCard.classList.toggle('hidden', !semiconductorRelevant);
    const etfCard = byId('etfSummary')?.closest('.card');
    if (etfCard) etfCard.classList.toggle('hidden', !(report.etfWeights || {}).isETF);
    byId('betaDecisionLayer').innerHTML = `<div class="betaHero">
      <div class="betaHeroTop"><div><div class="summaryKicker">MMF ${safe(beta.version || VERSION)} · REVIEW READY</div><h2 class="title">${safe(n[languageKey('headlineCN','headlineEN')])}</h2><div class="betaIdentity"><span class="pill">${safe(p.ticker)}</span><span class="pill">${safe(p.type)}</span><span class="pill">${text('基准','Benchmark')} ${safe(p.benchmark)}</span><span class="pill">${text('数据','Data')} ${safe(beta.asOf)}</span><span class="pill">${fresh.isStale ? 'STALE' : 'CURRENT / CHECKED'}</span></div></div><div class="titleActions"><button class="ghost compactBtn" onclick="MMFBeta.toggleReview()">${text('Review Mode','Review Mode')}</button><button class="ghost compactBtn" onclick="MMFBeta.exportReview(false)">${text('完整导出','Full Export')}</button></div></div>
      <p class="small">${safe(beta.reviewMode && beta.reviewMode[languageKey('principleCN','principleEN')])}</p>
      <div class="betaDecisionGrid">${renderDecisionBlocks(beta)}</div>
      <div class="betaNarrative"><h2>${text('专业市场解读','Professional Market Interpretation')}</h2><p>${safe(n[languageKey('professionalNarrativeCN','professionalNarrativeEN')])}</p></div>
      <div class="betaNarrative betaAction"><h2>${text('下一步行动','Next Action')}</h2><p>${safe(n[languageKey('actionCN','actionEN')])}</p></div>
    </div>${renderEvidence(beta)}<details class="card" id="betaReviewExportCard"><summary>${text('完整 Review 文本 / Markdown','Complete Review Text / Markdown')}</summary><div class="controls"><button class="ghost compactBtn" onclick="MMFBeta.exportReview(true)">${text('下载 .md','Download .md')}</button></div><pre id="betaReviewExport" class="betaReviewOutput">${text('点击“完整导出”生成。','Select “Full Export” to generate.')}</pre></details>`;
    const title = document.querySelector('.hero h1');
    if (title) title.innerHTML = `Miao Market Framework <span class="small">${VERSION} · Release</span>`;
    document.title = `MMF ${VERSION}`;
    if (reviewMode) document.querySelectorAll('#betaDecisionLayer details,#betaReviewExportCard').forEach(node => { node.open = true; });
  }

  function toggleReview() {
    reviewMode = !reviewMode;
    document.body.classList.toggle('betaReviewMode', reviewMode);
    const details = document.querySelectorAll('details');
    details.forEach(node => {
      if (reviewMode) {
        if (!node.open) node.dataset.betaOpened = '1';
        node.open = true;
      } else if (node.dataset.betaOpened === '1') {
        node.open = false;
        delete node.dataset.betaOpened;
      }
    });
    if (!reviewMode && typeof showLocalizedPage === 'function') showLocalizedPage(typeof localizedPage === 'undefined' ? 'mmf' : localizedPage);
  }

  async function exportReview(download) {
    const ticker = (byId('ticker')?.value || 'SOXL').trim().toUpperCase();
    const mode = byId('mode')?.value || 'live';
    const position = typeof savedExposureFor === 'function' ? savedExposureFor(ticker) : 0;
    let url = `/review-export/${encodeURIComponent(ticker)}?mode=${encodeURIComponent(mode)}&lang=${isEnglish() ? 'en' : 'cn'}&position_pct=${encodeURIComponent(position)}`;
    if (mode === 'replay' && byId('date')?.value.trim()) url += `&date=${encodeURIComponent(byId('date').value.trim())}`;
    const output = byId('betaReviewExport');
    if (output) output.textContent = text('正在生成完整审查文本…','Generating complete review text…');
    try {
      const response = await fetch(url, {cache:'no-store'});
      const body = await response.text();
      if (!response.ok) throw new Error(body);
      if (output) output.textContent = body;
      const card = byId('betaReviewExportCard'); if (card) card.open = true;
      if (download) {
        const blob = new Blob([body], {type:'text/markdown;charset=utf-8'});
        const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `MMF_${VERSION}_${ticker}_${isEnglish() ? 'en' : 'cn'}_review.md`; a.click(); URL.revokeObjectURL(a.href);
      }
    } catch (error) {
      if (output) output.textContent = `${text('导出失败','Export failed')}: ${error.message || error}`;
    }
  }

  ensureShell();
  const baseRender = window.render;
  window.render = function (report) { baseRender(report); renderBeta(report); };
  new MutationObserver(() => { if (typeof lastReport !== 'undefined' && lastReport) renderBeta(lastReport); }).observe(document.body, {attributes:true, attributeFilter:['class']});
  window.MMFBeta = {render:renderBeta, toggleReview, exportReview};
})();
