-- 1) Série oficial primária: Ranking de Instituições por Índice de Reclamações do Banco Central (Nu Pagamentos, Itaú e Bradesco)
SELECT
    periodo,
    ano,
    trimestre,
    parcial_2026,
    valores_extrapolados,
    instituicao,
    procedentes,
    clientes,
    indice,
    motivos,
    fonte_url
FROM bcb_complaints_ranking
ORDER BY ano, trimestre, indice ASC;

-- 2) Amostra antiga do Reclame Aqui (mantida apenas como exploratória e não representativa)
SELECT
    Categoria_Primaria AS categoria,
    COUNT(*) AS reclamacoes,
    ROUND(100.0 * AVG(COALESCE(Perda_Financeira, 0)), 1) AS pct_com_perda_financeira,
    ROUND(100.0 * AVG(COALESCE(Problema_Seguranca, 0)), 1) AS pct_com_sinal_seguranca
FROM customer_complaints
GROUP BY Categoria_Primaria
ORDER BY reclamacoes DESC;
