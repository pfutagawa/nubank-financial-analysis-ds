const PURPLE = '#820AD1';
const PURPLE_DARK = '#2F0549';
const PURPLE_MID = '#6B16A8';
const PURPLE_SOFT = '#C89BE5';
const PARTIAL_AMBER = '#C17200';
const MUTED = '#6F6673';
const GRID = '#ECE7EF';
const POSITIVE = '#157A54';
const NEGATIVE = '#B42318';

let currentView = 'ltm';
let dashboardPayload = null;

const plotConfig = {
  responsive: true,
  displaylogo: false,
  modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d'],
  scrollZoom: false,
};

const baseLayout = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { family: 'Inter, Segoe UI, sans-serif', color: '#17131A', size: 12 },
  margin: { l: 55, r: 22, t: 22, b: 48 },
  hoverlabel: { bgcolor: '#2F0549', bordercolor: '#2F0549', font: { color: '#fff' } },
  xaxis: { gridcolor: GRID, zerolinecolor: GRID, fixedrange: true },
  yaxis: { gridcolor: GRID, zerolinecolor: GRID, fixedrange: true },
  legend: { orientation: 'h', x: 0, y: 1.12, bgcolor: 'rgba(0,0,0,0)' },
};

function layout(extra = {}) {
  return {
    ...baseLayout,
    ...extra,
    xaxis: { ...baseLayout.xaxis, ...(extra.xaxis || {}) },
    yaxis: { ...baseLayout.yaxis, ...(extra.yaxis || {}) },
    legend: { ...baseLayout.legend, ...(extra.legend || {}) },
  };
}

const fmt1 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const fmt2 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmt0 = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 });

function usdB(value, digits = 2) {
  if (value == null) return '—';
  return `US$ ${digits === 1 ? fmt1.format(value) : fmt2.format(value)} bi`;
}

function pct(value, digits = 1) {
  if (value == null) return '—';
  const n = digits === 0 ? fmt0.format(value) : fmt1.format(value);
  return `${n}%`;
}

function values(rows, key) {
  return rows.map(row => row[key]);
}

function safePlot(id, traces, chartLayout) {
  const node = document.getElementById(id);
  if (!node || typeof Plotly === 'undefined') return;
  Plotly.newPlot(node, traces, chartLayout, plotConfig);
}

function setNodeText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function getActiveFinancialSeries(data, viewMode) {
  const views = data.views || {};
  if (viewMode === 'closed_years') {
    return (views.closed_years || data.financial).map(r => ({
      ...r,
      xLabel: String(r.year),
      isPartial: false,
    }));
  }
  if (viewMode === 'ytd_comparison') {
    return (views.ytd_comparison || []).map(r => ({
      ...r,
      xLabel: r.is_partial ? `2026* (parcial até ${data.meta.partial_reference || '2T26'})` : `2025 (${data.metrics_2026.ytd_comparison.label_2025})`,
      isPartial: Boolean(r.is_partial),
    }));
  }
  if (viewMode === 'quarterly') {
    return (data.financial_quarterly || []).map(q => ({
      year: q.ano,
      xLabel: q.parcial === 'sim' ? `${q.trimestre}* (parcial)` : q.trimestre,
      isPartial: q.parcial === 'sim',
      customers_m: q.clientes,
      arpac_usd: q.arpac_mensal,
      cost_to_serve_usd: q.custo_servir_mensal,
      revenue_usd_b: q.receita,
      gross_profit_usd_b: null,
      net_income_usd_b: q.lucro_liquido_ifrs,
      deposits_usd_b: q.depositos,
      credit_portfolio_usd_b: q.carteira_credito,
      interest_earning_portfolio_usd_b: q.carteira_credito_juros,
      source_url: q.fonte_url,
    }));
  }
  // Padrão: LTM (2021-2025 fechados + 2026* LTM)
  return (views.ltm || data.financial).map(r => ({
    ...r,
    xLabel: r.is_partial ? `2026* (parcial até ${data.meta.partial_reference || '2T26'})` : String(r.year),
    isPartial: Boolean(r.is_partial),
  }));
}

