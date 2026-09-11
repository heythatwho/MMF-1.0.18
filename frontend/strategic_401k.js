(function () {
  'use strict';

  let report = null;
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '--').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const language = () => document.documentElement.lang.toLowerCase().startsWith('en') ? 'en' : 'zh';
  const num = (value, digits = 1) => Number.isFinite(Number(value)) ? Number(value).toFixed(digits).replace(/\.0$/, '') : '--';
  const pct = value => value == null ? '--' : `${num(value)}%`;
  const zhStatus = value => ({
    'HOLD BASELINE':'维持基线',
    'WATCH':'观察',
    'ACCUMULATE WITH NEW CONTRIBUTIONS':'用新缴款逐步积累',
    'RARE LONG-TERM ACCUMULATION OPPORTUNITY':'罕见长期积累机会',
    'CAUTION / HOLD BASELINE':'谨慎 / 维持基线',
    'NO 401(k) ACTION REQUIRED':'无需 401(k) 行动',
    'REVIEW CONTRIBUTION TILT':'审查新缴款倾斜',
    'NORMAL':'正常',
    'MILD_RISK_ON':'温和 Risk-On',
    'STRONG_RISK_ON':'强 Risk-On',
    'MILD_RISK_OFF':'温和 Risk-Off',
    'STRONG_RISK_OFF':'强 Risk-Off',
    'RECOVERY':'修复期',
    'SYSTEMIC_STRESS':'系统压力',
    'CURRENT ALLOCATION NOT AVAILABLE':'当前持仓比例未录入',
    'REBALANCE WATCH':'再平衡观察',
    'HOLD':'维持',
    'ACCUMULATE':'积累',
    'RARE_OPPORTUNITY':'罕见机会',
    'CAUTION':'谨慎'
  })[String(value)] || String(value ?? '--');
  const label = (zh, en) => language() === 'en' ? en : zh;
  const status = value => language() === 'en' ? String(value ?? '--').replaceAll('_', ' ') : zhStatus(value);
  const help = (zh, en) => `<details class="sectionHelp"><summary>?</summary><div class="note"><p data-zh="${esc(zh)}" data-en="${esc(en)}">${esc(zh)}</p></div></details>`;

  function ensureStyles() {
    if ($('strategic401kStyles')) return;
    const style = document.createElement('style');
    style.id = 'strategic401kStyles';
    style.textContent = `
      .retirementHero{border-color:rgba(64,199,215,.42);background:linear-gradient(135deg,rgba(9,31,43,.98),rgba(16,25,45,.96))}
      .retirementLead{max-width:1040px;font-size:17px;line-height:1.65;color:#d6deea}
      .retirementDecision{border-left:4px solid var(--cyan);padding:13px 15px;background:rgba(64,199,215,.08);border-radius:0 8px 8px 0;margin-top:14px}
      .retirementGrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
      .retirementAsset{border:1px solid var(--line);border-radius:8px;padding:15px;background:#0b1220}
      .retirementAsset.best{border-color:rgba(215,181,109,.72);box-shadow:inset 0 0 0 1px rgba(215,181,109,.18)}
      .retirementAsset h3{margin:0 0 4px;color:var(--gold)}
      .retirementScores{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:13px 0}
      .retirementScore{padding:10px;border-radius:8px;background:rgba(64,199,215,.06);border:1px solid rgba(64,199,215,.18)}
      .retirementScore b{display:block;color:var(--gold);font-size:24px}
      .retirementFactors{font-size:12px;color:var(--muted);line-height:1.55}
      .retirementTable .recommended{color:var(--gold);font-weight:900}
      .retirementAlert{border:1px solid rgba(215,181,109,.38);background:rgba(215,181,109,.08);border-radius:8px;padding:13px}
      .retirementDaily{border-color:rgba(64,199,215,.34)}
      .retirementDaily .metric{font-size:22px;line-height:1.3}
      @media(max-width:900px){.retirementGrid{grid-template-columns:1fr}.retirementScores{grid-template-columns:1fr 1fr}}
    `;
    document.head.appendChild(style);
  }

  function ensureUi() {
    ensureStyles();
    const positionNav = $('positionNav');
    if (positionNav && !$('retirementNav')) {
      positionNav.insertAdjacentHTML('afterend', '<button id="retirementNav" class="ghost" onclick="showPage(\'retirement\')">401(k) 长期组合</button>');
    }
    const positionPage = $('positionPage');
    if (positionPage && !$('retirementPage')) {
      positionPage.insertAdjacentHTML('afterend', `
        <div id="retirementPage" class="pageView hidden">
          <div class="card retirementHero">
            <div class="titleRow"><div><div class="summaryKicker">MMF 401(k) STRATEGIC PORTFOLIO</div><h2 class="title" data-zh="401(k) 长期战略组合" data-en="401(k) Long-Term Strategic Portfolio">401(k) 长期战略组合</h2></div>
              ${help('这是独立于 SOXL 的退休资产引擎。两者只共享市场情报，不共享交易信号；盘中和五分钟数据不会进入 401(k) 决策。','This retirement engine is independent from SOXL. They share market intelligence, not execution signals; intraday and five-minute data never enter 401(k) decisions.')}
            </div>
            <p class="retirementLead" data-zh="用月、周、日数据分别审查组合漂移和长期机会。模型默认维持 60/25/15，只有机会与确认同时过门槛时，才建议临时调整未来新缴款。" data-en="Daily, weekly, and monthly evidence drive two separate reviews: portfolio drift and long-term opportunity. The 60/25/15 baseline remains unchanged unless both Opportunity and Confirmation clear their thresholds—and even then, only future contributions are tilted.">用月、周、日数据分别审查组合漂移和长期机会。模型默认维持 60/25/15，只有机会与确认同时过门槛时，才建议临时调整未来新缴款。</p>
            <div id="retirementDecision" class="retirementDecision">--</div>
          </div>
          <div class="grid4">
            <div class="card"><div class="label" data-zh="当前行动" data-en="Current Action">当前行动</div><div id="retirementAction" class="metric">--</div></div>
            <div class="card"><div class="label" data-zh="长期市场环境" data-en="Long-Term Regime">长期市场环境</div><div id="retirementRegime" class="metric">--</div></div>
            <div class="card"><div class="label" data-zh="现有持仓" data-en="Existing Holdings">现有持仓</div><div id="retirementHoldings" class="metric">--</div></div>
            <div class="card"><div class="label" data-zh="员工缴款率" data-en="Employee Contribution">员工缴款率</div><div id="retirementEmployeeContribution" class="metric">--</div></div>
          </div>
          <div class="card">
            <div class="titleRow"><div><div class="summaryKicker">CONTRIBUTION ENGINE</div><h2 class="title" data-zh="未来新缴款配置" data-en="Future New-Contribution Mix">未来新缴款配置</h2></div>
              ${help('基线是长期战略锚；建议栏只作用于未来新缴款，不代表系统自动交易、卖出现有基金或永久改变资产配置。温和、适中与罕见机会的最大倾斜分别为 5、10、15 个百分点。','The baseline is the strategic anchor. Recommendations apply only to future contributions—never automatic trades, sales of existing funds, or permanent allocation changes. Mild, moderate, and rare opportunities allow at most 5, 10, and 15 percentage points of tilt.')}
            </div>
            <table class="retirementTable"><thead><tr><th data-zh="资产桶" data-en="Asset Bucket">资产桶</th><th data-zh="基线" data-en="Baseline">基线</th><th data-zh="当前持仓" data-en="Current Holdings">当前持仓</th><th data-zh="建议新缴款" data-en="Recommended Contributions">建议新缴款</th></tr></thead><tbody id="retirementAllocationRows"></tbody></table>
            <div id="retirementContributionRead" class="note"></div>
          </div>
          <div class="card">
            <div class="titleRow"><div><div class="summaryKicker">OPPORTUNITY × CONFIRMATION</div><h2 class="title" data-zh="三类资产机会审查" data-en="Three-Bucket Opportunity Review">三类资产机会审查</h2></div>
              ${help('机会分衡量长期赔率：估值25%、回撤20%、宏观20%、相对趋势15%、广度10%、系统风险10%。确认分独立检查趋势、广度、相对强弱与风险环境。下跌本身不能触发积累。','Opportunity measures long-horizon asymmetry: valuation 25%, drawdown 20%, macro 20%, relative trend 15%, breadth 10%, and systemic risk 10%. Confirmation independently checks trend, breadth, relative strength, and risk. A decline alone cannot authorize accumulation.')}
            </div>
            <div id="retirementAssetGrid" class="retirementGrid"></div>
          </div>
          <div class="grid">
            <div class="card">
              <div class="titleRow"><h2 class="title" data-zh="组合漂移审查" data-en="Portfolio Drift Review">组合漂移审查</h2>
                ${help('漂移引擎和机会引擎彼此独立。只有录入实际持仓比例后才判断是否超出基线上下 5 个百分点；优先用新缴款修正，不自动卖出。','The drift and opportunity engines are independent. Drift is evaluated only after current holdings are entered, using a ±5 percentage-point band. Correct with new contributions first; never auto-sell.')}
              </div>
              <div id="retirementDriftRead" class="note">--</div><table><tbody id="retirementDriftRows"></tbody></table>
            </div>
            <div class="card">
              <div class="titleRow"><h2 class="title" data-zh="月度战略复核" data-en="Monthly Strategic Review">月度战略复核</h2>
                ${help('每日邮件只给简短状态；这个月度复核用于检查漂移、机会排名、确认门槛和缴款倾斜是否需要恢复基线。V1 已预留历史分位字段，但不会伪造不足的历史记录。','The daily email carries only a short status. This monthly review checks drift, opportunity ranking, confirmation thresholds, and whether a contribution tilt should return to baseline. V1 reserves historical-percentile fields without fabricating insufficient history.')}
              </div>
              <div id="retirementMonthly" class="note">--</div>
            </div>
          </div>
          <div class="card">
            <div class="titleRow"><h2 class="title" data-zh="数据边界与长期情境" data-en="Data Boundaries and Long-Term Context">数据边界与长期情境</h2>
              ${help('估值分目前是 config/401k_strategy.json 中可审计的标准化输入；广度是基金价格参与代理，不是假装成成分股广度。转入金额只作为处理中情境，不计入永久组合价值。','Valuation is an auditable normalized input in config/401k_strategy.json. Breadth is explicitly a fund-price participation proxy, not constituent breadth. The rollover amount is processing context only, not permanent portfolio value.')}
            </div>
            <div id="retirementBoundaries" class="note">--</div>
          </div>
        </div>`);
    }
    const mmf10 = $('mmf10StructureCard');
    if (mmf10 && !$('retirementDailyCard')) {
      mmf10.insertAdjacentHTML('afterend', `
        <div id="retirementDailyCard" class="card retirementDaily">
          <div class="titleRow"><div><div class="summaryKicker">401(k) DAILY STATUS</div><h2 class="title" data-zh="401(k) 长期组合摘要" data-en="401(k) Long-Term Portfolio Brief">401(k) 长期组合摘要</h2></div>
            ${help('这是每日极简状态，不重复 SOXL 的盘中分析。绝大多数交易日应显示“无需行动”；只有长期机会与确认共同变化时才升级提醒。','This is a compact daily status, not a repeat of SOXL intraday analysis. Most sessions should say “No action required”; alerts escalate only when long-term Opportunity and Confirmation change together.')}
          </div>
          <div id="retirementDailySummary" class="note">--</div>
          <button class="ghost compactBtn" onclick="showPage('retirement')" data-zh="打开 401(k) 专页" data-en="Open 401(k) Page">打开 401(k) 专页</button>
        </div>`);
    }
    const introGrid = document.querySelector('#introPage .introGrid');
    if (introGrid && !$('retirementIntroItem')) {
      introGrid.insertAdjacentHTML('beforeend', '<div id="retirementIntroItem" class="introItem"><h3 data-zh="401(k) 长期战略" data-en="401(k) Long-Term Strategy">401(k) 长期战略</h3><p class="note" data-zh="独立审查长期组合漂移、三类资产机会与未来新缴款倾斜；不使用盘中信号，也不自动交易。" data-en="Independently reviews portfolio drift, three-bucket opportunity, and future contribution tilts; it uses no intraday signals and performs no automatic trading.">独立审查长期组合漂移、三类资产机会与未来新缴款倾斜；不使用盘中信号，也不自动交易。</p></div>');
    }
  }

  function allocationName(key) {
    return ({SP500:label('标普500','S&P 500'), EXTENDED_MARKET:label('美国扩展市场','U.S. Extended Market'), INTERNATIONAL:label('国际股票','International Equity')})[key] || key;
  }

  function renderAssets(data) {
    const best = data.bestOpportunity?.key;
    $('retirementAssetGrid').innerHTML = (data.assets || []).map(asset => {
      if (!asset.available) return `<article class="retirementAsset ${asset.key === best ? 'best' : ''}"><h3>${esc(language() === 'en' ? asset.nameEN : asset.nameCN)}</h3><p class="note">${esc(language() === 'en' ? asset.reasonEN : asset.reasonCN)}</p></article>`;
      const factors = asset.scoreComponents || {};
      const factorText = Object.entries(factors).map(([key, item]) => `${({valuation:label('估值','Valuation'),drawdown:label('回撤','Drawdown'),macro:label('宏观','Macro'),relativeTrend:label('相对趋势','Relative trend'),breadth:label('广度代理','Breadth proxy'),systemicRisk:label('系统风险','Systemic risk')})[key] || key} ${num(item.score)} ${label(`（权重${item.weightPct}%）`,`(weight ${item.weightPct}%)`)}`).join(' · ');
      const why = language() === 'en' ? asset.whyEN : asset.whyCN;
      const risks = language() === 'en' ? asset.risksEN : asset.risksCN;
      return `<article class="retirementAsset ${asset.key === best ? 'best' : ''}">
        <div class="titleRow"><div><h3>${esc(language() === 'en' ? asset.nameEN : asset.nameCN)}</h3><div class="small">${esc(asset.fund)} · ${esc(asset.ticker)}</div></div><span class="pill">${esc(status(asset.status))}</span></div>
        <div class="retirementScores"><div class="retirementScore"><span>${esc(label('机会分','Opportunity'))}</span><b>${num(asset.opportunityScore)}</b></div><div class="retirementScore"><span>${esc(label('确认分','Confirmation'))}</span><b>${num(asset.confirmationScore)}</b></div></div>
        <p class="small">${esc(label('52周回撤','52-week drawdown'))} ${pct(asset.drawdown?.drawdown52WeekPct)} · ${esc(label('距200日均线','vs. 200DMA'))} ${pct(asset.drawdown?.distanceFrom200DmaPct)}</p>
        <div class="retirementFactors">${esc(factorText)}</div>
        <details><summary>${esc(label('为什么 / 风险 ▾','Why / Risks ▾'))}</summary><div class="note">${(why || []).map(x => `<p>${esc(x)}</p>`).join('')}${(risks || []).map(x => `<p>⚠ ${esc(x)}</p>`).join('')}</div></details>
      </article>`;
    }).join('');
  }

  function render401k(data) {
    report = data || report;
    ensureUi();
    if (!report || !report.version) {
      $('retirementDecision').textContent = label('等待长期数据。默认维持 60/25/15，不因缺失数据调整退休资产。','Awaiting long-horizon data. Keep 60/25/15 and do not change retirement assets on missing evidence.');
      $('retirementDailySummary').textContent = label('401(k)：等待长期数据；无需行动。','401(k): Awaiting long-horizon data; no action required.');
      return;
    }
    const best = report.bestOpportunity || {};
    $('retirementDecision').innerHTML = `<b>${esc(status(report.status))}</b><br>${esc(language() === 'en' ? report.dailySummaryEN : report.dailySummaryCN)}`;
    $('retirementAction').textContent = status(report.action);
    $('retirementRegime').textContent = status(report.marketRegime);
    $('retirementHoldings').textContent = status(report.existingHoldingsAction);
    $('retirementEmployeeContribution').textContent = `${num(report.employeeContributionPct)}%`;
    $('retirementDailySummary').innerHTML = `<p><b>${esc(status(report.action))}</b> · ${esc(language() === 'en' ? report.dailySummaryEN : report.dailySummaryCN)}</p><p class="small">${esc(label('只使用日、周、月数据；盘中信号已排除。','Daily, weekly, and monthly evidence only; intraday signals are excluded.'))}</p>`;
    const baseline = report.baselineAllocationPct || {}, current = report.currentAllocationPct || {}, recommended = report.recommendedContributionPct || {};
    $('retirementAllocationRows').innerHTML = ['SP500','EXTENDED_MARKET','INTERNATIONAL'].map(key => `<tr><td>${esc(allocationName(key))}</td><td>${pct(baseline[key])}</td><td>${current[key] == null ? esc(label('未录入','Not entered')) : pct(current[key])}</td><td class="recommended">${pct(recommended[key])}</td></tr>`).join('');
    const contributionLead = language() === 'en'
      ? `<p><b>Recommendation:</b> ${esc(status(report.action))}. ${report.contributionTiltRecommended ? esc(`Best opportunity: ${best.nameEN}. Temporarily tilt future contributions by ${num(report.contributionTiltPctPoints)} percentage points.`) : 'Keep baseline; no contribution change is required.'}</p><p class="small">Existing holdings remain HOLD; this is not an automatic order.</p>`
      : `<p><b>建议：</b>${esc(status(report.action))}。${report.contributionTiltRecommended ? esc(`最佳机会为${best.nameCN}，未来新缴款可临时倾斜 ${num(report.contributionTiltPctPoints)} 个百分点。`) : '维持基线；不需要更改未来缴款配置。'}</p><p class="small">现有持仓继续维持；这不是自动下单。</p>`;
    $('retirementContributionRead').innerHTML = contributionLead;
    renderAssets(report);
    const drift = report.portfolioDrift || {};
    $('retirementDriftRead').innerHTML = `<p><b>${esc(status(drift.status))}</b><br>${esc(language() === 'en' ? drift.action : ({'HOLD; ENTER CURRENT BALANCES BEFORE A DRIFT DECISION':'先录入当前持仓比例，再进行漂移判断；目前维持。','USE NEW CONTRIBUTIONS FIRST; DO NOT AUTO-SELL':'优先用新缴款修正；不自动卖出。','NO REBALANCE REQUIRED':'无需再平衡。'}[drift.action] || drift.action || '--'))}</p>`;
    $('retirementDriftRows').innerHTML = (drift.rows || []).map(row => `<tr><td>${esc(allocationName(row.asset))}</td><td>${pct(row.baselinePct)}</td><td>${row.currentPct == null ? esc(label('未录入','Not entered')) : pct(row.currentPct)}</td><td>${row.driftPctPoints == null ? '--' : `${Number(row.driftPctPoints) > 0 ? '+' : ''}${num(row.driftPctPoints)} pp`}</td></tr>`).join('');
    const monthly = report.monthlyReview || {};
    $('retirementMonthly').innerHTML = `<p><b>${esc(label('本月结论','Current review'))}：</b>${esc(status(monthly.recommendation))}</p><p>${esc(label('机会排名第一','Top opportunity'))}：${esc(allocationName(monthly.bestOpportunity))} · ${esc(label('机会','Opportunity'))} ${num(monthly.opportunityScore)} · ${esc(label('确认','Confirmation'))} ${num(monthly.confirmationScore)}</p><p>${esc(label('漂移状态','Drift status'))}：${esc(status(monthly.driftStatus))}</p><p class="small">${esc(label('历史机会分位：V1 架构已预留，样本不足时保持空值。','Historical opportunity percentile: architecture is ready; the value remains blank until sufficient history exists.'))}</p>`;
    const rollover = report.rolloverContext || {};
    const rolloverStatus = language() === 'en' ? (rollover.status || '--') : '处理中 / 到账日期未确认';
    const guardrailCN = {
      'NO AUTOMATIC TRADING':'不自动交易',
      'NO AUTOMATIC ALLOCATION CHANGES':'不自动改变资产配置',
      'NEW CONTRIBUTIONS BEFORE SELLING EXISTING HOLDINGS':'先调整新缴款，再考虑现有持仓',
      'DRAWDOWN ALONE IS NOT A BUY SIGNAL':'下跌本身不是买入信号',
      'MAX TEMPORARY DEVIATION ±15 PERCENTAGE POINTS':'临时倾斜最多 ±15 个百分点'
    };
    const guardrails = (report.guardrails || []).map(x => language() === 'en' ? x : (guardrailCN[x] || x));
    const trigger = language() === 'en' ? report.watchTrigger : `${best.nameCN}：机会分 ≥ 75 且确认分 ≥ 60`;
    $('retirementBoundaries').innerHTML = `<p><b>${esc(label('模型边界：','Model boundary:'))}</b>${esc(language() === 'en' ? report.separationRuleEN : report.separationRuleCN)}</p><p><b>${esc(label('数据频率：','Frequency:'))}</b>${esc(language() === 'en' ? 'DAILY / WEEKLY / MONTHLY · Intraday used: false' : '日线 / 周线 / 月线 · 不使用盘中数据')}</p><p><b>${esc(label('转入情境：','Rollover context:'))}</b>${esc(rolloverStatus)} · ${esc(rollover.source_plan || '--')} · ${rollover.estimated_incoming_amount == null ? '--' : `$${Number(rollover.estimated_incoming_amount).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})}`} · ${esc(label('不计作永久组合价值','not treated as permanent portfolio value'))}</p><p><b>${esc(label('触发线：','Watch trigger:'))}</b>${esc(trigger || '--')}</p><p class="small">${guardrails.map(x => `□ ${esc(x)}`).join('<br>')}</p>`;
    applyStaticLabels(language());
  }

  function applyStaticLabels(lang) {
    ensureUi();
    document.querySelectorAll('#retirementPage [data-zh][data-en],#retirementDailyCard [data-zh][data-en],#retirementIntroItem [data-zh][data-en]').forEach(node => {
      node.textContent = node.dataset[lang === 'en' ? 'en' : 'zh'];
    });
  }

  function setLanguage(lang) {
    applyStaticLabels(lang);
    if (report) render401k(report);
  }

  ensureUi();
  const originalShowPage = window.showPage;
  window.showPage = function (page) {
    originalShowPage(page);
    $('retirementPage')?.classList.toggle('hidden', page !== 'retirement');
    $('retirementNav')?.classList.toggle('active', page === 'retirement');
    $('retirementNav')?.classList.toggle('ghost', page !== 'retirement');
    if (page === 'retirement') render401k(lastReport?.strategic401k);
  };
  const originalRender = window.render;
  window.render = function (data) {
    originalRender(data);
    render401k(data?.strategic401k);
  };
  new MutationObserver(() => setLanguage(language())).observe(document.documentElement, {attributes:true, attributeFilter:['lang']});
  window.MMF401K = {ensureUi, render: render401k, setLanguage};
})();
