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

VALID_CURRENCIES = {"USD", "BRL"}
RECONCILIATION_TOLERANCE_USD_B = 0.01


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
    assert df["year"].tolist() == [2021, 2022, 2023, 2024, 2025], "A série anual fechada deve cobrir 2021–2025 sem lacunas"
    assert df["year"].is_unique, "Ano duplicado na série financeira anual"
    assert (df["customers_m"] > 0).all()
    assert df["activity_rate_pct"].between(0, 100).all()
    assert (df["revenue_usd_b"] > 0).all()
    assert (df["deposits_usd_b"] > 0).all()
    assert df["source_url"].notna().all() and (df["source_url"].astype(str).str.strip() != "").all()
    assert df["source_url"].str.startswith("https://www.sec.gov/").all(), "A série financeira deve apontar para fontes SEC/Nu primárias"


def validate_financial_quarterly() -> dict[str, float]:
    """Valida a série trimestral 1T25–2T26* e reconcilia os 4 trimestres de 2025 com o 20-F 2025."""
    q_path = PROCESSED / "financial_quarterly.csv"
    assert q_path.exists(), f"Arquivo trimestral ausente: {q_path}"
    q_df = pd.read_csv(q_path)

    required_cols = {
        "periodo_fim",
        "ano",
        "trimestre",
        "parcial",
        "receita",
        "lucro_liquido_ifrs",
        "clientes",
        "depositos",
        "carteira_credito",
        "carteira_credito_juros",
        "arpac_mensal",
        "custo_servir_mensal",
        "moeda",
        "unidade",
        "fonte_url",
    }
    missing = required_cols - set(q_df.columns)
    assert not missing, f"Colunas mínimas ausentes em financial_quarterly.csv: {sorted(missing)}"

    # (b) Não há períodos duplicados
    assert q_df["periodo_fim"].is_unique, "Existem datas de periodo_fim duplicadas em financial_quarterly.csv"
    assert q_df["trimestre"].is_unique, "Existem trimestres duplicados em financial_quarterly.csv"

    # (c) Todo período de 2026 tem parcial = sim (e anos fechados <= 2025 têm parcial = não)
    q_2026 = q_df[q_df["ano"] == 2026]
    assert not q_2026.empty, "A série trimestral deve conter os períodos disponíveis de 2026"
    assert (q_2026["parcial"] == "sim").all(), "Todo período de 2026 deve ter parcial = sim"

    q_closed = q_df[q_df["ano"] <= 2025]
    assert (q_closed["parcial"] == "não").all(), "Períodos de anos fechados (<= 2025) devem ter parcial = não"

    # (d) Unidades e moedas válidas
    assert set(q_df["moeda"].dropna().unique()).issubset(VALID_CURRENCIES), f"Moedas inválidas: {q_df['moeda'].unique()}"
    assert (q_df["moeda"] == "USD").all(), "Os resultados financeiros da Nu devem estar preservados em USD"
    assert q_df["unidade"].notna().all() and (q_df["unidade"].astype(str).str.strip() != "").all(), "Coluna unidade vazia"

    # (e) Toda linha tem fonte_url válida da SEC
    assert q_df["fonte_url"].notna().all(), "Há linhas sem fonte_url em financial_quarterly.csv"
    assert (q_df["fonte_url"].astype(str).str.strip() != "").all(), "Há fonte_url em branco em financial_quarterly.csv"
    assert q_df["fonte_url"].astype(str).str.startswith("https://www.sec.gov/").all(), (
        "Toda fonte_url em financial_quarterly.csv deve apontar para documento oficial na SEC"
    )

    # (a) Reconciliação 2025: soma dos 4 trimestres de 2025 bate com o total anual do 20-F 2025 (tolerância 0,01 bi)
    q_2025 = q_df[q_df["ano"] == 2025]
    assert len(q_2025) == 4, f"Esperados 4 trimestres para 2025, encontrados {len(q_2025)}"

    annual_df = pd.read_csv(PROCESSED / "financial_history.csv")
    row_2025 = annual_df[annual_df["year"] == 2025].iloc[0]

    sum_rev_2025 = float(q_2025["receita"].sum())
    annual_rev_2025 = float(row_2025["revenue_usd_b"])
    diff_rev = abs(sum_rev_2025 - annual_rev_2025)
    assert diff_rev <= RECONCILIATION_TOLERANCE_USD_B, (
        f"Reconciliação de receita 2025 falhou: soma trimestral={sum_rev_2025:.4f} vs 20-F={annual_rev_2025:.4f} "
        f"(diferença={diff_rev:.4f} > {RECONCILIATION_TOLERANCE_USD_B})"
    )

    sum_net_2025 = float(q_2025["lucro_liquido_ifrs"].sum())
    annual_net_2025 = float(row_2025["net_income_usd_b"])
    diff_net = abs(sum_net_2025 - annual_net_2025)
    assert diff_net <= RECONCILIATION_TOLERANCE_USD_B, (
        f"Reconciliação de lucro líquido IFRS 2025 falhou: soma trimestral={sum_net_2025:.4f} vs 20-F={annual_net_2025:.4f} "
        f"(diferença={diff_net:.4f} > {RECONCILIATION_TOLERANCE_USD_B})"
    )

    return {
        "sum_revenue_2025": round(sum_rev_2025, 4),
        "annual_revenue_2025": round(annual_rev_2025, 4),
        "diff_revenue_2025": round(diff_rev, 4),
        "sum_net_income_2025": round(sum_net_2025, 4),
        "annual_net_income_2025": round(annual_net_2025, 4),
        "diff_net_income_2025": round(diff_net, 4),
    }