function renderHeadline(data, viewMode = currentView) {
  const h = data.headline;
  const m26 = data.metrics_2026;
  const refQ = m26 ? m26.reference_quarter : '2T26';

  setNodeText('partial-badge-top', `2026* · ${m26 ? m26.partial_label : 'parcial até 2T26'}`);

  if (viewMode === 'closed_years') {
    setNodeText('metric-customers-label', 'Clientes · 4T25 (fechado)');
    setNodeText('metric-customers', `${fmt1.format(h.customers_m)} mi`);
    setNodeText('metric-customers-note', `+${fmt0.format(h.customer_growth_pct)}% entre 2021 e 2025`);

    setNodeText('metric-revenue-label', 'Receita anual · 2025 (20-F)');
    setNodeText('metric-revenue', usdB(h.revenue_usd_b));
    setNodeText('metric-revenue-note', `${fmt1.format(h.revenue_multiple)}× o nível de 2021`);

    setNodeText('metric-income-label', 'Lucro líquido IFRS · 2025');
    setNodeText('metric-income', usdB(h.net_income_usd_b));
    setNodeText('metric-income-note', 'IFRS · exercício fechado 2025');

    setNodeText('metric-deposits-label', 'Depósitos · 4T25 (fechado)');
    setNodeText('metric-deposits', usdB(h.deposits_usd_b, 1));
    setNodeText('metric-deposits-note', `${fmt1.format(h.deposit_multiple)}× o nível de 2021`);
    return;
  }

  if (viewMode === 'ytd_comparison' && m26) {
    const ytd = m26.ytd_comparison;
    const stk = m26.stocks_latest;
    setNodeText('metric-customers-label', `Clientes · estoque em ${refQ}*`);
    setNodeText('metric-customers', `${fmt1.format(stk.clientes_m)} mi`);
    setNodeText('metric-customers-note', `+${fmt1.format(stk.clientes_yoy_pct)}% vs. 2T25 (parcial até ${refQ})`);

    setNodeText('metric-revenue-label', `Receita · ${ytd.label_2026}* (parcial)`);
    setNodeText('metric-revenue', usdB(ytd.revenue_2026_usd_b));
    setNodeText('metric-revenue-note', `+${fmt1.format(ytd.revenue_yoy_pct)}% vs. ${ytd.label_2025} (${usdB(ytd.revenue_2025_usd_b)})`);

    setNodeText('metric-income-label', `Lucro líquido IFRS · ${ytd.label_2026}*`);
    setNodeText('metric-income', usdB(ytd.net_income_2026_usd_b));
    setNodeText('metric-income-note', `+${fmt1.format(ytd.net_income_yoy_pct)}% vs. ${ytd.label_2025} (${usdB(ytd.net_income_2025_usd_b)})`);

    setNodeText('metric-deposits-label', `Depósitos · estoque em ${refQ}*`);
    setNodeText('metric-deposits', usdB(stk.depositos_usd_b, 1));
    setNodeText('metric-deposits-note', `+${fmt1.format(stk.depositos_yoy_pct)}% vs. 2T25 (US$ ${fmt1.format(36.6)} bi)`);
    return;
  }

  if (viewMode === 'quarterly' && m26) {
    const qList = data.financial_quarterly || [];
    const lastQ = qList[qList.length - 1];
    const stk = m26.stocks_latest;
    setNodeText('metric-customers-label', `Clientes · estoque em ${refQ}*`);
    setNodeText('metric-customers', `${fmt1.format(stk.clientes_m)} mi`);
    setNodeText('metric-customers-note', `+${fmt1.format(stk.clientes_yoy_pct)}% YoY vs. 2T25`);

    setNodeText('metric-revenue-label', `Receita trimestral · ${refQ}*`);
    setNodeText('metric-revenue', usdB(lastQ ? lastQ.receita : null));
    setNodeText('metric-revenue-note', `Trimestre isolado ${refQ} (parcial 2026*)`);

    setNodeText('metric-income-label', `Lucro líquido IFRS · ${refQ}*`);
    setNodeText('metric-income', usdB(lastQ ? lastQ.lucro_liquido_ifrs : null));
    setNodeText('metric-income-note', `IFRS no trimestre ${refQ} (parcial 2026*)`);

    setNodeText('metric-deposits-label', `Depósitos · estoque em ${refQ}*`);
    setNodeText('metric-deposits', usdB(stk.depositos_usd_b, 1));
    setNodeText('metric-deposits-note', `Posição de fechamento do ${refQ}`);
    return;
  }

  // Visão LTM padrão (2021–2025 + 2026* LTM 2T26)
  if (m26) {
    const ltm = m26.ltm;
    const stk = m26.stocks_latest;
    setNodeText('metric-customers-label', `Clientes · ref. ${refQ}* (parcial)`);
    setNodeText('metric-customers', `${fmt1.format(stk.clientes_m)} mi`);
    setNodeText('metric-customers-note', `+${fmt0.format(h.customer_growth_to_2026_pct)}% desde 2021 · estoque em ${refQ}`);

    setNodeText('metric-revenue-label', `Receita · LTM ${refQ}* (3T25–2T26)`);
    setNodeText('metric-revenue', usdB(ltm.revenue_usd_b));
    setNodeText('metric-revenue-note', `${fmt1.format(h.revenue_ltm_multiple)}× 2021 · soma dos últimos 4 trimestres`);

    setNodeText('metric-income-label', `Lucro líquido IFRS · LTM ${refQ}*`);
    setNodeText('metric-income', usdB(ltm.net_income_usd_b));
    setNodeText('metric-income-note', `IFRS · janela LTM (${ltm.start_quarter}–${ltm.end_quarter})`);

    setNodeText('metric-deposits-label', `Depósitos · ref. ${refQ}* (parcial)`);
    setNodeText('metric-deposits', usdB(stk.depositos_usd_b, 1));
    setNodeText('metric-deposits-note', `${fmt1.format(h.deposit_2026_multiple)}× 2021 · estoque em ${refQ}`);
  }
}

