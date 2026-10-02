import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import requests
import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from pymongo.errors import DuplicateKeyError, OperationFailure, PyMongoError


def sanitize_text(text: str, secret: str | None = None) -> str:
    """
    Higieniza textos de log e exceções para evitar vazamento de credenciais.
    Mascara chaves de API, senhas e URLs completas.
    """
    if not text:
        return ""
    sanitized = str(text)
    if secret and len(secret) > 3:
        sanitized = sanitized.replace(secret, "***REDACTED***")
    # Mascara padrões comuns de apikey em URLs ou mensagens
    sanitized = re.sub(r"apikey=[^&\s'\"]+", "apikey=***REDACTED***", sanitized, flags=re.IGNORECASE)
    # Mascara credenciais em URIs do MongoDB
    sanitized = re.sub(
        r"mongodb(?:\+srv)?://[^@\s'\"]+@",
        "mongodb://***REDACTED***@",
        sanitized,
        flags=re.IGNORECASE,
    )
    return sanitized


def validate_record(raw_record: dict, ticker: str) -> tuple[dict | None, str]:
    """
    Valida os campos obrigatórios da cotação.
    Regras:
    - Data válida e no formato YYYY-MM-DD (preservada como string).
    - Preços OHLC obrigatórios, numéricos e positivos.
    - Máxima (high) não pode ser inferior à mínima (low).
    - Volume obrigatório, numérico e não negativo.

    Retorna (dicionário_validado, "") se válido ou (None, motivo) se inválido.
    """
    if not isinstance(raw_record, dict):
        return None, "registro não é um dicionário"

    ticker_clean = str(ticker).strip() if ticker else ""
    if not ticker_clean:
        return None, "ticker ausente ou vazio"

    # 1. Validação de datetime (deve ser string YYYY-MM-DD válida)
    dt_str = raw_record.get("datetime")
    if not dt_str or not isinstance(dt_str, str):
        return None, "campo 'datetime' ausente ou inválido"
    dt_str = dt_str.strip()
    try:
        parsed_dt = datetime.strptime(dt_str, "%Y-%m-%d")
        if parsed_dt.year < 1900 or parsed_dt.year > 2100:
            return None, f"ano fora da faixa aceitável: {parsed_dt.year}"
    except (ValueError, TypeError):
        return None, f"campo 'datetime' não segue o padrão YYYY-MM-DD ou data inexistente: '{dt_str}'"

    # 2. Validação dos preços OHLC
    prices: dict[str, float] = {}
    for field in ("open", "high", "low", "close"):
        val = raw_record.get(field)
        if val is None or pd.isna(val) or str(val).strip() == "":
            return None, f"preço '{field}' ausente"
        try:
            num = float(val)
        except (ValueError, TypeError):
            return None, f"preço '{field}' não numérico: {val}"
        if num < 0:
            return None, f"preço '{field}' negativo: {num}"
        prices[field] = num

    # 3. Consistência: máxima não pode ser menor que a mínima
    if prices["high"] < prices["low"]:
        return (
            None,
            f"máxima ({prices['high']}) inferior à mínima ({prices['low']})",
        )

    # 4. Validação do volume
    vol_val = raw_record.get("volume")
    if vol_val is None or pd.isna(vol_val) or str(vol_val).strip() == "":
        return None, "volume ausente"
    try:
        vol_num = float(vol_val)
    except (ValueError, TypeError):
        return None, f"volume não numérico: {vol_val}"
    if vol_num < 0:
        return None, f"volume negativo: {vol_num}"

    valid_doc = {
        "ticker": ticker_clean,
        "datetime": dt_str,  # Mantido como string YYYY-MM-DD para consistência com o histórico
        "open": prices["open"],
        "high": prices["high"],
        "low": prices["low"],
        "close": prices["close"],
        "volume": vol_num,
    }
    return valid_doc, ""


def ensure_unique_index(collection) -> bool:
    """
    Garante a presença do índice composto único em ('ticker', 'datetime').
    Se duplicatas impedirem sua criação, interrompe com mensagem clara sem apagar dados.
    """
    try:
        for idx in collection.list_indexes():
            keys = list(idx.get("key", {}).items())
            if keys == [("ticker", 1), ("datetime", 1)] and idx.get("unique"):
                return True
    except PyMongoError as e:
        print(f"Erro ao verificar índices existentes: {type(e).__name__}", file=sys.stderr)
        return False

    try:
        collection.create_index([("ticker", 1), ("datetime", 1)], unique=True)
        return True
    except (DuplicateKeyError, OperationFailure) as e:
        err_msg = str(e).lower()
        if "duplicate key" in err_msg or getattr(e, "code", None) == 11000:
            print(
                "\n❌ ERRO CRÍTICO: Existem registros duplicados na coleção 'historico_diario' "
                "que impedem a criação do índice composto único ('ticker', 'datetime').\n"
                "A ingestão foi cancelada para evitar inconsistências nos dados existentes.\n"
                "Nenhum dado foi apagado automaticamente.\n"
                "Execute o script de inspeção e limpeza controlada "
                "(scripts/limpar_historico_teste.py) antes de tentar novamente.",
                file=sys.stderr,
            )
            return False
        print(f"Erro inesperado ao criar índice único: {type(e).__name__}", file=sys.stderr)
        return False


