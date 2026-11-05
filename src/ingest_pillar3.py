from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw" / "pillar3"
RAW_2026_DIR = RAW_ROOT / "2026"
OUTPUT = ROOT / "data" / "processed" / "capital_risk_history_long.csv"
RISK_2025_DETAIL_OUTPUT = ROOT / "data" / "processed" / "risk_2025_detail.csv"
RISK_DETAIL_BY_PERIOD_OUTPUT = ROOT / "data" / "processed" / "risk_detail_by_period.csv"

DATE_2021 = {
    "anexo-pilar3-circular-3930-q2-2021.xlsx": "2021-06-30",
    "anexo-pilar3-circular-3930-q4-2021.xlsx": "2021-12-31",
}

QUARTER_END_MONTH_DAY = {
    1: "03-31",
    2: "06-30",
    3: "09-30",
    4: "12-31",
}


def source_paths() -> list[Path]:
    RAW_2026_DIR.mkdir(parents=True, exist_ok=True)
    paths = sorted(RAW_ROOT.glob("20*/*.xlsx"))
    if not paths:
        raise FileNotFoundError(
            f"Nenhum XLSX do Pilar 3 encontrado em {RAW_ROOT}. "
            "Os arquivos brutos são versionados no próprio repositório."
        )
    return paths


def infer_period_from_filename(path: Path) -> str | None:
    match = re.search(r"q([1-4])-(\d{4})", path.name.lower())
    if not match:
        return None
    quarter = int(match.group(1))
    year = int(match.group(2))
    return f"{year}-{QUARTER_END_MONTH_DAY[quarter]}"


def parse_2021(path: Path) -> pd.DataFrame:
    xls = pd.ExcelFile(path)
    if "CC1" not in xls.sheet_names:
        return pd.DataFrame(columns=["codigo", "descricao", "periodo", "valor", "arquivo"])
    df = pd.read_excel(xls, sheet_name="CC1", skiprows=3).iloc[:, :3]
    df.columns = ["codigo", "descricao", "valor"]
    df["periodo"] = DATE_2021.get(path.name) or infer_period_from_filename(path)
    df["arquivo"] = path.name
    return df[["codigo", "descricao", "periodo", "valor", "arquivo"]]


def parse_q1_2022(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name="KM1", header=None)
    periods = list(raw.iloc[2, 2:].dropna().astype(str))
    data = raw.iloc[4:, 0 : 2 + len(periods)].copy()
    data.columns = ["codigo", "descricao"] + periods
    long = data.melt(
        id_vars=["codigo", "descricao"],
        value_vars=periods,
        var_name="periodo_origem",
        value_name="valor",
    )
    long["periodo"] = "2022-03-31"
    long["arquivo"] = path.name
    return long[["codigo", "descricao", "periodo", "valor", "arquivo"]]


def parse_matrix_km1(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name="KM1", header=None)

    # Layout predominante nos arquivos do período: descrições nas colunas C/D,
    # metadados de período nas linhas 6/7 e valores a partir da linha 9.
    letters = raw.iloc[5, 4:].tolist()
    dates = raw.iloc[6, 4:].tolist()
    periods = [f"{letter}_{date}" for letter, date in zip(letters, dates)]
    data = raw.iloc[8:, [2, 3] + list(range(4, 4 + len(periods)))].copy()
    data.columns = ["codigo", "descricao"] + periods
    long = data.melt(
        id_vars=["codigo", "descricao"],
        var_name="periodo_origem",
        value_name="valor",
    )
    long["periodo"] = long["periodo_origem"].astype(str).str.extract(
        r"(\d{4}-\d{2}-\d{2})", expand=False
    )
    # Caso a coluna principal (a_) traga formato MM/YYYY (ex.: 03/2024 ou 9/2024),
    # usa a data canônica do trimestre do arquivo para a coluna "a_".
    fallback_period = infer_period_from_filename(path)
    if fallback_period:
        mask_first_col = long["periodo"].isna() & long["periodo_origem"].astype(str).str.startswith("a_")
        long.loc[mask_first_col, "periodo"] = fallback_period
    long["arquivo"] = path.name
    return long[["codigo", "descricao", "periodo", "valor", "arquivo"]]


def _extract_code_value(df: pd.DataFrame, target_code: str) -> float | None:
    if df.shape[1] <= 4:
        return None
    sub = df[[2, 4]].copy()
    sub[2] = sub[2].astype(str).str.strip()
    match = sub[sub[2] == str(target_code)]
    if match.empty:
        return None
    val = pd.to_numeric(match.iloc[0][4], errors="coerce")
    return float(val) if pd.notna(val) else None


