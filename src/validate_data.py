from __future__ import annotations

from pathlib import Path

import pandas as pd

try:
    from src.ingest_pillar3 import build_long_history
except ModuleNotFoundError:
    from ingest_pillar3 import build_long_history


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"


def validate_financial_history() -> None:
    df = pd.read_csv(PROCESSED / "financial_history.csv")
    required = {
        "year",
        "customers_m",
        "activity_rate_pct",
        "arpac_usd",
        "deposits_usd_b",
        "revenue_usd_b",
        "net_income_usd_b",
        "source_url",
    }
    missing = required - set(df.columns)
    assert not missing, f"Colunas ausentes em financial_history: {sorted(missing)}"
    assert df["year"].tolist() == [2021, 2022, 2023, 2024, 2025], "A série deve cobrir 2021–2025 sem lacunas anuais"
    assert df["year"].is_unique, "Ano duplicado na série financeira"
    assert (df["customers_m"] > 0).all()
    assert df["activity_rate_pct"].between(0, 100).all()
    assert (df["revenue_usd_b"] > 0).all()
    assert (df["deposits_usd_b"] > 0).all()
    assert df["source_url"].str.startswith("https://www.sec.gov/").all(), "A série financeira deve apontar para fontes SEC/Nu primárias"


def validate_vendored_sources() -> None:
    xlsx = sorted((RAW / "pillar3").glob("20*/*.xlsx"))
    assert len(xlsx) == 18, f"Esperados 18 arquivos regulatórios locais; encontrados {len(xlsx)}"

    years = {path.parent.name for path in xlsx}
    assert years == {"2021", "2022", "2023", "2024", "2025"}, f"Cobertura regulatória incompleta: {sorted(years)}"

    complaints_path = RAW / "customer" / "reclamacoes_com_insights.csv"
    assert complaints_path.exists(), "A amostra local de reclamações está ausente"
    complaints = pd.read_csv(complaints_path)
    required_customer = {"Reclamacao", "Categoria_Primaria", "Severidade_Estimada", "Cluster"}
    missing_customer = required_customer - set(complaints.columns)
    assert not missing_customer, f"Colunas ausentes na amostra de reclamações: {sorted(missing_customer)}"


def validate_regulatory_ingestion() -> None:
    df = build_long_history()
    assert not df.empty, "A ingestão local do Pilar 3 não produziu registros"
    years = set(pd.to_datetime(df["periodo"]).dt.year.unique())
    assert {2021, 2022, 2023, 2024, 2025}.issubset(years), f"Anos regulatórios ausentes após ingestão: {sorted(years)}"
    assert df["valor"].notna().all()
    assert df["descricao"].astype(str).str.len().gt(0).all()


def validate_risk_detail() -> None:
    df = pd.read_csv(PROCESSED / "risk_2025_detail.csv", parse_dates=["period"])
    required = {
        "quarter",
        "period",
        "capital_principal_brl_b",
        "rwa_total_brl_b",
        "icp_pct",
        "basel_index_pct",
        "rwa_credito_brl_b",
    }
    missing = required - set(df.columns)
    assert not missing, f"Colunas ausentes em risk_2025_detail: {sorted(missing)}"
    assert df["quarter"].tolist() == ["Q1", "Q2", "Q3"]
    assert (df["capital_principal_brl_b"] > 0).all()
    assert (df["rwa_total_brl_b"] > 0).all()
    assert df["basel_index_pct"].between(0, 100).all()
    assert df["icp_pct"].between(0, 100).all()


if __name__ == "__main__":
    validate_financial_history()
    validate_vendored_sources()
    validate_regulatory_ingestion()
    validate_risk_detail()
    print("Validação concluída: fontes locais e datasets 2021–2025 consistentes.")
