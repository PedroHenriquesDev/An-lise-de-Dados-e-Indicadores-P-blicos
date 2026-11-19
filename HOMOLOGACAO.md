# Homologação e reprodutibilidade

## Fonte e seleção dos dados

Fonte oficial: [Dados Abertos da PRF](https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf).

Foram selecionados os arquivos BAT de 2019 a 2025, na modalidade **Acidentes agrupados por ocorrência**. Não misturar com os arquivos agrupados por pessoa ou com o conjunto que inclui todas as causas e tipos por pessoa.

Dicionário oficial: [Dicionário de dados – Acidentes](https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dicionario-acidentes), seção “Dicionário de variáveis - acidentes agrupados por ocorrência (2017 em diante)”.

## Execução local

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m src.download --anos 2019 2020 2021 2022 2023 2024 2025
python -m src.etl --input data/raw --uf RJ
python -m src.build_article
```

## Critérios de homologação

- [ ] Os sete arquivos ZIP (2019–2025) foram baixados da página oficial.
- [ ] Os arquivos são os de acidentes agrupados por ocorrência.
- [ ] Os sete arquivos aparecem em `data/processed/etl_report.json`, com SHA-256.
- [ ] O relatório ETL registra a quantidade de linhas de entrada, saída e rejeitadas.
- [ ] O arquivo `acidentes.parquet` contém apenas `uf = RJ`.
- [ ] Os testes automatizados passam.
- [ ] O artigo `docs/index.html` foi gerado a partir do Parquet real.
- [ ] As imagens em `docs/assets/` correspondem à base processada.
- [ ] O site foi publicado e aberto em uma janela anônima para conferência.

## Limites da validação

Os testes automatizados do repositório usam dados sintéticos e verificam regras do ETL; eles não substituem a conferência com os arquivos oficiais. O dicionário local do projeto ainda precisa ser confrontado variável por variável com o dicionário oficial e com os valores observados nos sete CSVs. Até que essa etapa seja concluída, conclusões sobre domínios de variáveis (especialmente `uso_solo`) devem ser tratadas como pendentes.

A página de Dados Abertos da PRF informa que os arquivos BAT são disponibilizados em CSV compactado e apresenta arquivos separados por ocorrência e por pessoa. Os registros analisados são ocorrências atendidas pela PRF em rodovias federais; não representam todos os acidentes de trânsito no estado.
