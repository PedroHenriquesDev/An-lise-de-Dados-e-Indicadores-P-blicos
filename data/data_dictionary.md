# Dicionário de Dados

**Conjunto:** `data/processed/acidentes.parquet` (uma linha por acidente/ocorrência)
**Fonte original:** PRF, Boletim de Acidente de Trânsito (BAT), acidentes agrupados por ocorrência
**Dicionário oficial da PRF:** https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dicionario-acidentes
**Licença deste dicionário:** CC BY 4.0

> **Status: ESQUELETO.** As colunas brutas abaixo seguem o layout conhecido dos arquivos da PRF,
> mas esta versão **não foi conferida contra o dicionário oficial nem contra os arquivos reais**.
> Antes da entrega: (1) abra o dicionário oficial; (2) rode `df.info()` e `df[col].unique()` nos
> dados baixados; (3) preencha as colunas "Domínio observado" e corrija descrições/tipos.
> Itens marcados com **[VERIFICAR]** precisam dessa conferência.

Convenções: **Tipo bruto** = como vem no CSV (sempre lido como texto); **Tipo processado** = tipo no
Parquet (`Int*`/`Float64` aceitam nulos). Valores ausentes viram `NA`/`NaN`.

## 1. Variáveis originais (PRF)

| Variável | Descrição | Tipo bruto | Tipo processado | Formato / domínio | Tratamento no ETL |
|---|---|---|---|---|---|
| `id` | Identificador do acidente | inteiro | `Int64` | número | Convertido; duplicatas exatas removidas e registradas |
| `data_inversa` → `data` | Data da ocorrência | texto `AAAA-MM-DD` **[VERIFICAR; anos antigos podem usar `DD/MM/AAAA`]** | `datetime64` | ISO 8601 | Duas tentativas de formato; inválida => linha rejeitada |
| `dia_semana` | Dia da semana por extenso | texto | `category` | segunda…domingo | `strip` + capitalização |
| `horario` → `hora`, `minuto` | Hora da ocorrência | texto `HH:MM:SS` | `Int8` (hora 0-23, minuto 0-59) | 24 h | Fora do intervalo ou ausente => NA |
| `uf` | Unidade da Federação | texto | `category` | sigla de 2 letras | Maiúscula; ausente => linha rejeitada |
| `br` | Número da rodovia federal | inteiro | `Int16` | ex.: 101, 116 | Convertido |
| `km` | Quilômetro da rodovia | decimal com vírgula | `Float64` | 0 a 4500 (limite do ETL) | Vírgula => ponto; fora do intervalo => NA |
| `municipio` | Município da ocorrência | texto | `string` | MAIÚSCULAS | `strip` + maiúscula |
| `causa_acidente` | Causa presumida do acidente | texto | `category` | **[VERIFICAR]** lista de causas | Padronização de caixa |
| `causa_principal` | Indica se é a causa principal (arquivos recentes) | texto | `category` | Sim / Não **[VERIFICAR]** | Opcional: criada vazia se não existir |
| `tipo_acidente` | Tipo (colisão, saída de pista, etc.) | texto | `category` | **[VERIFICAR]** | Padronização de caixa |
| `ordem_tipo_acidente` | Ordem do tipo em acidentes com mais de um tipo | texto | `category` | **[VERIFICAR]** | Opcional |
| `classificacao_acidente` | Gravidade registrada pela PRF | texto | `category` | Sem vítimas / Com vítimas feridas / Com vítimas fatais / Ignorado **[VERIFICAR]** | Padronização de caixa |
| `fase_dia` | Fase do dia | texto | `category` | Amanhecer / Pleno dia / Anoitecer / Plena noite **[VERIFICAR]** | Padronização de caixa |
| `sentido_via` | Sentido da via | texto | `category` | Crescente / Decrescente / Não informado **[VERIFICAR]** | Padronização de caixa |
| `condicao_metereologica` | Condição meteorológica (grafia original da PRF) | texto | `category` | Céu claro, Chuva, Nublado… **[VERIFICAR]** | Padronização de caixa |
| `tipo_pista` | Tipo de pista | texto | `category` | Simples / Dupla / Múltipla **[VERIFICAR]** | Padronização de caixa |
| `tracado_via` | Traçado da via | texto | `category` | Reta, Curva, Cruzamento… **[VERIFICAR]** | Padronização de caixa |
| `uso_solo` | Uso do solo no entorno | texto | `category` | Sim = urbano / Não = rural **[VERIFICAR]** | Padronização de caixa |
| `pessoas` | Total de pessoas envolvidas | inteiro | `Int32` | ≥ 0 | Negativo => NA |
| `mortos` | Número de mortos | inteiro | `Int32` | ≥ 0 | Negativo => NA |
| `feridos_leves` | Feridos leves | inteiro | `Int32` | ≥ 0 | Negativo => NA |
| `feridos_graves` | Feridos graves | inteiro | `Int32` | ≥ 0 | Negativo => NA |
| `feridos` | Total de feridos | inteiro | `Int32` | ≥ 0 | Negativo => NA |
| `ilesos` | Ilesos | inteiro | `Int32` | ≥ 0 | Negativo => NA |
| `ignorados` | Estado ignorado | inteiro | `Int32` | ≥ 0 | Negativo => NA |
| `veiculos` | Veículos envolvidos | inteiro | `Int32` | ≥ 0 | Negativo => NA |
| `latitude` | Latitude (graus decimais) | decimal com vírgula | `Float64` | -34 a 6 | Vírgula => ponto; fora do Brasil => NA |
| `longitude` | Longitude (graus decimais) | decimal com vírgula | `Float64` | -74 a -34 | Vírgula => ponto; fora do Brasil => NA |
| `regional` | Superintendência regional da PRF | texto | `string` | ex.: SR-RJ | `strip` + maiúscula |
| `delegacia` | Delegacia responsável | texto | `string` | ex.: DEL1/7 **[VERIFICAR]** | `strip` + maiúscula |
| `uop` | Unidade operacional | texto | `string` | ex.: UOP02/RJ **[VERIFICAR]** | `strip` + maiúscula |

