from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from src.data_pipeline import (
    customer_summary,
    load_capital_risk_history,
    load_customer_sample,
    load_financial_history,
)


st.set_page_config(
    page_title="Nubank em Dados | 2021–2025",
    page_icon="N",
    layout="wide",
    initial_sidebar_state="expanded",
)

NU_PURPLE = "#820AD1"
NU_DARK = "#2F0549"
NU_MID = "#6B16A8"
NU_LIGHT = "#F7F2FA"
TEXT = "#17131A"
MUTED = "#6F6673"
GRID = "#ECE7EF"
POSITIVE = "#157A54"
NEGATIVE = "#B42318"

st.markdown(
    f"""
    <style>
        .stApp {{ background: #FCFBFD; color: {TEXT}; }}
        .block-container {{ max-width: 1320px; padding-top: 1.7rem; padding-bottom: 4rem; }}
        [data-testid="stSidebar"] {{ background: #F6F2F8; border-right: 1px solid #E8DFEC; }}
        h1, h2, h3 {{ letter-spacing: -0.035em; color: {TEXT}; }}
        .hero {{
            background: linear-gradient(118deg, #250038 0%, {NU_DARK} 46%, {NU_PURPLE} 100%);
            border-radius: 26px;
            padding: 2.4rem 2.6rem;
            color: white;
            margin-bottom: 1rem;
            box-shadow: 0 18px 50px rgba(47, 5, 73, .16);
        }}
        .hero .kicker {{ font-size: .76rem; font-weight: 750; letter-spacing: .16em; text-transform: uppercase; opacity: .72; }}
        .hero h1 {{ color: white; font-size: 2.65rem; margin: .35rem 0 .55rem 0; line-height: 1.03; }}
        .hero p {{ color: rgba(255,255,255,.82); font-size: 1.05rem; max-width: 900px; margin: 0; line-height: 1.55; }}
        .metric-card {{
            background: white; border: 1px solid #E9E1ED; border-radius: 18px;
            padding: 1.15rem 1.2rem; min-height: 128px;
            box-shadow: 0 8px 28px rgba(31, 12, 39, .045);
        }}
        .metric-label {{ color: {MUTED}; font-size: .76rem; letter-spacing: .075em; text-transform: uppercase; font-weight: 720; }}
        .metric-value {{ color: {NU_DARK}; font-size: 1.85rem; font-weight: 820; margin: .25rem 0 .15rem; letter-spacing: -.04em; }}
        .metric-note {{ color: {MUTED}; font-size: .82rem; line-height: 1.35; }}
        .insight {{
            background: white; border: 1px solid #E9E1ED; border-left: 4px solid {NU_PURPLE};
            border-radius: 9px 15px 15px 9px; padding: .95rem 1.05rem; margin: .55rem 0;
            line-height: 1.45;
        }}
        .insight b {{ color: {NU_DARK}; }}
        .section-note {{ color: {MUTED}; font-size: .88rem; line-height: 1.5; }}
        .source-chip {{ display:inline-block; background:#F1E7F6; color:{NU_DARK}; padding:.25rem .55rem; border-radius:999px; font-size:.75rem; font-weight:700; }}
        div[data-testid="stTabs"] button {{ font-weight: 700; }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600, show_spinner=False)
def get_data():
    financial = load_financial_history()
    risk, risk_source = load_capital_risk_history()
    complaints, complaints_source = load_customer_sample()
    return financial, risk, risk_source, complaints, complaints_source


financial, risk, risk_source, complaints, complaints_source = get_data()

st.sidebar.markdown("### Período da análise")
year_min, year_max = int(financial.year.min()), int(financial.year.max())
years = st.sidebar.slider("Anos", year_min, year_max, (year_min, year_max))
start_year, end_year = years
fin = financial[financial.year.between(start_year, end_year)].copy()

st.sidebar.markdown("---")
st.sidebar.markdown("### Escopo")
st.sidebar.caption(
    "A série financeira usa divulgações oficiais da Nu/SEC. A camada regulatória usa dados Pilar 3. "
    "Reclamações são uma amostra acadêmica complementar e não uma série temporal comparável."
)

st.markdown(
    """
    <div class="hero">
      <div class="kicker">Projeto de portfólio · Ciência de Dados & Analytics</div>
      <h1>Nubank em Dados</h1>
      <p>Crescimento, monetização, rentabilidade e risco entre 2021 e 2025 — uma leitura integrada de métricas financeiras oficiais, capital regulatório e sinais da experiência do cliente.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

latest = fin.iloc[-1]
first = fin.iloc[0]


def pct_change(new: float, old: float) -> float:
    return (new / old - 1) * 100


def metric_card(label: str, value: str, note: str) -> str:
    return f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-note'>{note}</div></div>"


cols = st.columns(4)
card_data = [
    ("Clientes", f"{latest.customers_m:.1f} mi", f"{pct_change(latest.customers_m, first.customers_m):+.0f}% desde {int(first.year)}"),
    ("Receita anual", f"US$ {latest.revenue_usd_b:.2f} bi", f"{latest.revenue_usd_b / first.revenue_usd_b:.1f}× o nível de {int(first.year)}"),
    ("Lucro líquido", f"US$ {latest.net_income_usd_b:.2f} bi", "IFRS · valor anual reportado"),
    ("Depósitos", f"US$ {latest.deposits_usd_b:.1f} bi", f"{latest.deposits_usd_b / first.deposits_usd_b:.1f}× o nível de {int(first.year)}"),
]
for col, values in zip(cols, card_data):
    col.markdown(metric_card(*values), unsafe_allow_html=True)

st.caption(f"Indicadores do último ano selecionado: {int(latest.year)}. Valores financeiros em US$, salvo indicação em contrário.")

tab_overview, tab_profit, tab_risk, tab_customer, tab_method = st.tabs(
    ["Visão geral", "Rentabilidade e eficiência", "Capital e risco", "Experiência do cliente", "Metodologia"]
)

with tab_overview:
    st.markdown("## Crescimento que se converteu em monetização")
    st.markdown(
        "<div class='section-note'>A leitura conjunta evita confundir expansão de base com criação de valor: clientes, receita, depósitos e ARPAC são acompanhados lado a lado.</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)
    with left:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=fin.year, y=fin.revenue_usd_b, name="Receita", marker_color=NU_PURPLE))
        fig.add_trace(go.Scatter(x=fin.year, y=fin.net_income_usd_b, name="Lucro líquido", mode="lines+markers", line=dict(color=NU_DARK, width=3), marker=dict(size=9)))
        fig.add_hline(y=0, line_width=1, line_color="#999")
        fig.update_layout(
            title="Receita e lucro líquido",
            yaxis_title="US$ bilhões",
            xaxis_title="",
            template="plotly_white",
            legend=dict(orientation="h", y=1.08, x=0),
            height=420,
            margin=dict(l=20, r=20, t=75, b=20),
        )
        fig.update_xaxes(dtick=1, gridcolor=GRID)
        fig.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=fin.year, y=fin.customers_m, mode="lines+markers", name="Clientes", line=dict(color=NU_PURPLE, width=4)), secondary_y=False)
        fig.add_trace(go.Bar(x=fin.year, y=fin.deposits_usd_b, name="Depósitos", marker_color="#C89BE5", opacity=.72), secondary_y=True)
        fig.update_layout(
            title="Escala da base e depósitos",
            template="plotly_white",
            legend=dict(orientation="h", y=1.08, x=0),
            height=420,
            margin=dict(l=20, r=20, t=75, b=20),
        )
        fig.update_xaxes(dtick=1, gridcolor=GRID)
        fig.update_yaxes(title_text="Clientes (milhões)", gridcolor=GRID, secondary_y=False)
        fig.update_yaxes(title_text="Depósitos (US$ bi)", gridcolor=GRID, secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns([1.1, .9])
    with left:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=fin.year, y=fin.arpac_usd, name="ARPAC mensal", mode="lines+markers", line=dict(color=NU_PURPLE, width=4), marker=dict(size=9)))
        fig.add_trace(go.Scatter(x=fin.year, y=fin.cost_to_serve_usd, name="Custo mensal por cliente ativo", mode="lines+markers", line=dict(color="#777", width=3, dash="dot"), marker=dict(size=8)))
        fig.update_layout(title="Monetização por cliente vs. custo de servir", yaxis_title="US$ por cliente ativo / mês", xaxis_title="", template="plotly_white", height=390, legend=dict(orientation="h", y=1.08, x=0), margin=dict(l=20, r=20, t=75, b=20))
        fig.update_xaxes(dtick=1, gridcolor=GRID)
        fig.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        revenue_multiple = latest.revenue_usd_b / first.revenue_usd_b
        customer_multiple = latest.customers_m / first.customers_m
        arpac_growth = pct_change(latest.arpac_usd, first.arpac_usd)
        st.markdown("### Leitura do período")
        st.markdown(f"<div class='insight'><b>Receita:</b> avançou de US$ {first.revenue_usd_b:.2f} bi para US$ {latest.revenue_usd_b:.2f} bi — {revenue_multiple:.1f}×.</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='insight'><b>Escala:</b> a base passou de {first.customers_m:.1f} mi para {latest.customers_m:.1f} mi de clientes — {customer_multiple:.1f}×.</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='insight'><b>Monetização:</b> o ARPAC mensal cresceu {arpac_growth:.0f}%, enquanto o custo de servir permaneceu próximo de US$ {latest.cost_to_serve_usd:.1f}.</div>", unsafe_allow_html=True)

    portfolio = fin.dropna(subset=["credit_portfolio_usd_b"])
    if not portfolio.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=portfolio.year, y=portfolio.credit_portfolio_usd_b, name="Cartão + empréstimos pessoais", marker_color=NU_PURPLE))
        fig.add_trace(go.Bar(x=portfolio.year, y=portfolio.interest_earning_portfolio_usd_b, name="Carteira geradora de juros", marker_color="#D9B9ED"))
        fig.update_layout(title="Expansão das carteiras de crédito", barmode="group", yaxis_title="US$ bilhões", xaxis_title="", template="plotly_white", height=390, legend=dict(orientation="h", y=1.08, x=0), margin=dict(l=20, r=20, t=75, b=20))
        fig.update_xaxes(dtick=1, gridcolor=GRID)
        fig.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fig, use_container_width=True)

