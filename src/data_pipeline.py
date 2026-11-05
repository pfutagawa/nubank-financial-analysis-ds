from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

from src.ingest_pillar3 import build_long_history


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
RAW_CUSTOMER = ROOT / "data" / "raw" / "customer"


def load_financial_history() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "financial_history.csv")
    df["year"] = df["year"].astype(int)
    return df.sort_values("year").reset_index(drop=True)


def load_financial_quarterly() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "financial_quarterly.csv")
    df["ano"] = df["ano"].astype(int)
    df["periodo_fim"] = df["periodo_fim"].astype(str)
    for col in [
        "receita",
        "lucro_liquido_ifrs",
        "clientes",
        "depositos",
        "carteira_credito",
        "carteira_credito_juros",
        "arpac_mensal",
        "custo_servir_mensal",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("periodo_fim").reset_index(drop=True)


def load_risk_detail_by_period() -> pd.DataFrame:
    detail_path = PROCESSED / "risk_detail_by_period.csv"
    if detail_path.exists():
        df = pd.read_csv(detail_path)
        return df.sort_values("period").reset_index(drop=True)
    fallback = pd.read_csv(PROCESSED / "risk_2025_detail.csv")
    fallback["year"] = pd.to_datetime(fallback["period"]).dt.year
    fallback["trimestre"] = fallback["quarter"].astype(str).str.replace("Q", "") + "T25"
    fallback["parcial"] = "não"
    fallback["moeda"] = "BRL"
    return fallback.sort_values("period").reset_index(drop=True)


def compute_metrics_2026(
    annual: pd.DataFrame | None = None,
    quarterly: pd.DataFrame | None = None,
    risk_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Calcula as métricas de 2026* parcial seguindo estritamente as regras do Passo 4:
    - Fluxos (receita, lucro): LTM (soma dos últimos 4 trimestres) e acumulado do ano (YTD)
      comparado ao mesmo período de 2025.
    - Estoques (clientes, depósitos, crédito): valor do último trimestre disponível, rotulado com o trimestre.
    - Basileia, Capital Principal, RWA: último trimestre disponível.
    - ARPAC e custo para servir: do trimestre ou do acumulado do ano, nunca misturados com a média anual.
    """
    if annual is None:
        annual = load_financial_history()
    if quarterly is None:
        quarterly = load_financial_quarterly()
    if risk_df is None:
        risk_df, _ = load_capital_risk_history()

    q_sorted = quarterly.sort_values("periodo_fim").reset_index(drop=True)
    q_2026 = q_sorted[q_sorted["ano"] == 2026].copy()
    q_2025 = q_sorted[q_sorted["ano"] == 2025].copy()

    latest_q = q_sorted.iloc[-1]
    latest_q_label = str(latest_q["trimestre"])
    latest_q_date = str(latest_q["periodo_fim"])
    n_quarters_2026 = len(q_2026)

    # Mesmos trimestres de 2025 para comparação YTD equivalente (ex.: 1T25 + 2T25 vs 1T26 + 2T26)
    q_2025_same = q_2025.iloc[:n_quarters_2026].copy()
    ytd_label_2026 = f"YTD {latest_q_label}" if n_quarters_2026 > 1 else latest_q_label
    ytd_label_2025 = (
        f"YTD {q_2025_same.iloc[-1]['trimestre']}"
        if len(q_2025_same) > 1
        else str(q_2025_same.iloc[-1]["trimestre"])
    )

    # LTM: últimos 4 trimestres disponíveis (ex.: 3T25 a 2T26)
    ltm_window = q_sorted.tail(4).copy()
    ltm_start_q = str(ltm_window.iloc[0]["trimestre"])
    ltm_end_q = str(ltm_window.iloc[-1]["trimestre"])
    ltm_label = f"LTM {ltm_end_q} ({ltm_start_q}–{ltm_end_q})"

    ltm_revenue = round(float(ltm_window["receita"].sum()), 4)
    ltm_net_income = round(float(ltm_window["lucro_liquido_ifrs"].sum()), 4)
    ltm_net_margin_pct = round(100.0 * ltm_net_income / ltm_revenue, 1) if ltm_revenue else 0.0

    ytd_2026_revenue = round(float(q_2026["receita"].sum()), 4)
    ytd_2025_revenue = round(float(q_2025_same["receita"].sum()), 4)
    ytd_revenue_yoy_pct = (
        round(100.0 * (ytd_2026_revenue / ytd_2025_revenue - 1.0), 1)
        if ytd_2025_revenue
        else 0.0
    )

    ytd_2026_net_income = round(float(q_2026["lucro_liquido_ifrs"].sum()), 4)
    ytd_2025_net_income = round(float(q_2025_same["lucro_liquido_ifrs"].sum()), 4)
    ytd_net_income_yoy_pct = (
        round(100.0 * (ytd_2026_net_income / ytd_2025_net_income - 1.0), 1)
        if ytd_2025_net_income
        else 0.0
    )

    ytd_2026_arpac_avg = round(float(q_2026["arpac_mensal"].mean()), 2)
    ytd_2025_arpac_avg = round(float(q_2025_same["arpac_mensal"].mean()), 2)
    ytd_2026_cost_avg = round(float(q_2026["custo_servir_mensal"].mean()), 2)
    ytd_2025_cost_avg = round(float(q_2025_same["custo_servir_mensal"].mean()), 2)

    q_2025_ref = q_2025_same.iloc[-1]
    stocks_latest = {
        "trimestre_referencia": latest_q_label,
        "periodo_fim": latest_q_date,
        "clientes_m": float(latest_q["clientes"]),
        "clientes_yoy_pct": round(
            100.0 * (float(latest_q["clientes"]) / float(q_2025_ref["clientes"]) - 1.0), 1
        ),
        "depositos_usd_b": float(latest_q["depositos"]),
        "depositos_yoy_pct": round(
            100.0 * (float(latest_q["depositos"]) / float(q_2025_ref["depositos"]) - 1.0), 1
        ),
        "carteira_credito_usd_b": float(latest_q["carteira_credito"]),
        "carteira_credito_yoy_pct": round(
            100.0
            * (float(latest_q["carteira_credito"]) / float(q_2025_ref["carteira_credito"]) - 1.0),
            1,
        ),
        "arpac_trimestre_usd": float(latest_q["arpac_mensal"]),
        "arpac_trimestre_2025_usd": float(q_2025_ref["arpac_mensal"]),
        "custo_servir_trimestre_usd": float(latest_q["custo_servir_mensal"]),
        "custo_servir_trimestre_2025_usd": float(q_2025_ref["custo_servir_mensal"]),
        "fonte_url": str(latest_q["fonte_url"]),
    }

    # Último trimestre disponível para Basileia, Capital Principal e RWA
    risk_sorted = risk_df.sort_values("period").reset_index(drop=True)
    latest_risk = risk_sorted.iloc[-1]
    risk_period_dt = pd.to_datetime(latest_risk["period"])
    risk_q_num = (risk_period_dt.month - 1) // 3 + 1
    risk_q_label = f"{risk_q_num}T{str(risk_period_dt.year)[-2:]}"

    prudential_latest = {
        "trimestre_referencia": risk_q_label,
        "periodo_fim": risk_period_dt.strftime("%Y-%m-%d"),
        "ano": int(risk_period_dt.year),
        "parcial": "sim" if risk_period_dt.year >= 2026 else "não",
        "capital_principal_brl_b": round(float(latest_risk["capital_principal_brl_b"]), 4),
        "rwa_total_brl_b": round(float(latest_risk["rwa_total_brl_b"]), 4),
        "basel_index_pct": round(float(latest_risk["basel_index_pct"]), 2),
        "icp_pct": round(float(latest_risk["icp_pct"]), 2),
        "capital_buffer_pct": round(float(latest_risk["capital_buffer_pct"]), 2),
        "moeda": "BRL",
    }

    return {
        "reference_quarter": latest_q_label,
        "reference_date": latest_q_date,
        "partial_label": f"parcial até {latest_q_label}",
        "ltm": {
            "label": ltm_label,
            "short_label": f"LTM ({ltm_end_q})",
            "start_quarter": ltm_start_q,
            "end_quarter": ltm_end_q,
            "quarters_included": ltm_window["trimestre"].tolist(),
            "revenue_usd_b": ltm_revenue,
            "net_income_usd_b": ltm_net_income,
            "net_margin_pct": ltm_net_margin_pct,
        },
        "ytd_comparison": {
            "label_2026": ytd_label_2026,
            "label_2025": ytd_label_2025,
            "quarters_2026": q_2026["trimestre"].tolist(),
            "quarters_2025": q_2025_same["trimestre"].tolist(),
            "revenue_2026_usd_b": ytd_2026_revenue,
            "revenue_2025_usd_b": ytd_2025_revenue,
            "revenue_yoy_pct": ytd_revenue_yoy_pct,
            "net_income_2026_usd_b": ytd_2026_net_income,
            "net_income_2025_usd_b": ytd_2025_net_income,
            "net_income_yoy_pct": ytd_net_income_yoy_pct,
            "net_margin_2026_pct": round(100.0 * ytd_2026_net_income / ytd_2026_revenue, 1),
            "net_margin_2025_pct": round(100.0 * ytd_2025_net_income / ytd_2025_revenue, 1),
            "arpac_ytd_2026_usd": ytd_2026_arpac_avg,
            "arpac_ytd_2025_usd": ytd_2025_arpac_avg,
            "cost_to_serve_ytd_2026_usd": ytd_2026_cost_avg,
            "cost_to_serve_ytd_2025_usd": ytd_2025_cost_avg,
        },
        "stocks_latest": stocks_latest,
        "prudential_latest": prudential_latest,
    }


def _normalize(text: object) -> str:
    value = "" if pd.isna(text) else str(text)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return " ".join(value.lower().strip().split())


def _metric_name(description: object) -> str | None:
    d = _normalize(description)
    if d == "capital principal":
        return "capital_principal_brl_b"
    if "rwa total" in d:
        return "rwa_total_brl_b"
    if "indice de capital principal" in d:
        return "icp_pct"
    if "indice de basileia" in d:
        return "basel_index_pct"
    if "margem excedente de capital principal" in d:
        return "capital_buffer_pct"
    return None


def _shape_capital_history(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    source_period = "periodo" if "periodo" in df.columns else "period"
    df["period"] = pd.to_datetime(df[source_period], errors="coerce")
    df["metric"] = df["descricao"].map(_metric_name)
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df.dropna(subset=["period", "metric", "valor"])

    if df.empty:
        return df

    wide = (
        df.sort_values("period")
        .groupby(["period", "metric"], as_index=False)["valor"]
        .last()
        .pivot(index="period", columns="metric", values="valor")
        .reset_index()
        .sort_values("period")
    )
    wide.columns.name = None

    for col in ["capital_principal_brl_b", "rwa_total_brl_b"]:
        if col in wide and not wide[col].dropna().empty and wide[col].dropna().median() > 1_000_000:
            wide[col] = wide[col] / 1e9

    for col in ["icp_pct", "basel_index_pct", "capital_buffer_pct"]:
        if col in wide and not wide[col].dropna().empty and wide[col].dropna().median() <= 1.5:
            wide[col] = wide[col] * 100

    wide["year"] = wide["period"].dt.year
    return wide[wide["year"].between(2021, 2026)].reset_index(drop=True)


def load_capital_risk_history(refresh: bool = False) -> tuple[pd.DataFrame, str]:
    """Load the local Pilar 3 history; rebuild it from versioned XLSX files when needed."""
    long_path = PROCESSED / "capital_risk_history_long.csv"

    if refresh or not long_path.exists():
        raw = build_long_history()
    else:
        raw = pd.read_csv(long_path)

    shaped = _shape_capital_history(raw)
    if not shaped.empty:
        max_year = int(shaped["year"].max())
        label = (
            "Pilar 3 · dados regulatórios locais 2021–2026*"
            if max_year >= 2026
            else "Pilar 3 · dados regulatórios locais 2021–2025 (último disponível: 4T25)"
        )
        return shaped, label

    fallback = pd.read_csv(PROCESSED / "risk_2025_detail.csv", parse_dates=["period"])
    fallback["year"] = fallback["period"].dt.year
    return fallback, "Detalhe regulatório local de 2025"


def load_bcb_complaints_ranking() -> tuple[pd.DataFrame, str]:
    """Carrega a série oficial do Ranking de Instituições por Índice de Reclamações do Banco Central."""
    path = PROCESSED / "bcb_complaints_ranking.csv"
    if not path.exists():
        return pd.DataFrame(), "Ranking oficial do Banco Central indisponível"
    df = pd.read_csv(path)
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
    df["trimestre"] = pd.to_numeric(df["trimestre"], errors="coerce").astype("Int64")
    df["procedentes"] = pd.to_numeric(df["procedentes"], errors="coerce")
    df["clientes"] = pd.to_numeric(df["clientes"], errors="coerce")
    df["indice"] = pd.to_numeric(df["indice"], errors="coerce")
    df = df.sort_values(["ano", "trimestre", "indice"]).reset_index(drop=True)
    return (
        df,
        "Banco Central do Brasil · Ranking de Instituições por Índice de Reclamações (1T24–3T26*)",
    )


def load_customer_sample() -> tuple[pd.DataFrame, str]:
    """Load the locally versioned academic complaint sample (mantida apenas como exploratória e não representativa)."""
    path = RAW_CUSTOMER / "reclamacoes_com_insights.csv"
    if not path.exists():
        return pd.DataFrame(), "Amostra exploratória indisponível"
    return (
        pd.read_csv(path),
        "Amostra exploratória e não representativa (Reclame Aqui — estudo acadêmico complementar)",
    )


def customer_summary(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    if df.empty:
        return {"categories": pd.DataFrame(), "severity": pd.DataFrame(), "clusters": pd.DataFrame()}

    categories = pd.DataFrame()
    severity = pd.DataFrame()
    clusters = pd.DataFrame()

    if "Categoria_Primaria" in df.columns:
        categories = (
            df["Categoria_Primaria"]
            .fillna("Não classificada")
            .value_counts()
            .rename_axis("categoria")
            .reset_index(name="reclamacoes")
        )
    if "Severidade_Estimada" in df.columns:
        severity = (
            df["Severidade_Estimada"]
            .fillna("Não classificada")
            .value_counts()
            .rename_axis("severidade")
            .reset_index(name="reclamacoes")
        )
    if "Cluster" in df.columns:
        clusters = (
            df["Cluster"]
            .fillna(-1)
            .astype(int)
            .value_counts()
            .sort_index()
            .rename_axis("cluster")
            .reset_index(name="reclamacoes")
        )

    return {"categories": categories, "severity": severity, "clusters": clusters}