def validate_vendored_sources() -> None:
    xlsx = sorted((RAW / "pillar3").glob("20*/*.xlsx"))
    assert len(xlsx) >= 18, f"Esperados ao menos 18 arquivos regulatórios locais; encontrados {len(xlsx)}"

    years = {path.parent.name for path in xlsx}
    assert {"2021", "2022", "2023", "2024", "2025"}.issubset(years), f"Cobertura regulatória incompleta: {sorted(years)}"
    assert years.issubset({"2021", "2022", "2023", "2024", "2025", "2026"}), f"Pastas inesperadas: {sorted(years)}"

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
        "source_url",
    }
    missing = required - set(df.columns)
    assert not missing, f"Colunas ausentes em risk_2025_detail: {sorted(missing)}"
    assert set(df["quarter"].tolist()).issuperset({"Q1", "Q2", "Q3"})
    assert df["period"].is_unique, "Período duplicado em risk_2025_detail"
    assert (df["capital_principal_brl_b"] > 0).all()
    assert (df["rwa_total_brl_b"] > 0).all()
    assert df["basel_index_pct"].between(0, 100).all()
    assert df["icp_pct"].between(0, 100).all()
    assert df["source_url"].notna().all()

    detail_period_path = PROCESSED / "risk_detail_by_period.csv"
    assert detail_period_path.exists(), "Arquivo generalizado risk_detail_by_period.csv ausente"
    detail_df = pd.read_csv(detail_period_path)
    assert detail_df["period"].is_unique, "Período duplicado em risk_detail_by_period.csv"
    assert (detail_df["moeda"] == "BRL").all(), "Métricas do Pilar 3 devem estar em BRL"
    assert detail_df["source_url"].notna().all()
    if (detail_df["year"] >= 2026).any():
        assert (detail_df.loc[detail_df["year"] >= 2026, "parcial"] == "sim").all()