with tab_profit:
    st.markdown("## Da perda à rentabilidade")
    prof = fin.copy()
    prof["gross_margin_pct"] = prof.gross_profit_usd_b / prof.revenue_usd_b * 100
    prof["net_margin_pct"] = prof.net_income_usd_b / prof.revenue_usd_b * 100

    left, right = st.columns(2)
    with left:
        fig = go.Figure()
        colors = [NEGATIVE if value < 0 else POSITIVE for value in prof.net_income_usd_b]
        fig.add_trace(go.Bar(x=prof.year, y=prof.net_income_usd_b, marker_color=colors, text=[f"US$ {v:.2f} bi" for v in prof.net_income_usd_b], textposition="outside", name="Lucro líquido"))
        fig.add_hline(y=0, line_width=1, line_color="#999")
        fig.update_layout(title="Lucro líquido anual", yaxis_title="US$ bilhões", xaxis_title="", template="plotly_white", height=420, showlegend=False, margin=dict(l=20, r=20, t=65, b=20))
        fig.update_xaxes(dtick=1, gridcolor=GRID)
        fig.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=prof.year, y=prof.gross_margin_pct, name="Margem bruta", mode="lines+markers", line=dict(color=NU_PURPLE, width=4)))
        fig.add_trace(go.Scatter(x=prof.year, y=prof.net_margin_pct, name="Margem líquida", mode="lines+markers", line=dict(color=NU_DARK, width=3)))
        fig.add_hline(y=0, line_width=1, line_color="#999")
        fig.update_layout(title="Margens implícitas nos resultados IFRS", yaxis_title="% da receita", xaxis_title="", template="plotly_white", height=420, legend=dict(orientation="h", y=1.08, x=0), margin=dict(l=20, r=20, t=75, b=20))
        fig.update_xaxes(dtick=1, gridcolor=GRID)
        fig.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fig, use_container_width=True)

    positive_years = prof.loc[prof.net_income_usd_b > 0, "year"]
    turn_year = int(positive_years.iloc[0]) if not positive_years.empty else None
    if turn_year:
        st.markdown(f"<div class='insight'><b>Ponto de inflexão:</b> na série selecionada, o lucro líquido reportado passa ao campo positivo em {turn_year} e alcança US$ {latest.net_income_usd_b:.2f} bi em {int(latest.year)}.</div>", unsafe_allow_html=True)

    adjusted = prof.dropna(subset=["adjusted_net_income_usd_b"])
    if not adjusted.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=adjusted.year, y=adjusted.net_income_usd_b, mode="lines+markers", name="IFRS", line=dict(color=NU_DARK, width=3)))
        fig.add_trace(go.Scatter(x=adjusted.year, y=adjusted.adjusted_net_income_usd_b, mode="lines+markers", name="Ajustado (não IFRS)", line=dict(color=NU_PURPLE, width=3, dash="dot")))
        fig.add_hline(y=0, line_width=1, line_color="#999")
        fig.update_layout(title="Lucro reportado vs. lucro ajustado divulgado", yaxis_title="US$ bilhões", xaxis_title="", template="plotly_white", height=380, legend=dict(orientation="h", y=1.08, x=0), margin=dict(l=20, r=20, t=75, b=20))
        fig.update_xaxes(dtick=1, gridcolor=GRID)
        fig.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("O lucro ajustado é uma métrica não IFRS divulgada pela companhia; o lucro líquido IFRS permanece a referência contábil principal.")

