"""Baixa os CSVs de acidentes (agrupados por ocorrência) da PRF para data/raw/.

Fonte oficial (página perene):
https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf

Os arquivos ficam hospedados em links públicos do Google Drive (sem login).
Os IDs abaixo foram copiados da página oficial; a PRF pode trocá-los ao
republicar os dados. Se um download falhar, abra a página, copie o novo link e
atualize o ID. Confira sempre o nome/conteúdo do arquivo baixado.

Uso:
    python -m src.download                 # anos padrão (2019-2025)
    python -m src.download --anos 2022 2023
"""
from __future__ import annotations

import argparse
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

# ano -> ID do arquivo no Google Drive (acidentes agrupados por ocorrência)
GDRIVE_IDS_OCORRENCIA = {
    2019: "1pN3fn2wY34GH6cY-gKfbxRJJBFE0lb_l",
    2020: "1esu6IiH5TVTxFoedv6DBGDd01Gvi8785",
    2021: "12xH8LX9aN2gObR766YN3cMcuycwyCJDz",
    2022: "1PRQjuV5gOn_nn6UNvaJyVURDIfbSAK4-",
    2023: "1-WO3SfNrwwZ5_l7fRTiwBKRw7mi1-HUq",
    2024: "14lB0vqMFkaZj8HZ44b0njYgxs9nAN8KO",
    2025: "1-G3MdmHBt6CprDwcW99xxC4BZ2DU5ryR",
}
DEFAULT_YEARS = sorted(GDRIVE_IDS_OCORRENCIA)


def download(years: list[int], dest: Path = RAW_DIR) -> list[str]:
    import gdown  # import tardio: só necessário para baixar

    dest.mkdir(parents=True, exist_ok=True)
    saved = []
    for year in years:
        if year not in GDRIVE_IDS_OCORRENCIA:
            raise KeyError(f"Ano {year} não configurado em GDRIVE_IDS_OCORRENCIA")
        # output terminando em '/' preserva o nome original do arquivo no Drive
        out = gdown.download(id=GDRIVE_IDS_OCORRENCIA[year], output=str(dest) + "/", quiet=False)
        if out is None:
            raise RuntimeError(f"Falha ao baixar {year}. Veja o aviso no topo deste arquivo.")
        saved.append(out)
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description="Download dos BAT (PRF) para data/raw/")
    parser.add_argument("--anos", nargs="+", type=int, default=DEFAULT_YEARS)
    args = parser.parse_args()
    for path in download(args.anos):
        print("baixado:", path)


if __name__ == "__main__":
    main()
