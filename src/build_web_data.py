from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.data_pipeline import (
    customer_summary,
    load_capital_risk_history,
    load_customer_sample,
    load_financial_history,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "data" / "dashboard-data.json"


def clean_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if hasattr(value, "item"):
        return value.item()
    return value


def records(df: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {key: clean_value(value) for key, value in row.items()}
        for row in df.to_dict(orient="records")
    ]


def build_payload() -> dict[str, Any]:
    financial = load_financial_history()
    risk, risk_source = load_capital_risk_history()
    complaints, complaints_source = load_customer_sample()
    risk_detail = pd.read_csv(ROOT / "data" / "processed" / "risk_2025_detail.csv")
    manifest = pd.read_csv(ROOT / "data" / "source_manifest.csv")

    summary = customer_summary(complaints)
    latest = financial.iloc[-1]
    first = financial.iloc[0]

    customer = {
        "total": int(len(complaints)),
        "loss_share_pct": None,
        "security_signals": None,
        "categories": records(summary["categories"]),
        "severity": records(summary["severity"]),
        "clusters": records(summary["clusters"]),
        "source_label": complaints_source,
    }

    if not complaints.empty and "Perda_Financeira" in complaints.columns:
        customer["loss_share_pct"] = round(
            float(pd.to_numeric(complaints["Perda_Financeira"], errors="coerce").fillna(0).mean() * 100),
            1,
        )
    if not complaints.empty and "Problema_Seguranca" in complaints.columns:
        customer["security_signals"] = int(
            pd.to_numeric(complaints["Problema_Seguranca"], errors="coerce").fillna(0).sum()
        )

    return {
        "meta": {
            "title": "Nubank em Dados",
            "period": "2021–2025",
            "generated_from": "datasets versionados no próprio repositório",
            "risk_source": risk_source,
        },
        "headline": {
            "latest_year": int(latest["year"]),
            "customers_m": float(latest["customers_m"]),
            "revenue_usd_b": float(latest["revenue_usd_b"]),
            "net_income_usd_b": float(latest["net_income_usd_b"]),
            "deposits_usd_b": float(latest["deposits_usd_b"]),
            "customer_growth_pct": round(float((latest["customers_m"] / first["customers_m"] - 1) * 100), 1),
            "revenue_multiple": round(float(latest["revenue_usd_b"] / first["revenue_usd_b"]), 1),
            "deposit_multiple": round(float(latest["deposits_usd_b"] / first["deposits_usd_b"]), 1),
        },
        "financial": records(financial),
        "risk": records(risk),
        "risk_2025": records(risk_detail),
        "customer": customer,
        "sources": records(manifest),
    }


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Payload web criado em {OUTPUT}")


if __name__ == "__main__":
    main()