function renderGrowth(data, viewMode = currentView) {
  const f = getActiveFinancialSeries(data, viewMode);
  const x = f.map(r => r.xLabel);
  const barColors = f.map(r => (r.isPartial ? PARTIAL_AMBER : PURPLE));
  const barPatterns = f.map(r => (r.isPartial ? '/' : ''));

  safePlot('chart-revenue-income', [
    {
      type: 'bar',
      x,
      y: values(f, 'revenue_usd_b'),
      name: 'Receita (2026* hachurado = parcial)',
      marker: {
        color: barColors,
        pattern: { shape: barPatterns },
      },
      hovertemplate: '<b>%{x}</b><br>Receita: US$ %{y:.2f} bi<extra></extra>',
    },
    {
      type: 'scatter',
      mode: 'lines+markers',
      x,
      y: values(f, 'net_income_usd_b'),
      name: 'Lucro líquido IFRS',
      line: { color: PURPLE_DARK, width: 3 },
      marker: {
        size: f.map(r => (r.isPartial ? 11 : 8)),
        symbol: f.map(r => (r.isPartial ? 'diamond' : 'circle')),
      },
      hovertemplate: '<b>%{x}</b><br>Lucro líquido IFRS: US$ %{y:.2f} bi<extra></extra>',
    },
  ], layout({ yaxis: { title: 'US$ bilhões', gridcolor: GRID, zerolinecolor: '#BEB6C2' }, barmode: 'overlay' }));

  safePlot('chart-scale', [
    {
      type: 'scatter',
      mode: 'lines+markers',
      x,
      y: values(f, 'customers_m'),
      name: 'Clientes (estoque)',
      line: { color: PURPLE, width: 4 },
      marker: {
        size: f.map(r => (r.isPartial ? 11 : 8)),
        symbol: f.map(r => (r.isPartial ? 'diamond' : 'circle')),
      },
      hovertemplate: '<b>%{x}</b><br>Clientes: %{y:.1f} mi<extra></extra>',
    },
    {
      type: 'bar',
      x,
      y: values(f, 'deposits_usd_b'),
      name: 'Depósitos (estoque)',
      yaxis: 'y2',
      opacity: 0.62,
      marker: {
        color: f.map(r => (r.isPartial ? '#E7B977' : PURPLE_SOFT)),
        pattern: { shape: barPatterns },
      },
      hovertemplate: '<b>%{x}</b><br>Depósitos: US$ %{y:.1f} bi<extra></extra>',
    },
  ], layout({
    yaxis: { title: 'Clientes (milhões)', gridcolor: GRID },
    yaxis2: { title: 'Depósitos (US$ bi)', overlaying: 'y', side: 'right', gridcolor: 'rgba(0,0,0,0)', fixedrange: true },
  }));

  safePlot('chart-arpac', [
    {
      type: 'scatter',
      mode: 'lines+markers',
      x,
      y: values(f, 'arpac_usd'),
      name: 'ARPAC mensal',
      line: { color: PURPLE, width: 4 },
      marker: {
        size: f.map(r => (r.isPartial ? 11 : 8)),
        symbol: f.map(r => (r.isPartial ? 'diamond' : 'circle')),
      },
      hovertemplate: '<b>%{x}</b><br>ARPAC: US$ %{y:.1f}<extra></extra>',
    },
    {
      type: 'scatter',
      mode: 'lines+markers',
      x,
      y: values(f, 'cost_to_serve_usd'),
      name: 'Custo de servir',
      line: { color: '#7B7480', width: 2.5, dash: 'dot' },
      marker: { size: 7 },
      hovertemplate: '<b>%{x}</b><br>Custo: US$ %{y:.1f}<extra></extra>',
    },
  ], layout({ yaxis: { title: 'US$ / cliente ativo / mês', gridcolor: GRID } }));

  const portfolio = f.filter(row => row.credit_portfolio_usd_b != null);
  const pLabels = portfolio.map(r => r.xLabel);
  const pPatterns = portfolio.map(r => (r.isPartial ? '/' : ''));

  safePlot('chart-portfolio', [
    {
      type: 'bar',
      x: pLabels,
      y: values(portfolio, 'credit_portfolio_usd_b'),
      name: 'Carteira total (cartão + empréstimos)',
      marker: {
        color: portfolio.map(r => (r.isPartial ? PARTIAL_AMBER : PURPLE)),
        pattern: { shape: pPatterns },
      },
      hovertemplate: '<b>%{x}</b><br>Carteira total: US$ %{y:.1f} bi<extra></extra>',
    },
    {
      type: 'bar',
      x: pLabels,
      y: values(portfolio, 'interest_earning_portfolio_usd_b'),
      name: 'Carteira geradora de juros (IEP)',
      marker: { color: '#D9B9ED' },
      hovertemplate: '<b>%{x}</b><br>IEP: US$ %{y:.1f} bi<extra></extra>',
    },
  ], layout({ barmode: 'group', yaxis: { title: 'US$ bilhões', gridcolor: GRID } }));

  const first = f[0];
  const last = f[f.length - 1];
  const arpacGrowth = (last.arpac_usd / first.arpac_usd - 1) * 100;
  const insights = [
    ['Receita (' + last.xLabel + ')', `${fmt1.format(last.revenue_usd_b / first.revenue_usd_b)}×`, `${usdB(first.revenue_usd_b)} → ${usdB(last.revenue_usd_b)}`],
    ['Clientes (' + last.xLabel + ')', `${fmt1.format(last.customers_m / first.customers_m)}×`, `${fmt1.format(first.customers_m)} mi → ${fmt1.format(last.customers_m)} mi`],
    ['ARPAC mensal', `+${fmt0.format(arpacGrowth)}%`, `US$ ${fmt1.format(first.arpac_usd)} → US$ ${fmt1.format(last.arpac_usd)} (${last.isPartial ? 'ref. 2T26 parcial' : 'fechado'})`],
  ];
  document.getElementById('growth-insights').innerHTML = insights.map(([label, value, note]) => `
    <div class="insight"><span>${label}</span><strong>${value}</strong><p>${note}</p></div>
  `).join('');
}