def main() -> int:
    # 1. Carrega as variáveis de ambiente do ficheiro .env
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(dotenv_path=env_path)

    api_key = os.getenv("TWELVE_DATA_API_KEY") or os.getenv("TWELVEDATA_API_KEY")
    mongo_uri = os.getenv("MONGO_URI")

    if not api_key:
        print("Erro: Chave TWELVE_DATA_API_KEY não configurada no ambiente/.env.", file=sys.stderr)
        return 1

    if not mongo_uri:
        print("Erro: MONGO_URI não configurada no ambiente/.env.", file=sys.stderr)
        return 1

    # 2. Tickers compatíveis com o plano gratuito da Twelve Data API (NYSE/ADRs)
    tickers = ["NU", "ITUB", "BBD"]
    url = "https://api.twelvedata.com/time_series"

    print(f"Iniciando coleta para os tickers: {tickers}\n")

    valid_records: list[dict] = []
    rejected_records: list[dict] = []
    failed_tickers: list[str] = []
    successful_tickers: list[str] = []

    # 3. Laço de coleta para cada ticker
    for index, ticker in enumerate(tickers):
        print(f"[{index + 1}/{len(tickers)}] Buscando cotações diárias para '{ticker}'...")

        params = {
            "symbol": ticker,
            "interval": "1day",
            "apikey": api_key,
            "outputsize": 30,
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            status_code = response.status_code
            try:
                data = response.json()
            except Exception:
                data = {}
        except requests.RequestException as e:
            # Nunca imprime str(e) para não expor a URL com a chave de API
            print(f"  ❌ Falha de conexão para '{ticker}': {type(e).__name__}", file=sys.stderr)
            failed_tickers.append(ticker)
            continue

        if status_code != 200 or data.get("status") == "error":
            raw_msg = data.get("message", f"HTTP {status_code}")
            safe_msg = sanitize_text(str(raw_msg), api_key)
            print(f"  ❌ Erro da API para '{ticker}' (HTTP {status_code}): {safe_msg}", file=sys.stderr)
            failed_tickers.append(ticker)
            continue

        values = data.get("values")
        if not values or not isinstance(values, list):
            print(f"  ⚠️ Nenhum registro retornado para '{ticker}'.", file=sys.stderr)
            failed_tickers.append(ticker)
            continue

        # Validação individual dos registros
        collection_time = datetime.now(timezone.utc)
        ticker_valid_count = 0

        for raw_item in values:
            valid_doc, reason = validate_record(raw_item, ticker)
            if valid_doc is not None:
                valid_doc["source"] = "Twelve Data"
                valid_doc["collected_at"] = collection_time
                valid_records.append(valid_doc)
                ticker_valid_count += 1
            else:
                rejected_records.append({"ticker": ticker, "reason": reason, "raw": raw_item.get("datetime")})

        print(f"  ✓ '{ticker}': {ticker_valid_count} cotações válidas processadas.")
        successful_tickers.append(ticker)

        # Pausa entre requisições para respeitar o rate limit da API gratuita
        if index < len(tickers) - 1:
            time.sleep(1)

    print(f"\nResumo da coleta: {len(valid_records)} válidos, {len(rejected_records)} rejeitados.")
    if rejected_records:
        print("Amostra de registros rejeitados:")
        for rej in rejected_records[:3]:
            print(f"  • {rej['ticker']} (data: {rej['raw']}): {rej['reason']}")

    # 4. Operação no MongoDB (upsert em lote)
    client = None
    try:
        client = MongoClient(mongo_uri)
        client.admin.command("ping")

        db = client["nubank_db"]
        collection = db["historico_diario"]

        # Garante o índice único antes da gravação
        if not ensure_unique_index(collection):
            return 1

        if not valid_records:
            print("Nenhum registro válido para gravar no banco.", file=sys.stderr)
            return 1 if failed_tickers else 0

        # Monta operações de UpdateOne com upsert=True por chave (ticker, datetime)
        operations = [
            UpdateOne(
                {"ticker": doc["ticker"], "datetime": doc["datetime"]},
                {"$set": doc},
                upsert=True,
            )
            for doc in valid_records
        ]

        bulk_result = collection.bulk_write(operations, ordered=False)

        inserted_count = bulk_result.upserted_count
        modified_count = bulk_result.modified_count
        matched_count = bulk_result.matched_count

        print("\n📊 Resultado da ingestão no MongoDB:")
        print(f"  • Documentos novos inseridos: {inserted_count}")
        print(f"  • Documentos existentes atualizados: {modified_count}")
        print(f"  • Documentos correspondentes sem alteração: {matched_count - modified_count}")
        print(f"  • Registros rejeitados na validação: {len(rejected_records)}")

    except PyMongoError as e:
        print(f"\n❌ Erro durante a operação no MongoDB: {type(e).__name__}", file=sys.stderr)
        return 1
    finally:
        if client:
            client.close()

    # 5. Validação final de status dos tickers
    if failed_tickers:
        print(f"\n❌ Atenção: A coleta ficou incompleta. Tickers com falha: {failed_tickers}", file=sys.stderr)
        return 1

    print("\n✅ Ingestão finalizada com sucesso para todos os tickers configurados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
