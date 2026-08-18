from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw" / "pillar3"
OUTPUT = ROOT / "data" / "processed" / "capital_risk_history_long.csv"

DATE_2021 = {
    "anexo-pilar3-circular-3930-q2-2021.xlsx": "2021-06-30",
    "anexo-pilar3-circular-3930-q4-2021.xlsx": "2021-12-31",
}


def source_paths() -> list[Path]:
    paths = sorted(RAW_ROOT.glob("20*/*.xlsx"))
    if not paths:
        raise FileNotFoundError(
            f"Nenhum XLSX do Pilar 3 encontrado em {RAW_ROOT}. "
            "Os arquivos brutos são versionados no próprio repositório."
        )
    return paths


def parse_2021(path: Path) -> pd.DataFrame:
    xls = pd.ExcelFile(path)
    if "CC1" not in xls.sheet_names:
        return pd.DataFrame(columns=["codigo", "descricao", "periodo", "valor", "arquivo"])
    df = pd.read_excel(xls, sheet_name="CC1", skiprows=3).iloc[:, :3]
    df.columns = ["codigo", "descricao", "valor"]
    df["periodo"] = DATE_2021[path.name]
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
    long["arquivo"] = path.name
    return long[["codigo", "descricao", "periodo", "valor", "arquivo"]]


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
    return result


if __name__ == "__main__":
    df = build_long_history()
    print(f"{len(df):,} registros regulatórios salvos em {OUTPUT}")
