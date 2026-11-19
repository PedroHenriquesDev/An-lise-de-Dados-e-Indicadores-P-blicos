# data/raw/

Esta pasta recebe os arquivos ZIP oficiais da PRF (CSV de acidentes agrupados por ocorrência).
Os arquivos brutos não são versionados por causa do tamanho. Baixe-os com:

```bash
python -m src.download --anos 2019 2020 2021 2022 2023 2024 2025
```

O script salva os arquivos como `datatranAAAA.zip`. Os identificadores de cada arquivo
foram conferidos com os links anuais da seção BAT na página oficial da PRF em 19/11/2026.

Fonte: https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf
Modalidade selecionada: acidentes agrupados por ocorrência.

Após o download, o ETL registra o nome e o SHA-256 de cada arquivo em
`data/processed/etl_report.json`.
