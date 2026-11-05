from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import pandas as pd
from pymongo import MongoClient
from pymongo.errors import PyMongoError

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


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "data" / "dashboard-data.json"
MARKET_CSV = ROOT / "data" / "processed" / "market_history.csv"


def clean_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if hasattr(value, "item"):
        return value.item()
    return value


def records(df: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {key: clean_value(value) for key, value in row.items()}
        for row in df.to_dict(orient="records")
    ]


def _configure_dns() -> None:
    """Configura DNS público (Google/Cloudflare) no dnspython para evitar timeout do 127.0.0.53 em queries SRV do mongodb+srv://."""
    try:
        import dns.resolver

        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = ["8.8.8.8", "1.1.1.1", "8.8.4.4"]
        resolver.timeout = 3.0
        resolver.lifetime = 6.0
        dns.resolver.default_resolver = resolver
    except Exception:
        pass


def load_market_history() -> pd.DataFrame:
    """Carrega historico_diario do MongoDB (se MONGO_URI disponível) ou do snapshot market_history.csv."""
    for env_candidate in (ROOT / ".env", ROOT.parent / ".env"):
        if env_candidate.exists():
            load_dotenv(dotenv_path=env_candidate)
            break

    mongo_uri = os.getenv("MONGO_URI")
    docs: list[dict[str, Any]] = []
    if mongo_uri:
        _configure_dns()
        client = None
        try:
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=8000, connectTimeoutMS=8000)
            collection = client["nubank_db"]["historico_diario"]
            docs = list(
                collection.find(
                    {},
                    {
                        "_id": 0,
                        "ticker": 1,
                        "datetime": 1,
                        "open": 1,
                        "high": 1,
                        "low": 1,
                        "close": 1,
                        "volume": 1,
                    },
                )
            )
        except PyMongoError as exc:
            print(f"Aviso MongoDB ({type(exc).__name__}): usando fallback local se disponível.")
            docs = []
        finally:
            if client:
                client.close()

    if docs:
        df = pd.DataFrame(docs)
        if MARKET_CSV.parent.exists():
            df.sort_values(["ticker", "datetime"]).to_csv(MARKET_CSV, index=False)
    elif MARKET_CSV.exists():
        df = pd.read_csv(MARKET_CSV)
    else:
        return pd.DataFrame(columns=["ticker", "datetime", "open", "high", "low", "close", "volume"])

    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["ticker", "datetime", "close"]).sort_values(["ticker", "datetime"]).reset_index(drop=True)
    return df[["ticker", "datetime", "open", "high", "low", "close", "volume"]]


