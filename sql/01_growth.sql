-- Crescimento anual de clientes, receita e depósitos
SELECT
    year,
    customers_m,
    ROUND(100.0 * (customers_m / LAG(customers_m) OVER (ORDER BY year) - 1), 1) AS customers_yoy_pct,
    revenue_usd_b,
    ROUND(100.0 * (revenue_usd_b / LAG(revenue_usd_b) OVER (ORDER BY year) - 1), 1) AS revenue_yoy_pct,
    deposits_usd_b,
    ROUND(100.0 * (deposits_usd_b / LAG(deposits_usd_b) OVER (ORDER BY year) - 1), 1) AS deposits_yoy_pct
FROM financial_history
ORDER BY year;