with tab_risk:
    st.markdown("## Capital regulatório e absorção de risco")
    st.markdown(f"<span class='source-chip'>{risk_source}</span>", unsafe_allow_html=True)

    risk_filtered = risk.copy()
    if "year" in risk_filtered:
        risk_filtered = risk_filtered[risk_filtered.year.between(start_year, end_year)]

    if risk_filtered.empty:
        st.info("Não há observações regulatórias disponíveis no intervalo selecionado.")
    else:
        left, right = st.columns(2)
        with left:
            if {"capital_principal_brl_b", "rwa_total_brl_b"}.intersection(risk_filtered.columns):
                fig = go.Figure()
                if "capital_principal_brl_b" in risk_filtered:
                    fig.add_trace(go.Scatter(x=risk_filtered.period, y=risk_filtered.capital_principal_brl_b, mode="lines+markers", name="Capital Principal", line=dict(color=NU_PURPLE, width=4)))
                if "rwa_total_brl_b" in risk_filtered:
                    fig.add_trace(go.Scatter(x=risk_filtered.period, y=risk_filtered.rwa_total_brl_b, mode="lines+markers", name="RWA total", line=dict(color=NU_DARK, width=3)))
                fig.update_layout(title="Capital Principal e RWA", yaxis_title="R$ bilhões", xaxis_title="", template="plotly_white", height=420, legend=dict(orientation="h", y=1.08, x=0), margin=dict(l=20, r=20, t=75, b=20))
                fig.update_yaxes(gridcolor=GRID)
                st.plotly_chart(fig, use_container_width=True)

        with right:
            if {"basel_index_pct", "icp_pct"}.intersection(risk_filtered.columns):
                fig = go.Figure()
                if "basel_index_pct" in risk_filtered:
                    fig.add_trace(go.Scatter(x=risk_filtered.period, y=risk_filtered.basel_index_pct, mode="lines+markers", name="Índice de Basileia", line=dict(color=NU_PURPLE, width=4)))
                if "icp_pct" in risk_filtered:
                    fig.add_trace(go.Scatter(x=risk_filtered.period, y=risk_filtered.icp_pct, mode="lines+markers", name="ICP", line=dict(color="#A26AC5", width=3, dash="dot")))
                fig.update_layout(title="Índices prudenciais", yaxis_title="%", xaxis_title="", template="plotly_white", height=420, legend=dict(orientation="h", y=1.08, x=0), margin=dict(l=20, r=20, t=75, b=20))
                fig.update_yaxes(gridcolor=GRID)
                st.plotly_chart(fig, use_container_width=True)

        latest_risk = risk_filtered.sort_values("period").iloc[-1]
        if "basel_index_pct" in latest_risk and pd.notna(latest_risk.get("basel_index_pct")):
            st.markdown(f"<div class='insight'><b>Última observação regulatória disponível:</b> Índice de Basileia de {latest_risk['basel_index_pct']:.2f}% e RWA total de R$ {latest_risk.get('rwa_total_brl_b', float('nan')):.1f} bi em {pd.to_datetime(latest_risk['period']).strftime('%m/%Y')}.</div>", unsafe_allow_html=True)

    detail_path = Path(__file__).parent / "data" / "processed" / "risk_2025_detail.csv"
    detail = pd.read_csv(detail_path)
    st.markdown("### Decomposição de risco em 2025")
    left, right = st.columns(2)
    with left:
        fig = px.bar(detail, x="quarter", y="rwa_credito_brl_b", text="rwa_credito_brl_b", labels={"quarter": "", "rwa_credito_brl_b": "R$ bilhões"}, title="RWA de crédito", color_discrete_sequence=[NU_PURPLE])
        fig.update_traces(texttemplate="R$ %{text:.1f} bi", textposition="outside")
        fig.update_layout(template="plotly_white", height=360, margin=dict(l=20, r=20, t=60, b=20))
        fig.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        market = detail[["quarter", "rwa_juros_brl_m", "rwa_cambio_brl_m"]].melt("quarter", var_name="tipo", value_name="valor")
        market["tipo"] = market["tipo"].map({"rwa_juros_brl_m": "Juros", "rwa_cambio_brl_m": "Câmbio"})
        fig = px.bar(market, x="quarter", y="valor", color="tipo", barmode="group", labels={"quarter": "", "valor": "R$ milhões", "tipo": "Risco"}, title="RWA de mercado: juros e câmbio", color_discrete_map={"Juros": NU_MID, "Câmbio": "#D8AFE9"})
        fig.update_layout(template="plotly_white", height=360, legend=dict(orientation="h", y=1.08, x=0), margin=dict(l=20, r=20, t=70, b=20))
        fig.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fig, use_container_width=True)

    fx_multiple = detail.iloc[-1].rwa_cambio_brl_m / detail.iloc[-2].rwa_cambio_brl_m
    st.markdown(f"<div class='insight'><b>Sinal para investigação:</b> no recorte Q1–Q3/2025 extraído do Pilar 3, o RWA cambial do Q3 é {fx_multiple:.1f}× o valor do Q2. O dashboard sinaliza a mudança; a explicação causal exige leitura das notas regulatórias e não é inferida automaticamente.</div>", unsafe_allow_html=True)

