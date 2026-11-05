from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import streamlit as st

from src.data_pipeline import (
    compute_metrics_2026,
    customer_summary,
    load_bcb_complaints_ranking,
    load_capital_risk_history,
    load_customer_sample,
    load_financial_history,
    load_financial_quarterly,
    load_risk_detail_by_period,
)


st.set_page_config(
    page_title="Nubank em Dados | 2021–2026*",
    page_icon="N",
    layout="wide",
    initial_sidebar_state="expanded",
)

NU_PURPLE = "#820AD1"
NU_DARK = "#2F0549"
NU_MID = "#6B16A8"
NU_LIGHT = "#F7F2FA"
PARTIAL_AMBER = "#C17200"
TEXT = "#17131A"
MUTED = "#6F6673"
GRID = "#ECE7EF"
POSITIVE = "#157A54"
NEGATIVE = "#B42318"
TICKER_COLORS = {
    "NU": NU_PURPLE,
    "ITUB": "#FF6B00",
    "ITUB4.SA": "#FF6B00",
    "BBD": "#CC092F",
    "BBDC4.SA": "#CC092F",
}

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
        .partial-banner {{
            background: #FFF4E5; border: 1px solid #F5D4A3; border-left: 4px solid {PARTIAL_AMBER};
            border-radius: 12px; padding: .85rem 1.1rem; margin: .7rem 0 1rem; color: #5C3400; font-size: .88rem;
        }}
        .section-note {{ color: {MUTED}; font-size: .88rem; line-height: 1.5; }}
        .source-chip {{ display:inline-block; background:#F1E7F6; color:{NU_DARK}; padding:.25rem .55rem; border-radius:999px; font-size:.75rem; font-weight:700; }}
        div[data-testid="stTabs"] button {{ font-weight: 700; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def _resolve_mongo_uri() -> str | None:
    root_env = Path(__file__).resolve().parent / ".env"
    parent_env = Path(__file__).resolve().parents[1] / ".env"
    if root_env.exists():
        load_dotenv(dotenv_path=root_env)
    elif parent_env.exists():
        load_dotenv(dotenv_path=parent_env)
    else:
        load_dotenv()

    mongo_uri = os.getenv("MONGO_URI")
    if mongo_uri:
        return mongo_uri

    try:
        if "MONGO_URI" in st.secrets:
            return str(st.secrets["MONGO_URI"])
    except Exception:
        pass
    return None


def _configure_dns() -> None:
    """Configura DNS público (8.8.8.8 / 1.1.1.1) no dnspython para evitar ConfigurationError do 127.0.0.53 em URIs mongodb+srv://."""
    try:
        import dns.resolver

        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = ["8.8.8.8", "1.1.1.1", "8.8.4.4"]
        resolver.timeout = 1.5
        resolver.lifetime = 3.0
        dns.resolver.default_resolver = resolver
    except Exception:
        pass


@st.cache_data(ttl=600, show_spinner=False)
def load_historico_diario() -> tuple[pd.DataFrame, str | None]:
    """Conecta ao MongoDB via MONGO_URI e extrai todos os documentos de historico_diario."""
    fallback_csv = Path(__file__).resolve().parent / "data" / "processed" / "market_history.csv"
    mongo_uri = _resolve_mongo_uri()
    docs: list[dict] = []
    mongo_err: str | None = None

    if mongo_uri:
        _configure_dns()
        client = None
        try:
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2500, connectTimeoutMS=2500)
            db = client["nubank_db"]
            collection = db["historico_diario"]
            docs = list(collection.find({}, {"_id": 0}))
        except PyMongoError as exc:
            mongo_err = f"Falha ao consultar o MongoDB ({type(exc).__name__})."
        finally:
            if client:
                client.close()
    else:
        mongo_err = "MONGO_URI não encontrada nas variáveis de ambiente (.env)."

    if docs:
        df = pd.DataFrame(docs)
    elif fallback_csv.exists():
        df = pd.read_csv(fallback_csv)
        mongo_err = None
    else:
        return pd.DataFrame(), mongo_err

    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "collected_at" in df.columns:
        df["collected_at"] = pd.to_datetime(df["collected_at"], errors="coerce").astype(str)

    df = df.dropna(subset=["ticker", "datetime", "close"]).sort_values(["ticker", "datetime"]).reset_index(drop=True)
    if docs and not df.empty and fallback_csv.parent.exists() and not fallback_csv.exists():
        df.assign(datetime=df["datetime"].dt.strftime("%Y-%m-%d")).to_csv(fallback_csv, index=False)
    return df, None


@st.cache_data(ttl=3600, show_spinner=False)
def get_data():
    financial = load_financial_history()
    quarterly = load_financial_quarterly()
    risk, risk_source = load_capital_risk_history()
    risk_detail = load_risk_detail_by_period()
    bcb_complaints, bcb_source = load_bcb_complaints_ranking()
    complaints, complaints_source = load_customer_sample()
    metrics_2026 = compute_metrics_2026(financial, quarterly, risk)
    return (
        financial,
        quarterly,
        risk,
        risk_source,
        risk_detail,
        bcb_complaints,
        bcb_source,
        complaints,
        complaints_source,
        metrics_2026,
    )


(
    financial,
    quarterly,
    risk,
    risk_source,
    risk_detail,
    bcb_complaints,
    bcb_source,
    complaints,
    complaints_source,
    metrics_2026,
) = get_data()
market_df, market_error = load_historico_diario()

VIEW_OPTIONS = {
    "ltm": "2021–2025 + 2026* (LTM 2T26)",
    "ytd_comparison": "2026* acumulado (YTD) vs. mesmo período de 2025",
    "closed_years": "Anos fechados (2021–2025)",
    "quarterly": "Série trimestral (1T25–2T26*)",
}

st.sidebar.markdown("### Visão de Resultados (2021–2026*)")
selected_view = st.sidebar.radio(
    "Modo de leitura de 2026* (parcial)",
    options=list(VIEW_OPTIONS.keys()),
    format_func=lambda k: VIEW_OPTIONS[k],
    index=0,
    help="2026 não é um ano fechado (o 20-F de 2026 só sai em 2027). Alterne entre LTM (soma dos últimos 4 trimestres), YTD 2026 vs. YTD 2025, anos fechados ou série trimestral.",
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Ativos de Mercado (MongoDB)")
available_tickers = (
    sorted(market_df["ticker"].dropna().astype(str).unique().tolist())
    if not market_df.empty and "ticker" in market_df.columns
    else ["NU", "ITUB", "BBD"]
)
selected_tickers = st.sidebar.multiselect(
    "Tickers para comparação",
    options=available_tickers,
    default=available_tickers,
    help="Selecione um ou mais tickers extraídos da coleção historico_diario no MongoDB para comparar nos gráficos.",
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Escopo (2021–2026*)")
st.sidebar.caption(
    "Cotações diárias de mercado vêm do MongoDB (`nubank_db.historico_diario`). "
    "A série financeira cobre 2021–2025 (20-F) e 2026* parcial até 2T26 (Form 6-K SEC), e a camada regulatória usa dados Pilar 3."
)

st.markdown(
    """
    <div class="hero">
      <div class="kicker">Projeto de portfólio · Ciência de Dados & Analytics · 2021–2026*</div>
      <h1>Nubank em Dados (2021–2026*)</h1>
      <p>Crescimento, monetização, rentabilidade e risco entre 2021 e 2026* (parcial até 2T26) — uma leitura integrada de métricas financeiras oficiais (SEC 20-F e 6-K), capital regulatório (Pilar 3) e sinais da experiência do cliente.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def pct_change(new: float, old: float) -> float:
    return (new / old - 1) * 100


def metric_card(label: str, value: str, note: str) -> str:
    return f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-note'>{note}</div></div>"


def build_view_dataframe(view_key: str) -> pd.DataFrame:
    ref_q = metrics_2026["reference_quarter"]
    ltm = metrics_2026["ltm"]
    ytd = metrics_2026["ytd_comparison"]
    stk = metrics_2026["stocks_latest"]

    closed = financial.copy()
    closed["x_label"] = closed["year"].astype(str)
    closed["is_partial"] = False

    if view_key == "closed_years":
        return closed

    if view_key == "ltm":
        row_2026 = pd.DataFrame(
            [
                {
                    "year": 2026,
                    "x_label": f"2026* (parcial até {ref_q})",
                    "is_partial": True,
                    "customers_m": stk["clientes_m"],
                    "arpac_usd": stk["arpac_trimestre_usd"],
                    "cost_to_serve_usd": stk["custo_servir_trimestre_usd"],
                    "revenue_usd_b": ltm["revenue_usd_b"],
                    "gross_profit_usd_b": float("nan"),
                    "net_income_usd_b": ltm["net_income_usd_b"],
                    "adjusted_net_income_usd_b": float("nan"),
                    "deposits_usd_b": stk["depositos_usd_b"],
                    "credit_portfolio_usd_b": stk["carteira_credito_usd_b"],
                    "interest_earning_portfolio_usd_b": float("nan"),
                }
            ]
        )
        return pd.concat([closed, row_2026], ignore_index=True)

    if view_key == "ytd_comparison":
        q_2t25 = quarterly[(quarterly["ano"] == 2025) & (quarterly["trimestre"] == "2T25")].iloc[0]
        return pd.DataFrame(
            [
                {
                    "year": 2025,
                    "x_label": f"2025 ({ytd['label_2025']})",
                    "is_partial": False,
                    "customers_m": float(q_2t25["clientes"]),
                    "arpac_usd": float(q_2t25["arpac_mensal"]),
                    "cost_to_serve_usd": float(q_2t25["custo_servir_mensal"]),
                    "revenue_usd_b": ytd["revenue_2025_usd_b"],
                    "gross_profit_usd_b": float("nan"),
                    "net_income_usd_b": ytd["net_income_2025_usd_b"],
                    "adjusted_net_income_usd_b": float("nan"),
                    "deposits_usd_b": float(q_2t25["depositos"]),
                    "credit_portfolio_usd_b": float(q_2t25["carteira_credito"]),
                    "interest_earning_portfolio_usd_b": float(q_2t25["carteira_credito_juros"]),
                },
                {
                    "year": 2026,
                    "x_label": f"2026* (parcial até {ref_q})",
                    "is_partial": True,
                    "customers_m": stk["clientes_m"],
                    "arpac_usd": stk["arpac_trimestre_usd"],
                    "cost_to_serve_usd": stk["custo_servir_trimestre_usd"],
                    "revenue_usd_b": ytd["revenue_2026_usd_b"],
                    "gross_profit_usd_b": float("nan"),
                    "net_income_usd_b": ytd["net_income_2026_usd_b"],
                    "adjusted_net_income_usd_b": float("nan"),
                    "deposits_usd_b": stk["depositos_usd_b"],
                    "credit_portfolio_usd_b": stk["carteira_credito_usd_b"],
                    "interest_earning_portfolio_usd_b": float("nan"),
                },
            ]
        )

    # Série trimestral 1T25–2T26*
    q_df = quarterly.copy()
    return pd.DataFrame(
        {
            "year": q_df["ano"],
            "x_label": q_df.apply(
                lambda r: f"{r['trimestre']}* (parcial)" if r["parcial"] == "sim" else str(r["trimestre"]),
                axis=1,
            ),
            "is_partial": q_df["parcial"] == "sim",
            "customers_m": q_df["clientes"],
            "arpac_usd": q_df["arpac_mensal"],
            "cost_to_serve_usd": q_df["custo_servir_mensal"],
            "revenue_usd_b": q_df["receita"],
            "gross_profit_usd_b": float("nan"),
            "net_income_usd_b": q_df["lucro_liquido_ifrs"],
            "adjusted_net_income_usd_b": float("nan"),
            "deposits_usd_b": q_df["depositos"],
            "credit_portfolio_usd_b": q_df["carteira_credito"],
            "interest_earning_portfolio_usd_b": q_df["carteira_credito_juros"],
        }
    )


fin_view = build_view_dataframe(selected_view)
first_closed = financial.iloc[0]
latest_closed = financial.iloc[-1]
ref_q = metrics_2026["reference_quarter"]
stk_2026 = metrics_2026["stocks_latest"]
ltm_2026 = metrics_2026["ltm"]
ytd_2026 = metrics_2026["ytd_comparison"]

cols = st.columns(4)
if selected_view == "closed_years":
    card_data = [
        ("Clientes · 4T25 (fechado)", f"{latest_closed.customers_m:.1f} mi", f"{pct_change(latest_closed.customers_m, first_closed.customers_m):+.0f}% desde 2021"),
        ("Receita anual · 2025 (20-F)", f"US$ {latest_closed.revenue_usd_b:.2f} bi", f"{latest_closed.revenue_usd_b / first_closed.revenue_usd_b:.1f}× o nível de 2021"),
        ("Lucro líquido IFRS · 2025", f"US$ {latest_closed.net_income_usd_b:.2f} bi", "IFRS · exercício fechado 2025"),
        ("Depósitos · 4T25 (fechado)", f"US$ {latest_closed.deposits_usd_b:.1f} bi", f"{latest_closed.deposits_usd_b / first_closed.deposits_usd_b:.1f}× o nível de 2021"),
    ]
elif selected_view == "ytd_comparison":
    card_data = [
        (f"Clientes · estoque em {ref_q}*", f"{stk_2026['clientes_m']:.1f} mi", f"+{stk_2026['clientes_yoy_pct']:.1f}% vs. 2T25 (parcial até {ref_q})"),
        (f"Receita · {ytd_2026['label_2026']}* (parcial)", f"US$ {ytd_2026['revenue_2026_usd_b']:.2f} bi", f"+{ytd_2026['revenue_yoy_pct']:.1f}% vs. {ytd_2026['label_2025']} (US$ {ytd_2026['revenue_2025_usd_b']:.2f} bi)"),
        (f"Lucro líquido IFRS · {ytd_2026['label_2026']}*", f"US$ {ytd_2026['net_income_2026_usd_b']:.2f} bi", f"+{ytd_2026['net_income_yoy_pct']:.1f}% vs. {ytd_2026['label_2025']} (US$ {ytd_2026['net_income_2025_usd_b']:.2f} bi)"),
        (f"Depósitos · estoque em {ref_q}*", f"US$ {stk_2026['depositos_usd_b']:.1f} bi", f"+{stk_2026['depositos_yoy_pct']:.1f}% vs. 2T25 (US$ 36.6 bi)"),
    ]
elif selected_view == "quarterly":
    last_q_row = quarterly.iloc[-1]
    card_data = [
        (f"Clientes · estoque em {ref_q}*", f"{stk_2026['clientes_m']:.1f} mi", f"+{stk_2026['clientes_yoy_pct']:.1f}% YoY vs. 2T25"),
        (f"Receita trimestral · {ref_q}*", f"US$ {last_q_row.receita:.2f} bi", f"Trimestre isolado {ref_q} (parcial 2026*)"),
        (f"Lucro líquido IFRS · {ref_q}*", f"US$ {last_q_row.lucro_liquido_ifrs:.2f} bi", f"IFRS no trimestre {ref_q} (parcial 2026*)"),
        (f"Depósitos · estoque em {ref_q}*", f"US$ {stk_2026['depositos_usd_b']:.1f} bi", f"Posição de fechamento do {ref_q}"),
    ]
else:
    card_data = [
        (f"Clientes · ref. {ref_q}* (parcial)", f"{stk_2026['clientes_m']:.1f} mi", f"{pct_change(stk_2026['clientes_m'], first_closed.customers_m):+.0f}% desde 2021 · estoque em {ref_q}"),
        (f"Receita · LTM {ref_q}* (3T25–2T26)", f"US$ {ltm_2026['revenue_usd_b']:.2f} bi", f"{ltm_2026['revenue_usd_b'] / first_closed.revenue_usd_b:.1f}× 2021 · últimos 4 trimestres"),
        (f"Lucro líquido IFRS · LTM {ref_q}*", f"US$ {ltm_2026['net_income_usd_b']:.2f} bi", f"IFRS · janela LTM ({ltm_2026['start_quarter']}–{ltm_2026['end_quarter']})"),
        (f"Depósitos · ref. {ref_q}* (parcial)", f"US$ {stk_2026['depositos_usd_b']:.1f} bi", f"{stk_2026['depositos_usd_b'] / first_closed.deposits_usd_b:.1f}× 2021 · estoque em {ref_q}"),
    ]

for col, values in zip(cols, card_data):
    col.markdown(metric_card(*values), unsafe_allow_html=True)

st.markdown(
    f"""
    <div class="partial-banner">
      <b>Nota metodológica (2026* parcial até {ref_q}):</b> 2026 não é um ano fechado (o Form 20-F de 2026 só sai em 2027).
      Fluxos (receita e lucro IFRS) de 2026* são analisados via <b>LTM ({ltm_2026['start_quarter']}–{ltm_2026['end_quarter']})</b> ou <b>acumulado do ano ({ytd_2026['label_2026']} vs. {ytd_2026['label_2025']})</b>, nunca comparando 2 trimestres com 12 meses fechados.
      Estoques (clientes, depósitos e crédito) refletem o fechamento do <b>{ref_q}</b>. Barras hachuradas diferenciam 2026* parcial.
    </div>
    """,
    unsafe_allow_html=True,
)

tab_market, tab_overview, tab_profit, tab_risk, tab_customer, tab_method = st.tabs(
    [
        "Mercado e Cotações (MongoDB)",
        "Visão geral (2021–2026*)",
        "Rentabilidade e eficiência",
        "Capital e risco",
        "Experiência do cliente",
        "Metodologia",
    ]
)

with tab_market:
    st.markdown("## Desempenho Histórico das Ações (`historico_diario`)")
    st.markdown(
        "<span class='source-chip'>MongoDB · nubank_db.historico_diario · Twelve Data API</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='section-note' style='margin-top:0.5rem;'>Comparação das séries históricas diárias extraídas manualmente para o MongoDB. Use o filtro <b>Tickers para comparação</b> na barra lateral para selecionar os ativos exibidos nos gráficos.</div>",
        unsafe_allow_html=True,
    )

    if market_error:
        st.error(f"Não foi possível carregar os dados do MongoDB: {market_error}")
    elif market_df.empty:
        st.info(
            "A coleção `historico_diario` está vazia no momento. Execute `python ingestao.py` manualmente para realizar a carga histórica."
        )
    elif not selected_tickers:
        st.warning("Selecione pelo menos um ticker no filtro da barra lateral para visualizar e comparar os gráficos.")
    else:
        filtered_market = market_df[market_df["ticker"].isin(selected_tickers)].copy()
        filtered_market = filtered_market.sort_values(["ticker", "datetime"])

        min_dt = filtered_market["datetime"].min()
        max_dt = filtered_market["datetime"].max()
        m1, m2, m3 = st.columns(3)
        m1.metric("Documentos filtrados", f"{len(filtered_market):,}".replace(",", "."))
        m2.metric("Tickers comparados", ", ".join(selected_tickers))
        m3.metric(
            "Janela temporal",
            f"{min_dt.strftime('%d/%m/%Y')} – {max_dt.strftime('%d/%m/%Y')}" if pd.notna(min_dt) and pd.notna(max_dt) else "N/D",
        )

        left_m, right_m = st.columns(2)
        with left_m:
            fig_close = px.line(
                filtered_market,
                x="datetime",
                y="close",
                color="ticker",
                color_discrete_map=TICKER_COLORS,
                title="Preço de fechamento diário (Close)",
                labels={"datetime": "Data", "close": "Preço de fechamento (US$)", "ticker": "Ticker"},
            )
            fig_close.update_traces(line=dict(width=2.5))
            fig_close.update_layout(
                template="plotly_white",
                height=420,
                legend=dict(orientation="h", y=1.08, x=0),
                margin=dict(l=20, r=20, t=75, b=20),
            )
            fig_close.update_xaxes(gridcolor=GRID)
            fig_close.update_yaxes(gridcolor=GRID)
            st.plotly_chart(fig_close, use_container_width=True)

        with right_m:
            norm_df = filtered_market.copy()
            first_close = norm_df.groupby("ticker")["close"].transform("first")
            norm_df["base_100"] = (norm_df["close"] / first_close) * 100.0

            fig_norm = px.line(
                norm_df,
                x="datetime",
                y="base_100",
                color="ticker",
                color_discrete_map=TICKER_COLORS,
                title="Evolução comparativa normalizada (Base 100 no início da série)",
                labels={"datetime": "Data", "base_100": "Índice (Base 100)", "ticker": "Ticker"},
            )
            fig_norm.add_hline(y=100, line_width=1, line_dash="dash", line_color="#999")
            fig_norm.update_traces(line=dict(width=2.5))
            fig_norm.update_layout(
                template="plotly_white",
                height=420,
                legend=dict(orientation="h", y=1.08, x=0),
                margin=dict(l=20, r=20, t=75, b=20),
            )
            fig_norm.update_xaxes(gridcolor=GRID)
            fig_norm.update_yaxes(gridcolor=GRID)
            st.plotly_chart(fig_norm, use_container_width=True)

        fig_vol = px.line(
            filtered_market,
            x="datetime",
            y="volume",
            color="ticker",
            color_discrete_map=TICKER_COLORS,
            title="Volume diário negociado por ticker",
            labels={"datetime": "Data", "volume": "Volume", "ticker": "Ticker"},
        )
        fig_vol.update_layout(
            template="plotly_white",
            height=360,
            legend=dict(orientation="h", y=1.08, x=0),
            margin=dict(l=20, r=20, t=75, b=20),
        )
        fig_vol.update_xaxes(gridcolor=GRID)
        fig_vol.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fig_vol, use_container_width=True)

        summary_rows = []
        for tkr, grp in filtered_market.groupby("ticker", sort=True):
            grp_sorted = grp.sort_values("datetime")
            first_val = float(grp_sorted["close"].iloc[0])
            last_val = float(grp_sorted["close"].iloc[-1])
            ret_pct = ((last_val / first_val) - 1.0) * 100.0 if first_val else 0.0
            summary_rows.append(
                {
                    "Ticker": tkr,
                    "Pregões": len(grp_sorted),
                    "Data Inicial": grp_sorted["datetime"].iloc[0].strftime("%Y-%m-%d"),
                    "Data Final": grp_sorted["datetime"].iloc[-1].strftime("%Y-%m-%d"),
                    "Fechamento Inicial (US$)": round(first_val, 2),
                    "Último Fechamento (US$)": round(last_val, 2),
                    "Mínima no Período (US$)": round(float(grp_sorted["low"].min()), 2),
                    "Máxima no Período (US$)": round(float(grp_sorted["high"].max()), 2),
                    "Retorno Acumulado (%)": round(ret_pct, 2),
                }
            )
        st.markdown("### Resumo estatístico dos tickers selecionados")
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

with tab_overview:
    st.markdown(f"## Crescimento que se converteu em monetização ({VIEW_OPTIONS[selected_view]})")
    st.markdown(
        "<div class='section-note'>A leitura conjunta evita confundir expansão de base com criação de valor. Barras hachuradas identificam períodos parciais de 2026* (parcial até 2T26).</div>",
        unsafe_allow_html=True,
    )

    bar_colors = [PARTIAL_AMBER if is_p else NU_PURPLE for is_p in fin_view["is_partial"]]
    bar_patterns = ["/" if is_p else "" for is_p in fin_view["is_partial"]]

    left, right = st.columns(2)
    with left:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=fin_view["x_label"],
                y=fin_view["revenue_usd_b"],
                name="Receita (2026* hachurado = parcial)",
                marker=dict(color=bar_colors, pattern_shape=bar_patterns),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=fin_view["x_label"],
                y=fin_view["net_income_usd_b"],
                name="Lucro líquido IFRS",
                mode="lines+markers",
                line=dict(color=NU_DARK, width=3),
                marker=dict(size=9),
            )
        )
        fig.add_hline(y=0, line_width=1, line_color="#999")
        fig.update_layout(
            title="Receita e lucro líquido IFRS",
            yaxis_title="US$ bilhões",
            xaxis_title="",
            template="plotly_white",
            legend=dict(orientation="h", y=1.08, x=0),
            height=420,
            margin=dict(l=20, r=20, t=75, b=20),
        )
        fig.update_xaxes(gridcolor=GRID)
        fig.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Scatter(
                x=fin_view["x_label"],
                y=fin_view["customers_m"],
                mode="lines+markers",
                name="Clientes (estoque)",
                line=dict(color=NU_PURPLE, width=4),
            ),
            secondary_y=False,
        )
        dep_colors = ["#E7B977" if is_p else "#C89BE5" for is_p in fin_view["is_partial"]]
        fig.add_trace(
            go.Bar(
                x=fin_view["x_label"],
                y=fin_view["deposits_usd_b"],
                name="Depósitos (estoque)",
                marker=dict(color=dep_colors, pattern_shape=bar_patterns),
                opacity=0.72,
            ),
            secondary_y=True,
        )
        fig.update_layout(
            title="Escala da base e depósitos (estoque 2026* em 2T26)",
            template="plotly_white",
            legend=dict(orientation="h", y=1.08, x=0),
            height=420,
            margin=dict(l=20, r=20, t=75, b=20),
        )
        fig.update_xaxes(gridcolor=GRID)
        fig.update_yaxes(title_text="Clientes (milhões)", gridcolor=GRID, secondary_y=False)
        fig.update_yaxes(title_text="Depósitos (US$ bi)", gridcolor=GRID, secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns([1.1, 0.9])
    with left:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=fin_view["x_label"],
                y=fin_view["arpac_usd"],
                name="ARPAC mensal",
                mode="lines+markers",
                line=dict(color=NU_PURPLE, width=4),
                marker=dict(size=9),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=fin_view["x_label"],
                y=fin_view["cost_to_serve_usd"],
                name="Custo mensal por cliente ativo",
                mode="lines+markers",
                line=dict(color="#777", width=3, dash="dot"),
                marker=dict(size=8),
            )
        )
        fig.update_layout(
            title="Monetização por cliente vs. custo de servir",
            yaxis_title="US$ por cliente ativo / mês",
            xaxis_title="",
            template="plotly_white",
            height=390,
            legend=dict(orientation="h", y=1.08, x=0),
            margin=dict(l=20, r=20, t=75, b=20),
        )
        fig.update_xaxes(gridcolor=GRID)
        fig.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        first_row = fin_view.iloc[0]
        last_row = fin_view.iloc[-1]
        revenue_multiple = last_row.revenue_usd_b / first_row.revenue_usd_b
        customer_multiple = last_row.customers_m / first_row.customers_m
        arpac_growth = pct_change(last_row.arpac_usd, first_row.arpac_usd)
        st.markdown("### Leitura da visão selecionada")
        st.markdown(
            f"<div class='insight'><b>Receita ({last_row.x_label}):</b> avançou de US$ {first_row.revenue_usd_b:.2f} bi para US$ {last_row.revenue_usd_b:.2f} bi — {revenue_multiple:.1f}×.</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='insight'><b>Escala ({last_row.x_label}):</b> a base passou de {first_row.customers_m:.1f} mi para {last_row.customers_m:.1f} mi de clientes — {customer_multiple:.1f}×.</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='insight'><b>Monetização:</b> o ARPAC mensal cresceu {arpac_growth:.0f}% (US$ {last_row.arpac_usd:.1f}), enquanto o custo de servir situou-se em US$ {last_row.cost_to_serve_usd:.1f}.</div>",
            unsafe_allow_html=True,
        )

    portfolio = fin_view.dropna(subset=["credit_portfolio_usd_b"])
    if not portfolio.empty:
        p_colors = [PARTIAL_AMBER if is_p else NU_PURPLE for is_p in portfolio["is_partial"]]
        p_patterns = ["/" if is_p else "" for is_p in portfolio["is_partial"]]
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=portfolio["x_label"],
                y=portfolio["credit_portfolio_usd_b"],
                name="Carteira total (cartão + empréstimos)",
                marker=dict(color=p_colors, pattern_shape=p_patterns),
            )
        )
        fig.add_trace(
            go.Bar(
                x=portfolio["x_label"],
                y=portfolio["interest_earning_portfolio_usd_b"],
                name="Carteira geradora de juros (IEP)",
                marker_color="#D9B9ED",
            )
        )
        fig.update_layout(
            title="Expansão das carteiras de crédito (estoque 2026* em 2T26)",
            barmode="group",
            yaxis_title="US$ bilhões",
            xaxis_title="",
            template="plotly_white",
            height=390,
            legend=dict(orientation="h", y=1.08, x=0),
            margin=dict(l=20, r=20, t=75, b=20),
        )
        fig.update_xaxes(gridcolor=GRID)
        fig.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fig, use_container_width=True)

with tab_profit:
    st.markdown(f"## Da perda à rentabilidade ({VIEW_OPTIONS[selected_view]})")
    prof = fin_view.copy()
    prof["gross_margin_pct"] = prof["gross_profit_usd_b"] / prof["revenue_usd_b"] * 100
    prof["net_margin_pct"] = prof["net_income_usd_b"] / prof["revenue_usd_b"] * 100

    left, right = st.columns(2)
    with left:
        fig = go.Figure()
        colors = [
            NEGATIVE if val < 0 else (PARTIAL_AMBER if is_p else POSITIVE)
            for val, is_p in zip(prof["net_income_usd_b"], prof["is_partial"])
        ]
        patterns = ["/" if is_p else "" for is_p in prof["is_partial"]]
        fig.add_trace(
            go.Bar(
                x=prof["x_label"],
                y=prof["net_income_usd_b"],
                marker=dict(color=colors, pattern_shape=patterns),
                text=[f"US$ {v:.2f} bi" for v in prof["net_income_usd_b"]],
                textposition="outside",
                name="Lucro líquido IFRS",
            )
        )
        fig.add_hline(y=0, line_width=1, line_color="#999")
        fig.update_layout(
            title="Lucro líquido IFRS (2026* hachurado = parcial)",
            yaxis_title="US$ bilhões",
            xaxis_title="",
            template="plotly_white",
            height=420,
            showlegend=False,
            margin=dict(l=20, r=20, t=65, b=20),
        )
        fig.update_xaxes(gridcolor=GRID)
        fig.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        fig = go.Figure()
        if prof["gross_margin_pct"].notna().any():
            fig.add_trace(
                go.Scatter(
                    x=prof["x_label"],
                    y=prof["gross_margin_pct"],
                    name="Margem bruta",
                    mode="lines+markers",
                    line=dict(color=NU_PURPLE, width=4),
                )
            )
        fig.add_trace(
            go.Scatter(
                x=prof["x_label"],
                y=prof["net_margin_pct"],
                name="Margem líquida IFRS",
                mode="lines+markers",
                line=dict(color=NU_DARK, width=3),
            )
        )
        fig.add_hline(y=0, line_width=1, line_color="#999")
        fig.update_layout(
            title="Margens implícitas nos resultados IFRS",
            yaxis_title="% da receita",
            xaxis_title="",
            template="plotly_white",
            height=420,
            legend=dict(orientation="h", y=1.08, x=0),
            margin=dict(l=20, r=20, t=75, b=20),
        )
        fig.update_xaxes(gridcolor=GRID)
        fig.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        f"<div class='insight'><b>Síntese 2021–2026*:</b> o lucro líquido IFRS virou positivo em 2023, atingiu US$ {latest_closed.net_income_usd_b:.2f} bi no ano fechado de 2025 (20-F) e alcança <b>US$ {ltm_2026['net_income_usd_b']:.2f} bi em {ltm_2026['label']}</b> (ou <b>US$ {ytd_2026['net_income_2026_usd_b']:.2f} bi no {ytd_2026['label_2026']} parcial</b> vs. US$ {ytd_2026['net_income_2025_usd_b']:.2f} bi no {ytd_2026['label_2025']}, alta de +{ytd_2026['net_income_yoy_pct']:.1f}%).</div>",
        unsafe_allow_html=True,
    )

    st.markdown("### Série trimestral auditável (1T25–2T26*)")
    st.dataframe(quarterly, use_container_width=True, hide_index=True)

with tab_risk:
    st.markdown("## Capital regulatório e absorção de risco (Pilar 3)")
    st.markdown(f"<span class='source-chip'>{risk_source}</span>", unsafe_allow_html=True)

    risk_filtered = risk.copy()
    if risk_filtered.empty:
        st.info("Não há observações regulatórias disponíveis.")
    else:
        left, right = st.columns(2)
        with left:
            if {"capital_principal_brl_b", "rwa_total_brl_b"}.intersection(risk_filtered.columns):
                fig = go.Figure()
                if "capital_principal_brl_b" in risk_filtered:
                    fig.add_trace(
                        go.Scatter(
                            x=risk_filtered.period,
                            y=risk_filtered.capital_principal_brl_b,
                            mode="lines+markers",
                            name="Capital Principal",
                            line=dict(color=NU_PURPLE, width=4),
                        )
                    )
                if "rwa_total_brl_b" in risk_filtered:
                    fig.add_trace(
                        go.Scatter(
                            x=risk_filtered.period,
                            y=risk_filtered.rwa_total_brl_b,
                            mode="lines+markers",
                            name="RWA total",
                            line=dict(color=NU_DARK, width=3),
                        )
                    )
                fig.update_layout(
                    title="Capital Principal e RWA (R$ bilhões)",
                    yaxis_title="R$ bilhões",
                    xaxis_title="",
                    template="plotly_white",
                    height=420,
                    legend=dict(orientation="h", y=1.08, x=0),
                    margin=dict(l=20, r=20, t=75, b=20),
                )
                fig.update_yaxes(gridcolor=GRID)
                st.plotly_chart(fig, use_container_width=True)

        with right:
            if {"basel_index_pct", "icp_pct"}.intersection(risk_filtered.columns):
                fig = go.Figure()
                if "basel_index_pct" in risk_filtered:
                    fig.add_trace(
                        go.Scatter(
                            x=risk_filtered.period,
                            y=risk_filtered.basel_index_pct,
                            mode="lines+markers",
                            name="Índice de Basileia",
                            line=dict(color=NU_PURPLE, width=4),
                        )
                    )
                if "icp_pct" in risk_filtered:
                    fig.add_trace(
                        go.Scatter(
                            x=risk_filtered.period,
                            y=risk_filtered.icp_pct,
                            mode="lines+markers",
                            name="ICP",
                            line=dict(color="#A26AC5", width=3, dash="dot"),
                        )
                    )
                fig.update_layout(
                    title="Índices prudenciais (%)",
                    yaxis_title="%",
                    xaxis_title="",
                    template="plotly_white",
                    height=420,
                    legend=dict(orientation="h", y=1.08, x=0),
                    margin=dict(l=20, r=20, t=75, b=20),
                )
                fig.update_yaxes(gridcolor=GRID)
                st.plotly_chart(fig, use_container_width=True)

        prud = metrics_2026["prudential_latest"]
        st.markdown(
            f"<div class='insight'><b>Último trimestre prudencial disponível ({prud['trimestre_referencia']} · {prud['periodo_fim']}):</b> Índice de Basileia de <b>{prud['basel_index_pct']:.2f}%</b>, ICP de <b>{prud['icp_pct']:.2f}%</b>, Capital Principal de <b>R$ {prud['capital_principal_brl_b']:.2f} bi</b> e RWA total de <b>R$ {prud['rwa_total_brl_b']:.1f} bi</b> (em R$, sem mistura com US$).</div>",
            unsafe_allow_html=True,
        )

    st.markdown("### Decomposição trimestral de risco (KM1, OV1 e MR1)")
    left, right = st.columns(2)
    with left:
        fig = px.bar(
            risk_detail,
            x="trimestre",
            y="rwa_credito_brl_b",
            text="rwa_credito_brl_b",
            labels={"trimestre": "", "rwa_credito_brl_b": "R$ bilhões"},
            title="RWA de crédito por trimestre",
            color_discrete_sequence=[NU_PURPLE],
        )
        fig.update_traces(texttemplate="R$ %{text:.1f} bi", textposition="outside")
        fig.update_layout(template="plotly_white", height=360, margin=dict(l=20, r=20, t=60, b=20))
        fig.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        market_risk = risk_detail[["trimestre", "rwa_juros_brl_m", "rwa_cambio_brl_m"]].melt(
            "trimestre", var_name="tipo", value_name="valor"
        )
        market_risk["tipo"] = market_risk["tipo"].map({"rwa_juros_brl_m": "Juros", "rwa_cambio_brl_m": "Câmbio"})
        fig = px.bar(
            market_risk,
            x="trimestre",
            y="valor",
            color="tipo",
            barmode="group",
            labels={"trimestre": "", "valor": "R$ milhões", "tipo": "Risco"},
            title="RWA de mercado: juros e câmbio",
            color_discrete_map={"Juros": NU_MID, "Câmbio": "#D8AFE9"},
        )
        fig.update_layout(
            template="plotly_white",
            height=360,
            legend=dict(orientation="h", y=1.08, x=0),
            margin=dict(l=20, r=20, t=70, b=20),
        )
        fig.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fig, use_container_width=True)

with tab_customer:
    st.markdown("## Experiência do cliente · Ranking Oficial de Reclamações do Banco Central (1T24–3T26*)")
    st.markdown(f"<span class='source-chip'>{bcb_source}</span>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class="partial-banner" style="margin-top:0.65rem;">
          <b>Nota metodológica (Banco Central do Brasil):</b> A partir do <b>2º trimestre de 2024 (2T24)</b>, o Banco Central passou a publicar o Ranking com <b>valores extrapolados</b> — estimando estatisticamente o total de reclamações reguladas procedentes a partir de amostra das demandas encerradas no trimestre. Essa mudança metodológica elevou o patamar numérico dos índices em todo o Sistema Financeiro Nacional a partir do 2T24, sem significar deterioração operacional abrupta em relação ao 1T24. Períodos de 2026 (<code>1T26*</code> a <code>3T26*</code>) compõem o ano parcial <code>2026*</code>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if bcb_complaints.empty:
        st.warning("A série oficial do Ranking de Reclamações do Banco Central não está disponível.")
    else:
        latest_bcb_period = bcb_complaints["periodo"].iloc[-1]
        latest_bcb = bcb_complaints[bcb_complaints["periodo"] == latest_bcb_period].copy()
        latest_bcb_label = f"{latest_bcb_period}*" if (latest_bcb["parcial_2026"] == "sim").any() else str(latest_bcb_period)

        b_cols = st.columns(3)
        inst_order = ["Nu Pagamentos (Nubank)", "Itaú", "Bradesco"]
        for col, inst_name in zip(b_cols, inst_order):
            row_inst = latest_bcb[latest_bcb["instituicao"] == inst_name]
            if not row_inst.empty:
                r = row_inst.iloc[0]
                proc_str = f"{int(r['procedentes']):,}".replace(",", ".") if pd.notna(r["procedentes"]) else "n/d"
                cli_mi = float(r["clientes"]) / 1_000_000.0
                col.markdown(
                    metric_card(
                        f"Índice BCB · {inst_name} ({latest_bcb_label})",
                        f"{float(r['indice']):.2f}".replace(".", ","),
                        f"{proc_str} procedentes · {cli_mi:.1f} mi clientes (valores extrapolados)",
                    ),
                    unsafe_allow_html=True,
                )

        BCB_COLORS = {
            "Nu Pagamentos (Nubank)": NU_PURPLE,
            "Itaú": "#FF6B00",
            "Bradesco": "#CC092F",
        }
        bcb_plot = bcb_complaints.copy()
        bcb_plot["periodo_label"] = bcb_plot.apply(
            lambda r: f"{r['periodo']}*" if r["parcial_2026"] == "sim" else str(r["periodo"]),
            axis=1,
        )

        left_b, right_b = st.columns([1.2, 0.8])
        with left_b:
            fig_bcb_idx = px.line(
                bcb_plot,
                x="periodo_label",
                y="indice",
                color="instituicao",
                markers=True,
                color_discrete_map=BCB_COLORS,
                title="Evolução trimestral do Índice de Reclamações BCB (1T24–3T26*)",
                labels={
                    "periodo_label": "Trimestre (2T24+ com valores extrapolados)",
                    "indice": "Índice BCB (procedentes / milhão de clientes)",
                    "instituicao": "Conglomerado",
                },
            )
            fig_bcb_idx.update_traces(line=dict(width=3), marker=dict(size=8))
            fig_bcb_idx.update_layout(
                template="plotly_white",
                height=420,
                legend=dict(orientation="h", y=1.1, x=0),
                margin=dict(l=20, r=20, t=75, b=20),
            )
            fig_bcb_idx.update_xaxes(gridcolor=GRID)
            fig_bcb_idx.update_yaxes(gridcolor=GRID)
            st.plotly_chart(fig_bcb_idx, use_container_width=True)

        with right_b:
            latest_bar = latest_bcb.dropna(subset=["procedentes"]).sort_values("indice", ascending=True)
            fig_bcb_proc = px.bar(
                latest_bar,
                x="procedentes",
                y="instituicao",
                orientation="h",
                color="instituicao",
                text="procedentes",
                color_discrete_map=BCB_COLORS,
                title=f"Reclamações reguladas procedentes ({latest_bcb_label})",
                labels={
                    "procedentes": "Reclamações procedentes (extrapoladas)",
                    "instituicao": "",
                },
            )
            fig_bcb_proc.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
            fig_bcb_proc.update_layout(
                template="plotly_white",
                height=420,
                showlegend=False,
                margin=dict(l=20, r=45, t=75, b=20),
            )
            fig_bcb_proc.update_xaxes(gridcolor=GRID)
            st.plotly_chart(fig_bcb_proc, use_container_width=True)

        st.markdown(
            f"<div class='insight'><b>Posição relativa no {latest_bcb_label}:</b> Com base de <b>119,6 milhões de clientes</b> no SFN, o conglomerado <b>Nu Pagamentos (Nubank)</b> registrou índice de <b>10,68</b> (1.278 reclamações reguladas procedentes extrapoladas, 13ª posição no Top 15), permanecendo estruturalmente abaixo de <b>Itaú (43,20)</b> e <b>Bradesco (57,23)</b> em toda a janela <code>1T24–3T26*</code>.</div>",
            unsafe_allow_html=True,
        )

        st.markdown("### Tabela auditável · Ranking de Reclamações do Banco Central (com `fonte_url`)")
        st.dataframe(
            bcb_complaints[
                [
                    "periodo",
                    "instituicao",
                    "indice",
                    "procedentes",
                    "clientes",
                    "valores_extrapolados",
                    "parcial_2026",
                    "motivos",
                    "fonte_url",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("---")
    with st.expander("⚠️ Apêndice exploratório e não representativo: amostra antiga do Reclame Aqui (clique para expandir)"):
        st.warning(
            "**AVISO METODOLÓGICO — AMOSTRA EXPLORATÓRIA, NÃO REPRESENTATIVA:** "
            "Os gráficos abaixo utilizam a amostra estática antiga do Reclame Aqui (`data/raw/customer/reclamacoes_com_insights.csv`), "
            "mantida no repositório apenas como apêndice exploratório de estudo acadêmico de NLP/clusterização. "
            "Ela **não possui cobertura temporal auditável 2021–2026*** e **foi substituída pela série oficial do Banco Central acima** "
            "como referência analítica de experiência do cliente."
        )
        if complaints.empty:
            st.info("A amostra local exploratória de reclamações não está disponível nesta execução.")
        else:
            summaries = customer_summary(complaints)
            c1, c2, c3 = st.columns(3)
            c1.metric("Reclamações na amostra exploratória", f"{len(complaints):,}".replace(",", "."))
            if "Perda_Financeira" in complaints:
                share = pd.to_numeric(complaints["Perda_Financeira"], errors="coerce").fillna(0).mean() * 100
                c2.metric("Marcadas com perda financeira", f"{share:.1f}%")
            if "Problema_Seguranca" in complaints:
                security = pd.to_numeric(complaints["Problema_Seguranca"], errors="coerce").fillna(0).sum()
                c3.metric("Sinais de segurança", f"{int(security)}")

            left, right = st.columns([1.15, 0.85])
            with left:
                categories = summaries["categories"].sort_values("reclamacoes", ascending=True)
                if not categories.empty:
                    fig = px.bar(
                        categories,
                        x="reclamacoes",
                        y="categoria",
                        orientation="h",
                        text="reclamacoes",
                        title="Principais categorias da amostra exploratória (não representativa)",
                        labels={"reclamacoes": "Reclamações", "categoria": ""},
                        color_discrete_sequence=[NU_PURPLE],
                    )
                    fig.update_traces(textposition="outside")
                    fig.update_layout(template="plotly_white", height=420, margin=dict(l=20, r=40, t=60, b=20))
                    fig.update_xaxes(gridcolor=GRID)
                    st.plotly_chart(fig, use_container_width=True)
            with right:
                severity = summaries["severity"]
                if not severity.empty:
                    fig = px.pie(
                        severity,
                        values="reclamacoes",
                        names="severidade",
                        hole=0.58,
                        title="Severidade estimada (amostra exploratória)",
                        color_discrete_sequence=[NU_DARK, NU_PURPLE, "#C89BE5", "#E9D9F1"],
                    )
                    fig.update_layout(
                        template="plotly_white",
                        height=420,
                        margin=dict(l=20, r=20, t=60, b=20),
                        legend=dict(orientation="h", y=-0.08),
                    )
                    st.plotly_chart(fig, use_container_width=True)

            clusters = summaries["clusters"]
            if not clusters.empty:
                fig = px.bar(
                    clusters,
                    x="cluster",
                    y="reclamacoes",
                    text="reclamacoes",
                    title="Distribuição dos clusters do estudo acadêmico (exploratório)",
                    labels={"cluster": "Cluster", "reclamacoes": "Reclamações"},
                    color_discrete_sequence=[NU_MID],
                )
                fig.update_layout(template="plotly_white", height=320, margin=dict(l=20, r=20, t=60, b=20))
                fig.update_xaxes(dtick=1)
                fig.update_yaxes(gridcolor=GRID)
                st.plotly_chart(fig, use_container_width=True)

with tab_method:
    st.markdown("## Como o projeto foi construído (2021–2026*)")
    st.markdown(
        """
        O objetivo desta versão é transformar o trabalho acadêmico original em um produto analítico reproduzível e auditável cobrindo **2021–2026*** (com 2026 tratado rigorosamente como ano parcial até `2T26`).

        **Fluxo principal**

        `divulgações oficiais SEC (20-F e 6-K) / Pilar 3 → Python + Pandas → validação e reconciliação → SQLite + SQL → Streamlit & GitHub Pages`
        """
    )

    manifest = pd.read_csv(Path(__file__).parent / "data" / "source_manifest.csv")
    st.dataframe(manifest, use_container_width=True, hide_index=True)

    st.markdown("### Arquitetura")
    st.code(
        """data/
├── raw/pillar3/                      # arquivos regulatórios 2021-2025 + pasta 2026 pronta
├── raw/customer/                     # amostra exploratória (não representativa) do Reclame Aqui
├── processed/
│   ├── financial_history.csv         # série anual fechada 2021-2025 (intacta)
│   ├── financial_quarterly.csv       # série trimestral 1T25-2T26* (com flag parcial)
│   ├── bcb_complaints_ranking.csv    # série oficial BCB de reclamações (1T24-3T26*)
│   ├── capital_risk_history_long.csv
│   ├── risk_detail_by_period.csv     # detalhamento prudencial generalizado por período
│   ├── risk_2025_detail.csv
│   └── market_history.csv
├── source_manifest.csv
src/
├── data_pipeline.py                  # carga local, LTM, YTD, estoques 2026* e BCB Ranking
├── ingest_sec_quarterly.py           # verificação de relatórios SEC 6-K/20-F
├── ingest_pillar3.py                 # reconstrução a partir dos XLSX brutos (2021-2026*)
├── ingest_complaints.py              # ingestão do Ranking BCB e verificação Consumidor.gov.br
├── build_database.py                 # gera SQLite analítico e views LTM/YTD
├── build_web_data.py                 # gera payload JSON para GitHub Pages (docs/)
└── validate_data.py                  # reconciliação 2025 e validações de integridade
sql/                                  # consultas de negócio (incluindo 05_ltm_and_ytd_2026.sql)
app.py                                # produto Streamlit
NOTAS_ATUALIZACAO.md                  # registro de decisões, reconciliação e guia de atualização
""",
        language="text",
    )

    st.markdown("### Limites e decisões metodológicas")
    st.markdown(
        """
- **2026* como ano parcial:** 2026 não é um ano fechado (o Form 20-F de 2026 só sai em 2027). Fluxos (receita e lucro) são comparados via **LTM (`3T25–2T26`)** ou **YTD (`1S26` vs. `1S25`)**, e estoques refletem o último trimestre disponível (`2T26`).
- Métricas financeiras são reportadas em **US$** e preservam a unidade utilizada nas divulgações da companhia na SEC.
- Capital regulatório e RWA são apresentados em **R$**, seguindo os arquivos regulatórios Pilar 3 versionados localmente.
- Medidas ajustadas são identificadas como **não IFRS** e não substituem o lucro líquido IFRS.
- **Experiência do cliente (Série Oficial BCB):** Utiliza o **Ranking de Instituições por Índice de Reclamações do Banco Central (`1T24–3T26*`)** para Nu Pagamentos, Itaú e Bradesco, preservando a nota metodológica de **valores extrapolados desde o 2º tri/2024 (`2T24`)**. A amostra antiga do Reclame Aqui foi rebaixada para apêndice exploratório e não representativo.
        """
    )

st.markdown("---")
st.caption(
    "*2026 refere-se ao ano parcial até 2T26 (30/06/2026). Projeto independente de portfólio. Não afiliado à Nu Holdings Ltd."
)
