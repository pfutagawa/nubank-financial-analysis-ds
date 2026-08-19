-- Conversão de receita em lucro ao longo do período
SELECT
    year,
    revenue_usd_b,
    gross_profit_usd_b,
    ROUND(100.0 * gross_profit_usd_b / revenue_usd_b, 1) AS gross_margin_pct,
    net_income_usd_b,
    ROUND(100.0 * net_income_usd_b / revenue_usd_b, 1) AS net_margin_pct,
    adjusted_net_income_usd_b
FROM financial_history
ORDER BY year;
