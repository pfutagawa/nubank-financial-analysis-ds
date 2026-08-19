# Nubank em Dados — Crescimento, Rentabilidade e Risco (2021–2025)

Projeto de portfólio em Ciência de Dados e Analytics que integra métricas financeiras oficiais da Nu Holdings, dados regulatórios do Pilar 3 e uma amostra complementar de reclamações públicas para responder a uma pergunta central:

> **Como o crescimento do Nubank entre 2021 e 2025 se traduziu em monetização e rentabilidade — e quais sinais de capital, risco e experiência do cliente acompanharam essa expansão?**

## Duas interfaces, uma única camada de dados

O projeto possui duas formas de consumo construídas sobre os mesmos datasets tratados:

- **Streamlit / Python:** versão analítica completa para exploração local, com filtro de período e abas temáticas.
- **GitHub Pages:** versão pública responsiva para acesso imediato no navegador, sem instalação ou ambiente Python.

A URL pública preparada para o deploy é:

`https://pfutagawa.github.io/nubank-financial-analysis-ds/`

O site será publicado automaticamente pelo GitHub Actions após uma futura integração da versão aprovada à `main`.

## Produto analítico

A análise combina **Python, Pandas, SQL, SQLite, Plotly, Streamlit, HTML/CSS e JavaScript**, com fontes rastreáveis e validação automatizada.

O produto está organizado em cinco frentes:

1. **Visão geral** — clientes, receita, depósitos, ARPAC e carteiras de crédito.
2. **Rentabilidade e eficiência** — lucro líquido, margens e comparação entre métricas IFRS e ajustadas.
3. **Capital e risco** — Capital Principal, RWA, Índice de Basileia, ICP e componentes de risco.
4. **Experiência do cliente** — categorias, severidade e clusters de uma amostra acadêmica de reclamações públicas.
5. **Metodologia** — fontes, unidades, arquitetura e limitações.

## Principais indicadores da série

| Indicador | 2021 | 2025 |
|---|---:|---:|
| Clientes | 53,9 mi | 131,0 mi |
| Receita anual | US$ 1,70 bi | US$ 15,77 bi |
| Depósitos | US$ 9,7 bi | US$ 41,9 bi |
| ARPAC mensal | US$ 4,5 | US$ 13,3 |
| Lucro líquido IFRS | -US$ 0,17 bi | US$ 2,87 bi |

As variações e relações entre indicadores são calculadas a partir da camada de dados, evitando conclusões fixadas manualmente na interface.

## Fontes

### Resultados financeiros e operacionais

A série anual foi curada a partir de divulgações oficiais da Nu arquivadas na SEC:

- **2021:** Nu Q4/FY 2021 Results — SEC 6-K  
  `https://www.sec.gov/Archives/edgar/data/1691493/000129281422000527/nupr4q21_6k.htm`
- **2022–2024:** Nu Form 20-F 2024  
  `https://www.sec.gov/Archives/edgar/data/1691493/000129281425001517/nuform20f_2024.htm`
- **2025:** Nu Form 20-F 2025  
  `https://www.sec.gov/Archives/edgar/data/1691493/000129281426002166/nuform20f_2025.htm`

Os dados tratados ficam em `data/processed/financial_history.csv`.

### Capital e risco

Os arquivos regulatórios do **Pilar 3** necessários à análise estão versionados neste próprio repositório, organizados por ano em `data/raw/pillar3/2021` a `data/raw/pillar3/2025`.

O pipeline `src/ingest_pillar3.py` processa os XLSX locais e gera `data/processed/capital_risk_history_long.csv`. A camada cobre Capital Principal, RWA e índices prudenciais; detalhes adicionais de 2025 são mantidos em `risk_2025_detail.csv`.

Referência regulatória: **Banco Central do Brasil — divulgação prudencial / Pilar 3**.

### Experiência do cliente

Os arquivos usados na análise complementar de reclamações estão versionados em `data/raw/customer/`. A base não oferece uma dimensão temporal confiável e comparável para 2021–2025; por isso, é utilizada apenas como **amostra transversal** para categorias, severidade e clusters.

Fonte pública de origem da coleta: **Reclame Aqui**.

## Arquitetura