function renderProfitability(data, viewMode = currentView) {
  const f = getActiveFinancialSeries(data, viewMode);
  const x = f.map(r => r.xLabel);
  const income = values(f, 'net_income_usd_b');
  const colors = f.map(r => {
    if (r.net_income_usd_b < 0) return NEGATIVE;
    return r.isPartial ? PARTIAL_AMBER : POSITIVE;
  });
  const patterns = f.map(r => (r.isPartial ? '/' : ''));

  safePlot('chart-income', [{
    type: 'bar',
    x,
    y: income,
    marker: {
      color: colors,
      pattern: { shape: patterns },
    },
    text: income.map(v => usdB(v)),
    textposition: 'outside',
    cliponaxis: false,
    hovertemplate: '<b>%{x}</b><br>Lucro líquido IFRS: US$ %{y:.2f} bi<extra></extra>',
  }], layout({ showlegend: false, yaxis: { title: 'US$ bilhões', gridcolor: GRID, zerolinecolor: '#BEB6C2' } }));

  const grossMargin = f.map(row => (row.gross_profit_usd_b != null && row.revenue_usd_b ? (row.gross_profit_usd_b / row.revenue_usd_b) * 100 : null));
  const netMargin = f.map(row => (row.net_income_usd_b != null && row.revenue_usd_b ? (row.net_income_usd_b / row.revenue_usd_b) * 100 : null));
  const traces = [];
  if (grossMargin.some(v => v != null)) {
    traces.push({
      type: 'scatter',
      mode: 'lines+markers',
      x,
      y: grossMargin,
      name: 'Margem bruta',
      connectgaps: false,
      line: { color: PURPLE, width: 4 },
      marker: { size: 8 },
      hovertemplate: '<b>%{x}</b><br>Margem bruta: %{y:.1f}%<extra></extra>',
    });
  }
  traces.push({
    type: 'scatter',
    mode: 'lines+markers',
    x,
    y: netMargin,
    name: 'Margem líquida IFRS',
    line: { color: PURPLE_DARK, width: 3 },
    marker: {
      size: f.map(r => (r.isPartial ? 11 : 8)),
      symbol: f.map(r => (r.isPartial ? 'diamond' : 'circle')),
    },
    hovertemplate: '<b>%{x}</b><br>Margem líquida IFRS: %{y:.1f}%<extra></extra>',
  });

  safePlot('chart-margins', traces, layout({ yaxis: { title: '% da receita', ticksuffix: '%', gridcolor: GRID, zerolinecolor: '#BEB6C2' } }));

  const latest = f[f.length - 1];
  const m26 = data.metrics_2026;
  if (m26) {
    document.getElementById('profit-insight').innerHTML =
      `<strong>Leitura de rentabilidade (2021–2026*):</strong> o lucro líquido IFRS tornou-se positivo em <b>2023</b>, fechou <b>2025</b> em <b>${usdB(2.8717)}</b> (20-F) e atingiu <b>${usdB(m26.ltm.net_income_usd_b)}</b> em <b>${m26.ltm.label}</b> (ou <b>${usdB(m26.ytd_comparison.net_income_2026_usd_b)}</b> no acumulado parcial <b>${m26.ytd_comparison.label_2026}</b> vs. <b>${usdB(m26.ytd_comparison.net_income_2025_usd_b)}</b> no <b>${m26.ytd_comparison.label_2025}</b>, alta de <b>+${fmt1.format(m26.ytd_comparison.net_income_yoy_pct)}%</b>).`;
  } else {
    document.getElementById('profit-insight').innerHTML =
      `<strong>Ponto de inflexão:</strong> o lucro líquido IFRS alcança <b>${usdB(latest.net_income_usd_b)}</b> em ${latest.xLabel}.`;
  }
}

