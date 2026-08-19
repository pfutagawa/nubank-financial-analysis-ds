-- Perfil da amostra acadêmica de reclamações
SELECT
    Categoria_Primaria AS categoria,
    COUNT(*) AS reclamacoes,
    ROUND(100.0 * AVG(COALESCE(Perda_Financeira, 0)), 1) AS pct_com_perda_financeira,
    ROUND(100.0 * AVG(COALESCE(Problema_Seguranca, 0)), 1) AS pct_com_sinal_seguranca
FROM customer_complaints
GROUP BY Categoria_Primaria
ORDER BY reclamacoes DESC;
