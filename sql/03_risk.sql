-- Capital regulatório, RWA e índices prudenciais
SELECT
    period,
    capital_principal_brl_b,
    rwa_total_brl_b,
    basel_index_pct,
    icp_pct,
    capital_buffer_pct,
    ROUND(rwa_total_brl_b / NULLIF(capital_principal_brl_b, 0), 2) AS rwa_por_unidade_capital
FROM capital_risk_history
ORDER BY period;