with tab_customer:
    st.markdown("## Sinais da experiência do cliente")
    st.markdown(
        "<div class='section-note'><b>Importante:</b> esta camada usa uma amostra acadêmica de reclamações públicas. Como a base disponível não contém uma dimensão temporal confiável e comparável, ela não é usada para afirmar evolução entre 2021 e 2025.</div>",
        unsafe_allow_html=True,
    )

    if complaints.empty:
        st.warning("A amostra remota de reclamações não pôde ser carregada nesta execução. As demais análises permanecem disponíveis.")
    else:
        summaries = customer_summary(complaints)
        c1, c2, c3 = st.columns(3)
        c1.metric("Reclamações na amostra", f"{len(complaints):,}".replace(",", "."))
        if "Perda_Financeira" in complaints:
            share = pd.to_numeric(complaints["Perda_Financeira"], errors="coerce").fillna(0).mean() * 100
            c2.metric("Marcadas com perda financeira", f"{share:.1f}%")
        if "Problema_Seguranca" in complaints:
            security = pd.to_numeric(complaints["Problema_Seguranca"], errors="coerce").fillna(0).sum()
            c3.metric("Sinais de segurança", f"{int(security)}")

        left, right = st.columns([1.15, .85])
        with left:
            categories = summaries["categories"].sort_values("reclamacoes", ascending=True)
            if not categories.empty:
                fig = px.bar(categories, x="reclamacoes", y="categoria", orientation="h", text="reclamacoes", title="Principais categorias da amostra", labels={"reclamacoes": "Reclamações", "categoria": ""}, color_discrete_sequence=[NU_PURPLE])
                fig.update_traces(textposition="outside")
                fig.update_layout(template="plotly_white", height=440, margin=dict(l=20, r=40, t=60, b=20))
                fig.update_xaxes(gridcolor=GRID)
                st.plotly_chart(fig, use_container_width=True)
        with right:
            severity = summaries["severity"]
            if not severity.empty:
                fig = px.pie(severity, values="reclamacoes", names="severidade", hole=.58, title="Severidade estimada", color_discrete_sequence=[NU_DARK, NU_PURPLE, "#C89BE5", "#E9D9F1"])
                fig.update_layout(template="plotly_white", height=440, margin=dict(l=20, r=20, t=60, b=20), legend=dict(orientation="h", y=-.08))
                st.plotly_chart(fig, use_container_width=True)

        clusters = summaries["clusters"]
        if not clusters.empty:
            fig = px.bar(clusters, x="cluster", y="reclamacoes", text="reclamacoes", title="Distribuição dos clusters do estudo acadêmico", labels={"cluster": "Cluster", "reclamacoes": "Reclamações"}, color_discrete_sequence=[NU_MID])
            fig.update_layout(template="plotly_white", height=330, margin=dict(l=20, r=20, t=60, b=20))
            fig.update_xaxes(dtick=1)
            fig.update_yaxes(gridcolor=GRID)
            st.plotly_chart(fig, use_container_width=True)