def _build_views(
    financial: pd.DataFrame,
    quarterly: pd.DataFrame,
    metrics_2026: dict[str, Any],
) -> dict[str, Any]:
    """Constrói as visões obrigatórias para o dashboard sem misturar 2026 parcial com anos fechados."""
    closed_rows = []
    for row in records(financial):
        closed_rows.append(
            {
                **row,
                "period_label": str(row["year"]),
                "parcial": "não",
                "is_partial": False,
                "reference_note": f"Ano fechado {row['year']} (20-F)",
            }
        )

    ref_q = metrics_2026["reference_quarter"]
    ltm = metrics_2026["ltm"]
    ytd = metrics_2026["ytd_comparison"]
    stocks = metrics_2026["stocks_latest"]

    ltm_2026_row = {
        "year": 2026,
        "period_label": f"2026* (LTM {ref_q})",
        "short_label": f"2026* ({ metrics_2026['partial_label'] })",
        "parcial": "sim",
        "is_partial": True,
        "reference_note": f"{ltm['label']} · estoques em {ref_q}",
        "customers_m": stocks["clientes_m"],
        "active_customers_m": None,
        "activity_rate_pct": None,
        "arpac_usd": stocks["arpac_trimestre_usd"],
        "cost_to_serve_usd": stocks["custo_servir_trimestre_usd"],
        "revenue_usd_b": ltm["revenue_usd_b"],
        "gross_profit_usd_b": None,
        "gross_margin_pct": None,
        "net_income_usd_b": ltm["net_income_usd_b"],
        "adjusted_net_income_usd_b": None,
        "deposits_usd_b": stocks["depositos_usd_b"],
        "credit_portfolio_usd_b": stocks["carteira_credito_usd_b"],
        "interest_earning_portfolio_usd_b": None,
        "source_url": stocks["fonte_url"],
    }

    q_2025_2q = quarterly[(quarterly["ano"] == 2025) & (quarterly["trimestre"] == "2T25")].iloc[0]
    ytd_rows = [
        {
            "year": 2025,
            "period_label": f"2025 ({ytd['label_2025']})",
            "parcial": "não",
            "is_partial": False,
            "reference_note": f"Mesmo período de 2025 ({', '.join(ytd['quarters_2025'])}) · estoques em 2T25",
            "customers_m": float(q_2025_2q["clientes"]),
            "arpac_usd": float(q_2025_2q["arpac_mensal"]),
            "arpac_ytd_avg_usd": ytd["arpac_ytd_2025_usd"],
            "cost_to_serve_usd": float(q_2025_2q["custo_servir_mensal"]),
            "cost_to_serve_ytd_avg_usd": ytd["cost_to_serve_ytd_2025_usd"],
            "revenue_usd_b": ytd["revenue_2025_usd_b"],
            "net_income_usd_b": ytd["net_income_2025_usd_b"],
            "net_margin_pct": ytd["net_margin_2025_pct"],
            "deposits_usd_b": float(q_2025_2q["depositos"]),
            "credit_portfolio_usd_b": float(q_2025_2q["carteira_credito"]),
            "interest_earning_portfolio_usd_b": clean_value(q_2025_2q["carteira_credito_juros"]),
        },
        {
            "year": 2026,
            "period_label": f"2026* (parcial até {ref_q})",
            "parcial": "sim",
            "is_partial": True,
            "reference_note": f"Acumulado 2026 ({', '.join(ytd['quarters_2026'])}) · estoques em {ref_q}",
            "customers_m": stocks["clientes_m"],
            "arpac_usd": stocks["arpac_trimestre_usd"],
            "arpac_ytd_avg_usd": ytd["arpac_ytd_2026_usd"],
            "cost_to_serve_usd": stocks["custo_servir_trimestre_usd"],
            "cost_to_serve_ytd_avg_usd": ytd["cost_to_serve_ytd_2026_usd"],
            "revenue_usd_b": ytd["revenue_2026_usd_b"],
            "net_income_usd_b": ytd["net_income_2026_usd_b"],
            "net_margin_pct": ytd["net_margin_2026_pct"],
            "deposits_usd_b": stocks["depositos_usd_b"],
            "credit_portfolio_usd_b": stocks["carteira_credito_usd_b"],
            "interest_earning_portfolio_usd_b": None,
        },
    ]

    return {
        "closed_years": closed_rows,
        "ltm": closed_rows + [ltm_2026_row],
        "ytd_comparison": ytd_rows,
        "quarterly": records(quarterly),
    }