function renderRisk(data) {
  const risk = data.risk.filter(row => row.period);
  document.getElementById('risk-source').textContent = data.meta.risk_source || 'Pilar 3 · dados regulatórios locais';
  const x = risk.map(row => row.period);

  safePlot('chart-capital', [
    {
      type: 'scatter', mode: 'lines+markers', x, y: values(risk, 'capital_principal_brl_b'), name: 'Capital Principal',
      connectgaps: false, line: { color: PURPLE, width: 4 }, marker: { size: 7 },
      hovertemplate: '<b>%{x|%m/%Y}</b><br>Capital Principal: R$ %{y:.1f} bi<extra></extra>',
    },
    {
      type: 'scatter', mode: 'lines+markers', x, y: values(risk, 'rwa_total_brl_b'), name: 'RWA total',
      connectgaps: false, line: { color: PURPLE_DARK, width: 3 }, marker: { size: 7 },
      hovertemplate: '<b>%{x|%m/%Y}</b><br>RWA total: R$ %{y:.1f} bi<extra></extra>',
    },
  ], layout({ yaxis: { title: 'R$ bilhões', gridcolor: GRID }, xaxis: { gridcolor: GRID, type: 'date' } }));

  safePlot('chart-prudential', [
    {
      type: 'scatter', mode: 'lines+markers', x, y: values(risk, 'basel_index_pct'), name: 'Índice de Basileia',
      connectgaps: false, line: { color: PURPLE, width: 4 }, marker: { size: 7 },
      hovertemplate: '<b>%{x|%m/%Y}</b><br>Basileia: %{y:.2f}%<extra></extra>',
    },
    {
      type: 'scatter', mode: 'lines+markers', x, y: values(risk, 'icp_pct'), name: 'ICP',
      connectgaps: false, line: { color: PURPLE_SOFT, width: 3, dash: 'dot' }, marker: { size: 7 },
      hovertemplate: '<b>%{x|%m/%Y}</b><br>ICP: %{y:.2f}%<extra></extra>',
    },
  ], layout({ yaxis: { title: '%', ticksuffix: '%', gridcolor: GRID }, xaxis: { gridcolor: GRID, type: 'date' } }));

  const detail = Array.isArray(data.risk_detail_by_period) && data.risk_detail_by_period.length
    ? data.risk_detail_by_period
    : data.risk_2025;
  const xDetail = detail.map(r => r.trimestre || r.quarter);

  safePlot('chart-credit-risk', [{
    type: 'bar', x: xDetail, y: values(detail, 'rwa_credito_brl_b'),
    marker: { color: PURPLE }, text: values(detail, 'rwa_credito_brl_b').map(v => `R$ ${fmt1.format(v)} bi`), textposition: 'outside',
    hovertemplate: '<b>%{x}</b><br>RWA crédito: R$ %{y:.1f} bi<extra></extra>',
  }], layout({ showlegend: false, yaxis: { title: 'R$ bilhões', gridcolor: GRID } }));

  safePlot('chart-market-risk', [
    {
      type: 'bar', x: xDetail, y: values(detail, 'rwa_juros_brl_m'), name: 'Juros', marker: { color: PURPLE_MID },
      hovertemplate: '<b>%{x}</b><br>Juros: R$ %{y:.1f} mi<extra></extra>',
    },
    {
      type: 'bar', x: xDetail, y: values(detail, 'rwa_cambio_brl_m'), name: 'Câmbio', marker: { color: '#D8AFE9' },
      hovertemplate: '<b>%{x}</b><br>Câmbio: R$ %{y:.1f} mi<extra></extra>',
    },
  ], layout({ barmode: 'group', yaxis: { title: 'R$ milhões', gridcolor: GRID } }));

  if (detail.length >= 2) {
    const latest = detail[detail.length - 1];
    const qLabel = latest.trimestre || latest.quarter;
    document.getElementById('risk-insight').innerHTML =
      `<strong>Último trimestre prudencial disponível (${qLabel}):</strong> Índice de Basileia de <b>${fmt2.format(latest.basel_index_pct)}%</b>, Capital Principal de <b>R$ ${fmt2.format(latest.capital_principal_brl_b)} bi</b> e RWA total de <b>R$ ${fmt1.format(latest.rwa_total_brl_b)} bi</b>. Valores mantidos em R$ conforme divulgação do Pilar 3/BCB.`;
  }
}

