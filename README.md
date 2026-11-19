# Análise-de-Dados-e-Indicadores-Públicos

# Acidentes em Rodovias Federais (PRF)

![Python](https://img.shields.io/badge/python-3.12-blue)
![Código: MIT](https://img.shields.io/badge/c%C3%B3digo-MIT-green)
![Dados e texto: CC BY 4.0](https://img.shields.io/badge/dados%20e%20texto-CC%20BY%204.0-lightgrey)
![FAIR](https://img.shields.io/badge/princ%C3%ADpios-FAIR-orange)

**Artigo (GitHub Pages):** o endereço ficará disponível em
`https://pedrohenriquesdev.github.io/An-lise-de-Dados-e-Indicadores-P-blicos/`.

| | |
|---|---|
| **Autores** | Pedro Henriques Silva, Carlos Eduardo Julio da Costa|
| **Instituição / Curso** | Unilasalle RJ, Bacharelado em Sistemas de Informação |
| **Disciplina / Semestre** | Linguagem de Programação (Análise e Visualização de Dados com Python), 6º período, 2026/2 |
| **Docente** | Alexandre Louzada |

## Resumo executivo

Acidentes em rodovias federais representam um problema relevante de saúde pública e de gestão da infraestrutura viária no Brasil. Este trabalho analisa os dados abertos do Boletim de Acidente de Trânsito (BAT) da Polícia Rodoviária Federal (PRF), com acidentes agrupados por ocorrência, no período de 2019 a 2025, com recorte para o estado do Rio de Janeiro (RJ). 
O método consiste em um pipeline ETL em Python (leitura com detecção de codificação, tratamento de tipos, métricas derivadas, rejeição documentada de registros inválidos e relatório de qualidade), seguido de análise exploratória e geração automatizada do artigo HTML e das visualizações.

**Perguntas de pesquisa**

- **RQ1:** Como a gravidade dos acidentes varia por horário, dia da semana e condição meteorológica?
- **RQ2:** Quais causas concentram mais mortes e isso difere entre trechos urbanos e rurais?
- **RQ3:** Quais trechos concentram mais acidentes e como evoluíram entre 2019 e 2025?

**Palavras-chave:** acidentes de trânsito; rodovias federais; Polícia Rodoviária Federal; dados abertos; análise exploratória; FAIR

## Fonte dos dados

- **Origem:** Polícia Rodoviária Federal (PRF), Boletim de Acidente de Trânsito (BAT), acidentes agrupados por ocorrência.
- **Link perene:** https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf
- **Dicionário oficial:** https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dicionario-acidentes
- **Data de consulta da fonte:** 19/11/2026
- **Recorte usado:** 2019 a 2025, UF = RJ

## Estrutura do repositório

```
.
├── README.md
├── LICENSE                    # MIT (código)
├── LICENSE-DATA.md            # CC BY 4.0 (dados processados e texto) e nota sobre a fonte
├── requirements.txt           # dependências do projeto
├── data/
│   ├── raw/                   # CSVs originais (não versionados; script de download)
│   ├── processed/             # saída do ETL (Parquet + rejeitados + relatório)
│   └── data_dictionary.md     # dicionário de variáveis
├── src/
│   ├── etl.py                 # limpeza, tipos, métricas derivadas, relatório de qualidade
│   ├── download.py            # download dos CSVs da fonte
│   └── build_article.py       # gera artigo HTML e gráficos da base processada
├── tests/test_etl.py          # testes do ETL com dados sintéticos
├── docs/                      # site do artigo (GitHub Pages)
│   ├── index.html              # página inicial / artigo gerado
│   └── assets/                 # gráficos gerados
└── .github/workflows/pages.yml # publicação automática no GitHub Pages
```

## Como reproduzir

Os arquivos oficiais são publicados pela PRF em ZIP contendo CSV. Para este estudo, o script usa exclusivamente a opção **Acidentes agrupados por ocorrência** para cada ano de 2019 a 2025 (uma linha por ocorrência), e não as bases agrupadas por pessoa. Os identificadores de download foram conferidos com os links da página oficial consultada em 19/11/2026.

A geração e publicação completas também podem ser executadas pelo GitHub Actions: abra a aba **Actions**, selecione **Gerar artigo e publicar no GitHub Pages** e clique em **Run workflow**. O processo baixa as bases, roda os testes, executa o ETL para RJ, gera o artigo e publica a pasta `docs/`. O download depende de os links públicos do Google Drive da PRF permanecerem acessíveis.

```bash
# 1. Clonar e criar ambiente
git clone https://github.com/PedroHenriquesDev/An-lise-de-Dados-e-Indicadores-P-blicos.git
cd An-lise-de-Dados-e-Indicadores-P-blicos
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Baixar os dados brutos
python -m src.download --anos 2019 2020 2021 2022 2023 2024 2025

# 3. Rodar o ETL
python -m src.etl --input data/raw --uf RJ

# 4. Testes
python -m pytest -q

# 5. Gerar artigo HTML e gráficos reais para o GitHub Pages
python -m src.build_article
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
| **Accessible** | Repositório público; dados brutos obtidos no portal da PRF; publicação Pages configurada por workflow |
| **Interoperable** | Dicionário de dados; saída em Parquet (aberto) |
| **Reusable** | Licença MIT (código), CC BY 4.0 (texto e derivados), dicionário e relatório de rastreabilidade; versões das dependências ainda precisam ser totalmente fixadas |

## Licenças e citação

- Código: [MIT](LICENSE).
- Dados processados, dicionário e texto: [CC BY 4.0](LICENSE-DATA.md). Os dados originais são da PRF; veja a nota na licença.

> SILVA, Pedro Henrique; COSTA, Carlos Eduardo Julio da. Acidentes em Rodovias Federais (PRF). 2026. Repositório GitHub. Disponível em: https://github.com/PedroHenriquesDev/An-lise-de-Dados-e-Indicadores-P-blicos. Acesso em: 6 nov. 2026.
