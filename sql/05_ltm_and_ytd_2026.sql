-- Métricas de 2026* (ano parcial): LTM (últimos 4 trimestres), YTD 2026 vs. mesmo período de 2025 e estoques do último trimestre

-- 1) Fluxos em LTM (soma dos últimos 4 trimestres) + estoques no último trimestre disponível
SELECT
    periodo_referencia,
    janela_trimestres,
    periodo_fim,
    parcial,
    receita_ltm_usd_b,
    lucro_liquido_ifrs_ltm_usd_b,
    margem_liquida_ltm_pct,
    clientes_ultimo_trimestre_m,
    depositos_ultimo_trimestre_usd_b,
    carteira_credito_ultimo_trimestre_usd_b,
    arpac_ultimo_trimestre_usd,
    custo_servir_ultimo_trimestre_usd,
    moeda
FROM vw_financial_ltm;

-- 2) Acumulado do ano (YTD 2026 parcial) comparado ao mesmo período de 2025 (YTD 2025)
SELECT
    ano,
    periodo_acumulado,
    parcial,
    trimestres_acumulados,
    receita_ytd_usd_b,
    ROUND(
        100.0 * (receita_ytd_usd_b / LAG(receita_ytd_usd_b) OVER (ORDER BY ano) - 1.0),
        1
    ) AS receita_ytd_yoy_pct,
    lucro_liquido_ifrs_ytd_usd_b,
    ROUND(
        100.0 * (lucro_liquido_ifrs_ytd_usd_b / LAG(lucro_liquido_ifrs_ytd_usd_b) OVER (ORDER BY ano) - 1.0),
        1
    ) AS lucro_ytd_yoy_pct,
    margem_liquida_ytd_pct,
    arpac_medio_ytd_usd,
    custo_servir_medio_ytd_usd,
    trimestre_estoque,
    clientes_fim_periodo_m,
    depositos_fim_periodo_usd_b,
    carteira_credito_fim_periodo_usd_b,
    arpac_trimestre_ponta_usd,
    custo_servir_trimestre_ponta_usd,
    moeda
FROM vw_financial_ytd_vs_prior_year
ORDER BY ano;

-- 3) Estoques e indicadores prudenciais no último trimestre disponível (sem misturar moedas US$ e R$)
SELECT
    trimestre_financeiro_ref,
    data_financeiro_ref,
    financeiro_parcial,
    clientes_m,
    depositos_usd_b,
    carteira_credito_usd_b,
    arpac_mensal_usd,
    custo_servir_mensal_usd,
    trimestre_prudencial_ref,
    data_prudencial_ref,
    prudencial_parcial,
    capital_principal_brl_b,
    rwa_total_brl_b,
    basel_index_pct,
    icp_pct,
    capital_buffer_pct
FROM vw_latest_stocks_and_prudential;

