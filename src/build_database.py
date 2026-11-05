from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_pipeline import (
    load_bcb_complaints_ranking,
    load_capital_risk_history,
    load_customer_sample,
    load_financial_history,
    load_financial_quarterly,
    load_risk_detail_by_period,
)


DB_DIR = ROOT / "database"
DB_PATH = DB_DIR / "nubank_analytics.db"


SQL_VIEWS = [
    """
    CREATE VIEW IF NOT EXISTS vw_financial_ltm AS
    WITH ordered AS (
        SELECT
            *,
            ROW_NUMBER() OVER (ORDER BY periodo_fim DESC) AS rn
        FROM financial_quarterly
    ),
    last4 AS (
        SELECT * FROM ordered WHERE rn <= 4
    ),
    latest AS (
        SELECT * FROM ordered WHERE rn = 1
    ),
    earliest_last4 AS (
        SELECT * FROM ordered WHERE rn = 4
    )
    SELECT
        'LTM ' || (SELECT trimestre FROM latest) AS periodo_referencia,
        (SELECT trimestre FROM earliest_last4) || ' a ' || (SELECT trimestre FROM latest) AS janela_trimestres,
        (SELECT periodo_fim FROM latest) AS periodo_fim,
        'sim' AS parcial,
        ROUND(SUM(receita), 4) AS receita_ltm_usd_b,
        ROUND(SUM(lucro_liquido_ifrs), 4) AS lucro_liquido_ifrs_ltm_usd_b,
        ROUND(100.0 * SUM(lucro_liquido_ifrs) / NULLIF(SUM(receita), 0), 1) AS margem_liquida_ltm_pct,
        (SELECT clientes FROM latest) AS clientes_ultimo_trimestre_m,
        (SELECT depositos FROM latest) AS depositos_ultimo_trimestre_usd_b,
        (SELECT carteira_credito FROM latest) AS carteira_credito_ultimo_trimestre_usd_b,
        (SELECT arpac_mensal FROM latest) AS arpac_ultimo_trimestre_usd,
        (SELECT custo_servir_mensal FROM latest) AS custo_servir_ultimo_trimestre_usd,
        'USD' AS moeda
    FROM last4;
    """,
    """
    CREATE VIEW IF NOT EXISTS vw_financial_ytd_vs_prior_year AS
    WITH q2026_count AS (
        SELECT COUNT(*) AS n_q FROM financial_quarterly WHERE ano = 2026
    ),
    ranked AS (
        SELECT
            *,
            ROW_NUMBER() OVER (PARTITION BY ano ORDER BY periodo_fim ASC) AS q_idx
        FROM financial_quarterly
        WHERE ano IN (2025, 2026)
    ),
    filtered AS (
        SELECT r.*
        FROM ranked r
        CROSS JOIN q2026_count c
        WHERE r.q_idx <= c.n_q
    ),
    latest_per_year AS (
        SELECT *
        FROM filtered
        WHERE (ano, q_idx) IN (
            SELECT ano, MAX(q_idx) FROM filtered GROUP BY ano
        )
    )
    SELECT
        f.ano,
        CASE
            WHEN f.ano = 2026 THEN 'YTD ' || l.trimestre || ' (parcial)'
            ELSE 'YTD ' || l.trimestre
        END AS periodo_acumulado,
        MAX(f.parcial) AS parcial,
        COUNT(*) AS trimestres_acumulados,
        ROUND(SUM(f.receita), 4) AS receita_ytd_usd_b,
        ROUND(SUM(f.lucro_liquido_ifrs), 4) AS lucro_liquido_ifrs_ytd_usd_b,
        ROUND(100.0 * SUM(f.lucro_liquido_ifrs) / NULLIF(SUM(f.receita), 0), 1) AS margem_liquida_ytd_pct,
        ROUND(AVG(f.arpac_mensal), 2) AS arpac_medio_ytd_usd,
        ROUND(AVG(f.custo_servir_mensal), 2) AS custo_servir_medio_ytd_usd,
        l.trimestre AS trimestre_estoque,
        l.clientes AS clientes_fim_periodo_m,
        l.depositos AS depositos_fim_periodo_usd_b,
        l.carteira_credito AS carteira_credito_fim_periodo_usd_b,
        l.arpac_mensal AS arpac_trimestre_ponta_usd,
        l.custo_servir_mensal AS custo_servir_trimestre_ponta_usd,
        'USD' AS moeda
    FROM filtered f
    JOIN latest_per_year l ON l.ano = f.ano
    GROUP BY f.ano;
    """,
    """
    CREATE VIEW IF NOT EXISTS vw_latest_stocks_and_prudential AS
    WITH latest_fin AS (
        SELECT * FROM financial_quarterly ORDER BY periodo_fim DESC LIMIT 1
    ),
    latest_risk AS (
        SELECT * FROM risk_detail_by_period ORDER BY period DESC LIMIT 1
    )
    SELECT
        f.trimestre AS trimestre_financeiro_ref,
        f.periodo_fim AS data_financeiro_ref,
        f.parcial AS financeiro_parcial,
        f.clientes AS clientes_m,
        f.depositos AS depositos_usd_b,
        f.carteira_credito AS carteira_credito_usd_b,
        f.arpac_mensal AS arpac_mensal_usd,
        f.custo_servir_mensal AS custo_servir_mensal_usd,
        r.trimestre AS trimestre_prudencial_ref,
        r.period AS data_prudencial_ref,
        r.parcial AS prudencial_parcial,
        r.capital_principal_brl_b,
        r.rwa_total_brl_b,
        r.basel_index_pct,
        r.icp_pct,
        r.capital_buffer_pct
    FROM latest_fin f
    CROSS JOIN latest_risk r;
    """,
]


def build_database() -> Path:
    DB_DIR.mkdir(exist_ok=True)

    financial = load_financial_history()
    financial_quarterly = load_financial_quarterly()
    risk, _ = load_capital_risk_history()
    risk_detail = load_risk_detail_by_period()
    bcb_complaints, _ = load_bcb_complaints_ranking()
    complaints, _ = load_customer_sample()

    with sqlite3.connect(DB_PATH) as conn:
        for view_name in (
            "vw_financial_ltm",
            "vw_financial_ytd_vs_prior_year",
            "vw_latest_stocks_and_prudential",
        ):
            conn.execute(f"DROP VIEW IF EXISTS {view_name}")

        financial.to_sql("financial_history", conn, if_exists="replace", index=False)
        financial_quarterly.to_sql("financial_quarterly", conn, if_exists="replace", index=False)
        risk.to_sql("capital_risk_history", conn, if_exists="replace", index=False)
        risk_detail.to_sql("risk_detail_by_period", conn, if_exists="replace", index=False)
        if not bcb_complaints.empty:
            bcb_complaints.to_sql("bcb_complaints_ranking", conn, if_exists="replace", index=False)
        if not complaints.empty:
            complaints.to_sql("customer_complaints", conn, if_exists="replace", index=False)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_financial_year ON financial_history(year)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_quarterly_period ON financial_quarterly(periodo_fim)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_quarterly_year ON financial_quarterly(ano)"
        )
        if "period" in risk.columns:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_risk_period ON capital_risk_history(period)")
        if "period" in risk_detail.columns:
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_risk_detail_period ON risk_detail_by_period(period)"
            )

        for view_sql in SQL_VIEWS:
            conn.execute(view_sql)

    return DB_PATH


if __name__ == "__main__":
    path = build_database()
    print(f"Banco analítico criado em: {path}")
