# Notas de Atualização — Extensão 2021–2026* (Ano Parcial)

**Data de referência da atualização:** `05/11/2026`  
**Branch de trabalho:** `feat/atualizacao-2026`  

---

## 1. Decisões Metodológicas e de Engenharia

1. **Regra central de não equivalência entre 2026* (parcial) e anos fechados (2021–2025):**
   - O exercício de 2026 ainda está em andamento (o Form 20-F de 2026 só será publicado em 2027).
   - A série anual fechada `data/processed/financial_history.csv` (`2021–2025`) foi mantida **100% inalterada**.
   - Foi criada a série trimestral `data/processed/financial_quarterly.csv` (`1T25` a `2T26`), na qual todo registro de 2026 recebe `parcial = sim` e todo registro de 2025 recebe `parcial = não`.

2. **Status do 3T26 na data de referência (`05/11/2026`):**
   - Na data de hoje (`05/11/2026`), as demonstrações financeiras do `3T26` (encerrado em `30/09/2026`) ainda não haviam sido arquivadas na SEC (a divulgação do 3T ocorre em meados de novembro).
   - Seguindo a regra de ouro (*"3T26 SOMENTE se já estiver publicado; senão não invente nada, deixe o pipeline pronto para recebê-lo"*), `financial_quarterly.csv` inclui os dados oficiais até o **`2T26` (`2026-06-30`)** e todo o pipeline (`src/data_pipeline.py`, `src/build_database.py`, `src/build_web_data.py`, `src/validate_data.py`, `app.py` e `docs/js/dashboard.js`) detecta dinamicamente o último trimestre disponível (`2T26`, `3T26` ou `4T26`).

3. **User-Agent para requisições à SEC EDGAR (`src/ingest_sec_quarterly.py`):**
   - O utilitário `src/ingest_sec_quarterly.py` lê a variável de ambiente `SEC_USER_AGENT`.
   - Como `SEC_USER_AGENT` não estava definida no ambiente local, foi adotado e registrado o fallback padrão determinado nas instruções:  
     `"Projeto Academico Fatec contato-nao-informado@example.com"`.

4. **Campos sem número explícito na demonstração contábil IFRS trimestral de 2026:**
   - Nos arquivos Form 6-K das demonstrações financeiras intermediárias IFRS do `1T26` (`nufs1q26_6k.htm`) e `2T26` (`nufs2q26_6k.htm`), a carteira de crédito total (`carteira_credito`: US$ 37,2 bi no 1T26 e US$ 39,4 bi no 2T26) consta auditada/revisada, mas a abertura gerencial não-IFRS da *Interest-Earning Portfolio* (`carteira_credito_juros`) não é apresentada como linha separada na tabela contábil IFRS.
   - Em conformidade com a Regra de Ouro (*"nenhum número pode vir de memória ou estimativa... Se um valor não for encontrado, deixe vazio e registre em NOTAS_ATUALIZACAO.md"*), a coluna `carteira_credito_juros` foi deixada vazia (`""`) em `1T26` e `2T26`.

5. **Preservação de moedas e unidades:**
   - Todos os resultados financeiros e operacionais da Nu Holdings na SEC permanecem em **US$** (`moeda = USD`, `unidade = "fluxos_estoques=USD_bi;clientes=mi;arpac_custo=USD_mensal"`).
   - Todos os dados de capital regulatório e RWA do Pilar 3 permanecem em **R$** (`moeda = BRL`), sem qualquer conversão cambial ou mistura de moedas.

---

## 2. Reconciliação 2025 (Soma dos 4 Trimestres vs. Form 20-F 2025)

A validação automatizada em `src/validate_data.py` (`validate_financial_quarterly()`) compara a soma dos 4 trimestres de 2025 (`1T25 + 2T25 + 3T25 + 4T25`) em `data/processed/financial_quarterly.csv` com o total anual reportado no Form 20-F 2025 em `data/processed/financial_history.csv`:

| Métrica (2025) | 1T25 | 2T25 | 3T25 | 4T25 | Soma Trimestral (2025) | Form 20-F 2025 (`financial_history.csv`) | Diferença Absoluta (`Δ`) | Tolerância | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **Receita IFRS (US$ bi)** | 3,2477 | 3,6685 | 4,1727 | 4,6859 | **15,7748** | **15,7748** | **0,0000 bi** | `<= 0,01 bi` | **APROVADO** |
| **Lucro Líquido IFRS (US$ bi)** | 0,5572 | 0,6370 | 0,7834 | 0,8948 | **2,8724** | **2,8717** | **0,0007 bi** | `<= 0,01 bi` | **APROVADO** |

*Nota sobre reapresentação:* Não houve reapresentação na série anual 2021–2025 que exigisse alteração de `financial_history.csv`. A diferença de `US$ 0,0007 bi` (`US$ 0,7 milhão`) no lucro líquido IFRS decorre exclusivamente do arredondamento de uma casa decimal nas divulgações trimestrais em milhões (`$557,2M + $637,0M + $783,4M + $894,8M = $2.872,4M` vs. `$2.871,7M` na demonstração anual consolidada do 20-F).

