"""Pipeline ETL dos Boletins de Acidente de Trânsito (BAT) da PRF.

Entrada : CSVs "agrupados por ocorrência" (uma linha por acidente), podendo estar
          em .csv, .csv.gz ou .zip (com um único CSV dentro).
Saída   : - data/processed/acidentes.parquet (ou .csv.gz)
          - data/processed/acidentes_rejeitados.csv.gz  (linhas descartadas + motivo)
          - data/processed/etl_report.json              (contagens e hashes: rastreabilidade)

Princípios do pipeline:
  * Determinístico: mesma entrada => mesma saída.
  * Não destrutivo: o bruto nunca é alterado; toda linha descartada vai para o
    arquivo de rejeitados e toda correção/imputação é contada no relatório.
  * Valores inválidos (coordenadas fora do Brasil, contagens negativas, km absurdo)
    viram NaN em vez de apagar a linha inteira.

Uso:
    python -m src.etl --input data/raw --uf RJ
    python -m src.etl --input data/raw/*.zip --output data/processed/acidentes.csv.gz --format csv.gz
"""
from __future__ import annotations

import argparse
import codecs
import gzip
import hashlib
import json
import logging
import re
import unicodedata
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

LOG = logging.getLogger("etl")

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

# --------------------------------------------------------------------------- #
# Esquema esperado (nomes após normalização). Confira com o dicionário oficial #
# da PRF; colunas ausentes são criadas vazias e avisadas no log.               #
# --------------------------------------------------------------------------- #
REQUIRED_COLUMNS = ["id", "data_inversa", "uf", "br", "km", "mortos"]

COUNT_COLUMNS = [
    "pessoas", "mortos", "feridos_leves", "feridos_graves",
    "ilesos", "ignorados", "feridos", "veiculos",
]
CATEGORY_COLUMNS = [
    "dia_semana", "causa_acidente", "tipo_acidente", "classificacao_acidente",
    "fase_dia", "sentido_via", "condicao_metereologica",  # grafia original da PRF
    "tipo_pista", "tracado_via", "uso_solo",
]
TEXT_COLUMNS = ["municipio", "regional", "delegacia", "uop"]

# Colunas que podem existir em arquivos mais novos (opcionais)
OPTIONAL_COLUMNS = ["causa_principal", "ordem_tipo_acidente"]

EXPECTED_COLUMNS = (
    ["id", "data_inversa", "horario", "uf", "br", "km", "latitude", "longitude"]
    + CATEGORY_COLUMNS + TEXT_COLUMNS + COUNT_COLUMNS + OPTIONAL_COLUMNS
)

NA_VALUES = ["", "NA", "N/A", "NULL", "null", "(null)", "NaN", "nan", "-", "(NULL)"]

# Limites de plausibilidade (caixa envolvente aproximada do território brasileiro)
LAT_RANGE = (-34.0, 6.0)
LON_RANGE = (-74.0, -34.0)
KM_RANGE = (0.0, 4500.0)

# Pesos do índice de severidade. DEFINA E CITE A REFERÊNCIA NO ARTIGO.
# (Sugestão: pesos inspirados no conceito de UPS/DNIT; confirme na fonte antes de citar.)
SEVERITY_WEIGHTS = {"mortos": 13, "feridos_graves": 6, "feridos_leves": 4}

PERIODOS = ["madrugada", "manha", "tarde", "noite"]  # 0-5, 6-11, 12-17, 18-23


# --------------------------------------------------------------------------- #
# Leitura                                                                      #
# --------------------------------------------------------------------------- #
def _head_bytes(path: Path, n: int = 1_000_000) -> bytes:
    """Lê os primeiros n bytes do CSV, mesmo dentro de .zip/.gz."""
    suffix = path.suffix.lower()
    if suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            members = [m for m in z.namelist() if m.lower().endswith(".csv")]
            if len(members) != 1:
                raise ValueError(f"{path.name}: esperado 1 CSV no zip, achei {members}")
            with z.open(members[0]) as fh:
                return fh.read(n)
    if suffix == ".gz":
        with gzip.open(path, "rb") as fh:
            return fh.read(n)
    with open(path, "rb") as fh:
        return fh.read(n)