function renderCustomer(data) {
  const c = data.customer;
  const bcb = Array.isArray(c.bcb_ranking) ? c.bcb_ranking : (data.bcb_complaints_ranking || []);

  if (c.official_source_label) {
    setNodeText('bcb-complaints-source', c.official_source_label);
  }

  if (bcb.length) {
    const latestPeriod = c.official_latest_period || bcb[bcb.length - 1].periodo;
    const latestRows = bcb.filter(r => r.periodo === latestPeriod);

    const findInst = namePart => latestRows.find(r => String(r.instituicao).includes(namePart));
    const nuRow = findInst('Nu');
    const itauRow = findInst('Itaú');
    const bradRow = findInst('Bradesco');

    if (nuRow) {
      setNodeText('bcb-card-nu-label', `Nu Pagamentos · ${latestPeriod}* (parcial)`);
      setNodeText('bcb-card-nu', fmt2.format(nuRow.indice));
      setNodeText('bcb-card-nu-note', `${fmt0.format(nuRow.procedentes || 0)} procedentes / ${fmt1.format((nuRow.clientes || 0) / 1e6)} mi clientes`);
    }
    if (itauRow) {
      setNodeText('bcb-card-itau-label', `Itaú · ${latestPeriod}* (parcial)`);
      setNodeText('bcb-card-itau', fmt2.format(itauRow.indice));
      setNodeText('bcb-card-itau-note', `${fmt0.format(itauRow.procedentes || 0)} procedentes / ${fmt1.format((itauRow.clientes || 0) / 1e6)} mi clientes`);
    }
    if (bradRow) {
      setNodeText('bcb-card-bradesco-label', `Bradesco · ${latestPeriod}* (parcial)`);
      setNodeText('bcb-card-bradesco', fmt2.format(bradRow.indice));
      setNodeText('bcb-card-bradesco-note', `${fmt0.format(bradRow.procedentes || 0)} procedentes / ${fmt1.format((bradRow.clientes || 0) / 1e6)} mi clientes`);
    }

    const instStyles = [
      { name: 'Nu Pagamentos (Nubank)', color: PURPLE, width: 4 },
      { name: 'Itaú', color: '#FF6B00', width: 3 },
      { name: 'Bradesco', color: '#CC092F', width: 3 },
    ];

    const indexTraces = instStyles.map(st => {
      const rows = bcb.filter(r => r.instituicao === st.name);
      return {
        type: 'scatter',
        mode: 'lines+markers',
        name: st.name,
        x: rows.map(r => (r.parcial_2026 === 'sim' ? `${r.periodo}*` : r.periodo)),
        y: rows.map(r => r.indice),
        line: { color: st.color, width: st.width },
        marker: {
          size: rows.map(r => (r.parcial_2026 === 'sim' ? 10 : 7)),
          symbol: rows.map(r => (r.parcial_2026 === 'sim' ? 'diamond' : 'circle')),
        },
        hovertemplate: `<b>${st.name}</b> · %{x}<br>Índice BCB: %{y:.2f} / milhão de clientes<extra></extra>`,
      };
    });

    safePlot('chart-bcb-index', indexTraces, layout({
      yaxis: { title: 'Índice (reclamações / 1 mi clientes)', gridcolor: GRID },
    }));

    safePlot('chart-bcb-latest', [
      {
        type: 'bar',
        name: `Reclamações procedentes (${latestPeriod}*)`,
        x: latestRows.map(r => r.instituicao),
        y: latestRows.map(r => r.procedentes),
        marker: {
          color: latestRows.map(r => (String(r.instituicao).includes('Nu') ? PURPLE : (String(r.instituicao).includes('Itaú') ? '#FF6B00' : '#CC092F'))),
          pattern: { shape: '/' },
        },
        text: latestRows.map(r => (r.procedentes != null ? fmt0.format(r.procedentes) : '—')),
        textposition: 'outside',
        hovertemplate: '<b>%{x}</b><br>Procedentes: %{y:,.0f}<extra></extra>',
      },
    ], layout({
      showlegend: false,
      yaxis: { title: `Reclamações procedentes (${latestPeriod}*)`, gridcolor: GRID },
    }));
  }

  document.getElementById('customer-total').textContent = fmt0.format(c.total);
  document.getElementById('customer-loss').textContent = c.loss_share_pct == null ? '—' : pct(c.loss_share_pct);
  document.getElementById('customer-security').textContent = c.security_signals == null ? '—' : fmt0.format(c.security_signals);

  const categories = [...c.categories].sort((a, b) => a.reclamacoes - b.reclamacoes);
  safePlot('chart-categories', [{
    type: 'bar', orientation: 'h', x: values(categories, 'reclamacoes'), y: values(categories, 'categoria'),
    marker: { color: PURPLE }, text: values(categories, 'reclamacoes'), textposition: 'outside', cliponaxis: false,
    hovertemplate: '<b>%{y}</b><br>%{x} reclamações<extra></extra>',
  }], layout({ showlegend: false, margin: { l: 150, r: 38, t: 22, b: 45 }, xaxis: { title: 'Reclamações', gridcolor: GRID } }));

  safePlot('chart-severity', [{
    type: 'pie', labels: values(c.severity, 'severidade'), values: values(c.severity, 'reclamacoes'), hole: .58,
    marker: { colors: [PURPLE_DARK, PURPLE, PURPLE_SOFT, '#E9D9F1'] }, textinfo: 'percent',
    hovertemplate: '<b>%{label}</b><br>%{value} reclamações · %{percent}<extra></extra>',
  }], layout({ margin: { l: 20, r: 20, t: 20, b: 35 }, legend: { orientation: 'h', x: 0, y: -.05 } }));

  safePlot('chart-clusters', [{
    type: 'bar', x: values(c.clusters, 'cluster').map(String), y: values(c.clusters, 'reclamacoes'),
    marker: { color: PURPLE_MID }, text: values(c.clusters, 'reclamacoes'), textposition: 'outside',
    hovertemplate: '<b>Cluster %{x}</b><br>%{y} reclamações<extra></extra>',
  }], layout({ showlegend: false, xaxis: { title: 'Cluster', gridcolor: GRID }, yaxis: { title: 'Reclamações', gridcolor: GRID } }));
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[char]));
}

