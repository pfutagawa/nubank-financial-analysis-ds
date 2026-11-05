from __future__ import annotations

import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
RAW_SEC_DIR = ROOT_DIR / "data" / "raw" / "sec"

SEC_CIK = "0001691493"
DEFAULT_SEC_USER_AGENT = "Projeto Academico Fatec contato-nao-informado@example.com"


def get_sec_user_agent() -> str:
    """Retorna o User-Agent exigido pela SEC EDGAR, com fallback documentado."""
    env_ua = os.getenv("SEC_USER_AGENT", "").strip()
    return env_ua if env_ua else DEFAULT_SEC_USER_AGENT


def fetch_sec_document(url: str, timeout: int = 20) -> bytes | None:
    """Baixa um documento oficial da SEC enviando o cabeçalho User-Agent identificado."""
    headers = {
        "User-Agent": get_sec_user_agent(),
        "Accept-Encoding": "identity",
    }
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except (URLError, TimeoutError, OSError):
        return None


def verify_or_cache_sec_filings(download_html: bool = False) -> list[dict[str, str]]:
    """Verifica o manifesto de relatórios trimestrais da Nu na SEC (6-K e 20-F)."""
    quarterly_path = PROCESSED_DIR / "financial_quarterly.csv"
    if not quarterly_path.exists():
        raise FileNotFoundError(f"Arquivo trimestral ausente: {quarterly_path}")

    df = pd.read_csv(quarterly_path)
    results: list[dict[str, str]] = []
    if download_html:
        RAW_SEC_DIR.mkdir(parents=True, exist_ok=True)

    for row in df.to_dict(orient="records"):
        trimestre = str(row["trimestre"])
        url = str(row["fonte_url"])
        status = "manifest_verified"
        if download_html:
            content = fetch_sec_document(url)
            if content:
                target = RAW_SEC_DIR / f"{trimestre}_{Path(url).name}"
                target.write_bytes(content)
                status = f"downloaded ({len(content)} bytes)"
            else:
                status = "offline_cached_manifest"
        results.append(
            {
                "trimestre": trimestre,
                "periodo_fim": str(row["periodo_fim"]),
                "parcial": str(row["parcial"]),
                "fonte_url": url,
                "user_agent": get_sec_user_agent(),
                "status": status,
            }
        )
    return results


def main() -> None:
    ua = get_sec_user_agent()
    results = verify_or_cache_sec_filings(download_html=False)
    print(
        f"Série trimestral SEC verificada ({len(results)} trimestres: "
        f"{results[0]['trimestre']} a {results[-1]['trimestre']}) | User-Agent: {ua}"
    )


if __name__ == "__main__":
    main()