def detect_encoding(path: Path) -> str:
    """UTF-8 (com ou sem BOM) se a amostra decodificar; senão latin-1."""
    head = _head_bytes(path)
    decoder = codecs.getincrementaldecoder("utf-8")()
    try:
        decoder.decode(head, final=False)  # tolera caractere cortado no fim da amostra
        return "utf-8-sig"
    except UnicodeDecodeError:
        return "latin-1"


def detect_separator(path: Path, encoding: str) -> str:
    first_line = _head_bytes(path, 20_000).decode(encoding, errors="replace").splitlines()[0]
    return ";" if first_line.count(";") >= first_line.count(",") else ","


def normalize_column_name(name: str) -> str:
    """'Condição Metereológica ' -> 'condicao_metereologica' (ASCII, snake_case)."""
    ascii_name = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    return re.sub(r"[^0-9a-zA-Z]+", "_", ascii_name).strip("_").lower()


def read_raw(path: Path) -> pd.DataFrame:
    """Lê um CSV bruto como texto (dtype=str) para não perder informação."""
    encoding = detect_encoding(path)
    sep = detect_separator(path, encoding)
    kwargs = dict(sep=sep, dtype=str, na_values=NA_VALUES, keep_default_na=False)
    try:
        df = pd.read_csv(path, encoding=encoding, **kwargs)
    except UnicodeDecodeError:
        LOG.warning("%s: falha em %s, relendo como latin-1", path.name, encoding)
        encoding = "latin-1"
        df = pd.read_csv(path, encoding=encoding, **kwargs)
    LOG.info("%s: %d linhas, encoding=%s, sep=%r", path.name, len(df), encoding, sep)
    df.columns = [normalize_column_name(c) for c in df.columns]
    df["arquivo_origem"] = path.name
    return df


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


# --------------------------------------------------------------------------- #
# Limpeza e transformação                                                      #
# --------------------------------------------------------------------------- #
def parse_decimal(s: pd.Series) -> pd.Series:
    """Converte '-22,9068' ou '-22.9068' em float (vírgula decimal brasileira)."""
    cleaned = s.astype("string").str.strip().str.replace(",", ".", regex=False)
    return pd.to_numeric(cleaned, errors="coerce").astype("Float64")