## 2. Variáveis derivadas (criadas pelo ETL)

| Variável | Descrição | Tipo | Regra |
|---|---|---|---|
| `ano` | Ano da ocorrência | `Int16` | `data.year` |
| `mes` | Mês (1-12) | `Int8` | `data.month` |
| `dia_semana_num` | Dia da semana (0 = segunda … 6 = domingo) | `Int8` | `data.dayofweek` |
| `fim_de_semana` | Ocorreu em sábado/domingo | `bool` | `dia_semana_num >= 5` |
| `periodo_dia` | Faixa do dia | `category` | madrugada 0-5, manha 6-11, tarde 12-17, noite 18-23 |
| `trecho` | Rótulo da rodovia | `string` | `"BR-" + br` |
| `total_vitimas` | Mortos + feridos leves + feridos graves | `Int32` | soma (NA se algum componente for NA) |
| `tem_morte` | Houve ao menos um morto | `bool` | `mortos > 0` |
| `tem_ferido_grave` | Houve ao menos um ferido grave | `bool` | `feridos_graves > 0` |
| `indice_severidade` | Severidade ponderada | `Int32` | `13·mortos + 6·feridos_graves + 4·feridos_leves` **[VERIFICAR/CITAR referência dos pesos]** |
| `inconsistencia_contagem` | `pessoas` difere da soma de mortos+leves+graves+ilesos+ignorados | `bool` | sinalização; a linha é mantida |
| `arquivo_origem` | Arquivo bruto de onde a linha veio | `string` | rastreabilidade |

## 3. Artefatos de rastreabilidade

| Arquivo | Conteúdo |
|---|---|
| `data/processed/acidentes_rejeitados.csv.gz` | Linhas descartadas, com a coluna `motivo_rejeicao` |
| `data/processed/etl_report.json` | Contagens de cada correção, versões de bibliotecas e SHA-256 dos arquivos de entrada |

## 4. Limitações conhecidas

- Os dados são registros de acidentes **atendidos pela PRF em rodovias federais**; não representam
  todos os acidentes do país nem vias estaduais/municipais.
- Mortos contabilizados no local; óbitos posteriores no hospital podem não constar.
- O esquema de colunas mudou ao longo dos anos; este ETL foi desenhado para arquivos recentes
  (ex.: 2019 em diante). Anos anteriores exigem conferência.
