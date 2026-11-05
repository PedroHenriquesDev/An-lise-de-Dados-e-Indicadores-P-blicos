# An-lise-de-Dados-e-Indicadores-P-blicos

# [TÍTULO DO PROJETO]: Acidentes em Rodovias Federais (PRF)

![Python](https://img.shields.io/badge/python-3.12-blue)
![Código: MIT](https://img.shields.io/badge/c%C3%B3digo-MIT-green)
![Dados e texto: CC BY 4.0](https://img.shields.io/badge/dados%20e%20texto-CC%20BY%204.0-lightgrey)
![FAIR](https://img.shields.io/badge/princ%C3%ADpios-FAIR-orange)

**Artigo (GitHub Pages):** https://github.com/PedroHenriquesDev/An-lise-de-Dados-e-Indicadores-P-blicos/tree/main

| | |
|---|---|
| **Autores** | Pedro Henriques Silva, Carlos Eduardo Julio da Costa|
| **Instituição / Curso** | Unilasalle RJ, Bacharelado em Sistemas de Informação |
| **Disciplina / Semestre** | Linguagem de Programação (Análise e Visualização de Dados com Python), 6º período, 2026/2 |
| **Docente** | Alexandre Louzada |

## Resumo executivo

[Escreva 4 a 6 linhas: contexto (acidentes em rodovias federais), dados (BAT da PRF, período e recorte),
método (pipeline ETL em Python + análise exploratória) e principais achados.]

**Perguntas de pesquisa**

- **RQ1:** [ex.: como a gravidade dos acidentes varia por horário, dia da semana e condição meteorológica?]
- **RQ2:** [ex.: quais causas concentram mais mortes e isso difere entre trechos urbanos e rurais?]
- **RQ3:** [ex.: quais trechos concentram mais acidentes e como evoluíram entre 2019 e 2025?]

**Palavras-chave:** acidentes de trânsito; rodovias federais; Polícia Rodoviária Federal; dados abertos; análise exploratória; FAIR

## Fonte dos dados

- **Origem:** Polícia Rodoviária Federal (PRF), Boletim de Acidente de Trânsito (BAT), acidentes agrupados por ocorrência.
- **Link perene:** https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf
- **Dicionário oficial:** https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dicionario-acidentes
- **Data de acesso:** __/__/2026
- **Recorte usado:** [anos e UF, ex.: 2019 a 2025, RJ]

## Estrutura do repositório

```
.
├── README.md
├── LICENSE                    # MIT (código)
├── LICENSE-DATA.md            # CC BY 4.0 (dados processados e texto) e nota sobre a fonte
├── requirements.txt           # dependências com versões fixadas
├── data/
│   ├── raw/                   # CSVs originais (não versionados; script de download)
│   ├── processed/             # saída do ETL (Parquet + rejeitados + relatório)
│   └── data_dictionary.md     # dicionário de variáveis
├── notebooks/
│   └── analise_exploratoria.ipynb
├── src/
│   ├── etl.py                 # limpeza, tipos, métricas derivadas, relatório de qualidade
│   └── download.py            # download dos CSVs da fonte
├── tests/test_etl.py          # testes do ETL com dados sintéticos
└── docs/                      # artigo HTML (GitHub Pages)
    ├── index.html
    └── assets/
```

## Como reproduzir

```bash
# 1. Clonar e criar ambiente
git clone https://github.com/[USUARIO]/[REPOSITORIO].git
cd [REPOSITORIO]
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Baixar os dados brutos (sem login)
python -m src.download --anos 2019 2020 2021 2022 2023 2024 2025

# 3. Rodar o ETL (exemplo: só o Rio de Janeiro)
python -m src.etl --input data/raw --uf RJ

# 4. (Opcional) Testes
python -m pytest -q

# 5. Abrir a análise
jupyter lab notebooks/analise_exploratoria.ipynb
```

Saídas do ETL em `data/processed/`:

- `acidentes.parquet`: tabela limpa, uma linha por acidente
- `acidentes_rejeitados.csv.gz`: linhas descartadas e o motivo
- `etl_report.json`: contagens de cada correção, versões e SHA-256 dos arquivos de entrada

## Decisões de tratamento (resumo)

- CSVs lidos como texto, com detecção de codificação (UTF-8 ou latin-1) e de separador.
- Vírgula decimal convertida para ponto em `km`, `latitude` e `longitude`.
- Nada é apagado em silêncio: duplicatas exatas e linhas com data ou UF inválida vão para o arquivo de rejeitados.
- Valores implausíveis (coordenadas fora do Brasil, km absurdo, contagens negativas) viram `NA`; a linha é mantida.
- Inconsistências entre `pessoas` e a soma das categorias são sinalizadas em `inconsistencia_contagem`.

Detalhes e regras em [`data/data_dictionary.md`](data/data_dictionary.md).

## Conformidade FAIR

| Princípio | Como é atendido |
|---|---|
| **Findable** | README com resumo, palavras-chave, autoria e link perene da fonte |
| **Accessible** | Repositório público; download sem credenciais; artigo em GitHub Pages |
| **Interoperable** | Dicionário de dados; saída em Parquet (aberto) |
| **Reusable** | Licença MIT (código) e CC BY 4.0 (dados e texto); `requirements.txt` com versões fixadas |

## Licenças e citação

- Código: [MIT](LICENSE).
- Dados processados, dicionário e texto: [CC BY 4.0](LICENSE-DATA.md). Os dados originais são da PRF; veja a nota na licença.

Sugestão de citação:

> [SOBRENOME, Nome et al.]. *[Título do projeto]*. 2026. Repositório GitHub. Disponível em: https://github.com/[USUARIO]/[REPOSITORIO].