def validate_bcb_complaints_ranking() -> None:
    """Valida a série oficial do Ranking de Reclamações do Banco Central (Nu Pagamentos, Itaú e Bradesco)."""
    bcb_path = PROCESSED / "bcb_complaints_ranking.csv"
    assert bcb_path.exists(), f"Série oficial do Ranking BCB ausente: {bcb_path}"
    df = pd.read_csv(bcb_path)

    required_cols = {
        "periodo",
        "ano",
        "trimestre",
        "parcial_2026",
        "valores_extrapolados",
        "instituicao",
        "procedentes",
        "clientes",
        "indice",
        "motivos",
        "nota_metodologica",
        "fonte_url",
    }
    missing = required_cols - set(df.columns)
    assert not missing, f"Colunas ausentes em bcb_complaints_ranking.csv: {sorted(missing)}"

    expected_insts = {"Nu Pagamentos (Nubank)", "Itaú", "Bradesco"}
    assert set(df["instituicao"].unique()) == expected_insts, (
        f"Instituições esperadas {expected_insts}, encontradas {set(df['instituicao'].unique())}"
    )

    # Sem duplicidade de (periodo, instituicao)
    assert not df.duplicated(subset=["periodo", "instituicao"]).any(), (
        "Existem pares (periodo, instituicao) duplicados em bcb_complaints_ranking.csv"
    )

    # Regra 2026 parcial
    assert (df.loc[df["ano"] == 2026, "parcial_2026"] == "sim").all(), "Períodos de 2026 devem ter parcial_2026 = sim"
    assert (df.loc[df["ano"] <= 2025, "parcial_2026"] == "não").all(), "Períodos <= 2025 devem ter parcial_2026 = não"

    # Preservação da nota metodológica (valores extrapolados desde o 2º tri/2024)
    assert (df.loc[df["periodo"] == "1T24", "valores_extrapolados"] == "não").all(), (
        "O 1T24 deve ter valores_extrapolados = não"
    )
    assert (df.loc[df["periodo"] != "1T24", "valores_extrapolados"] == "sim").all(), (
        "Todos os períodos a partir do 2T24 devem ter valores_extrapolados = sim"
    )
    assert df.loc[df["periodo"] != "1T24", "nota_metodologica"].astype(str).str.contains("extrapolados", case=False, na=False).all(), (
        "Todas as linhas a partir do 2T24 devem preservar a nota metodológica sobre valores extrapolados"
    )
    assert df["nota_metodologica"].notna().all(), "Coluna nota_metodologica não pode ser nula"

    # Índices, clientes e motivos preenchidos + fonte_url oficial do BCB em todas as linhas
    assert (df["indice"] > 0).all(), "Todo registro deve ter índice BCB positivo"
    assert (df["clientes"] > 0).all(), "Todo registro deve ter quantidade de clientes positiva"
    assert df["motivos"].notna().all() and (df["motivos"].astype(str).str.strip() != "").all(), (
        "Todo registro deve informar os principais motivos de reclamação"
    )
    assert df["fonte_url"].notna().all() and (df["fonte_url"].astype(str).str.strip() != "").all(), (
        "Nenhum número pode ficar sem fonte_url em bcb_complaints_ranking.csv"
    )
    assert df["fonte_url"].astype(str).str.startswith("https://www3.bcb.gov.br/").all(), (
        "Toda fonte_url em bcb_complaints_ranking.csv deve apontar para o endpoint oficial do Banco Central"
    )


def validate_source_manifest() -> None:
    manifest_path = ROOT / "data" / "source_manifest.csv"
    assert manifest_path.exists(), "data/source_manifest.csv ausente"
    manifest = pd.read_csv(manifest_path)
    datasets = set(manifest["dataset"])
    assert "financial_quarterly" in datasets, "financial_quarterly deve constar no source_manifest.csv"
    assert "bcb_complaints_ranking" in datasets, "bcb_complaints_ranking deve constar no source_manifest.csv"
    assert manifest["notes"].notna().all()


if __name__ == "__main__":
    validate_financial_history()
    reconciliation = validate_financial_quarterly()
    validate_vendored_sources()
    validate_regulatory_ingestion()
    validate_risk_detail()
    validate_bcb_complaints_ranking()
    validate_source_manifest()
    print(
        "Validação concluída: fontes locais e datasets 2021–2026* consistentes | "
        f"Reconciliação 2025: Receita Δ={reconciliation['diff_revenue_2025']:.4f} bi, "
        f"Lucro IFRS Δ={reconciliation['diff_net_income_2025']:.4f} bi (tolerância <= 0.01 bi) | "
        "Ranking BCB 1T24–3T26* validado."
    )
