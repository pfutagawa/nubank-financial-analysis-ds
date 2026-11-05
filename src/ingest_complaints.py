from __future__ import annotations

import csv
import io
import json
import re
import unicodedata
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_CUSTOMER = ROOT / "data" / "raw" / "customer"
PROCESSED = ROOT / "data" / "processed"
BCB_RANKING_OUTPUT = PROCESSED / "bcb_complaints_ranking.csv"
CONSUMIDOR_GOV_OUTPUT = PROCESSED / "consumidor_gov_summary.csv"

BCB_LIST_URL = "https://www3.bcb.gov.br/rdrweb/rest/ext/ranking"
BCB_FILE_URL = "https://www3.bcb.gov.br/rdrweb/rest/ext/ranking/arquivo"
CONSUMIDOR_CKAN_API = "https://dados.mj.gov.br/api/3/action/package_show?id=reclamacoes-do-consumidor-gov-br"

BCB_METHODOLOGY_NOTE = (
    "A partir do 2º tri/2024 (2T24), o Banco Central passou a adotar valores extrapolados "
    "(projeção estatística a partir de amostra de reclamações reguladas procedentes) para todo "
    "o universo de demandas respondidas pelas instituições no trimestre, elevando o patamar "
    "numérico dos índices sem significar piora operacional automática."
)

TARGET_INSTITUTIONS = {
    "NU PAGAMENTOS": "Nu Pagamentos (Nubank)",
    "NUBANK": "Nu Pagamentos (Nubank)",
    "ITAU": "Itaú",
    "BRADESCO": "Bradesco",
}


def _normalize(text: object) -> str:
    val = "" if text is None else str(text)
    val = unicodedata.normalize("NFKD", val).encode("ascii", "ignore").decode("ascii")
    return " ".join(val.upper().strip().split())


def match_target_institution(raw_name: object) -> str | None:
    norm = _normalize(raw_name)
    if "NU PAGAMENTOS" in norm or "NUBANK" in norm or norm.startswith("NU "):
        return "Nu Pagamentos (Nubank)"
    if "ITAU" in norm:
        return "Itaú"
    if "BRADESCO" in norm:
        return "Bradesco"
    return None


def _http_get(url: str, timeout: int = 20) -> bytes | None:
    req = Request(
        url,
        headers={
            "User-Agent": "Projeto Academico Fatec contato-nao-informado@example.com",
            "Accept": "*/*",
        },
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (URLError, TimeoutError, OSError):
        return None


def build_bcb_file_url(ano: int, trimestre: int, tipo: str = "Bancos e Financeiras") -> str:
    params = urlencode(
        {
            "ano": ano,
            "periodicidade": "TRIMESTRAL",
            "periodo": trimestre,
            "tipo": tipo,
        }
    )
    return f"{BCB_FILE_URL}?{params}"


def parse_bcb_csv_bytes(raw_bytes: bytes, ano: int, trimestre: int, fonte_url: str) -> list[dict[str, Any]]:
    text = raw_bytes.decode("latin-1", errors="replace")
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    rows: list[dict[str, Any]] = []
    q_label = f"{trimestre}T{str(ano)[-2:]}"
    extrapolado = "sim" if (ano > 2024 or (ano == 2024 and trimestre >= 2)) else "não"

    for row in reader:
        normalized_keys = {_normalize(k): v for k, v in row.items() if k}
        inst_raw = (
            normalized_keys.get("INSTITUICAO FINANCEIRA")
            or normalized_keys.get("INSTITUICAO")
            or ""
        )
        inst_clean = match_target_institution(inst_raw)
        if not inst_clean:
            continue

        def _to_float(val: object) -> float | None:
            if val is None:
                return None
            s = str(val).strip().replace(".", "").replace(",", ".")
            s = re.sub(r"[^0-9.\-]", "", s)
            try:
                return float(s) if s else None
            except ValueError:
                return None

        procedentes = _to_float(
            normalized_keys.get("QUANTIDADE DE RECLAMACOES REGULADAS PROCEDENTES")
        )
        clientes = _to_float(normalized_keys.get("QUANTIDADE TOTAL DE CLIENTES"))
        indice = _to_float(normalized_keys.get("INDICE"))

        if procedentes is None or clientes is None or indice is None:
            continue

        rows.append(
            {
                "periodo": q_label,
                "ano": ano,
                "trimestre": trimestre,
                "parcial_2026": "sim" if ano >= 2026 else "não",
                "valores_extrapolados": extrapolado,
                "instituicao": inst_clean,
                "instituicao_bcb": str(inst_raw).strip(),
                "procedentes": round(procedentes, 2),
                "clientes": int(round(clientes)),
                "indice": round(indice, 2),
                "motivos_principais": str(
                    normalized_keys.get("MOTIVOS")
                    or "Cartão de crédito / Conta / Operações de crédito e segurança (conforme RDR/BCB)"
                ).strip(),
                "nota_metodologica": BCB_METHODOLOGY_NOTE,
                "fonte_url": fonte_url,
            }
        )
    return rows


def try_download_bcb_ranking(years: range = range(2021, 2027)) -> pd.DataFrame:
    """Tenta baixar os CSVs trimestrais do Ranking de Reclamações no portal de Dados Abertos do BCB."""
    all_rows: list[dict[str, Any]] = []
    for ano in years:
        for trimestre in (1, 2, 3, 4):
            if ano == 2026 and trimestre > 3:
                continue
            url = build_bcb_file_url(ano, trimestre, "Bancos e Financeiras")
            raw = _http_get(url, timeout=12)
            if raw and len(raw) > 200:
                parsed = parse_bcb_csv_bytes(raw, ano, trimestre, url)
                all_rows.extend(parsed)
    return pd.DataFrame(all_rows)


def check_consumidor_gov_open_data() -> dict[str, Any]:
    """Verifica acesso ao dataset aberto do Consumidor.gov.br (MJSP / dados.mj.gov.br)."""
    raw = _http_get(CONSUMIDOR_CKAN_API, timeout=10)
    if not raw:
        return {"online": False, "resources": 0}
    try:
        payload = json.loads(raw.decode("utf-8"))
        resources = payload.get("result", {}).get("resources", [])
        return {"online": True, "resources": len(resources)}
    except Exception:
        return {"online": False, "resources": 0}


def load_or_sync_bcb_ranking(try_network: bool = False) -> pd.DataFrame:
    if try_network:
        downloaded = try_download_bcb_ranking()
        if not downloaded.empty:
            BCB_RANKING_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            downloaded.sort_values(["ano", "trimestre", "indice"]).to_csv(
                BCB_RANKING_OUTPUT, index=False
            )
            return downloaded

    if not BCB_RANKING_OUTPUT.exists():
        raise FileNotFoundError(
            f"Dataset oficial BCB ausente: {BCB_RANKING_OUTPUT}. "
            "Execute src/ingest_complaints.py com acesso à rede ou verifique o arquivo versionado."
        )
    return pd.read_csv(BCB_RANKING_OUTPUT)


if __name__ == "__main__":
    df = load_or_sync_bcb_ranking(try_network=False)
    print(
        f"Série oficial do Ranking de Reclamações BCB pronta: {len(df)} registros "
        f"({df['periodo'].iloc[0]} a {df['periodo'].iloc[-1]}) em {BCB_RANKING_OUTPUT}"
    )

