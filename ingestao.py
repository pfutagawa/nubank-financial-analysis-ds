import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import requests
import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError


def main() -> None:
    # 1. Carrega as variáveis de ambiente do ficheiro .env
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(dotenv_path=env_path)

    api_key = os.getenv("TWELVE_DATA_API_KEY") or os.getenv("TWELVEDATA_API_KEY")
    mongo_uri = os.getenv("MONGO_URI")

    if not api_key:
        print("Erro: Chave da Twelve Data API não encontrada no ficheiro .env (TWELVE_DATA_API_KEY).", file=sys.stderr)
        sys.exit(1)

    if not mongo_uri:
        print("Erro: MONGO_URI não encontrada no ficheiro .env.", file=sys.stderr)
        sys.exit(1)

    # 2. Lista de tickers para extração
    tickers = ["NU", "ITUB4.SA", "BBDC4.SA"]
    url = "https://api.twelvedata.com/time_series"
    dataframes: list[pd.DataFrame] = []

    print(f"Iniciando coleta para os tickers: {tickers}\n")

    # 3. Laço de repetição (loop) para buscar o histórico de cada ativo
    for index, ticker in enumerate(tickers):
        print(f"[{index + 1}/{len(tickers)}] Buscando cotações diárias para '{ticker}' na Twelve Data API...")

        params = {
            "symbol": ticker,
            "interval": "1day",
            "apikey": api_key,
            "outputsize": 30,  # Histórico diário (30 pregões)
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"  ❌ Erro na requisição para '{ticker}': {e}", file=sys.stderr)
            continue

        # Validação de erros na resposta da API
        if data.get("status") == "error":
            print(f"  ❌ Erro da API para '{ticker}': {data.get('message', 'Erro desconhecido')}", file=sys.stderr)
            continue

        values = data.get("values")
        if not values:
            print(f"  ⚠️ Nenhum dado retornado para o ticker '{ticker}'.", file=sys.stderr)
            continue

        # Criação do DataFrame com os campos retornados
        df = pd.DataFrame(values)

        # Conversão dos campos OHLCV para numéricos
        ohlc_cols = ["open", "high", "low", "close"]
        for col in ohlc_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

        # Adiciona a nova coluna 'ticker' com o ativo correspondente
        df["ticker"] = ticker

        # Adiciona as colunas de rastreabilidade
        collection_time = datetime.now(timezone.utc)
        df["source"] = "Twelve Data"
        df["collected_at"] = collection_time

        dataframes.append(df)
        print(f"  ✓ '{ticker}': {len(df)} registros processados com sucesso.")

        # Pausa breve entre requisições para respeitar o rate limit da API gratuita
        if index < len(tickers) - 1:
            time.sleep(1)

    # 4. Consolidação de todos os DataFrames
    if not dataframes:
        print("\nNenhum dado foi obtido para os tickers informados. Encerrando.", file=sys.stderr)
        sys.exit(1)

    consolidated_df = pd.concat(dataframes, ignore_index=True)
    print(f"\n📊 DataFrame consolidado com {len(consolidated_df)} registros no total.")
    print(f"Colunas presentes: {list(consolidated_df.columns)}")

    # 5. Converte para lista de dicionários usando to_dict('records')
    records = consolidated_df.to_dict("records")

    # Garante a compatibilidade do timestamp nativo com o driver BSON do MongoDB
    for record in records:
        if isinstance(record.get("collected_at"), pd.Timestamp):
            record["collected_at"] = record["collected_at"].to_pydatetime()

    # 6. Inserção em massa (bulk insert) no MongoDB
    if "<" in mongo_uri and ">" in mongo_uri:
        print(
            "\nAviso: A MONGO_URI parece conter caracteres '<' e '>'. Certifique-se de que a senha está preenchida corretamente."
        )

    print("\nConectando ao MongoDB...")
    client = None
    try:
        client = MongoClient(mongo_uri)
        # Teste de conectividade
        client.admin.command("ping")
        print("Conexão com o MongoDB estabelecida com sucesso!")

        db = client["nubank_db"]
        collection = db["historico_diario"]

        resultado = collection.insert_many(records)
        print(
            f"🚀 Sucesso: {len(resultado.inserted_ids)} documentos inseridos "
            f"na base de dados 'nubank_db', coleção 'historico_diario'."
        )

    except PyMongoError as e:
        print(f"Erro ao interagir com o MongoDB: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    main()