const TICKER_COLORS = {
  NU: PURPLE,
  ITUB: '#FF6B00',
  'ITUB4.SA': '#FF6B00',
  BBD: '#CC092F',
  'BBDC4.SA': '#CC092F',
};

function renderMarket(data) {
  const market = Array.isArray(data.market) ? data.market : [];
  const filterWrap = document.getElementById('ticker-filter-options');
  const section = document.getElementById('mercado');
  if (!filterWrap || !section) return;

  if (!market.length) {
    filterWrap.innerHTML = '<span style="font-size:.82rem;color:#6f6673">Execute python ingestao.py para popular as cotações históricas.</span>';
    return;
  }

  const tickers = [...new Set(market.map(r => r.ticker).filter(Boolean))].sort();
  const selected = new Set(tickers);

  function updateMarketCharts() {
    const activeTickers = tickers.filter(t => selected.has(t));
    const closeTraces = [];
    const normTraces = [];
    const volTraces = [];

    for (const ticker of activeTickers) {
      const rows = market
        .filter(r => r.ticker === ticker && r.datetime && r.close != null)
        .sort((a, b) => String(a.datetime).localeCompare(String(b.datetime)));
      if (!rows.length) continue;

      const x = rows.map(r => r.datetime);
      const yClose = rows.map(r => Number(r.close));
      const firstClose = yClose[0] || 1;
      const yNorm = yClose.map(v => (v / firstClose) * 100);
      const yVol = rows.map(r => Number(r.volume || 0));
      const color = TICKER_COLORS[ticker] || PURPLE_MID;

      closeTraces.push({
        type: 'scatter',
        mode: 'lines',
        name: ticker,
        x,
        y: yClose,
        line: { color, width: 2.5 },
        hovertemplate: `<b>${escapeHtml(ticker)}</b> · %{x}<br>Fechamento: US$ %{y:.2f}<extra></extra>`,
      });

      normTraces.push({
        type: 'scatter',
        mode: 'lines',
        name: ticker,
        x,
        y: yNorm,
        line: { color, width: 2.5 },
        hovertemplate: `<b>${escapeHtml(ticker)}</b> · %{x}<br>Índice: %{y:.1f} (Base 100)<extra></extra>`,
      });

      volTraces.push({
        type: 'scatter',
        mode: 'lines',
        name: ticker,
        x,
        y: yVol,
        line: { color, width: 1.8 },
        hovertemplate: `<b>${escapeHtml(ticker)}</b> · %{x}<br>Volume: %{y:,.0f}<extra></extra>`,
      });
    }

    safePlot('chart-market-close', closeTraces, layout({
      yaxis: { title: 'US$ (Fechamento)', gridcolor: GRID },
      xaxis: { type: 'date', gridcolor: GRID },
    }));

    safePlot('chart-market-norm', normTraces, layout({
      yaxis: { title: 'Índice (Base 100)', gridcolor: GRID },
      xaxis: { type: 'date', gridcolor: GRID },
    }));

    safePlot('chart-market-volume', volTraces, layout({
      yaxis: { title: 'Volume diário', gridcolor: GRID },
      xaxis: { type: 'date', gridcolor: GRID },
    }));
  }

  filterWrap.innerHTML = tickers.map(t => `
    <label class="ticker-chip active">
      <input type="checkbox" value="${escapeHtml(t)}" checked>
      <span>${escapeHtml(t)}</span>
    </label>
  `).join('');

  filterWrap.querySelectorAll('input[type="checkbox"]').forEach(input => {
    input.addEventListener('change', e => {
      const val = e.target.value;
      const chip = e.target.closest('.ticker-chip');
      if (e.target.checked) {
        selected.add(val);
        if (chip) chip.classList.add('active');
      } else {
        selected.delete(val);
        if (chip) chip.classList.remove('active');
      }
      updateMarketCharts();
    });
  });

  updateMarketCharts();
}