with tab_method:
    st.markdown("## Como o projeto foi construído")
    st.markdown(
        """
        O objetivo desta versão é transformar o trabalho acadêmico original em um produto analítico reproduzível e auditável. A apresentação visual é consequência da preparação dos dados — não a fonte dos números.

        **Fluxo principal**

        `divulgações oficiais / Pilar 3 → Python + Pandas → validação → SQLite + SQL → Streamlit`
        """
    )

    manifest = pd.read_csv(Path(__file__).parent / "data" / "source_manifest.csv")
    st.dataframe(manifest, use_container_width=True, hide_index=True)

    st.markdown("### Arquitetura")
    st.code(
        """data/
├── raw/pillar3/              # arquivos regulatórios baixados pelo pipeline
├── processed/
│   ├── financial_history.csv
│   └── risk_2025_detail.csv
├── source_manifest.csv
src/
├── data_pipeline.py          # carga, cache e padronização
├── ingest_pillar3.py         # reconstrução a partir dos XLSX brutos
├── build_database.py         # gera SQLite analítico
└── validate_data.py
sql/                          # consultas de negócio
app.py                        # produto Streamlit
""",
        language="text",
    )

    st.markdown("### Limites e decisões metodológicas")
    st.markdown(
        """
- Métricas financeiras anuais são reportadas em **US$** e preservam a unidade utilizada nas divulgações da companhia.
- Capital regulatório e RWA são apresentados em **R$**, seguindo os arquivos Pilar 3 usados no estudo original.
- Medidas ajustadas são identificadas como **não IFRS** e não substituem o lucro líquido IFRS.
- A base de reclamações é analisada apenas como **amostra transversal complementar**, sem extrapolação temporal.
- Mudanças anormais são sinalizadas para investigação; o dashboard não inventa causalidade onde a fonte não a fornece.
        """
    )

st.markdown("---")
st.caption("Projeto independente de portfólio. Não afiliado à Nu Holdings Ltd. Fontes e decisões metodológicas estão documentadas na aba Metodologia e no repositório.")