def _clean_text(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Limpa o DataFrame bruto.

    Retorna (df_limpo, df_rejeitados, relatório).
    """
    report: dict = {"linhas_entrada": int(len(df))}
    df = df.copy()
    df.columns = [normalize_column_name(c) for c in df.columns]

    missing_required = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_required:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing_required}")

    missing_optional = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing_optional:
        LOG.warning("Colunas esperadas ausentes (criadas vazias): %s", missing_optional)
        for c in missing_optional:
            df[c] = pd.NA
    report["colunas_ausentes_criadas_vazias"] = missing_optional
    report["colunas_extras_ignoradas"] = sorted(
        set(df.columns) - set(EXPECTED_COLUMNS) - {"arquivo_origem"}
    )
    if "arquivo_origem" not in df.columns:
        df["arquivo_origem"] = pd.NA

    # ---- 1. Texto: trim, espaços duplicados, caixa --------------------------
    for c in CATEGORY_COLUMNS:
        df[c] = _clean_text(df[c]).str.capitalize()
    for c in TEXT_COLUMNS:
        df[c] = _clean_text(df[c]).str.upper()
    for c in ["causa_principal", "ordem_tipo_acidente"]:
        df[c] = _clean_text(df[c])
    df["uf"] = _clean_text(df["uf"]).str.upper()

    # ---- 2. Duplicatas exatas (rastreadas, não apagadas em silêncio) --------
    content_cols = [c for c in df.columns if c != "arquivo_origem"]
    dup_mask = df.duplicated(subset=content_cols, keep="first")
    rejects = [df.loc[dup_mask].assign(motivo_rejeicao="linha_duplicada_exata")]
    df = df.loc[~dup_mask].copy()
    report["duplicatas_exatas_removidas"] = int(dup_mask.sum())

    id_num = pd.to_numeric(df["id"], errors="coerce")
    id_collisions = int(id_num.dropna().duplicated().sum())
    report["avisos"] = {"ids_repetidos_com_conteudo_diferente": id_collisions}
    if id_collisions:
        LOG.warning("%d ids repetidos com conteúdo diferente (mantidos)", id_collisions)

    # ---- 3. Data -------------------------------------------------------------
    raw_date = _clean_text(df["data_inversa"])
    data = pd.to_datetime(raw_date, format="%Y-%m-%d", errors="coerce")
    retry = data.isna() & raw_date.notna()
    if retry.any():
        data.loc[retry] = pd.to_datetime(raw_date[retry], format="%d/%m/%Y", errors="coerce")
    df["data"] = data

    bad_date = df["data"].isna()
    bad_uf = df["uf"].isna()
    reject_mask = bad_date | bad_uf
    reasons = np.where(bad_date, "data_invalida", "uf_ausente")
    if reject_mask.any():
        rejects.append(df.loc[reject_mask].assign(motivo_rejeicao=reasons[reject_mask.to_numpy()]))
    report["rejeitadas_data_invalida"] = int(bad_date.sum())
    report["rejeitadas_uf_ausente"] = int((bad_uf & ~bad_date).sum())
    df = df.loc[~reject_mask].copy()

    # ---- 4. Hora --------------------------------------------------------------
    hm = _clean_text(df["horario"]).str.extract(r"^(\d{1,2}):(\d{2})")
    hora = pd.to_numeric(hm[0], errors="coerce")
    minuto = pd.to_numeric(hm[1], errors="coerce")
    hora = hora.where(hora.between(0, 23))
    minuto = minuto.where(minuto.between(0, 59))
    df["hora"] = hora.astype("Int8")
    df["minuto"] = minuto.astype("Int8")
    report["horario_invalido_ou_ausente"] = int(df["hora"].isna().sum())

    # ---- 5. Tipos numéricos -----------------------------------------------------
    df["id"] = pd.to_numeric(df["id"], errors="coerce").astype("Int64")
    df["br"] = pd.to_numeric(df["br"], errors="coerce").astype("Int16")

    negativos = {}
    for c in COUNT_COLUMNS:
        v = pd.to_numeric(df[c], errors="coerce")
        neg = v < 0
        negativos[c] = int(neg.sum())
        df[c] = v.where(~neg).astype("Int32")
    report["contagens_negativas_para_nan"] = negativos

    # ---- 6. km e coordenadas (inválidos -> NaN, linha mantida) -------------------
    km = parse_decimal(df["km"])
    km_out = ~km.between(*KM_RANGE) & km.notna()
    report["km_fora_do_intervalo_para_nan"] = int(km_out.sum())
    df["km"] = km.where(~km_out)

    lat = parse_decimal(df["latitude"])
    lon = parse_decimal(df["longitude"])
    coord_out = (~lat.between(*LAT_RANGE) & lat.notna()) | (~lon.between(*LON_RANGE) & lon.notna())
    report["coordenadas_fora_do_brasil_para_nan"] = int(coord_out.sum())
    df["latitude"] = lat.where(~coord_out)
    df["longitude"] = lon.where(~coord_out)

    # ---- 7. Consistência entre contagens (sinalizada, não corrigida) --------------
    comps = ["mortos", "feridos_leves", "feridos_graves", "ilesos", "ignorados"]
    soma = df[comps].sum(axis=1, min_count=len(comps))
    df["inconsistencia_contagem"] = (df["pessoas"].notna() & soma.notna() & (df["pessoas"] != soma))
    report["linhas_com_inconsistencia_contagem"] = int(df["inconsistencia_contagem"].sum())

    # ---- 8. Métricas derivadas -------------------------------------------------------
    df["ano"] = df["data"].dt.year.astype("Int16")
    df["mes"] = df["data"].dt.month.astype("Int8")
    df["dia_semana_num"] = df["data"].dt.dayofweek.astype("Int8")  # 0 = segunda
    df["fim_de_semana"] = df["dia_semana_num"] >= 5
    df["periodo_dia"] = pd.cut(
        df["hora"].to_numpy(dtype="float64", na_value=np.nan),
        bins=[-1, 5, 11, 17, 23], labels=PERIODOS,
    )
    df["total_vitimas"] = df["mortos"] + df["feridos_leves"] + df["feridos_graves"]
    df["tem_morte"] = df["mortos"] > 0
    df["tem_ferido_grave"] = df["feridos_graves"] > 0
    df["indice_severidade"] = sum(w * df[c] for c, w in SEVERITY_WEIGHTS.items())
    df["trecho"] = "BR-" + df["br"].astype("string")

    # ---- 9. Tipos finais e ordem de colunas --------------------------------------------
    for c in CATEGORY_COLUMNS + ["uf", "periodo_dia", "causa_principal", "ordem_tipo_acidente"]:
        df[c] = df[c].astype("category")

    ordered = [
        "id", "data", "ano", "mes", "dia_semana", "dia_semana_num", "fim_de_semana",
        "hora", "minuto", "periodo_dia", "uf", "municipio", "br", "trecho", "km",
        "latitude", "longitude", "causa_acidente", "causa_principal", "tipo_acidente",
        "ordem_tipo_acidente", "classificacao_acidente", "fase_dia", "sentido_via",
        "condicao_metereologica", "tipo_pista", "tracado_via", "uso_solo",
        "pessoas", "mortos", "feridos_leves", "feridos_graves", "feridos", "ilesos",
        "ignorados", "veiculos", "total_vitimas", "tem_morte", "tem_ferido_grave",
        "indice_severidade", "inconsistencia_contagem", "regional", "delegacia", "uop",
        "arquivo_origem",
    ]
    df = df[ordered].sort_values(["data", "id"], kind="stable").reset_index(drop=True)

    rejected = pd.concat(rejects, ignore_index=True) if rejects else pd.DataFrame()
    report["linhas_saida"] = int(len(df))
    report["linhas_rejeitadas_total"] = int(len(rejected))
    return df, rejected, report


# --------------------------------------------------------------------------- #
# Orquestração                                                                  #
# --------------------------------------------------------------------------- #
def discover_inputs(paths: list[str]) -> list[Path]:
    """Aceita arquivos e/ou diretórios; retorna lista ordenada e sem repetição."""
    found: list[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            for pattern in ("*.csv", "*.csv.gz", "*.zip"):
                found.extend(p.glob(pattern))
        elif p.is_file():
            found.append(p)
        else:
            raise FileNotFoundError(p)
    unique = sorted(set(found))
    if not unique:
        raise FileNotFoundError("Nenhum CSV/ZIP encontrado nas entradas informadas.")
    return unique


def save_table(df: pd.DataFrame, path: Path, fmt: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "parquet":
        out = path.with_suffix(".parquet")
        df.to_parquet(out, index=False)  # requer pyarrow
    elif fmt == "csv.gz":
        out = path.parent / (path.name.split(".")[0] + ".csv.gz")
        df.to_csv(out, index=False, compression="gzip")
    else:
        raise ValueError(fmt)
    return out


def run(inputs: list[str], output: Path, fmt: str = "parquet", uf: str | None = None) -> dict:
    files = discover_inputs(inputs)
    LOG.info("Arquivos de entrada: %s", [f.name for f in files])

    frames = [read_raw(f) for f in files]
    raw = pd.concat(frames, ignore_index=True)
    df, rejected, report = clean(raw)

    if uf:
        before = len(df)
        df = df.loc[df["uf"].astype("string") == uf.upper()].reset_index(drop=True)
        report["filtro_uf"] = {"uf": uf.upper(), "linhas_antes": before, "linhas_depois": len(df)}
        LOG.info("Filtro UF=%s: %d -> %d linhas", uf.upper(), before, len(df))

    out_path = save_table(df, output, fmt)
    if len(rejected):
        rej_path = output.parent / "acidentes_rejeitados.csv.gz"
        rejected.to_csv(rej_path, index=False, compression="gzip")

    report.update(
        {
            "gerado_em_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "versoes": {"pandas": pd.__version__, "numpy": np.__version__},
            "entradas": [{"arquivo": f.name, "sha256": sha256_of(f)} for f in files],
            "saida": out_path.name,
            "formato_saida": fmt,
            "pesos_severidade": SEVERITY_WEIGHTS,
        }
    )
    report_path = output.parent / "etl_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    LOG.info("Saída: %s | Relatório: %s", out_path, report_path)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="ETL dos BAT da PRF (acidentes por ocorrência)")
    parser.add_argument("--input", nargs="+", default=[str(RAW_DIR)],
                        help="Arquivos e/ou diretórios com CSV/ZIP (padrão: data/raw)")
    parser.add_argument("--output", type=Path, default=PROCESSED_DIR / "acidentes.parquet")
    parser.add_argument("--format", choices=["parquet", "csv.gz"], default="parquet")
    parser.add_argument("--uf", default=None, help="Filtra uma UF (ex.: RJ). Padrão: todas")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(args.input, args.output, args.format, args.uf)


if __name__ == "__main__":
    main()