```text
.
├── app.py                              # dashboard Streamlit
├── data/
│   ├── raw/
│   │   ├── pillar3/
│   │   │   ├── 2021/ ... 2025/       # XLSX regulatórios versionados
│   │   ├── customer/                  # amostra acadêmica de reclamações
│   │   └── macro/                     # série macro de referência
│   ├── processed/
│   │   ├── financial_history.csv
│   │   ├── capital_risk_history_long.csv
│   │   └── risk_2025_detail.csv
│   └── source_manifest.csv
├── database/
│   └── nubank_analytics.db             # gerado localmente
├── docs/
│   ├── index.html                      # dashboard público
│   ├── css/style.css
│   ├── js/dashboard.js
│   └── data/dashboard-data.json        # gerado no build
├── src/
│   ├── data_pipeline.py                # carga local e padronização
│   ├── ingest_pillar3.py               # processamento dos XLSX locais
│   ├── build_database.py               # construção da camada SQLite
│   ├── build_web_data.py               # gera payload da versão pública
│   └── validate_data.py                # testes de integridade
├── sql/
│   ├── 01_growth.sql
│   ├── 02_profitability.sql
│   ├── 03_risk.sql
│   └── 04_customer.sql
└── .github/workflows/                  # validação, build e deploy
```

## Reprodutibilidade

O dashboard não depende de baixar dados de outro repositório durante a execução. Os arquivos necessários à aplicação estão versionados aqui; a pipeline bruta permanece disponível para auditoria e reconstrução.

### Windows / PowerShell

Na raiz do repositório:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m ensurepip --upgrade
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
.\.venv\Scripts\python.exe .\src\validate_data.py
.\.venv\Scripts\python.exe -m streamlit run .\app.py
```

Abra `http://localhost:8501` caso o navegador não seja iniciado automaticamente.

### Reconstruir a camada regulatória

```powershell
.\.venv\Scripts\python.exe .\src\ingest_pillar3.py
```

### Criar o banco SQLite

```powershell
.\.venv\Scripts\python.exe .\src\build_database.py
```

### Gerar os dados da versão web

```powershell
.\.venv\Scripts\python.exe -m src.build_web_data
```

O comando cria `docs/data/dashboard-data.json` a partir da mesma camada usada pelo Streamlit.

## SQL como camada analítica

As consultas em `sql/` tornam explícitas perguntas de negócio que também aparecem nos dashboards:

- crescimento de clientes, receita e depósitos;
- evolução da rentabilidade;
- capital regulatório e RWA;
- composição da amostra de reclamações.

A camada SQLite pode ser regenerada localmente a qualquer momento a partir dos datasets versionados.

## Decisões metodológicas

- **IFRS como referência:** receita e lucro líquido reportados são as métricas contábeis principais.
- **Métricas ajustadas identificadas:** medidas não IFRS são apresentadas como complementares.
- **Moedas preservadas:** resultados consolidados permanecem em US$; capital regulatório e RWA permanecem em R$.
- **Sem causalidade inventada:** mudanças relevantes são destacadas como sinais para investigação quando a fonte não sustenta uma explicação causal.
- **Reclamações sem extrapolação temporal:** a amostra é usada transversalmente e não como série histórica 2021–2025.

## Qualidade e CI

O GitHub Actions executa automaticamente:

- instalação das dependências em Python 3.12;
- compilação do Streamlit e dos módulos Python;
- validação da série financeira;
- conferência dos arquivos regulatórios locais;
- reconstrução do histórico Pilar 3;
- validação da amostra de reclamações;
- geração e validação do payload JSON da versão web;
- verificação sintática do JavaScript;
- criação do artifact do GitHub Pages;
- deploy apenas quando a versão aprovada chegar à `main`.

## Origem acadêmica e autoria

O trabalho que deu origem ao tema foi desenvolvido no Projeto Integrador III da FATEC por **Felipe Tavares, Paulo Futagawa, Thaís Nakazone e Thiago Teles**.

Este repositório é a **adaptação individual de portfólio de Paulo Futagawa**. A curadoria da série financeira oficial 2021–2025, a reorganização dos dados, a arquitetura local, a camada SQL, as validações automatizadas e o redesign do produto analítico pertencem a esta versão de portfólio.

## Status

- [x] dashboard Streamlit em português
- [x] série financeira oficial 2021–2025
- [x] dados regulatórios 2021–2025 versionados localmente
- [x] pipeline de ingestão e validação
- [x] camada SQLite + SQL
- [x] análise complementar de reclamações com limitação documentada
- [x] versão pública responsiva em GitHub Pages
- [x] pipeline Python → JSON → navegador
- [x] build do Pages validado em pull request
- [ ] deploy público após integração à `main`

## Aviso

Projeto independente para fins acadêmicos e de portfólio. Não é afiliado à Nu Holdings Ltd. e não constitui recomendação de investimento.
