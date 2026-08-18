from __future__ import annotations

import sqlite3
from pathlib import Path

from data_pipeline import load_capital_risk_history, load_customer_sample, load_financial_history


ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / "database"
DB_PATH = DB_DIR / "nubank_analytics.db"


def build_database() -> Path:
    DB_DIR.mkdir(exist_ok=True)

    financial = load_financial_history()
    risk, _ = load_capital_risk_history()
    complaints, _ = load_customer_sample()

    with sqlite3.connect(DB_PATH) as conn:
        financial.to_sql("financial_history", conn, if_exists="replace", index=False)
        risk.to_sql("capital_risk_history", conn, if_exists="replace", index=False)
        if not complaints.empty:
            complaints.to_sql("customer_complaints", conn, if_exists="replace", index=False)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_financial_year ON financial_history(year)")
        if "period" in risk.columns:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_risk_period ON capital_risk_history(period)")

    return DB_PATH


if __name__ == "__main__":
    path = build_database()
    print(f"Banco analítico criado em: {path}")