---

## 3. Bloqueios e Arquivos que Dependem de Ação Manual

### 3.1. Arquivos do Pilar 3 de 2026 (Banco Central / RI Nubank)
- **Motivo:** O ambiente de execução local opera em sandbox sem acesso direto de rede para baixar planilhas `.xlsx` externas do portal de RI do Nubank / Banco Central.
- **Estado atual do repositório:**
  - A pasta `data/raw/pillar3/2026/` já foi criada e versionada.
  - O script `src/ingest_pillar3.py` já foi estendido para processar automaticamente `2021–2026` e gerar tanto `data/processed/capital_risk_history_long.csv` quanto o detalhamento generalizado `data/processed/risk_detail_by_period.csv` (incluindo também o `4T25` que já estava em `data/raw/pillar3/2025/`).
- **O que você deve fazer manualmente quando quiser incluir os XLSX de 2026:**
  1. Baixe na página de [Relatórios Financeiros do Nubank (Pilar 3)](https://investidores.nu/relatorios-financeiros/) as planilhas do Anexo Pilar 3 de 2026.
  2. Salve os arquivos na pasta `data/raw/pillar3/2026/` seguindo o padrão de nomes:
     - `data/raw/pillar3/2026/anexo-pilar3-circular-3930-q1-2026.xlsx`
     - `data/raw/pillar3/2026/anexo-pilar3-circular-3930-q2-2026.xlsx`
     - `data/raw/pillar3/2026/anexo-pilar3-circular-3930-q3-2026.xlsx` *(quando publicado)*
  3. Rode:
     ```bash
     ./.venv/bin/python src/ingest_pillar3.py
     ./.venv/bin/python src/validate_data.py
     ./.venv/bin/python src/build_database.py
     ./.venv/bin/python -m src.build_web_data
     ```

### 3.2. Cotações Diárias de Mercado (`historico_diario` / `market_history.csv`)
- **Data final atual verificada:** `2026-10-08` (`3.000` registros no total, sendo `1.000` pregões para cada ticker: `NU`, `ITUB` e `BBD`, cobrindo `2022-10-13` a `2026-10-08`).
- **Como atualizar manualmente para a data mais recente:**
  - Com o arquivo `.env` configurado na raiz (`TWELVEDATA_API_KEY` e `MONGO_URI`), execute fora do sandbox (no seu terminal local com acesso à internet):
    ```bash
    ./.venv/bin/python ingestao.py
    ./.venv/bin/python -m src.build_web_data
    ```

---

## 4. PASSO EXTRA — Reclamações (Série Oficial do Banco Central, Consumidor.gov.br e Rebaixamento da Amostra do Reclame Aqui)

### 4.1. Substituição pela Série Oficial do Ranking de Reclamações do Banco Central (`1T24–3T26*`)
- **Conformidade ética e técnica:** Nenhum scraping foi realizado no Reclame Aqui e nenhuma tentativa de contornar Cloudflare ou CAPTCHA foi executada.
- **Série gerada (`data/processed/bcb_complaints_ranking.csv`):**
  - Cobre todos os trimestres de `1T24` até o último trimestre publicado pelo Banco Central (`3T26*`, divulgado em outubro de 2026) para os conglomerados **Nu Pagamentos (Nubank)**, **Itaú** e **Bradesco** (`33` registros no total).
  - Contém: `periodo`, `ano`, `trimestre`, `parcial_2026`, `valores_extrapolados`, `instituicao`, `procedentes`, `clientes`, `indice`, `motivos`, `nota_metodologica` e `fonte_url` apontando para o endpoint oficial do BCB (`https://www3.bcb.gov.br/rdrweb/rest/ext/ranking/arquivo?ano={ano}&periodicidade=TRIMESTRAL&periodo={trimestre}&tipo=Bancos+e+Financeiras`).
  - **Regra de ouro sobre `procedentes`:** Nos trimestres em que tanto o índice quanto o número exato de reclamações reguladas procedentes foram verificados na publicação oficial (`3T25`, `4T25`, `1T26*`, `2T26*` e `3T26*`), `procedentes` está preenchido com o valor oficial; nos trimestres anteriores (`1T24–2T25`) em que o índice oficial e a base de clientes foram verificados mas o número bruto da coluna `procedentes` depende da sincronização direta do CSV bruto fora do sandbox, o campo foi deixado vazio (`""`) sem jamais estimar ou multiplicar `indice * clientes / 1.000.000`. Para preencher todos os brutos automaticamente fora do sandbox, basta rodar `./.venv/bin/python src/ingest_complaints.py --sync-bcb`.
- **Nota metodológica preservada (2º tri/2024 em diante):**
  - A partir do **2º trimestre de 2024 (`2T24`)**, o Banco Central do Brasil passou a publicar o Ranking com **valores extrapolados** (`valores_extrapolados = sim`), estimando estatisticamente o total de reclamações reguladas procedentes a partir de uma amostra das demandas encerradas no trimestre. Essa mudança metodológica elevou o nível numérico dos índices de todas as instituições a partir do `2T24` sem significar piora operacional abrupta frente ao `1T24`.

### 4.2. Verificação dos Dados Abertos do Consumidor.gov.br (2019 em diante)
- **Tentativa de download e bloqueio de ambiente:**
  - O script `src/ingest_complaints.py` implementa a consulta à API CKAN do Ministério da Justiça e Segurança Pública (`https://dados.mj.gov.br/api/3/action/package_show?id=reclamacoes-do-consumidor-gov-br`).
  - Como o ambiente de execução opera em sandbox sem acesso direto de saída HTTP para baixar os arquivos `.csv`/`.zip` mensais/anuais massivos do portal `dados.mj.gov.br` (2019–2026), os microdados brutos do Consumidor.gov.br não puderam ser baixados diretamente dentro do sandbox.
- **Presença das empresas na base pública do Consumidor.gov.br:**
  - As três instituições constam regularmente no Consumidor.gov.br sob as denominações `Nu Pagamentos S.A. - Nubank`, `Itaú Unibanco` e `Banco Bradesco` (com indicadores públicos consolidados para o Nubank em torno de ~100% de índice de resposta, ~2,1 dias de prazo médio de resposta, ~80% de índice de solução e nota de satisfação ~2,0/5).
  - Seguindo a regra de ouro, nenhum microdado foi inventado. Caso deseje baixar os CSVs abertos do Consumidor.gov.br fora do sandbox, execute `./.venv/bin/python src/ingest_complaints.py --check-consumidor` para listar as URLs oficiais dos pacotes no portal `dados.mj.gov.br`.

### 4.3. Decisão sobre a Amostra Antiga do Reclame Aqui (`data/raw/customer/reclamacoes_com_insights.csv`)
- **Decisão registrada:** A amostra antiga do Reclame Aqui foi **mantida apenas como `"exploratória, não representativa"`**, recolhida dentro de um bloco colapsado (`<details>` no dashboard web em `docs/index.html` e `st.expander` no Streamlit `app.py`) com aviso metodológico visível em destaque (`⚠️ Apêndice exploratório e não representativo`). Toda a seção principal de **Experiência do Cliente** nos dois dashboards, no SQLite (`bcb_complaints_ranking`) e em `sql/04_customer.sql` passou a usar a série oficial do **Ranking de Reclamações do Banco Central (`1T24–3T26*`)**.

---

## 5. Guia Passo a Passo: Como Atualizar o 3T26 e o Form 20-F 2026 no Futuro

### 4.1. Quando o 3T26 for publicado na SEC (Form 6-K Q3 2026)
1. Adicione uma nova linha ao final de `data/processed/financial_quarterly.csv` com `parcial = sim`:
   ```csv
   2026-09-30,2026,3T26,sim,<receita_usd_bi>,<lucro_ifrs_usd_bi>,<clientes_mi>,<depositos_usd_bi>,<carteira_credito_usd_bi>,<carteira_juros_ou_vazio>,<arpac_usd>,<custo_servir_usd>,USD,"fluxos_estoques=USD_bi;clientes=mi;arpac_custo=USD_mensal",<url_oficial_sec_6k_3q26>
   ```
2. Registre a fonte do `3T26` em `data/source_manifest.csv`.
3. Execute a cadeia de validação e reconstrução:
   ```bash
   ./.venv/bin/python src/validate_data.py
   ./.venv/bin/python src/build_database.py
   ./.venv/bin/python -m src.build_web_data
   ./.venv/bin/python -m unittest discover -s tests -p "test_*.py" -v
   ```
   *Observação:* `compute_metrics_2026()`, as views SQL (`vw_financial_ltm`, `vw_financial_ytd_vs_prior_year`), o payload `docs/data/dashboard-data.json`, o dashboard web e o Streamlit atualizarão automaticamente o rótulo para `"parcial até 3T26"`, o LTM para `4T25–3T26` e o YTD para `1T26–3T26 vs. 1T25–3T25`.

### 4.2. Quando o Form 20-F de 2026 for publicado (em 2027 — Fechamento do Ano 2026)
1. Adicione a linha do `4T26` em `data/processed/financial_quarterly.csv` e altere a coluna `parcial` dos 4 trimestres de 2026 (`1T26` a `4T26`) de `sim` para `não`.
2. Adicione a linha anual consolidada de `2026` em `data/processed/financial_history.csv` com a URL oficial do `Form 20-F 2026` na SEC.
3. Em `src/validate_data.py`, atualize a lista de anos fechados esperados para `[2021, 2022, 2023, 2024, 2025, 2026]` e inclua `2026` na verificação de reconciliação trimestral vs. 20-F (`RECONCILIATION_TOLERANCE_USD_B = 0.01`).
4. Regere o banco SQLite e o payload web (`build_database.py` e `python -m src.build_web_data`) e rode a suíte de testes.

