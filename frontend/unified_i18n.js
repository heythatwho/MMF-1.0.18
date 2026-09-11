(function () {
  'use strict';

  const PAGE_IDS = ['introPage', 'mmfPage', 'timeframePage', 'behaviorPage', 'enemyPage', 'positionPage', 'retirementPage'];
  const NAV_LABELS = {
    intro: ['介绍', 'Introduction'],
    mmf: ['MMF 战场分析', 'MMF Battlefield'],
    timeframe: ['多周期趋势', 'Multi-Timeframe Trend'],
    behavior: ['市场行为分析', 'Market Behavior'],
    enemy: ['敌谋预判', 'Enemy Intent'],
    position: ['仓位作战室', 'Position War Room'],
    retirement: ['401(k) 长期组合', '401(k) Portfolio']
  };

  const STATIC_TEXT = new Map([
    ['退出登录', 'Log out'],
    ['介绍', 'Introduction'],
    ['MMF 战场分析', 'MMF Battlefield'],
    ['多周期趋势', 'Multi-Timeframe Trend'],
    ['市场行为分析', 'Market Behavior'],
    ['敌谋预判', 'Enemy Intent'],
    ['仓位作战室', 'Position War Room'],
    ['MMF 是什么', 'What MMF Is'],
    ['Miao Market Framework 是一套市场解读、布局和仓位工程系统。它不试图预测明天一定涨跌，而是把价格、量能、宏观、情绪、板块、资金角色、交易纪律和账户承受力统一放进一个分析框架，帮助使用者判断现在该进攻、观察，还是继续持有现金。', 'Miao Market Framework is a market-intelligence, deployment, and position-engineering system. It does not claim that tomorrow must rise or fall. It combines price, volume, macro conditions, sentiment, sectors, capital roles, trading discipline, and account capacity to decide whether the account should attack, observe, or preserve cash.'],
    ['仓位工程学 Position Engineering', 'Position Engineering'],
    ['MMF 不把交易简化成“看涨所以买”。更重要的问题是：市场质量有多差、价格折扣有多深、风险是板块风险还是系统风险、账户还剩多少战略纵深。', 'MMF does not reduce trading to “bullish, therefore buy.” The more important questions are how weak market quality is, how deep the price discount is, whether risk is sector-specific or systemic, and how much strategic depth remains in the account.'],
    ['市场质量和价格质量必须分开。弱市场里，25%可以是普通赔率仓默认上限；但如果价格已经深度折扣、风险闸门仍通过、账户还有现金纵深，系统可以把仓位层级升级为 Deep Odds Position / 深度赔率仓。', 'Market quality and price quality must remain separate. In a weak market, 25% may be the default ceiling for a standard odds position. If discount is deep, the risk gate still passes, and the account retains cash depth, the system may upgrade the tier to a Deep Odds Position.'],
    ['新的仓位引擎不只输出一个数字，而是输出观察仓、普通赔率仓、深度赔率仓、趋势仓和风险闸门。深度赔率仓买的不是趋势反转，而是市场已经支付出来的折扣和反弹赔率；趋势仓必须等结构和资金重新修复后另算。', 'The position engine does not output one number. It separates observation, standard-odds, deep-odds, and trend positions behind a risk gate. Deep-odds positions buy paid-for discount and rebound asymmetry; trend positions require repaired structure and capital confirmation.'],
    ['支撑不是一个精确点，市场经常会刺穿支撑、扫止损、测试真实需求。MMF 更关心账户是否立于不败，而不是是否买到最低点。', 'Support is a zone, not an exact point. Markets often sweep stops and test real demand before deciding whether to repair. MMF cares more about account resilience than buying the precise low.'],
    ['孙子兵法市场哲学 Sun Tzu Market Philosophy', 'Sun Tzu Market Philosophy'],
    ['先为不可胜，以待敌之可胜。', 'First make yourself invincible; then wait for the market to reveal an opportunity.'],
    ['大多数交易系统都在回答“明天市场会涨还是跌”。MMF 认为这是一个错误的问题。市场是复杂适应系统，没有人能够长期准确预测。', 'Most trading systems ask whether the market will rise or fall tomorrow. MMF treats that as the wrong question. Markets are complex adaptive systems, and no one can forecast them accurately over time.'],
    ['MMF 研究的是：在不知道市场未来会怎么走的情况下，如何长期活下来，以及如何在市场犯错的时候获利。', 'MMF studies how to remain viable without knowing the future and how to profit when the market creates a mispricing.'],
    ['第一原则：生存', 'First Principle: Survival'],
    ['先把单笔损失和总仓位控制在账户可承受范围，再等待机会。', 'Control single-trade loss and total exposure inside account tolerance before waiting for opportunity.'],
    ['不问市场一定怎么走，只问如果这样走，我怎么办。', 'Do not ask what the market must do. Decide what the account will do if each path occurs.'],
    ['不是赚最多，而是赚属于自己计划的那一段。', 'The objective is not every dollar; it is the segment that belongs to the plan.'],
    ['MMF 公理：交易的目标不是保证每笔不亏，而是避免任何单一路径让账户失去下一局。', 'MMF axiom: the goal is not to guarantee that every trade wins, but to prevent any single path from taking away the account\'s next campaign.'],
    ['MMF 公理：', 'MMF Axiom:'],
    ['最终原则：不可胜在己，可胜在敌。不败由我决定，赚钱交给市场决定。', 'Final principle: survival belongs to the account; opportunity belongs to the market. Control defeat and let the market decide when profit is available.'],
    ['最终原则：', 'Final Principle:'],
    ['交易纪律：见好就收不是胆小，而是系统纪律。只赚计划内的那一段，不为计划外上涨追价。', 'Trading discipline: taking planned profit is not timidity. Capture the planned segment and do not chase an unplanned extension.'],
    ['交易纪律：', 'Trading Discipline:'],
    ['适合谁使用', 'Who MMF Is For'],
    ['适合已经理解技术形态、量价、仓位管理、风险预算、ETF结构和概率思维的进阶交易者或投资者。', 'MMF is designed for advanced traders and investors who already understand technical structure, price/volume, position management, risk budgets, ETF mechanics, and probabilistic thinking.'],
    ['它不是喊单系统，而是交易前的作战参谋：整理证据、情景、赔率、失效条件和账户影响。', 'It is not a signal service. It is a pre-trade staff officer that organizes evidence, scenarios, odds, invalidation, and account impact.'],
    ['核心使用方式', 'Core Workflow'],
    ['先看总览与 MMF-10 判断市场状态，再看每日战情确认事实与行动；需要追溯证据时展开辅助证据库，判断趋势时进入多周期页，最后在仓位作战室落实账户计划。', 'Start with the Executive Summary and MMF-10, confirm facts and actions in the daily battlefield, expand the evidence library only when needed, use the multi-timeframe page for trend, and implement the account plan in the Position War Room.'],
    ['敌谋预判负责挑战原假设；Market Vacation 表示证据不足时保留现金和下一次出手机会。', 'Enemy Intent challenges the working thesis. Market Vacation preserves cash and the next opportunity when evidence is insufficient.'],
    ['页面模块说明', 'Page Module Guide'],
    ['总览', 'Executive Summary'],
    ['先看战场分数、市场温度、入场质量、赔率与当前行动。', 'Read battlefield score, market temperature, entry quality, odds, and the current action first.'],
    ['MMF-10 结构层', 'MMF-10 Structure Layer'],
    ['判断资金去向、市场结构、半导体领导力、系统风险和四种情景。', 'Evaluate capital destination, market structure, semiconductor leadership, systemic risk, and four explicit scenarios.'],
    ['把价格事实、盘面含义、资金原因、建议行动和作废条件合并在同一处。', 'Combines price facts, market meaning, capital drivers, recommended action, and invalidation in one place.'],
    ['月线定环境、周线定结构、日线定战场、小时与五分钟定执行。', 'Monthly defines the environment, weekly the structure, daily the battlefield, and hourly/five-minute evidence the execution.'],
    ['识别共识、参与者行为、资金去向与可能的流动性测试。', 'Identifies consensus, participant behavior, capital destination, and possible liquidity tests.'],
    ['主动寻找替代解释、系统风险与会推翻当前计划的证据。', 'Actively searches for alternative explanations, systemic risk, and evidence that would overturn the plan.'],
    ['把市场许可转成真实仓位、现金缓冲、分批计划与账户影响。', 'Converts market permission into real exposure, cash buffer, staged orders, and account impact.'],
    ['按需查看情绪、Fibonacci、板块、宏观、资金角色、期权、新闻与十大维度。', 'Inspect sentiment, Fibonacci, sectors, macro, capital roles, options, news, and MMF-10 only when deeper evidence is needed.'],
    ['Live 看最新，Snapshot 看缓存，Replay 回看指定日期。', 'Live reads the latest data, Snapshot uses cached data, and Replay reconstructs a specified date.'],
    ['第一原则：不败', 'First Principle: Survival'],
    ['形胜之法：情景而非预测', 'Scenario Discipline, Not Prediction'],
    ['投资哲学：只赚属于我的那一段', 'Investment Philosophy: Own Your Slice'],
    ['负相关市场哲学', 'Sequential and Concurrent Market Philosophy'],
    ['什么时候适合用', 'When MMF Is Useful'],
    ['什么时候尤其好用', 'When MMF Is Especially Valuable'],
    ['MMF 的使用方法', 'How to Use MMF'],
    ['功能模块说明', 'Module Guide'],
    ['运行 MMF', 'Run MMF'],
    ['邮件预览 Email Preview', 'Email Preview'],
    ['立即发送邮件', 'Send Email Now'],
    ['订阅/发送 Subscription', 'Subscription / Send'],
    ['MMF 第一原则', 'MMF FIRST PRINCIPLE'],
    ['交易不保证每笔不亏；目标是避免任何单一路径让账户失去下一局。', 'No trade is guaranteed to avoid a loss. The objective is to prevent any single path from taking away the account\'s next campaign.'],
    ['交易的目标不是预测市场。交易的目标是：无论市场怎么走，我都不会输。', 'The goal is not to predict the market. It is to keep the account viable across every plausible path.'],
    ['不可胜在己', 'Survival Is Controllable'],
    ['不败由我决定。', 'Risk boundaries belong to the account.'],
    ['风险边界由账户设计。', 'Risk boundaries are designed at the account level.'],
    ['可胜在敌', 'Opportunity Belongs to the Market'],
    ['赚钱交给市场决定。', 'The market decides when profit is available.'],
    ['盈利机会由市场提供。', 'The market decides when profit is available.'],
    ['情景推演', 'Scenario Discipline'],
    ['市场可以有无数种走法，但账户必须永远有下一局。', 'The market may take many paths; the account must retain the next campaign.'],
    ['战场分数 MMF Score', 'MMF Battlefield Score'],
    ['市场温度 Temperature', 'Market Temperature'],
    ['入场质量 Entry Quality', 'Entry Quality'],
    ['点击展开 4 项评分与解读 ▾', 'Expand four component scores and interpretation ▾'],
    ['趋势确认', 'Trend Confirmation'],
    ['入场时机', 'Entry Timing'],
    ['价格折扣', 'Price Discount'],
    ['部署质量', 'Deployment Quality'],
    ['赔率质量', 'Odds Quality'],
    ['风险环境', 'Risk Regime'],
    ['赔率 Reward / Risk', 'Reward / Risk'],
    ['战术赔率 · 恢复潜力赔率', 'Tactical odds · Recovery-potential odds'],
    ['总览 Executive Summary', 'Executive Summary'],
    ['指标说明', 'Metric Guide'],
    ['打开完整页面', 'Open Full Page'],
    ['结构、相对强弱与资金去向', 'Structure, Relative Strength, and Capital Flow'],
    ['市场状态机', 'Market State Machine'],
    ['市场结构', 'Market Structure'],
    ['半导体领导力', 'Semiconductor Leadership'],
    ['系统风险', 'Systemic Risk'],
    ['问 MMF · 本地 Ollama', 'Ask MMF · Local Ollama'],
    ['提问', 'Ask'],
    ['盘中执行许可', 'Intraday Execution Permission'],
    ['建仓评级', 'Entry Rating'],
    ['建议仓位', 'Suggested Position'],
    ['当前价格', 'Current Price'],
    ['当日变化', 'Daily Change'],
    ['每日战情与行动复盘', 'Daily Battlefield and Action Debrief'],
    ['事实 + 4 项复盘', 'Facts + Four-part Debrief'],
    ['同一处先看价格事实，再看盘面含义、建议行动和失效条件。', 'Read the price facts first, then market meaning, recommended action, and invalidation in one sequence.'],
    ['上涨K线', 'Up candle'],
    ['下跌K线', 'Down candle'],
    ['ETF权重影响', 'ETF Weight Impact'],
    ['战争五事 · 道天地将法', 'Five Strategic Factors'],
    ['仓位质量与账户影响', 'Position Quality and Account Impact'],
    ['交易质量 Trade Quality', 'Trade Quality'],
    ['市场质量 Market Quality', 'Market Quality'],
    ['最高战术仓位', 'Maximum Tactical Position'],
    ['现金缓冲', 'Cash Buffer'],
    ['主动权管理', 'Initiative Management'],
    ['主动权指数', 'Initiative Index'],
    ['现金选择权', 'Cash Optionality'],
    ['上涨参与权', 'Upside Participation'],
    ['执行可行性', 'Execution Feasibility'],
    ['实战迭代引擎', 'Field Evolution Engine'],
    ['市场阶段', 'Market Phase'],
    ['流动性事件', 'Liquidity Event'],
    ['情绪部署级别', 'Sentiment Deployment Class'],
    ['退出质量', 'Exit Quality'],
    ['五分钟资金博弈', 'Five-minute Capital Auction'],
    ['5分钟K线', 'Five-minute Candlesticks'],
    ['量', 'Volume'],
    ['辅助证据库', 'Supporting Evidence Library'],
    ['十大维度 MMF-10 Dimensions', 'MMF-10 Dimensions'],
    ['恐惧与贪婪归因 Fear & Greed Attribution', 'Fear & Greed Attribution'],
    ['Fibonacci 共振区', 'Fibonacci Confluence Zones'],
    ['板块轮动热力图', 'Sector Rotation Heatmap'],
    ['宏观环境 Macro', 'Macro Environment'],
    ['聪明钱 vs 散户 / 机构', 'Smart Money vs Retail / Institutions'],
    ['期权定位 Options Positioning', 'Options Positioning'],
    ['今日消息 News Impact', 'News Impact'],
    ['邮件每日摘要', 'Daily Email Brief'],
    ['中文邮件预览', 'English Email Preview'],
    ['请点击“邮件预览”。', 'Select “Email Preview”.'],
    ['动态区间', 'Dynamic Range'],
    ['上沿突破', 'Upper Breakout'],
    ['下沿失守', 'Lower Breakdown'],
    ['参考现价', 'Reference Price'],
    ['资金行为', 'Capital Behavior'],
    ['当前共识', 'Current Consensus'],
    ['参与者映射', 'Participant Map'],
    ['反身性路径', 'Reflexivity Paths'],
    ['账户应对', 'Account Response'],
    ['挑战权重', 'Challenge Weight'],
    ['当前假设：', 'Current assumption:'],
    ['庙算挑战：', 'Adversarial challenge:'],
    ['另一种解释：', 'Alternative explanation:'],
    ['什么会改变判断：', 'What changes the plan:'],
    ['当前回答：', 'Current answer:'],
    ['当前仓位', 'Current Exposure'],
    ['模型上限', 'Model Ceiling'],
    ['当前可执行新增', 'Currently Executable Additions'],
    ['账户亏损容忍', 'Account Loss Tolerance'],
    ['下一步建议', 'Next Action'],
    ['组合策略', 'Portfolio Strategy'],
    ['仓位输入与分批订单', 'Position Inputs and Staged Orders'],
    ['账户影响情景', 'Account Impact Scenarios'],
    ['执行纪律清单', 'Execution Discipline Checklist'],
    ['月线', 'Monthly'],
    ['周线', 'Weekly'],
    ['日线', 'Daily'],
    ['盘中 / 5分钟', 'Intraday / 5-minute'],
    ['多周期合成判断', 'Multi-Timeframe Synthesis'],
    ['当前模式', 'Current Mode'],
    ['类型', 'Type'],
    ['价格', 'Price'],
    ['依据', 'Evidence'],
    ['强度', 'Strength'],
    ['动作', 'Action'],
    ['作废', 'Invalidation'],
    ['区域', 'Zone'],
    ['参考价位', 'Reference Level'],
    ['概率', 'Probability'],
    ['走向', 'Path'],
    ['成立条件', 'Activation'],
    ['作废条件', 'Invalidation'],
    ['盯什么', 'What to Watch'],
    ['应对', 'Response'],
    ['数值', 'Value'],
    ['指标', 'Metric'],
    ['时间', 'Time'],
    ['阶段', 'Phase'],
    ['变化', 'Change'],
    ['成交量', 'Volume'],
    ['展开原始行情口径 ▾', 'Expand raw market-data definitions ▾'],
    ['展开全部权重明细 ▾', 'Expand all weight details ▾'],
    ['展开五事诊断与动作 ▾', 'Expand five-factor diagnosis and actions ▾'],
    ['展开账户影响、上下行情景与执行计划 ▾', 'Expand account impact, upside/downside scenarios, and execution plan ▾'],
    ['展开信息区域、结构模型与执行模式 ▾', 'Expand information zones, structure models, and execution mode ▾'],
    ['展开实战证据、资金效率与战役复盘 ▾', 'Expand field evidence, capital efficiency, and campaign review ▾'],
    ['情绪、Fibonacci、板块、宏观、资金、期权与消息 · 按需展开 ▾', 'Sentiment, Fibonacci, sectors, macro, flow, options, and news · expand as needed ▾'],
    ['防漏评分表 · 点击展开证据 ▾', 'Anti-omission scorecard · expand supporting evidence ▾']
  ]);

  const HELP_EN = {
    'Daily Battlefield and Action Debrief': [
      'This combines market facts and the daily debrief in one reading path: verify price, range, and volume first; then read interpretation, recommended action, and invalidation.',
      'The facts layer does not issue a verdict. The action layer must state the best current response, its trigger, and its stop condition.'
    ],
    'Market Behavior': [
      'This section identifies crowded beliefs, who may be forced to act, and the liquidity tests that can exploit consensus. It does not predict one price path.',
      'Read what the market believes first, then who may need to act. The full participant map and reflexivity paths live on the Market Behavior page.'
    ],
    'Executive Summary': [
      'This is the command brief for the full report. Read battlefield score, temperature, entry quality, and reward/risk together before choosing attack, observation, or rest.',
      'Battlefield score evaluates the environment; temperature reads crowd emotion; entry quality evaluates current execution conditions; reward/risk is upside space divided by downside risk, not win probability.'
    ],
    'Intraday Execution Permission': [
      'This compresses MMF-10 into a current-session execution permission using price, daily change, entry rating, and maximum suggested size.',
      'It answers whether a probe is allowed now and how small it must remain. It is not a long-term conclusion and never replaces account-level position control.'
    ],
    'Position Quality and Account Impact': [
      'Market quality and trade quality are separate. Market quality describes the environment; trade quality asks whether the account can survive if this position is wrong.',
      'Maximum tactical size and cash buffer are risk boundaries, not instructions to fill the allowance. Account impact is the instrument move multiplied by position size.'
    ],
    'ETF Weight Impact': [
      'This decomposes which ETF constituents pulled the instrument up or down. Impact is an approximate percentage-point contribution: weight multiplied by the constituent\'s one-day move.',
      'A move driven by one weight has different quality from broad confirmation. Read the largest drag and support first.'
    ],
    'Five Strategic Factors': [
      'Doctrine, Weather, Terrain, Commanders, and Discipline force a structured review of principles, macro conditions, price terrain, capital leadership, and execution rules.',
      'The purpose is to prevent a decision based on one candle or one indicator.'
    ],
    'Five-minute Capital Auction': [
      'This is the intraday execution view: five-minute acceptance, VWAP, EMA20, and volume rhythm.',
      'It helps select timing but cannot independently overturn daily structure, the risk regime, or account limits.'
    ],
    'Fear & Greed Attribution': [
      'This explains what contributes to the sentiment score and why an external temperature may differ from MMF\'s internal battlefield reading.',
      'Extreme sentiment is context, not an automatic buy or sell instruction.'
    ],
    'Fibonacci Confluence Zones': [
      'These are terrain and confluence zones across several lookbacks, not exact forecasts.',
      'Below price, watch for real absorption; above price, watch for supply. A level becomes actionable only when capital behavior confirms it.'
    ],
    'Sector Rotation Heatmap': [
      'Darker green indicates relative strength and darker red relative weakness. Read group averages first, then check whether leadership is broad or concentrated.',
      'Synchronized weakness across semiconductors, growth, and defensive groups is more systemic than an isolated semiconductor decline.'
    ],
    'Macro Environment': [
      'Macro and sector conditions describe tailwind, headwind, or mixed weather. They modify position size, confirmation requirements, and tolerance; they are not standalone entries.'
    ],
    'Smart Money vs Retail / Institutions': [
      'This separates institutional, retail, fund, market-maker, leveraged, and ETF-flow roles. The task is not to declare who is always right, but to identify who is setting the current tempo.'
    ],
    'Options Positioning': [
      'Put/Call Volume measures current contract flow; Put/Call OI measures outstanding positioning; Average IV prices expected volatility; Net Gamma Proxy estimates whether hedging may amplify or dampen moves.',
      'These are professional context variables, not directional predictions. Read expiry and source first, then positioning crowding, gamma sign, spot levels, and cash-market volume together.'
    ],
    'News Impact': [
      'Separate factual news, emotional reaction, and information that genuinely changes earnings, policy, liquidity, or the risk regime.',
      'A headline enters the battlefield only when price, volume, or capital behavior accepts it.'
    ],
    'MMF-10 Dimensions': [
      'This anti-omission checklist reviews technicals, sentiment, flow, fundamentals, sectors, macro, smart money, retail, options, and news.',
      'One strong dimension does not authorize attack. Plan quality rises when several independent dimensions confirm.'
    ]
  };

  const METRIC_HELP_EN = {
    'MMF Battlefield Score': ['A 0–100 composite of trend, price location, volume, sentiment, macro, sectors, capital roles, options, and news. It is not a price forecast.', 'Higher scores permit more active posture; middle and low scores demand stronger confirmation, smaller size, or continued waiting.'],
    'Market Temperature': ['A sentiment and crowding gauge anchored in Fear & Greed and interpreted through MMF battlefield conditions.', 'Low is fearful, high is greedy, and neutral is not extreme. Temperature is context, not an order.'],
    'Trend Confirmation': ['Measures whether trend, sector leadership, and price/volume behavior have actually repaired. A cheap price is not trend confirmation.'],
    'Entry Timing': ['Answers whether today offers a technically comfortable execution point. A low score can coexist with attractive long-term discount.'],
    'Price Discount': ['Measures the current discount from the 252-day high. A deep discount does not guarantee low risk and must be repriced if fundamentals or the risk regime change.'],
    'Deployment Quality': ['Combines discount, odds, risk gate, and trend confirmation to judge whether capital deserves deployment. High deployment with weak timing usually calls for staged odds tranches, not a full entry.'],
    'Entry Quality': ['Measures whether the current trade has enough confirmation, definable risk, and a clear invalidation path. Low quality does not mean price cannot rise; it means execution risk is harder to control.'],
    'Reward / Risk': ['Potential upside divided by downside risk. It is neither a guaranteed return nor win probability.', 'Tactical odds use the first executable objective; recovery odds describe a broader rebound path. Execution should use tactical odds.'],
    'Suggested Position': ['A maximum current-session allowance derived from MMF-10, not a command to deploy. A 0–5% range means confirmation may still justify doing nothing.']
  };

  const originalText = new WeakMap();
  let baseRender = null;
  let basePositionRender = null;
  let baseShowPage = null;

  function byId(id) { return document.getElementById(id); }
  function setText(id, value) {
    const node = byId(id);
    if (node && value !== undefined && value !== null) node.textContent = String(value);
  }
  function setHtml(id, value) {
    const node = byId(id);
    if (node && value !== undefined && value !== null) node.innerHTML = String(value);
  }
  function esc(value) {
    return String(value ?? '--').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
  function num(value, digits = 2) {
    const n = Number(value);
    return Number.isFinite(n) ? n.toFixed(digits).replace(/\.00$/, '') : '--';
  }
  function signed(value, suffix = '%') {
    const n = Number(value);
    return Number.isFinite(n) ? `${n > 0 ? '+' : ''}${num(n)}${suffix}` : '--';
  }
  function stars(value) { return value?.stars || value || '--'; }
  function englishEnum(value) {
    return String(value ?? '--')
      .replace(/\s*\/\s*[^/]*[\u3400-\u9fff][^/]*/g, '')
      .replace('↑ 修复/偏强', 'Recovering / Bullish')
      .replace('→ 震荡/未确认', 'Sideways / Unconfirmed')
      .replace('↓ 走弱/偏空', 'Weakening / Bearish')
      .replace('OBSERVATION', 'Observation')
      .replace('Market Vacation', 'Market Vacation');
  }

  function roots() {
    return [...PAGE_IDS.map(byId), byId('subscriptionModal'), byId('fibModal')].filter(Boolean);
  }
  function restoreText(root) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      if (originalText.has(node)) node.nodeValue = originalText.get(node);
    }
  }
  function translateText(root) {
    root.querySelectorAll('[data-zh][data-en]').forEach(node => {
      if (!originalText.has(node.firstChild) && node.childNodes.length === 1 && node.firstChild?.nodeType === 3) {
        originalText.set(node.firstChild, node.firstChild.nodeValue);
      }
      node.textContent = node.dataset.en;
    });
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      const raw = node.nodeValue || '';
      const trimmed = raw.trim();
      const translated = STATIC_TEXT.get(trimmed);
      if (!translated) continue;
      if (!originalText.has(node)) originalText.set(node, raw);
      node.nodeValue = raw.replace(trimmed, translated);
    }
  }

  function translateStaticEnglish() {
    roots().forEach(translateText);
    document.querySelectorAll('[data-zh][data-en]').forEach(node => node.textContent = node.dataset.en);
  }

  function translateHelpNotes() {
    const page = byId('mmfPage');
    if (!page) return;
    page.querySelectorAll('.sectionHelp[data-mmf-help="true"]').forEach(help => {
      const row = help.closest('.titleRow');
      const title = row?.querySelector('h2.title')?.textContent.trim();
      const paragraphs = HELP_EN[title];
      const note = help.querySelector(':scope > .note');
      if (note && paragraphs) note.innerHTML = paragraphs.map(p => `<p>${p}</p>`).join('');
    });
    page.querySelectorAll('.sectionHelp[data-mmf-metric-help="true"]').forEach(help => {
      const label = help.closest('.titleRow')?.querySelector('.label')?.textContent.trim();
      const paragraphs = METRIC_HELP_EN[label];
      const note = help.querySelector(':scope > .note');
      if (note && paragraphs) note.innerHTML = paragraphs.map(p => `<p>${p}</p>`).join('');
    });
  }

  function restoreChinese() {
    roots().forEach(restoreText);
    document.querySelectorAll('[data-zh][data-en]').forEach(node => node.textContent = node.dataset.zh);
    const page = byId('mmfPage');
    page?.querySelectorAll('.sectionHelp[data-mmf-help="true"]').forEach(help => {
      const title = help.closest('.titleRow')?.querySelector('h2.title')?.textContent.trim();
      const paragraphs = typeof mmfHelpNotes !== 'undefined' ? mmfHelpNotes[title] : null;
      const note = help.querySelector(':scope > .note');
      if (note && paragraphs) note.innerHTML = paragraphs.map(p => `<p>${p}</p>`).join('');
    });
    page?.querySelectorAll('.sectionHelp[data-mmf-metric-help="true"]').forEach(help => {
      const label = help.closest('.titleRow')?.querySelector('.label')?.textContent.trim();
      const paragraphs = typeof mmfMetricHelpNotes !== 'undefined' ? mmfMetricHelpNotes[label] : null;
      const note = help.querySelector(':scope > .note');
      if (note && paragraphs) note.innerHTML = paragraphs.map(p => `<p>${p}</p>`).join('');
    });
    const ask = byId('askQuestion');
    if (ask) ask.placeholder = '例如：为什么 RSI 超卖但仓位还是低？';
  }

  function englishExecutive(j) {
    const ex = j.executiveSummary || {};
    const q = j.dailyBattlefield?.quote || {};
    const fg = j.fearGreed || {};
    const pe = j.positionEngineering || {};
    const gate = pe.riskRegimeGate || {};
    const heat = j.sectorHeatmap || {};
    const vacation = ex.marketVacation === 'YES';
    setText('headline', vacation
      ? 'Confirmation is still incomplete. Preserve cash optionality and wait for a cleaner risk/reward signal.'
      : 'Tactical participation is permitted, but additions still require price, volume, and sector confirmation.');
    const bullets = [
      `Command posture: ${englishEnum(ex.marketStatus)} · MMF ${num(ex.mmfScore)}/100.`,
      `${esc(j.meta?.ticker || 'SOXL')} last/close ${num(q.close ?? q.last)} · previous-close change ${signed(q.prevCloseChangePct ?? q.changePct)}.`,
      `Fear & Greed ${num(fg.score, 1)} / ${esc(fg.label || '--')}.`,
      `Sector rotation: ${esc(heat.mode || '--')}. Read breadth before upgrading an odds position into a trend position.`
    ];
    setHtml('bullets', bullets.map(x => `<li>${x}</li>`).join(''));
    setText('strategy', `Recommended action: ${gate.status === 'PASS' ? 'manage the existing position and add only after the defined confirmation gates are met' : 'freeze additions and preserve cash until the risk gate reopens'}. Current exposure is ${num(j.accountState?.currentPositionPct ?? pe.currentPositionPct, 1)}%; the model ceiling is ${num(pe.maxTacticalPositionPct, 1)}%.`);
    setText('score', num(ex.mmfScore));
    setText('temp', num(ex.marketTemperature));
    setText('entry', stars(ex.entryTiming || ex.entryQuality));
    setText('trendConfirmation', stars(ex.trendConfirmation));
    setText('entryTimingDetail', stars(ex.entryTiming));
    setText('priceDiscountQuality', stars(ex.priceDiscountQuality));
    setText('deploymentQuality', stars(ex.deploymentQuality));
    setText('rr', `${num(ex.executableRewardRisk ?? ex.rewardRisk)} Tactical · ${num(ex.recoveryRewardRisk)} Recovery`);
    setText('rrLegend', 'Tactical odds govern execution; recovery odds describe broader rebound potential. Both are recalculated from live levels.');
    setText('behaviorCardSummary', `Price ${num(q.close ?? q.last)}. Capital posture is ${englishEnum(j.strategicBehaviorMap?.capitalBehavior?.postureCN)}. Treat volume as evidence only when the current session has reliable volume.`);
  }

  function englishDaily(j) {
    const q = j.dailyBattlefield?.quote || {};
    const ti = j.dailyBattlefield?.technicalIndicators || {};
    const replay = j.dailyReplay || {};
    const pe = j.positionEngineering || {};
    const heat = j.sectorHeatmap || {};
    const weight = j.etfWeights || {};
    const volume = j.intradayDecision?.volumeStructure || {};
    const last = q.close ?? q.last;
    const exposure = Number(j.accountState?.currentPositionPct ?? pe.currentPositionPct ?? 0);
    const room = Math.max(0, Number(pe.maxTacticalPositionPct || 0) - exposure);
    setText('dailyTitle', `${esc(j.meta?.ticker || 'SOXL')} Daily Battlefield`);
    setText('dailySummary', `${q.session === 'extended' ? 'Extended-hours snapshot' : 'Regular-session report'}: last/close ${num(last)}, previous-close change ${signed(q.prevCloseChangePct ?? q.changePct)}, range ${num(q.low)}–${num(q.high)}. ${volume.available === false ? 'Current-session volume is incomplete and cannot confirm accumulation or distribution.' : `Volume ${esc(q.volume || '--')} must be read against its recent average.`}`);
    const blocks = [
      ['Market Meaning', `The report remains in an observation or tactical phase. One session does not confirm a trend reversal. Price is ${num(last)} versus EMA20 ${num(ti.ema20)} and RSI14 ${num(ti.rsi14)}.`],
      ['Capital and Cause', `Capital behavior is ${englishEnum(j.strategicBehaviorMap?.capitalBehavior?.postureCN)}. Sector rotation is ${esc(heat.mode || '--')}; check whether the largest weights and breadth confirm the next move.`],
      ['Recommended Action', exposure > 0 ? `Manage the existing ${num(exposure, 1)}% exposure. Do not use an empty-account entry rule. The remaining theoretical room is ${num(room, 1)}%, and it becomes executable only after confirmation.` : `A small observation tranche may be considered only after the defined activation level, volume, and semiconductor breadth confirm together.`],
      ['Next-session Confirmation / Invalidation', `Confirm acceptance above the nearest activation area, defense of the current low/anchor, reliable volume, and semiconductor-leader participation. An accepted breakdown freezes additions and triggers a new MMF review.`]
    ];
    setHtml('replayBlocks', blocks.map((x, i) => `<div class="replayStep"><h3><span class="stepNo">${String(i + 1).padStart(2, '0')}</span>${x[0]}</h3><p>${x[1]}</p></div>`).join(''));
    const drags = weight.drags || weight.topDrags || [];
    const supports = weight.supports || weight.topSupports || [];
    const drag = drags[0] || weight.mainDrag || {};
    const support = supports[0] || weight.mainSupport || {};
    setText('etfSummary', `The largest ETF-weight influence explains who drove the move; it is not an isolated signal. Main drag: ${esc(drag.ticker || weight.topDrag?.ticker || '--')}. Main support: ${esc(support.ticker || weight.topSupport?.ticker || '--')}.`);
    const wd = j.warriorDoctrine || {};
    setText('warriorSummary', `${num(wd.score, 2)}/10. The five factors are not yet fully aligned; cash remains future campaign capacity.`);
    const warriorCards = [...(byId('warriorDoctrine')?.children || [])];
    (wd.items || []).forEach((item, i) => {
      const card = warriorCards[i];
      if (!card) return;
      const cn = card.querySelector('.dimCN');
      if (cn) cn.textContent = '';
      const h3 = card.querySelector('h3');
      if (h3) {
        const pill = h3.querySelector('.pill');
        h3.childNodes.forEach(node => { if (node.nodeType === 3) node.nodeValue = ''; });
        h3.insertBefore(document.createTextNode(`${item.nameEN} `), pill || null);
      }
      const sections = card.querySelectorAll('.sectionText');
      if (sections[0]) { sections[0].querySelector('b').textContent = 'Diagnosis'; sections[0].querySelector('span').textContent = 'Read principle, market weather, price terrain, capital leadership, and discipline together. The score is context, not a standalone order.'; }
      if (sections[1]) { sections[1].querySelector('b').textContent = 'Action'; sections[1].querySelector('span').textContent = 'Act only when the relevant evidence and account-risk conditions confirm together.'; }
      const summary = card.querySelector('details summary');
      if (summary) summary.textContent = 'View evidence';
      const note = card.querySelector('details .note');
      if (note) note.textContent = String(item.evidenceCN || '--').replaceAll('；', ' · ').replaceAll('。', '.');
    });
  }

  function englishMmf10(j) {
    const m = j.mmf10DailyOutput || {};
    const state = j.marketVacationStateMachine || {};
    const structure = j.adaptiveMarketStructure || {};
    const leadership = j.semiconductorLeadership || {};
    const systemic = j.systemicRiskFilter || {};
    const rotation = j.capitalRotation || {};
    const relative = j.relativeStrengthMatrix || {};
    const auction = j.intradayAuctionStructure || {};
    const catalyst = j.catalystRegime || {};
    const earnings = j.earningsCalendar || {};
    const macro = j.macroTransmission || {};
    const change = j.structuralChange || {};
    const scenarioModel = j.scenarioModel || {};
    const scenarios = scenarioModel.scenarios || j.scenarioEngine || [];
    const micro = structure.micro || {};
    const daily = structure.daily || {};
    const higher = structure.higherOrder || {};
    const groupEN = value => ({'电动车 / 电池':'EV / Batteries','可选消费':'Consumer Cyclicals','工业 / 原材料':'Industrials / Materials','通信服务':'Communication Services','金融':'Financials','半导体链':'Semiconductors','宏观 / 避险':'Macro / Safe Havens'}[value] || value || '--');
    const destinations = [...(rotation.destinations || []), ...(rotation.safeHavens || [])].map(x => groupEN(x.name)).join(', ') || 'No clear destination confirmed';
    const systemicRead = systemic.status === 'HIGH'
      ? 'Multiple markets now confirm a systemic-risk cluster.'
      : systemic.status === 'ELEVATED'
        ? 'Several cross-market warnings are active, but the full systemic cluster is not yet complete.'
        : 'Cross-market confirmation is insufficient; isolated SOXL/SOXX weakness remains sector risk, rotation, or deleveraging unless broader evidence changes.';
    const structuralRead = change.materialChange
      ? 'New structural information is present today; reweight the scenarios, but do not turn one change into an automatic order.'
      : 'No material structural change today. Persistent weakness is not reported again as new information.';
    const auctionRead = {
      'OPENING LIQUIDATION → STABILIZATION': 'The opening liquidation was followed by stabilization without persistent new lows. This is absorption evidence, not confirmed accumulation.',
      'CONTINUOUS SELLING': 'Selling persisted through the session and price stayed near the lows; absorption language is not justified.',
      'OPENING DRIVE FAILURE': 'The opening advance failed and became liquidity for later selling.',
      'BALANCED / MIXED AUCTION': 'The session remained a mixed auction without one-sided control.',
      'UNCONFIRMED / NO RELIABLE INTRADAY AUCTION': 'Reliable five-minute auction data is unavailable; the daily bar cannot reconstruct where the volume occurred.'
    }[auction.classification] || 'Intraday auction evidence is not yet conclusive.';
    setText('mmf10State', englishEnum(rotation.classification || '--'));
    setHtml('mmf10Brief', `<p><b>Capital regime:</b> ${esc(rotation.classification || '--')}. Destination: ${esc(destinations)}.</p><p><b>Structural change:</b> ${esc(structuralRead)}</p><p><b>State machine:</b> ${esc(state.state || '--')}. Price alone triggers review, not action.</p><p><b>Four scenarios:</b> ${scenarios.map(x => `${esc(x.name)} ${num(x.probability, 0)}%`).join(' · ')}. These are evidence weights, not predictions.</p>`);
    setText('mmf10Vacation', englishEnum(state.state || state.label || j.marketVacation));
    setText('mmf10Regime', englishEnum(structure.regime || structure.label || '--'));
    setText('mmf10Leadership', englishEnum(leadership.status || leadership.state || leadership.label || '--'));
    setText('mmf10Systemic', `${englishEnum(systemic.status || systemic.level || systemic.state || '--')} · ${englishEnum(systemic.direction || '--')}`);
    setHtml('mmf10Relative', '<tr><th>Relationship</th><th>Level</th><th>Change</th><th>20-day Relative</th><th>Recent 5-day</th></tr>' + (relative.rows || []).map(x => `<tr><td>${esc(x.relationship)}</td><td>${esc(x.status)}</td><td>${esc(x.change)}${x.changedToday ? ' · new today' : ''}</td><td>${signed(x.relative20dPct)}</td><td>${signed(x.recent5dPct)}</td></tr>`).join(''));
    setHtml('mmf10Rotation', `<p><b>${esc(rotation.classification || '--')}</b>. Capital leaving equities: ${rotation.isMoneyLeavingEquities ? 'Yes' : 'No'}; leaving semiconductors: ${rotation.isMoneyLeavingSemiconductors ? 'Yes' : 'No'}.</p><p><b>Destination:</b> ${esc(destinations)}.</p><p>Rotation away from semiconductors is not automatically a market-wide risk-off event. Track where the capital is being accepted.</p>`);
    setHtml('mmf10Structure', `<tr><th>Layer</th><th>Range / Reference</th><th>Interpretation</th></tr><tr><td>Micro</td><td>${num(micro.low)}–${num(micro.high)}</td><td>${esc(micro.position || '--')} · ${micro.source === 'current_session_range' ? 'current session' : 'recent five-session band'}</td></tr><tr><td>Daily</td><td>${num(daily.low)}–${num(daily.high)}</td><td>EMA20 ${num(daily.ema20)} · EMA50 ${num(daily.ema50)}</td></tr><tr><td>Higher order</td><td>${num(higher.low)}–${num(higher.high)}</td><td>Longer-term support, resistance, and Fibonacci gates remain separate from the micro range.</td></tr><tr><td>Rule</td><td colspan="2">A level is a coordinate that triggers review, not a trade signal. Acceptance, volume, leadership, breadth, volatility, and macro transmission must confirm the break.</td></tr>`);
    setHtml('mmf10Auction', `<p><b>${esc(auction.classification || '--')}</b>. ${esc(auctionRead)}</p><p>Opening drive ${signed(auction.openingDrivePct)} · Recovery from session low ${signed(auction.recoveryFromSessionLowPct)} · Closing auction ${signed(auction.closingAuctionPct)}.</p><p>Absorption is not confirmed accumulation. Require later price acceptance and leadership confirmation.</p>`);
    setHtml('mmf10Catalyst', `<p><b>Event risk:</b> ${esc(catalyst.eventRisk || '--')} · <b>Structural risk:</b> ${esc(catalyst.structuralRisk || systemic.status || '--')} · <b>Current regime:</b> ${esc(catalyst.status || '--')}.</p><p>${esc(catalyst.eventDataStatus || 'No confirmed event data.')}</p><p>${esc(systemicRead)}</p>`);
    setHtml('mmf10EarningsSummary', `<p><b>Risk level: ${esc(earnings.riskLevel || 'UNCONFIRMED')}</b>. ${esc(earnings.summaryEN || earnings.reasonEN || 'Earnings dates are unconfirmed.')}</p><p>${esc(earnings.actionEN || 'The calendar adjusts event risk; it does not predict the result.')} Tracked-weight coverage ${num(earnings.trackedWeightCoveragePct)}%; weight reporting within seven days ${num(earnings.weightReportingWithin7DaysPct)}%.</p>`);
    setHtml('mmf10Earnings', '<tr><th>Symbol</th><th>Tracked Weight</th><th>Expected Date</th><th>Days</th><th>Session</th><th>EPS Estimate</th></tr>' + ((earnings.events || []).length ? (earnings.events || []).slice(0,10).map(x => `<tr><td>${esc(x.symbol)}</td><td>${num(x.trackedWeightPct)}%</td><td>${esc(x.reportDate)}</td><td>${num(x.daysUntil,0)}</td><td>${x.reportSession === 'PRE_MARKET' ? 'Pre-market' : x.reportSession === 'AFTER_HOURS' ? 'After hours' : 'Not provided'}</td><td>${x.estimate == null ? '--' : `${num(x.estimate)} ${esc(x.currency || '')}`}</td></tr>`).join('') : `<tr><td colspan="6">${esc(earnings.reasonEN || earnings.summaryEN || 'No confirmed upcoming earnings date.')}</td></tr>`));
    const nextEarnings = (earnings.events || [])[0] || {};
    setText('mmf10EarningsRisk', earnings.riskLevel || 'UNCONFIRMED');
    setText('mmf10EarningsNext', nextEarnings.symbol || '--');
    setText('mmf10EarningsDate', nextEarnings.reportDate ? `${nextEarnings.reportDate} · ${num(nextEarnings.daysUntil, 0)} days` : '--');
    setText('mmf10EarningsWeight', `${num(earnings.weightReportingWithin7DaysPct)}%`);
    setText('mmf10EarningsSpotlightRead', nextEarnings.symbol ? `${nextEarnings.symbol} · ${nextEarnings.reportSession === 'PRE_MARKET' ? 'Pre-market' : nextEarnings.reportSession === 'AFTER_HOURS' ? 'After hours' : 'Session not provided'}${nextEarnings.estimate == null ? '' : ` · EPS estimate ${num(nextEarnings.estimate)} ${nextEarnings.currency || ''}`}` : (earnings.reasonEN || earnings.summaryEN || 'No confirmed upcoming earnings date.'));
    setHtml('mmf10Macro', `<p><b>${esc(macro.status || '--')}</b>. ${macro.status === 'TIGHTENING / HEADWIND' ? 'Rates or the dollar are tightening the valuation channel into long-duration technology and leveraged semiconductors.' : macro.status === 'EASING / TAILWIND' ? 'Rates and the dollar are providing a marginal valuation tailwind.' : 'Macro signals are mixed and remain a confirmation layer rather than a standalone order.'}</p><p>${(macro.chain || []).map(esc).join(' → ')}</p>`);
    const scenarioCopy = [
      ['Range / Consolidation','Price is still digesting risk without aligned direction and leadership.','Remain accepted inside the micro range without a confirmed relative-strength break.','Sustained acceptance outside the range with volume, leadership, and breadth.','Repeated rejection at both boundaries, volume concentration, and relative-strength inflections.','Observe or remain in Market Vacation; do not chase the middle of the range.'],
      ['Bullish Breakout / Trend Resumption','A credible recovery requires semiconductors, QQQ, and volume to repair together.',`Reclaim the micro high ${num(micro.high)} and EMA20 ${num(daily.ema20)} with SOXX/QQQ and NVDA/QQQ improvement.`,'The breakout quickly falls back into the range or lacks semiconductor breadth.','SOXX, NVDA, QQQ, breadth, pullback volume, and closing acceptance.','Upgrade Observation to Active only after multi-layer confirmation; deploy in tranches.'],
      ['Orderly Further Decline (Non-systemic)','Semiconductors can continue deleveraging while the broader market remains stable.',`Test or break the micro low ${num(micro.low)} while QQQ/SPX remain stable and capital is accepted elsewhere.`,'Selling spreads across sectors, volatility, and credit into a systemic cluster.','Capital destination, SOXX/QQQ, VIX, HYG, and whether early selling stabilizes.','Recalculate odds and range. A lower price triggers review, not a mechanical buy.'],
      ['Systemic Risk / Disorderly Selloff','This path gains weight only when several markets deteriorate together.','SOXX, NVDA, QQQ, SPX, breadth, volatility, and credit confirm the same risk cluster.','Broad markets remain stable, capital rotates elsewhere, or a breakdown is quickly reclaimed.','Cross-market signal count, closing auction, credit, volatility, and macro shock.','Freeze additions, protect the account, and reopen Temple Calculation.']
    ];
    setHtml('scenarios', '<tr><th>Path</th><th>Probability</th><th>Why</th><th>Activation</th><th>Invalidation</th><th>Watch</th><th>Response</th></tr>' + scenarios.map((x, i) => { const c = scenarioCopy[i] || [x.name,'Conditional path.','Require confirming evidence.','The evidence fails.','Relevant cross-market evidence.','Keep the response conditional.']; return `<tr><td>${esc(c[0])}</td><td>${num(x.probability, 0)}%</td><td>${esc(c[1])}</td><td>${esc(c[2])}</td><td>${esc(c[3])}</td><td>${esc(c[4])}</td><td>${esc(c[5])}</td></tr>`; }).join(''));
    setHtml('checklist', `<div>□ Has price been accepted outside ${num(micro.low)}–${num(micro.high)}, or merely touched it?</div><div>□ Did current-session volume confirm the move?</div><div>□ Did SOXX/QQQ and NVDA/QQQ improve or deteriorate together?</div><div>□ Is systemic risk ${esc(systemic.direction || '--')} at ${esc(systemic.status || '--')}?</div><div>□ Does the evidence justify moving from ${esc(state.state || '--')} to another action state?</div>`);
    const card = byId('mmf10StructureCard');
    const detailSummary = card?.querySelector(':scope > details > summary');
    if (detailSummary) detailSummary.textContent = 'Expand the full structural review, scenarios, and next-session checks ▾';
    const detailHeadings = ['Relative Strength Matrix','Capital Rotation / Destination','Event Risk vs Structural Risk','Earnings Calendar','Multi-Timeframe Price Structure','Intraday Auction and Volume','Macro Transmission Chain','Four Scenarios · Conditions and Invalidation','Next-Session Confirmation Checklist','Daily 12-Question Conclusions'];
    card?.querySelectorAll(':scope > details h3').forEach((node, i) => { if (detailHeadings[i]) node.textContent = detailHeadings[i]; });
    const answerMap = {
      '1. What happened?': auctionRead,
      '2. Where did money go?': destinations,
      '3. Market-wide or sector-specific?': `${rotation.classification || '--'}. ${systemicRead}`,
      '4. Semiconductor relative strength?': `Leadership state: ${englishEnum(leadership.status || leadership.state || leadership.label || '--')}.`,
      '5. NVDA relative strength?': (() => { const row = (relative.rows || []).find(x => x.relationship === 'NVDA vs QQQ'); return row ? `NVDA vs QQQ is ${row.status} and ${row.change}${row.changedToday ? '; this is new today' : ''}.` : 'NVDA relative strength is unavailable.'; })(),
      '6. What regime?': `Structure regime: ${englishEnum(structure.regime || structure.label || '--')}; catalyst regime: ${englishEnum(catalyst.status || '--')}; earnings risk: ${englishEnum(earnings.riskLevel || 'UNCONFIRMED')}. ${earnings.summaryEN || earnings.reasonEN || ''}`,
      '7. Did volume confirm?': auction.available === false ? 'Reliable current-session auction volume is unavailable; confirmation is frozen.' : `${auctionRead} Confirmation still requires later price acceptance.`,
      '8. Did systemic risk change?': `Systemic-risk direction: ${englishEnum(systemic.direction || '--')}; current level: ${englishEnum(systemic.status || systemic.level || systemic.state || '--')}.`,
      '9. Four next scenarios?': scenarios.map(x => `${x.name} ${num(x.probability, 0)}%`).join(' · '),
      '10. What invalidates the base case?': scenarioCopy[0][3],
      '11. Structural change today?': structuralRead,
      '12. Vacation / Observation / Active?': `Current action state: ${englishEnum(state.state || state.label || '--')}.`
    };
    const answerRows = [...(byId('mmf10Answers')?.querySelectorAll('tr') || [])];
    if (answerRows[0]?.cells?.length >= 2) {
      answerRows[0].cells[0].textContent = 'Required Question';
      answerRows[0].cells[1].textContent = 'Current Read';
    }
    (m.answers || []).forEach((x, i) => {
      const row = answerRows[i + 1];
      if (!row?.cells || row.cells.length < 2) return;
      row.cells[0].textContent = x.question;
      row.cells[1].textContent = answerMap[x.question] || 'Use the current report evidence and keep the conclusion conditional.';
    });
  }

  function englishTimeframes(j) {
    const ma = j.monthlyAnalysis || {};
    const wa = j.weeklyAnalysis || {};
    const q = j.dailyBattlefield?.quote || {};
    const ti = j.dailyBattlefield?.technicalIndicators || {};
    const intra = j.intradayBattle || {};
    setHtml('timeframeSynthesis', `<b>Top-down read:</b> Monthly ${englishEnum(ma.trend)}; weekly ${englishEnum(wa.trend)}; daily price ${num(q.close ?? q.last)} versus EMA20 ${num(ti.ema20)} and EMA50 ${num(ti.ema50)}. Higher timeframes define the risk environment; lower timeframes supply early-change and execution evidence.`);
    setHtml('timeframeMonthlyText', `<p><b>Trend:</b> ${englishEnum(ma.trend)}</p><p>The current monthly bar is unfinished. Use it to judge the strategic regime, not as an entry trigger.</p><p>EMA20 ${num(ma.ema20)} · EMA50 ${num(ma.ema50)}. A steep long-term slope requires confirmation that patient capital is still absorbing pullbacks.</p>`);
    setHtml('timeframeWeeklyText', `<p><b>Trend:</b> ${englishEnum(wa.trend)}</p><p>The current weekly bar is unfinished. Weekly structure evaluates medium-term damage and recovery; it does not predict next week.</p><p>EMA20 ${num(wa.ema20)} · EMA50 ${num(wa.ema50)}.</p>`);
    setHtml('timeframeDailyText', `<p><b>Last / close:</b> ${num(q.close ?? q.last)} · ${signed(q.prevCloseChangePct ?? q.changePct)}</p><p>Daily structure provides the primary confirmation layer. Compare price with EMA20 ${num(ti.ema20)}, EMA50 ${num(ti.ema50)}, RSI14 ${num(ti.rsi14)}, and current volume quality.</p>`);
    setHtml('timeframeIntradayText', `<p><b>Source:</b> ${esc(intra.source || q.source || '--')}</p><p>Use the five-minute path to select execution timing, not to overturn account risk or higher-timeframe structure by itself. Latest available bar: ${esc(intra.latestTime || q.latestTime || '--')}.</p>`);
  }

  function participantAction(group) {
    const actions = {
      'Technical Traders': 'Monitor the nearest anchor, moving averages, and prior lows; failed support can trigger clustered stops.',
      'Swing Traders': 'Look for lighter-volume pullbacks and stronger-volume rebounds before committing more capital.',
      'Institutional Allocators': 'Require semiconductor strength to broaden into indices and major weights.',
      'Options / Hedging Flows': 'Reposition around round numbers, prior highs/lows, and crowded support, potentially amplifying false breaks.',
      'Liquidity Providers': 'Test where stops and passive orders are concentrated; liquidity is a target, not proof of intent.'
    };
    return actions[group] || 'Treat the participant map as a testable behavior hypothesis, not a claim about a specific institution.';
  }

  function englishBehavior(j) {
    const b = j.strategicBehaviorMap || {};
    const a = b.dynamicAnchorRange || {};
    const cb = b.capitalBehavior || {};
    setText('behaviorTitle', 'Market Behavior Analysis');
    setText('behaviorPrinciple', 'More complete calculations create better decisions; incomplete calculations create fragile conviction.');
    setText('behaviorCore', 'The objective is not to predict one price path. It is to anticipate who may need to act next and how the account should respond.');
    setText('behaviorSummary', `Current price is ${num(b.pathMeta?.currentPrice)}. The active behavior range is ${num(a.low)}–${num(a.high)}. The nearest consensus zone is a test of real demand and forced selling, not an automatic entry.`);
    setText('behaviorAccountResponse', 'Pre-design the account response to an advance, decline, range, and false move. Do not use one path to prove the thesis.');
    setText('behaviorPathMeta', `Report date: ${esc(b.pathMeta?.asOfDate || '--')} · timeframe: Daily / current MMF report · reference price: ${num(b.pathMeta?.currentPrice)}. The path is recalculated on every run; broken support becomes overhead resistance.`);
    setText('capitalBehaviorPosture', englishEnum(cb.postureCN));
    setText('capitalBehaviorScore', cb.score == null ? 'Awaiting current volume' : `${num(cb.score, 1)}/10`);
    setText('capitalBehaviorAction', englishEnum(cb.postureCN));
    setText('capitalBehaviorWatchMetric', 'Price / Volume');
    setHtml('capitalBehaviorSummary', `<p>${cb.score == null ? 'Current-session volume is not reliable enough to classify accumulation or distribution.' : 'Capital behavior must be confirmed by what price does after the volume event.'}</p><p>Do not upgrade an odds position into a trend position until flow, price acceptance, and sector breadth align.</p>`);
    setHtml('capitalBehaviorEvidence', `<p>Last / close ${num(b.pathMeta?.currentPrice)}. Sector rotation is ${esc(j.sectorHeatmap?.mode || '--')}. VIX is ${num(j.macro?.vix ?? j.macroTransmission?.vix)}.</p><p>A missing or partial volume reading is not the same as low volume.</p>`);
    setText('capitalBehaviorAccount', `Current exposure is ${num(j.accountState?.currentPositionPct ?? j.positionEngineering?.currentPositionPct, 1)}%. Preserve cash optionality until capital behavior strengthens.`);
    setText('anchorMode', englishEnum(a.mode));
    setHtml('anchorBasis', `<p>The range is recalculated from recent swing structure, Fibonacci confluence, price, and volume. It is not permanent support or resistance.</p><p>Recalculate above ${num(a.breakoutAbove)} or below ${num(a.breakdownBelow)}. An accepted break changes the role of the old boundary.</p>`);
    const candidates = [
      ...(a.supportCandidates || []).map(x => ({...x, type: 'Support'})),
      ...(a.resistanceCandidates || []).map(x => ({...x, type: 'Resistance'}))
    ].slice(0, 8);
    setHtml('anchorCandidates', '<tr><th>Type</th><th>Price</th><th>Evidence</th><th>Strength</th></tr>' + candidates.map(x => `<tr><td>${x.type}</td><td>${num(x.price)}</td><td>${esc(x.label)}</td><td>${esc(x.strength)}</td></tr>`).join(''));
    const consensus = [
      `The active range is ${num(a.low)}–${num(a.high)}; treat it as a behavior zone until price is accepted outside it.`,
      `The nearest confluence is a test of who will absorb supply and who may be forced to sell.`,
      'Semiconductors remain the main window into risk appetite; confirmation should broaden beyond one ticker.',
      'The market still requires confirmation rather than unconditional trend chasing.',
      `Capital posture is ${englishEnum(cb.postureCN)}.`
    ];
    setHtml('behaviorConsensus', (b.consensusNow || []).map((x, i) => `<p><b>${esc(x.confidence)} confidence</b> · ${consensus[i] || 'Treat this belief as a testable hypothesis.'}</p>`).join(''));
    setHtml('behaviorParticipants', (b.participantMap || []).map(x => `<p><b>${esc(x.group)}</b><br>${participantAction(x.group)}</p>`).join(''));
    const scenarioText = {
      'Support Holds': [`Buyers absorb the pullback near the consensus area and keep price inside the range.`, 'Only a planned probe is permitted; one defended session is not permission to fill the position.'],
      'False Breakdown': [`Price briefly sweeps below consensus support, then reclaims it as forced selling is absorbed.`, 'Reassess a probe only if volume quality and sector breadth do not deteriorate.'],
      'Consensus Failure': [`Price is accepted below the anchor while volume, semiconductor breadth, or volatility confirms weakness.`, 'Freeze additions and rerun MMF; a lower price is not automatically better odds.'],
      'Base Path': [`Price continues to digest risk without consistent directional or leadership confirmation.`, 'Preserve optionality and avoid chasing the middle of the range.']
    };
    setHtml('behaviorScenarios', (b.liquidityScenarios || []).map(x => { const t = scenarioText[x.scenario] || ['Treat the path as conditional.', 'Keep the account response conditional.']; return `<div class="behaviorPath"><h3>${esc(x.scenario)}</h3><p>${t[0]}</p><p><b>Account response:</b> ${t[1]}</p></div>`; }).join(''));
  }

  function englishChallenge(ch, j) {
    if (typeof enemyChallengeEN === 'function') return enemyChallengeEN(ch, j);
    return {title: ch.nameCN || 'Adversarial challenge', challenge: ch.challengeCN, alternative: ch.alternativeCN, answer: ch.whatWouldChangeCN};
  }
  function englishEnemy(j) {
    const r = j.enemyIntentReview || {};
    setText('enemyTitle', 'Enemy Intent');
    setText('enemyPrinciple', 'Plans improve when the strongest opposing explanation is made explicit before deployment.');
    setText('enemyCore', 'The review is not designed to prove the thesis. It searches for what may be wrong, what the market could exploit, and what evidence must change the plan.');
    setHtml('enemySummary', `<p>If the market wanted to exploit the current plan, where would the account be most predictable?</p><p>Do not confuse a deep-odds position with a confirmed trend position. Narrative confidence never overrides invalidation and account risk.</p>`);
    const pe = j.positionEngineering || {};
    const gate = pe.riskRegimeGate || {};
    setHtml('enemyContext', `<p>Position tier: ${esc(englishEnum(pe.positionTier))}; dynamic range ${num(pe.dynamicSuggestedRangePct?.low, 0)}–${num(pe.dynamicSuggestedRangePct?.high, 0)}%; extension ceiling ${num(pe.extensionCapPct, 0)}%.</p><p>Risk gate: ${esc(gate.status || '--')}. Capital posture: ${esc(englishEnum(j.strategicBehaviorMap?.capitalBehavior?.postureCN))}.</p>`);
    setHtml('enemyChallenges', (r.challenges || []).map(ch => { const x = englishChallenge(ch, j); return `<div class="behaviorPath"><h3>${esc(x.title)} <span class="pill">Challenge Weight ${esc(ch.confidence)}</span></h3><p><b>Challenge:</b> ${esc(x.challenge)}</p><p><b>Alternative explanation:</b> ${esc(x.alternative)}</p><p><b>What changes the plan:</b> ${esc(x.answer)}</p></div>`; }).join(''));
    setText('enemyFinal', 'The plan passes only when its major opposing explanations have observable control conditions and the worst credible path does not break the account.');
  }

  function englishInitiative(j) {
    const im = typeof initiativeAccountView === 'function' ? initiativeAccountView(j) : (j.initiativeManagement || {});
    const c = im.components || {};
    const ef = im.executionFeasibility || {};
    setText('initiativeState', im.labelEN || englishEnum(im.label));
    setText('initiativeScore', num(im.score));
    setText('initiativeCash', num(c.cashOptionality));
    setText('initiativeParticipation', num(c.participationOptionality));
    setText('initiativeExecution', ef.score == null ? '--' : `${num(ef.score, 0)}/100`);
    setText('initiativePrinciple', im.principleEN || 'Initiative matters more than direction.');
    setText('initiativeRead', im.accountReadEN || 'Initiative combines participation, cash, re-entry capacity, exit capacity, and plan readiness.');
    setHtml('initiativeZones', '<tr><th>Role</th><th>Zone / Levels</th><th>Default Size</th><th>Required Information</th><th>Invalidation</th></tr>' + (im.informationZones || []).map(z => `<tr><td><b>${esc(z.roleEN || englishEnum(z.role))}</b></td><td>${z.levels ? z.levels.map(num).join(' / ') : `${num(z.low)}–${num(z.high)}`}</td><td>${num(z.defaultSizePct, 0)}%</td><td>${esc(z.triggerEN)}<br><span class="small">${esc(z.meaningEN)}</span></td><td>${esc(z.invalidationEN)}</td></tr>`).join(''));
    setHtml('initiativeModels', (im.structureHypotheses || []).map(x => `<div class="dim"><h3>${esc(x.nameEN || x.name)} <span class="pill">${num(x.confidence, 0)}%</span></h3><p class="note">${esc(x.evidenceEN)}</p><p class="small">Action: ${esc(x.actionEN)}<br>Invalidation: ${esc(x.invalidationEN)}</p></div>`).join(''));
    const lf = im.liquidityFollowThrough || {};
    setHtml('initiativeFollow', `<p><b>${esc(englishEnum(lf.state))}</b> · ${esc(lf.window || '--')}</p><p>${esc(lf.readEN || lf.summaryEN || '--')}</p>`);
    setHtml('initiativeTemple', '<b>Temple recalculation triggers</b>' + (im.templeRecalculationTriggersEN || ['A key boundary is accepted as broken.', 'The core liquidity interpretation fails.', 'Account risk overrides the model allowance.']).map(x => `<p>□ ${esc(x)}</p>`).join(''));
    setHtml('initiativeFeasibility', `<p><b>Current mode: ${esc(ef.currentMode || '--')}</b></p><p>${esc(ef.defaultModeEN || '--')}</p><p>${esc(ef.activeModeEN || '--')}</p><p>${esc(ef.constraintEN || '--')}</p>`);
  }

  function englishField(j) {
    const f = j.fieldEvolution || {};
    const phase = f.marketPhase || {};
    const liq = f.liquidityAssessment || {};
    const emotion = f.emotionReaction || {};
    const exit = f.exitQuality || {};
    const tail = f.tailRisk || {};
    const symmetry = f.symmetry || {};
    const capital = f.capitalEfficiency || {};
    setText('fieldPhase', phase.labelEN || '--');
    setText('fieldLiquidity', liq.labelEN || '--');
    setText('fieldDeployment', englishEnum(emotion.deploymentClass));
    setText('fieldExitQuality', `${esc(exit.grade || '--')} · ${num(exit.score, 0)}/5`);
    setText('fieldCoreLesson', f.coreLessonEN || 'Every live campaign should improve the next decision rule.');
    setText('fieldLiquidityRead', `${liq.readEN || '--'} ${emotion.readEN || ''}`);
    setText('fieldEmotion', emotion.ruleEN || emotion.readEN || '--');
    setText('fieldTailRisk', tail.readEN || '--');
    setText('fieldSymmetry', symmetry.readEN || '--');
    setText('fieldExitRead', `${exit.ruleEN || ''} ${exit.actionEN || ''}`.trim() || '--');
    setText('fieldCapitalRules', capital.principleEN || '--');
  }

  function englishPosition(j) {
    const pe = j.positionEngineering || {};
    const q = j.dailyBattlefield?.quote || {};
    const exposure = Number(byId('planExposurePct')?.value || j.accountState?.currentPositionPct || pe.currentPositionPct || 0);
    const ceiling = Number(pe.maxTacticalPositionPct || 0);
    const room = Math.max(0, ceiling - exposure);
    setText('planHeadline', `${esc(j.meta?.ticker || 'SOXL')} account plan: ${num(exposure, 1)}% exposure, ${num(room, 1)}% theoretical room, and ${num(Math.max(0, 100 - exposure), 1)}% cash / other assets.`);
    setHtml('planBullets', `<li>Last / close ${num(q.close ?? q.last)} · ${signed(q.prevCloseChangePct ?? q.changePct)}.</li><li>Position tier: ${esc(englishEnum(pe.positionTier))}; risk gate ${esc(pe.riskRegimeGate?.status || '--')}.</li><li>The model ceiling is optional capacity, not required exposure.</li><li>Account risk overrides any technical permission to add.</li>`);
    const riskLimit = Number(byId('planMaxLossPct')?.value || 0);
    const avg = Number(byId('planAvgCost')?.value || 0);
    const accountImpact = avg > 0 && Number(q.close ?? q.last) > 0 ? exposure * (Number(q.close ?? q.last) / avg - 1) : null;
    const breached = riskLimit > 0 && accountImpact != null && accountImpact <= -riskLimit;
    setText('planAction', breached ? 'Reduce Risk / Exit Review' : (room > 0 ? 'Conditional Hold / Add Review' : 'Hold / Risk Review'));
    setText('planRemainingRoom', breached ? '0%' : `${num(room, 1)}%`);
    setHtml('planNextMove', `<b>Next action:</b> ${breached ? 'Freeze additions and decide which tranche to reduce until account risk returns inside tolerance.' : 'Manage the existing position. Add only after the report\'s activation conditions are accepted; reduce when an invalidation path is accepted.'}`);
    setText('planStrategy', 'Portfolio strategy: preserve enough cash and risk capacity for the next campaign. Each tranche needs a distinct mission, trigger, and exit rule.');
    const riskLabel = document.querySelector('label[for="planMaxLossPct"]');
    if (riskLabel) riskLabel.innerHTML = 'Account loss tolerance (% of NAV)<span>Maximum loss this ticker may contribute to total account NAV</span>';
  }

  function englishEvidence(j) {
    const opt = j.optionsContext || {};
    const fg = j.fearGreed || {};
    const heat = j.sectorHeatmap || {};
    setText('heatmapMode', heat.mode || '--');
    setText('heatmapSummary', 'Green indicates relative strength and red relative weakness. Read group averages first, then decide whether leadership is broad or concentrated.');
    const groupNames = ['Indices / Growth', 'Semiconductor Chain', 'Communication Services', 'Consumer Cyclicals', 'Clean Energy', 'EV / Batteries', 'Financials', 'Defensive / Value', 'Industrials / Materials', 'Real Estate', 'Macro / Safe Havens'];
    byId('heatmapGrid')?.querySelectorAll('.heatTitle').forEach((node, i) => { node.textContent = groupNames[i] || node.textContent; });
    setText('optionsText', `Put/Call Volume measures today\'s bearish-versus-bullish contract flow. Put/Call OI measures outstanding positioning. Average IV is the market price of expected volatility. Net Gamma Exposure Proxy estimates whether dealer hedging may amplify (negative) or dampen (positive) moves; it is not a true dealer inventory reading.`);
    setText('macroText', `Fear & Greed is ${num(fg.score, 1)} / ${esc(fg.label || '--')}. VIX and cross-asset proxies should modify position size and confirmation requirements, not act as standalone entry signals.`);
    setText('smartText', 'Treat flow, positioning, and institutional proxies as supporting evidence. They do not identify a specific buyer or seller and cannot authorize a trade by themselves.');
    setText('newsText', 'Classify news by whether it changes earnings, policy, liquidity, or the risk regime. Price reaction matters more than headline volume.');
    setText('fgNote', 'Fear & Greed is a context variable, not an entry trigger. Extreme readings matter only when price, volume, and market structure confirm the interpretation.');
    setText('fibSummary', 'Fibonacci levels are terrain markers and confluence zones, not precise predictions. A level becomes actionable only when capital behavior confirms it.');
    if (byId('optionsTable') && opt) {
      byId('optionsTable').querySelectorAll('th,td').forEach(translateText);
    }
  }

  function hydrateEnglish(j) {
    if (!j || uiLanguage !== 'en') return;
    englishExecutive(j);
    englishDaily(j);
    englishMmf10(j);
    englishTimeframes(j);
    englishBehavior(j);
    englishEnemy(j);
    englishInitiative(j);
    englishField(j);
    englishPosition(j);
    englishEvidence(j);
    window.MMF401K?.setLanguage('en');
    translateStaticEnglish();
    translateHelpNotes();
    const ask = byId('askQuestion');
    if (ask) ask.placeholder = 'For example: Why can RSI be oversold while position size remains low?';
    setText('askAnswer', byId('askAnswer')?.textContent.includes('先运行') ? 'Run MMF once, then ask a question about the current report.' : byId('askAnswer')?.textContent);
  }

  function showSharedPage(page) {
    localizedPage = page;
    byId('englishPage')?.classList.add('hidden');
    baseShowPage(page);
    PAGE_IDS.forEach(id => {
      const node = byId(id);
      if (node) node.dataset.language = uiLanguage;
    });
    if (uiLanguage === 'en') {
      translateStaticEnglish();
      translateHelpNotes();
      if (lastReport) hydrateEnglish(lastReport);
    } else restoreChinese();
    window.MMF401K?.setLanguage(uiLanguage);
    setSharedNav(page);
  }

  function setSharedNav(page) {
    Object.entries(NAV_LABELS).forEach(([key, labels]) => {
      const button = byId(key === 'position' ? 'positionNav' : `${key}Nav`);
      if (!button) return;
      button.textContent = labels[uiLanguage === 'en' ? 1 : 0];
      button.classList.toggle('active', key === page);
      button.classList.toggle('ghost', key !== page);
    });
  }

  function restoreMmf10ChineseChrome() {
    const card = byId('mmf10StructureCard');
    const detailSummary = card?.querySelector(':scope > details > summary');
    if (detailSummary) detailSummary.textContent = '展开 MMF-10 完整结构审查、情景与明日确认 ▾';
    const headings = ['相对强弱矩阵','资本轮动 / 资金去向','事件风险 vs 结构风险','财报日历 Earnings Calendar','多周期价格结构','盘中拍卖与量能','宏观传导链','四情景 · 条件与作废','下一交易日确认清单','每日 12 问结论'];
    card?.querySelectorAll(':scope > details h3').forEach((node, i) => { if (headings[i]) node.textContent = headings[i]; });
  }

  function applySharedLanguage() {
    const english = uiLanguage === 'en';
    document.documentElement.lang = english ? 'en' : 'zh-CN';
    document.body.classList.toggle('lang-en', english);
    byId('englishPage')?.classList.add('hidden');
    const toggle = byId('languageToggle');
    if (toggle) toggle.textContent = english ? '中文版' : 'English';

    if (!english) {
      restoreChinese();
      if (lastReport) {
        baseRender(lastReport);
        basePositionRender(lastReport);
      }
      restoreMmf10ChineseChrome();
      if (byId('status')?.textContent === 'English email preview ready') setText('status', 'Ready');
    }
    showSharedPage(localizedPage || 'mmf');
    if (english) hydrateEnglish(lastReport);
    window.MMF401K?.setLanguage(uiLanguage);
    if (lastReport && typeof updateReportDate === 'function') updateReportDate(lastReport.meta || {});
  }

  function install() {
    if (window.MMFUnifiedI18n?.installed) return;
    window.MMFUnifiedI18n.installed = true;
    baseRender = render;
    basePositionRender = renderPositionPlan;
    baseShowPage = showPage;

    if (typeof unmountEnglishPositionInputs === 'function') unmountEnglishPositionInputs();
    const noop = function () {};
    renderEnglishSubpage = noop;
    renderEnglishSubpageFull = noop;
    hydrateEnglishData = noop;
    renderEnglishInitiative = noop;
    renderEnglishFieldEvolution = noop;
    renderEnglishCapitalEfficiency = noop;
    appendEnglishBattlefieldCoverage = noop;
    appendEnglishBehaviorCoverage = noop;
    appendEnglishEnemyCoverage = noop;
    appendEnglishPositionCoverage = noop;
    mountEnglishPositionInputs = noop;
    ensureEnglishEmailActions = noop;

    activeEmailTargets = function () {
      return {details: byId('emailDetails'), box: byId('emailBox')};
    };
    showLocalizedPage = showSharedPage;
    setLocalizedNav = setSharedNav;
    applyLanguage = applySharedLanguage;

    render = function (j) {
      baseRender(j);
      if (uiLanguage === 'en') hydrateEnglish(j);
    };
    renderPositionPlan = function (j) {
      basePositionRender(j);
      if (uiLanguage === 'en') hydrateEnglish(j);
    };

    Object.keys(NAV_LABELS).forEach(page => {
      const button = byId(page === 'position' ? 'positionNav' : `${page}Nav`);
      if (button) button.onclick = () => showSharedPage(page);
    });

    byId('englishPage')?.setAttribute('aria-hidden', 'true');
  }

  window.MMFUnifiedI18n = {install};
})();