def build_risk_detail_by_period() -> pd.DataFrame:
    """Generaliza o detalhamento prudencial (KM1 + OV1 + MR1) por período (2024–2026*)."""
    records: list[dict[str, object]] = []
    for path in source_paths():
        year_folder = path.parent.name
        if not year_folder.isdigit() or int(year_folder) < 2024:
            continue
        xls = pd.ExcelFile(path)
        if not {"KM1", "OV1", "MR1"}.issubset(set(xls.sheet_names)):
            continue

        km1 = pd.read_excel(xls, sheet_name="KM1", header=None)
        ov1 = pd.read_excel(xls, sheet_name="OV1", header=None)
        mr1 = pd.read_excel(xls, sheet_name="MR1", header=None)

        period = infer_period_from_filename(path)
        if not period:
            raw_date = str(km1.iloc[6, 4])
            m = re.search(r"(\d{4}-\d{2}-\d{2})", raw_date)
            period = m.group(1) if m else raw_date

        q_match = re.search(r"q([1-4])-(\d{4})", path.name.lower())
        q_num = int(q_match.group(1)) if q_match else 4
        year_num = int(q_match.group(2)) if q_match else int(period[:4])
        quarter_code = f"Q{q_num}"
        trimestre_br = f"{q_num}T{str(year_num)[-2:]}"

        cp = _extract_code_value(km1, "1")
        n1 = _extract_code_value(km1, "2")
        pr = _extract_code_value(km1, "3")
        rwa = _extract_code_value(km1, "4")
        icp = _extract_code_value(km1, "5")
        basel = _extract_code_value(km1, "7")
        buf = _extract_code_value(km1, "12")
        rwa_cred = _extract_code_value(ov1, "1")
        rwa_juros = _extract_code_value(mr1, "1")
        rwa_cam = _extract_code_value(mr1, "3")

        if None in (cp, n1, pr, rwa, icp, basel, buf, rwa_cred, rwa_juros, rwa_cam):
            continue

        records.append(
            {
                "year": year_num,
                "quarter": quarter_code,
                "trimestre": trimestre_br,
                "period": period,
                "parcial": "sim" if year_num >= 2026 else "não",
                "capital_principal_brl_b": round(cp / 1e9, 4),
                "nivel_1_brl_b": round(n1 / 1e9, 4),
                "patrimonio_referencia_brl_b": round(pr / 1e9, 4),
                "rwa_total_brl_b": round(rwa / 1e9, 4),
                "icp_pct": round(icp * 100, 2),
                "basel_index_pct": round(basel * 100, 2),
                "capital_buffer_pct": round(buf * 100, 2),
                "rwa_credito_brl_b": round(rwa_cred / 1e9, 2),
                "rwa_juros_brl_m": round(rwa_juros / 1e6, 1),
                "rwa_cambio_brl_m": round(rwa_cam / 1e6, 1),
                "moeda": "BRL",
                "source_url": f"https://github.com/pfutagawa/nubank-financial-analysis-ds/tree/main/data/raw/pillar3/{year_num}",
                "arquivo": path.name,
            }
        )

    detail_df = pd.DataFrame(records)
    if not detail_df.empty:
        detail_df = (
            detail_df.sort_values("period")
            .drop_duplicates(subset=["period"], keep="last")
            .reset_index(drop=True)
        )
        RISK_DETAIL_BY_PERIOD_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        detail_df.to_csv(RISK_DETAIL_BY_PERIOD_OUTPUT, index=False)

        # Atualiza também risk_2025_detail.csv mantendo as colunas originais para compatibilidade
        cols_2025 = [
            "quarter",
            "period",
            "capital_principal_brl_b",
            "nivel_1_brl_b",
            "patrimonio_referencia_brl_b",
            "rwa_total_brl_b",
            "icp_pct",
            "basel_index_pct",
            "capital_buffer_pct",
            "rwa_credito_brl_b",
            "rwa_juros_brl_m",
            "rwa_cambio_brl_m",
            "source_url",
        ]
        df_2025 = detail_df[detail_df["year"] == 2025][cols_2025].reset_index(drop=True)
        if not df_2025.empty:
            df_2025.to_csv(RISK_2025_DETAIL_OUTPUT, index=False)

    return detail_df


def build_long_history() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in source_paths():
        if path.parent.name == "2021":
            frame = parse_2021(path)
        elif path.name == "anexo-pilar3-circular-3930-q1-2022.xlsx":
            frame = parse_q1_2022(path)
        else:
            frame = parse_matrix_km1(path)
        frames.append(frame)

    result = pd.concat(frames, ignore_index=True)
    result["valor"] = pd.to_numeric(result["valor"], errors="coerce")
    result["periodo"] = pd.to_datetime(result["periodo"], errors="coerce")
    result = (
        result.dropna(subset=["descricao", "periodo", "valor"])
        .sort_values(["periodo", "codigo", "arquivo"])
        .reset_index(drop=True)
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT, index=False)
    build_risk_detail_by_period()
    return result


if __name__ == "__main__":
    df = build_long_history()
    files_2026 = sorted(RAW_2026_DIR.glob("*.xlsx"))
    print(
        f"{len(df):,} registros regulatórios salvos em {OUTPUT} "
        f"(arquivos 2026 presentes: {len(files_2026)})"
    )
