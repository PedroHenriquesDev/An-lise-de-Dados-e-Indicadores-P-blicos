# data/raw/

Esta pasta recebe os CSVs originais da PRF (acidentes agrupados por ocorrência).
Os arquivos têm mais de 50 MB, então **não são versionados**; baixe com:

```bash
python -m src.download --anos 2022 2023 2024 2025
```

Fonte: https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf
Data de acesso: __/__/2026  (preencha)

Após o download, registre aqui o nome e o SHA-256 de cada arquivo (o ETL também grava os
hashes em `data/processed/etl_report.json`).