function renderSources(data) {
  const body = document.getElementById('source-table');
  body.innerHTML = data.sources.map(row => `
    <tr>
      <td><strong>${escapeHtml(row.dataset)}</strong></td>
      <td>${escapeHtml(row.period)}</td>
      <td>${escapeHtml(row.source_type)}</td>
      <td>${escapeHtml(row.source)}</td>
    </tr>
  `).join('');
}

function setupViewSelector(data) {
  const buttons = document.querySelectorAll('.view-btn[data-view]');
  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      const nextView = btn.getAttribute('data-view');
      if (!nextView) return;
      currentView = nextView;
      buttons.forEach(b => {
        const isActive = b === btn;
        b.classList.toggle('active', isActive);
        b.setAttribute('aria-selected', isActive ? 'true' : 'false');
      });
      renderHeadline(data, currentView);
      renderGrowth(data, currentView);
      renderProfitability(data, currentView);
    });
  });
}

async function init() {
  try {
    const response = await fetch('data/dashboard-data.json', { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    dashboardPayload = data;

    setupViewSelector(data);
    renderHeadline(data, currentView);
    renderMarket(data);
    renderGrowth(data, currentView);
    renderProfitability(data, currentView);
    renderRisk(data);
    renderCustomer(data);
    renderSources(data);
  } catch (error) {
    console.error('Falha ao carregar dashboard:', error);
    document.getElementById('load-error').hidden = false;
  }
}

document.addEventListener('DOMContentLoaded', init);
