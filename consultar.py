import os
import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient


def main() -> None:
    load_dotenv()

    mongo_uri = os.getenv("MONGO_URI")
    client = MongoClient(mongo_uri)
    db = client["nubank_db"]
    collection = db["historico_diario"]

    total = collection.count_documents({})
    print(f"📊 Total de documentos em nubank_db.historico_diario: {total}\n")

    # Contagem por ticker
    pipeline = [
        {"$group": {"_id": "$ticker", "total": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    contagem = list(collection.aggregate(pipeline))
    if contagem:
        print("📈 Quantidade de documentos por ativo:")
        for item in contagem:
            ticker_name = item["_id"] if item["_id"] else "Sem ticker"
            print(f"  • {ticker_name}: {item['total']} registros")
        print()

    # Exibe amostra dos dados no terminal como DataFrame formatado
    docs = list(collection.find().sort("collected_at", -1).limit(5))
    if docs:
        df = pd.DataFrame(docs)
        print("🔍 Amostra dos 5 registros mais recentes:")
        print(df.to_string(index=False))
    else:
        print("Nenhum documento encontrado.")


if __name__ == "__main__":
    main()