def build_payload() -> dict[str, Any]:
    financial = load_financial_history()
    financial_quarterly = load_financial_quarterly()
    risk, risk_source = load_capital_risk_history()
    risk_detail_all = load_risk_detail_by_period()
    bcb_complaints, bcb_complaints_source = load_bcb_complaints_ranking()
    complaints, complaints_source = load_customer_sample()
    risk_detail_2025 = pd.read_csv(ROOT / "data" / "processed" / "risk_2025_detail.csv")
    manifest = pd.read_csv(ROOT / "data" / "source_manifest.csv")
    market = load_market_history()
    metrics_2026 = compute_metrics_2026(financial, financial_quarterly, risk)

    summary = customer_summary(complaints)
    latest = financial.iloc[-1]
    first = financial.iloc[0]

    latest_bcb_period = str(bcb_complaints["periodo"].iloc[-1]) if not bcb_complaints.empty else "3T26"
    latest_bcb_rows = (
        bcb_complaints[bcb_complaints["periodo"] == latest_bcb_period]
        if not bcb_complaints.empty
        else pd.DataFrame()
    )

    customer = {
        "official_source_label": bcb_complaints_source,
        "official_latest_period": latest_bcb_period,
        "official_methodology_note": (
            str(bcb_complaints["nota_metodologica"].iloc[-1])
            if not bcb_complaints.empty
            else "Valores extrapolados desde o 2º tri/2024."
        ),
        "bcb_ranking": records(bcb_complaints),
        "bcb_latest": records(latest_bcb_rows),
        "exploratory_warning": (
            "AVISO: A amostra abaixo (Reclame Aqui) é mantida exclusivamente como exploratória e não representativa. "
            "A referência oficial de reclamações do projeto é o Ranking de Instituições por Índice de Reclamações do Banco Central."
        ),
        "total": int(len(complaints)),
        "loss_share_pct": None,
        "security_signals": None,
        "categories": records(summary["categories"]),
        "severity": records(summary["severity"]),
        "clusters": records(summary["clusters"]),
        "source_label": complaints_source,
    }

    if not complaints.empty and "Perda_Financeira" in complaints.columns:
        customer["loss_share_pct"] = round(
            float(pd.to_numeric(complaints["Perda_Financeira"], errors="coerce").fillna(0).mean() * 100),
            1,
        )
    if not complaints.empty and "Problema_Seguranca" in complaints.columns:
        customer["security_signals"] = int(
            pd.to_numeric(complaints["Problema_Seguranca"], errors="coerce").fillna(0).sum()
        )

    return {
        "meta": {
            "title": "Nubank em Dados",
            "period": "2021–2026*",
            "partial_year": 2026,
            "partial_reference": metrics_2026["reference_quarter"],
            "partial_label": metrics_2026["partial_label"],
            "generated_from": "datasets versionados no próprio repositório (2021–2026*) e MongoDB (historico_diario)",
            "risk_source": risk_source,
        },
        "headline": {
            "latest_year": int(latest["year"]),
            "reference_quarter_2026": metrics_2026["reference_quarter"],
            "customers_m": float(latest["customers_m"]),
            "customers_2026_m": metrics_2026["stocks_latest"]["clientes_m"],
            "revenue_usd_b": float(latest["revenue_usd_b"]),
            "revenue_ltm_2026_usd_b": metrics_2026["ltm"]["revenue_usd_b"],
            "revenue_ytd_2026_usd_b": metrics_2026["ytd_comparison"]["revenue_2026_usd_b"],
            "net_income_usd_b": float(latest["net_income_usd_b"]),
            "net_income_ltm_2026_usd_b": metrics_2026["ltm"]["net_income_usd_b"],
            "net_income_ytd_2026_usd_b": metrics_2026["ytd_comparison"]["net_income_2026_usd_b"],
            "deposits_usd_b": float(latest["deposits_usd_b"]),
            "deposits_2026_usd_b": metrics_2026["stocks_latest"]["depositos_usd_b"],
            "customer_growth_pct": round(float((latest["customers_m"] / first["customers_m"] - 1) * 100), 1),
            "customer_growth_to_2026_pct": round(
                float((metrics_2026["stocks_latest"]["clientes_m"] / first["customers_m"] - 1) * 100), 1
            ),
            "revenue_multiple": round(float(latest["revenue_usd_b"] / first["revenue_usd_b"]), 1),
            "revenue_ltm_multiple": round(
                float(metrics_2026["ltm"]["revenue_usd_b"] / first["revenue_usd_b"]), 1
            ),
            "deposit_multiple": round(float(latest["deposits_usd_b"] / first["deposits_usd_b"]), 1),
            "deposit_2026_multiple": round(
                float(metrics_2026["stocks_latest"]["depositos_usd_b"] / first["deposits_usd_b"]), 1
            ),
        },
        "metrics_2026": metrics_2026,
        "views": _build_views(financial, financial_quarterly, metrics_2026),
        "market": records(market),
        "financial": records(financial),
        "financial_quarterly": records(financial_quarterly),
        "risk": records(risk),
        "risk_2025": records(risk_detail_2025),
        "risk_detail_by_period": records(risk_detail_all),
        "bcb_complaints_ranking": records(bcb_complaints),
        "customer": customer,
        "sources": records(manifest),
    }


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Payload web criado em {OUTPUT}")


if __name__ == "__main__":
    main()
