# Nubank em Dados — Crescimento, Rentabilidade, Risco e Mercado (2021–2026*)

[![Dashboard Online (GitHub Pages)](https://img.shields.io/badge/🌐_Dashboard_Online-pfutagawa.github.io-820AD1?style=for-the-badge)](https://pfutagawa.github.io/nubank-financial-analysis-ds/)

👉 **Acesse o dashboard interativo no GitHub Pages:** [**https://pfutagawa.github.io/nubank-financial-analysis-ds/**](https://pfutagawa.github.io/nubank-financial-analysis-ds/)

Projeto de portfólio em Ciência de Dados e Analytics que integra cotações históricas de mercado (MongoDB + Twelve Data API), métricas financeiras oficiais da Nu Holdings (anual 2021–2025 e trimestral `1T25–2T26*`), dados regulatórios do Pilar 3 e a série oficial do **Ranking de Instituições por Índice de Reclamações do Banco Central (`1T24–3T26*`)** para responder a uma pergunta central:

> **Como o crescimento do Nubank entre 2021 e 2026* se traduziu em monetização, rentabilidade e desempenho de mercado — e quais sinais de capital, risco e experiência do cliente acompanharam essa expansão?**

*\*Nota central sobre 2026: 2026 ainda é um **ano parcial** (o Form 20-F de 2026 só será publicado em 2027). O projeto preserva a série anual fechada 2021–2025 intacta e adota grão trimestral (`1T25–2T26`) para tratar 2026* sempre com a marca `"parcial"` — exibindo fluxos (receita e lucro) em **LTM (`3T25–2T26`)** ou no **acumulado do ano (`YTD 2T26` vs. `YTD 2T25`)** e estoques no último trimestre disponível (`2T26`).*

## Duas interfaces, uma única camada de dados

O projeto possui duas formas de consumo construídas sobre os mesmos datasets tratados:

- **GitHub Pages (`github.io`):** [**https://pfutagawa.github.io/nubank-financial-analysis-ds/**](https://pfutagawa.github.io/nubank-financial-analysis-ds/) — versão pública responsiva e interativa para acesso imediato no navegador, com seletor de visão (`2021–2025 + 2026* LTM`, `YTD 2026 vs. YTD 2025`, `Anos fechados 2021–2025` e `Série trimestral 1T25–2T26*`).
- **Streamlit / Python (`app.py`):** versão analítica local conectada ao MongoDB (`nubank_db.historico_diario`), com os mesmos seletores de visão para `2026*`, filtros interativos de tickers na barra lateral e abas temáticas.

## Produto analítico

A análise combina **Python, Pandas, MongoDB (PyMongo), SQL, SQLite, Plotly, Streamlit, HTML/CSS e JavaScript**, com fontes rastreáveis e validação automatizada.

O produto está organizado em seis frentes:

1. **Mercado e Cotações (MongoDB)** — série histórica longa (`outputsize=1000`, até `08/10/2026`) de `NU`, `ITUB` e `BBD`, com filtro interativo de tickers, preço de fechamento, desempenho normalizado (Base 100) e volume negociado.
2. **Visão geral (2021–2026\*)** — clientes, receita, depósitos, ARPAC e carteiras de crédito, diferenciando visualmente `2026*` parcial com barras hachuradas.
3. **Rentabilidade e eficiência** — lucro líquido IFRS, margens e comparação entre visões LTM, YTD e trimestral.
4. **Capital e risco** — Capital Principal, RWA, Índice de Basileia, ICP e componentes de risco (em R$, até o último trimestre disponível na base local).
5. **Experiência do cliente (Série Oficial do Banco Central)** — comparação trimestral (`1T24–3T26*`) do Índice de Reclamações reguladas procedentes do BCB entre **Nu Pagamentos (Nubank)**, **Itaú** e **Bradesco** (com nota metodológica de valores extrapolados desde o 2º tri/2024), mantendo a amostra antiga do Reclame Aqui apenas em apêndice colapsado como `"exploratória, não representativa"`.
6. **Metodologia** — fontes, reconciliação trimestral-anual, unidades, arquitetura e limitações.

## Principais indicadores da série (2021–2026*)

| Indicador | 2021 (fechado) | 2025 (20-F fechado) | 2026* (parcial · período de referência) |
|---|---:|---:|---:|
| Clientes (estoque) | 53,9 mi | 131,0 mi | **139,0 mi** (`2T26` · 30/06/2026) |
| Receita IFRS (fluxo) | US$ 1,70 bi | US$ 15,77 bi | **US$ 19,34 bi** (`LTM 2T26`: 3T25–2T26) / **US$ 10,48 bi** (`YTD 2T26` vs. US$ 6,92 bi no `YTD 2T25`) |
| Lucro líquido IFRS (fluxo) | -US$ 0,17 bi | US$ 2,87 bi | **US$ 3,61 bi** (`LTM 2T26`: 3T25–2T26) / **US$ 1,93 bi** (`YTD 2T26` vs. US$ 1,19 bi no `YTD 2T25`) |
| Depósitos (estoque) | US$ 9,7 bi | US$ 41,9 bi | **US$ 45,3 bi** (`2T26` · 30/06/2026) |
| Carteira de crédito total (estoque) | US$ 6,6 bi | US$ 32,7 bi | **US$ 39,4 bi** (`2T26` · 30/06/2026) |
| ARPAC mensal | US$ 4,5 | US$ 13,3 | **US$ 17,1** (trimestre `2T26`) / **US$ 16,5** (média `YTD 2T26`) |
| Custo mensal de servir | US$ 0,9 | US$ 0,8 | **US$ 1,0** (trimestre `2T26` e média `YTD 2T26`) |
| Índice de Basileia / RWA (Pilar 3, R$) | 13,31% (4T21) | 16,57% / R$ 171,1 bi (4T25) | **16,57% / R$ 171,1 bi** (último disponível localmente: `4T25`) |
| Índice de Reclamações BCB (Nu / Itaú / Bradesco) | n/d na série 2024+ | **15,93** / 50,06 / 54,48 (`4T25`) | **10,68** / 43,20 / 57,23 (`3T26*` · valores extrapolados desde `2T24`) |

As variações e relações entre indicadores são calculadas a partir da camada de dados (`src/data_pipeline.py` e SQLite), evitando conclusões fixadas manualmente na interface.

## Fontes

### Resultados financeiros e operacionais (SEC — CIK `0001691493`)

A série anual fechada (`data/processed/financial_history.csv`, 2021–2025) e a série trimestral (`data/processed/financial_quarterly.csv`, `1T25–2T26*`) foram curadas exclusivamente a partir de divulgações oficiais da Nu Holdings Ltd. arquivadas na SEC:

- **2021 (Anual):** Nu Q4/FY 2021 Results — SEC Form 6-K  
  `https://www.sec.gov/Archives/edgar/data/1691493/000129281422000794/nuq421_6k.htm`
- **2022–2024 (Anual):** Nu Form 20-F 2024  
  `https://www.sec.gov/Archives/edgar/data/1691493/000129281425001514/nuform20f_2024.htm`
- **2025 (Anual e 4T25):** Nu Form 20-F 2025  
  `https://www.sec.gov/Archives/edgar/data/1691493/000129281426002166/nuform20f_2025.htm`
- **1T25 (Trimestral — 31/03/2025):** Nu Form 6-K Q1 2025  
  `https://www.sec.gov/Archives/edgar/data/1691493/000129281425002061/nufs1q25_6k.htm`
- **2T25 (Trimestral — 30/06/2025):** Nu Form 6-K Q2 2025  
  `https://www.sec.gov/Archives/edgar/data/1691493/000129281425002998/nufs2q25_6k.htm`
- **3T25 (Trimestral — 30/09/2025):** Nu Form 6-K Q3 2025  
  `https://www.sec.gov/Archives/edgar/data/1691493/000129281425003943/nufs3q25_6k.htm`
- **1T26* (Trimestral parcial — 31/03/2026):** Nu Form 6-K Q1 2026  
  `https://www.sec.gov/Archives/edgar/data/1691493/000129281426003053/nufs1q26_6k.htm`
- **2T26* (Trimestral parcial — 30/06/2026):** Nu Form 6-K Q2 2026  
  `https://www.sec.gov/Archives/edgar/data/1691493/000129281426004222/nufs2q26_6k.htm`

### Capital e risco (Pilar 3 / Banco Central)

Os arquivos regulatórios do **Pilar 3** estão versionados neste próprio repositório em `data/raw/pillar3/2021` a `data/raw/pillar3/2025`, com a pasta `data/raw/pillar3/2026/` pronta para receber os anexos trimestrais de 2026.

O pipeline `src/ingest_pillar3.py` processa `2021–2026*` e gera `data/processed/capital_risk_history_long.csv` e o detalhamento prudencial generalizado por período `data/processed/risk_detail_by_period.csv` (preservando `data/processed/risk_2025_detail.csv` por compatibilidade).

### Experiência do cliente (Banco Central do Brasil — Dados Abertos)

A camada principal de Experiência do Cliente utiliza a série oficial do **Ranking de Instituições por Índice de Reclamações do Banco Central do Brasil** (`data/processed/bcb_complaints_ranking.csv`, cobrindo `1T24–3T26*`) para **Nu Pagamentos (Nubank)**, **Itaú** e **Bradesco**:

- **Portal de Dados Abertos do BCB:**  
  `https://dadosabertos.bcb.gov.br/dataset/ranking-de-instituicoes-por-indice-de-reclamacoes`
- **Endpoint REST Oficial (RDR Ranking Trimestral):**  
  `https://www3.bcb.gov.br/rdrweb/rest/ext/ranking/arquivo?ano={ano}&periodicidade=TRIMESTRAL&periodo={trimestre}&tipo=Bancos+e+Financeiras`
- **Nota metodológica preservada:** A partir do **2º trimestre de 2024 (`2T24`)**, o Banco Central passou a divulgar o ranking com **valores extrapolados** (estimativa estatística do total de reclamações reguladas procedentes a partir de amostra das demandas encerradas no trimestre).
- **Amostra antiga do Reclame Aqui (`data/raw/customer/`):** Mantida no repositório exclusivamente como `"exploratória, não representativa"`, recolhida em apêndice colapsado com aviso explícito nos dois dashboards (`docs/` e `app.py`).

## Arquitetura

```text
.
├── app.py                                # dashboard Streamlit (2021–2026* com seletor LTM/YTD e BCB Ranking)
├── ingestao.py                           # ingestão manual de cotações (Twelve Data → MongoDB)
├── NOTAS_ATUALIZACAO.md                  # decisões, reconciliação 2025, BCB/Consumidor.gov.br e guia 3T26/20-F
├── data/
│   ├── raw/
│   │   ├── pillar3/
│   │   │   ├── 2021/ ... 2025/           # XLSX regulatórios versionados
│   │   │   └── 2026/                     # pasta pronta para os XLSX do Pilar 3 de 2026
│   │   ├── customer/                     # amostra exploratória (não representativa) do Reclame Aqui
│   │   └── macro/                        # série macro de referência
│   ├── processed/
│   │   ├── financial_history.csv         # série anual fechada 2021–2025 (intacta)
│   │   ├── financial_quarterly.csv       # série trimestral 1T25–2T26* (parcial=sim em 2026)
│   │   ├── bcb_complaints_ranking.csv    # série oficial do Ranking de Reclamações BCB (1T24–3T26*)
│   │   ├── capital_risk_history_long.csv # histórico longo do Pilar 3
│   │   ├── risk_detail_by_period.csv     # detalhamento KM1/OV1/MR1 por trimestre
│   │   ├── risk_2025_detail.csv          # recorte 2025 preservado para compatibilidade
│   │   └── market_history.csv            # snapshot local de 3.000 cotações diárias
│   └── source_manifest.csv               # manifesto rastreável de todas as fontes
├── database/
│   └── nubank_analytics.db               # SQLite com tabelas e views LTM/YTD + bcb_complaints_ranking
├── docs/
│   ├── index.html                        # dashboard público GitHub Pages (2021–2026*)
│   ├── css/style.css
│   ├── js/dashboard.js
│   └── data/dashboard-data.json          # gerado por python -m src.build_web_data
├── src/
│   ├── data_pipeline.py                  # carga local, LTM, YTD, estoques 2026* e BCB Ranking
│   ├── ingest_sec_quarterly.py           # verificação/download SEC com User-Agent identificado
│   ├── ingest_pillar3.py                 # processamento dos XLSX locais (2021–2026*)
│   ├── ingest_complaints.py              # ingestão do Ranking BCB e verificação Consumidor.gov.br
│   ├── build_database.py                 # construção da camada SQLite e views de 2026*
│   ├── build_web_data.py                 # gera payload da versão pública com as 3 visões
│   └── validate_data.py                  # reconciliação 2025 e validações de integridade
├── sql/
│   ├── 01_growth.sql
│   ├── 02_profitability.sql
│   ├── 03_risk.sql
│   ├── 04_customer.sql                   # consultas na série oficial BCB + amostra exploratória
│   └── 05_ltm_and_ytd_2026.sql           # consultas LTM e YTD 2026* vs. 2025
├── tests/
│   └── test_verificacoes.py              # testes unitários de ingestão, reconciliação, métricas 2026* e BCB Ranking
└── .github/workflows/                    # validação, testes, build e deploy
```

## Reprodutibilidade

### Windows / PowerShell

Na raiz do repositório:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m ensurepip --upgrade
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
.\.venv\Scripts\python.exe .\src\ingest_pillar3.py
.\.venv\Scripts\python.exe .\src\ingest_complaints.py
.\.venv\Scripts\python.exe .\src\validate_data.py
.\.venv\Scripts\python.exe .\src\build_database.py
.\.venv\Scripts\python.exe -m src.build_web_data
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
.\.venv\Scripts\python.exe -m streamlit run .\app.py
```

### Linux / macOS

```bash
./.venv/bin/python src/ingest_pillar3.py
./.venv/bin/python src/ingest_complaints.py
./.venv/bin/python src/validate_data.py
./.venv/bin/python src/build_database.py
./.venv/bin/python -m src.build_web_data
./.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v
./.venv/bin/streamlit run app.py
```

## Status

- [x] dashboard Streamlit em português atualizado para `2021–2026*`
- [x] série financeira anual oficial `2021–2025` intacta
- [x] série financeira trimestral `1T25–2T26*` com reconciliação 2025 validada (`Δ <= 0,01 bi`)
- [x] métricas de `2026*` parcial implementadas (`LTM`, `YTD vs. 2025` e estoques em `2T26`)
- [x] pipeline regulatório Pilar 3 pronto para `2021–2026*` e detalhamento generalizado por período
- [x] camada SQLite + SQL com views `vw_financial_ltm`, `vw_financial_ytd_vs_prior_year` e `vw_latest_stocks_and_prudential`
- [x] série oficial do **Ranking de Reclamações do Banco Central (`1T24–3T26*`)** para Nu Pagamentos, Itaú e Bradesco (com nota de valores extrapolados desde `2T24`) e amostra antiga do Reclame Aqui mantida apenas como exploratória/não representativa
- [x] versão pública responsiva em GitHub Pages (`docs/`) com seletor de visão e destaque visual para `2026*` parcial
- [x] documentação técnica e guia de atualização futura em `NOTAS_ATUALIZACAO.md`
- [ ] adição manual dos XLSX do Pilar 3 de 2026 em `data/raw/pillar3/2026/` e merge na `main` após revisão

## Aviso

Projeto independente para fins acadêmicos e de portfólio. Não é afiliado à Nu Holdings Ltd. e não constitui recomendação de investimento.
