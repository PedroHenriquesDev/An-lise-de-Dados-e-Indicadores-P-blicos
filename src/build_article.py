"""Gera artigo HTML e gráficos reais a partir de data/processed/acidentes.parquet."""
from pathlib import Path
import html, json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
DOCS = ROOT / "docs"
ASSETS = DOCS / "assets"

def load_data():
    p = DATA / "acidentes.parquet"
    c = DATA / "acidentes.csv.gz"
    if p.exists():
        df = pd.read_parquet(p)
    elif c.exists():
        df = pd.read_csv(c, parse_dates=["data"])
    else:
        raise FileNotFoundError("Base ausente. Execute src.download e depois src.etl conforme README.")
    if "uf" in df:
        df = df[df.uf.astype("string").str.upper().eq("RJ")].copy()
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df = df.dropna(subset=["data"])
    if df.empty:
        raise ValueError("Não há registros válidos do RJ na base.")
    return df

def bar(series, title, xlabel, ylabel, filename, horizontal=False, line=False):
    fig, ax = plt.subplots(figsize=(9, 4.5), layout="constrained")
    if line:
        series.plot(ax=ax, marker="o", linewidth=2)
    elif horizontal:
        series.plot(kind="barh", ax=ax)
    else:
        series.plot(kind="bar", ax=ax)
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold")
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
    ax.grid(axis="x" if horizontal else "y", alpha=.2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(ASSETS / filename, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)

def fmt(n):
    return f"{int(n):,}".replace(",", ".")

def main():
    DOCS.mkdir(exist_ok=True); ASSETS.mkdir(exist_ok=True)
    df = load_data()
    charts = {"rq1": [], "rq2": [], "rq3": [], "extra": []}
    def add(filename, title, description, group="extra"):
        if (ASSETS / filename).exists():
            charts[group].append(f'<figure><img src="assets/{filename}" alt="{html.escape(title)}"><figcaption><b>{html.escape(title)}.</b> {html.escape(description)}</figcaption></figure>')
    annual = df.groupby(df.data.dt.year).size().sort_index()
    bar(annual, "Acidentes registrados por ano", "Ano", "Ocorrências", "acidentes-ano.png", line=True)
    add("acidentes-ano.png", "Evolução anual", "Número absoluto de ocorrências por ano; permite observar a evolução temporal do recorte.", "rq3")
    periods_order = ["madrugada", "manha", "tarde", "noite"]
    if "periodo_dia" in df:
        periods = df.periodo_dia.astype("string").value_counts().reindex(periods_order).dropna()
        periods = periods[periods > 0]
        if len(periods):
            bar(periods, "Ocorrências por período do dia", "Período", "Ocorrências", "periodo-dia.png")
            add("periodo-dia.png", "Período do dia", "Distribuição das ocorrências por faixa horária. Este gráfico descreve frequência, não gravidade.", "rq1")
    days_order = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
    if "dia_semana" in df:
        days = df.dia_semana.astype("string").str.lower().value_counts().reindex(days_order).dropna()
        days = days[days > 0]
        if len(days):
            bar(days, "Ocorrências por dia da semana", "Dia", "Ocorrências", "dia-semana.png")
            add("dia-semana.png", "Dia da semana", "Distribuição das ocorrências conforme o dia registrado.", "rq1")
    if {"causa_acidente", "mortos"}.issubset(df.columns):
        tmp = df.assign(_mortos=pd.to_numeric(df.mortos, errors="coerce").fillna(0))
        causes = tmp.groupby("causa_acidente", observed=True)._mortos.sum().nlargest(10).sort_values()
        if len(causes):
            bar(causes, "Causas registradas com maior soma de vítimas fatais", "Causa", "Mortos registrados", "causas-mortes.png", horizontal=True)
            add("causas-mortes.png", "Causas e vítimas fatais", "Soma do campo mortos por causa registrada; associação descritiva, não prova causalidade.", "rq2")
    if "br" in df:
        roads = pd.to_numeric(df.br, errors="coerce").dropna().value_counts().head(10).sort_values()
        if len(roads):
            roads.index = [f"BR-{int(v)}" for v in roads.index]
            bar(roads, "Rodovias com maior número de ocorrências", "Rodovia", "Ocorrências", "rodovias.png")
            add("rodovias.png", "Rodovias em destaque", "Dez rodovias federais com mais ocorrências no recorte. O campo BR não identifica, sozinho, um trecho geográfico preciso.", "rq3")
    if "classificacao_acidente" in df:
        classes = df.classificacao_acidente.astype("string").value_counts().head(8).sort_values()
        if len(classes):
            bar(classes, "Ocorrências por classificação registrada", "Classificação", "Ocorrências", "classificacao.png")
            add("classificacao.png", "Classificação", "Distribuição conforme classificação informada pela PRF.", "rq1")
    years = sorted(df.data.dt.year.unique())
    deaths = fmt(pd.to_numeric(df.mortos, errors="coerce").fillna(0).sum()) if "mortos" in df else "Não disponível"
    injured = fmt(pd.to_numeric(df.feridos, errors="coerce").fillna(0).sum()) if "feridos" in df else "Não disponível"
    report_note = ""
    rp = DATA / "etl_report.json"
    if rp.exists():
        try:
            r = json.loads(rp.read_text(encoding="utf-8"))
            report_note = f" Relatório do ETL: {fmt(r.get('linhas_entrada', 0))} linhas de entrada, {fmt(r.get('linhas_rejeitadas_total', 0))} rejeitadas e {fmt(r.get('linhas_saida', 0))} na saída."
        except Exception:
            pass
    cards = "".join(f'<div class="metric"><span>{k}</span><b>{v}</b></div>' for k,v in [
        ("Ocorrências analisadas", fmt(len(df))), ("Período coberto", f"{years[0]}–{years[-1]}"),
        ("Mortos registrados", deaths), ("Feridos registrados", injured)])
    html_doc = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Acidentes em Rodovias Federais — PRF | RJ</title><meta name="description" content="Artigo científico sobre acidentes em rodovias federais no RJ.">
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#f3f6f7;color:#183141;font:16px/1.7 system-ui,Segoe UI,sans-serif}}
header{{background:#102f40;color:#fff;padding:58px 22px}}.wrap,main{{max-width:1050px;margin:auto}}.eyebrow{{color:#a6dbe7;text-transform:uppercase;letter-spacing:.13em;font-size:.78rem;font-weight:700}}.authors{{margin:18px 0 4px;font-size:1.08rem;font-weight:700;color:#fff}}.affiliation{{margin:3px 0;color:#d9e8ed;font-size:.96rem}}.repo-link{{display:inline-block;margin-top:16px;padding:10px 16px;border:1px solid #8fc5d3;border-radius:8px;color:#fff;text-decoration:none;font-weight:700}}.repo-link:hover{{background:#1b4b60}}
h1{{font-size:clamp(2rem,5vw,3.6rem);line-height:1.1;margin:12px 0}}header p{{color:#d9e8ed;max-width:760px}}
main{{padding:25px 20px}}section,.abstract{{background:#fff;border:1px solid #dce5e9;border-radius:15px;padding:26px;margin:20px 0;box-shadow:0 7px 22px #1831410a}}
h2{{color:#14516a;margin:0 0 12px;font-size:1.45rem}}h3{{margin:18px 0 5px;font-size:1.05rem}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:12px;margin:18px 0}}.metric{{background:#edf5f7;padding:16px;border-radius:11px}}.metric span{{display:block;color:#637783;font-size:.85rem}}.metric b{{font-size:1.5rem;color:#14566d}}
.charts{{display:grid;grid-template-columns:1fr;gap:18px}}.rq-tabs{{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}}.rq-tab{{border:1px solid #b9cbd2;background:#edf5f7;color:#14516a;padding:12px 18px;border-radius:9px;font-weight:750;cursor:pointer}}.rq-tab[aria-selected="true"]{{background:#14516a;color:#fff;border-color:#14516a}}.rq-panel{{display:none;border:1px solid #dce5e9;border-radius:13px;padding:20px;margin-top:12px}}.rq-panel.active{{display:block}}.rq-question{{font-size:1.12rem;font-weight:750;color:#173e50;background:#edf5f7;padding:16px;border-radius:10px;margin:8px 0 18px}}.rq-explanation{{margin-top:20px;background:#f7f9fa;border-left:4px solid #2c8198;padding:16px 18px;border-radius:7px}}figure{{margin:0;border:1px solid #dce5e9;border-radius:12px;padding:12px;min-width:0}}figure img{{width:100%;height:auto;display:block}}figcaption{{font-size:.9rem;color:#60717c;padding:7px 3px}}
.notice{{background:#fff8e8;border-left:4px solid #d29b38;padding:13px 16px}}a{{color:#176b87}}pre{{overflow:auto;background:#132f3d;color:#edf7fa;padding:16px;border-radius:9px}}footer{{text-align:center;padding:25px;color:#657680;font-size:.88rem}}
@media(max-width:600px){{section,.abstract{{padding:19px}}header{{padding:40px 20px}}}}
</style></head><body><header><div class="wrap"><div class="eyebrow">Artigo científico · Dados públicos</div>
<h1>Acidentes em Rodovias Federais no Estado do Rio de Janeiro</h1><p>Análise exploratória dos registros da Polícia Rodoviária Federal no período {years[0]}–{years[-1]}.</p><p class="authors">Pedro Henriques Silva; Carlos Eduardo Júlio da Costa</p><p class="affiliation"><i>Departamento de Sistemas de Informação — Universidade LaSalle, Niterói/RJ</i></p><p class="affiliation"><i>Disciplina: Linguagens de Programação — 6º Período</i></p><a class="repo-link" href="https://github.com/PedroHenriquesDev/An-lise-de-Dados-e-Indicadores-P-blicos" target="_blank" rel="noopener">📦 Ver Repositório GitHub (Código e Dados)</a></div></header>
<main><div class="abstract"><h2>Resumo</h2><p>Este estudo analisa registros de acidentes em rodovias federais atendidos pela Polícia Rodoviária Federal (PRF), com recorte para o estado do Rio de Janeiro. A unidade de análise é a ocorrência registrada. O método compreende obtenção dos arquivos públicos, padronização e validação dos campos, criação de variáveis derivadas e análise descritiva de padrões temporais, causas registradas, rodovias e classificação dos acidentes.</p><p><b>Palavras-chave:</b> acidentes de trânsito; rodovias federais; PRF; dados abertos; análise exploratória; Rio de Janeiro.</p></div>
<section><h2>1. Introdução</h2><p>Os acidentes de trânsito constituem tema relevante para a segurança viária e para o planejamento de políticas públicas. Registros administrativos permitem descrever padrões temporais e territoriais dos acidentes atendidos pela PRF. Este estudo limita-se a ocorrências registradas em rodovias federais no estado do Rio de Janeiro; portanto, não representa a totalidade dos acidentes do estado nem abrange automaticamente vias estaduais e municipais.</section>
<section><h2>2. Objetivos e perguntas de pesquisa</h2><p>O objetivo geral é explorar os registros de acidentes em rodovias federais no RJ, descrevendo sua distribuição temporal, características registradas e concentração por rodovia.</p><ul><li><b>RQ1:</b> Como a gravidade dos acidentes varia por horário, dia da semana e condição meteorológica?</li><li><b>RQ2:</b> Quais causas concentram mais mortes e isso difere entre trechos urbanos e rurais?</li><li><b>RQ3:</b> Quais trechos concentram mais acidentes e como evoluíram entre 2019 e 2025?</li></ul><p>A comparação urbano/rural depende da validação do domínio da variável de uso do solo no dicionário oficial da PRF.</section>
<section><h2>3. Materiais e métodos</h2><h3>3.1 Fonte e recorte</h3><p>Foram utilizados dados abertos do Boletim de Acidente de Trânsito (BAT) da PRF, agrupados por ocorrência, para UF RJ. Fonte: <a href="https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dados-abertos-da-prf">Portal de Dados Abertos da PRF</a>. Dicionário: <a href="https://www.gov.br/prf/pt-br/acesso-a-informacao/dados-abertos/dicionario-acidentes">Dicionário de acidentes</a>.</p><h3>3.2 Tratamento</h3><p>O ETL em Python detecta codificação e separador, padroniza nomes e textos, converte datas e números, remove duplicatas exatas com rastreabilidade e rejeita registros com data inválida ou UF ausente. Valores negativos em contagens e valores implausíveis de quilometragem ou coordenadas são convertidos em ausentes. Inconsistências entre total de pessoas e categorias são sinalizadas, sem correção silenciosa.</p><h3>3.3 Variáveis e análise</h3><p>São derivadas variáveis de ano, mês, dia da semana, fim de semana, período do dia, rodovia, total de vítimas e indicadores de presença de morte ou ferido grave. As figuras são calculadas diretamente da base processada. Contagens absolutas não equivalem a taxas de risco, pois não há denominador de fluxo de veículos ou exposição.</p><p>O índice ponderado de severidade existente no ETL não fundamenta conclusões principais enquanto seus pesos não forem justificados por referência metodológica validada.</section>
<section><h2>4. Resultados e visualizações</h2><div class="metrics">{cards}</div><p>Foram analisadas {fmt(len(df))} ocorrências válidas, no período {years[0]}–{years[-1]}.{html.escape(report_note)}</p>
<div class="rq-tabs" role="tablist" aria-label="Perguntas de pesquisa"><button class="rq-tab" role="tab" id="tab-rq1" aria-controls="panel-rq1" aria-selected="true" onclick="showRQ('rq1')">RQ1 · Quando?</button><button class="rq-tab" role="tab" id="tab-rq2" aria-controls="panel-rq2" aria-selected="false" onclick="showRQ('rq2')">RQ2 · Causas e mortes</button><button class="rq-tab" role="tab" id="tab-rq3" aria-controls="panel-rq3" aria-selected="false" onclick="showRQ('rq3')">RQ3 · Rodovias e evolução</button></div>
<div class="rq-panel active" id="panel-rq1" role="tabpanel" aria-labelledby="tab-rq1"><div class="rq-question">RQ1: Como a gravidade dos acidentes varia por horário, dia da semana e condição meteorológica?</div><div class="charts">{''.join(charts['rq1']) or '<p>Não há gráficos disponíveis para as variáveis desta pergunta na base processada.</p>'}</div><div class="rq-explanation"><h3>Explicação da RQ1</h3><p>Os gráficos disponíveis descrevem a distribuição das ocorrências por período do dia e dia da semana (e classificação, quando presente). Eles ajudam a identificar em quais períodos há mais registros, mas frequência não é sinônimo de gravidade. A pergunta só poderá ser respondida integralmente quando houver gráficos cruzando indicadores de gravidade com horário, dia da semana e condição meteorológica. A condição meteorológica e a gravidade não são inferidas a partir de contagens gerais.</p></div></div>
<div class="rq-panel" id="panel-rq2" role="tabpanel" aria-labelledby="tab-rq2"><div class="rq-question">RQ2: Quais causas concentram mais mortes e isso difere entre trechos urbanos e rurais?</div><div class="charts">{''.join(charts['rq2']) or '<p>Não há gráficos disponíveis para esta pergunta na base processada.</p>'}</div><div class="rq-explanation"><h3>Explicação da RQ2</h3><p>O gráfico apresenta a soma do campo de mortes por causa registrada pela PRF, permitindo comparar os totais associados a cada categoria. Essa associação é descritiva e não demonstra, por si só, causalidade. A comparação entre trechos urbanos e rurais não é exibida porque depende da validação do campo de classificação territorial e da geração de uma visualização específica; portanto, não se afirma aqui que uma categoria predomina em ambiente urbano ou rural.</p></div></div>
<div class="rq-panel" id="panel-rq3" role="tabpanel" aria-labelledby="tab-rq3"><div class="rq-question">RQ3: Quais trechos concentram mais acidentes e como evoluíram entre 2019 e 2025?</div><div class="charts">{''.join(charts['rq3']) or '<p>Não há gráficos disponíveis para esta pergunta na base processada.</p>'}</div><div class="rq-explanation"><h3>Explicação da RQ3</h3><p>O gráfico de rodovias destaca as BRs com maior número absoluto de ocorrências, enquanto a série anual mostra a evolução dos registros ao longo do período disponível. Como o campo BR não individualiza necessariamente um trecho ou quilômetro específico, os resultados permitem apontar rodovias em destaque, mas não localizar segmentos exatos sem cruzar também os campos de quilômetro e município. As contagens não são taxas de risco e não consideram volume de tráfego.</p></div></div>
<p class="notice">As abas organizam as evidências por pergunta de pesquisa. Os gráficos apresentam contagens absolutas; não devem ser interpretados como taxas ou risco individual. As partes não cobertas pelas variáveis disponíveis estão explicitamente indicadas nas explicações.</p></section>
<script>function showRQ(id){{document.querySelectorAll('.rq-panel').forEach(p=>p.classList.toggle('active',p.id==='panel-'+id));document.querySelectorAll('.rq-tab').forEach(t=>{{const active=t.id==='tab-'+id;t.setAttribute('aria-selected',active?'true':'false');}});}}</script>
<section><h2>5. Discussão</h2><p>As visualizações descrevem a distribuição dos registros ao longo do tempo e entre categorias informadas pela PRF. Comparações anuais podem ser afetadas por mudanças de preenchimento, classificação e disponibilidade dos campos. As causas são categorias registradas no boletim e não comprovam, isoladamente, relações causais. Para avaliar risco por trecho seriam necessários dados de exposição, como volume de tráfego e extensão percorrida.</p><p>Para responder integralmente à comparação urbano/rural, é necessário confirmar a semântica e os domínios de <code>uso_solo</code> na documentação oficial.</section>
<section><h2>6. Limitações</h2><ul><li>Os registros representam acidentes atendidos pela PRF em rodovias federais.</li><li>O esquema e a disponibilidade das variáveis podem variar entre anos.</li><li>Ausências e inconsistências de preenchimento podem afetar comparações.</li><li>Totais absolutos não são taxas ajustadas por fluxo de veículos ou extensão viária.</li><li>O dicionário do projeto ainda exige conferência integral com a documentação oficial.</li></ul></section>
<section><h2>7. Reprodutibilidade</h2><p>Os arquivos brutos não são versionados devido ao tamanho. Para reproduzir o processamento e gerar novamente o artigo:</p><pre><code>python -m venv .venv
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python -m src.download --anos 2019 2020 2021 2022 2023 2024 2025
python -m src.etl --input data/raw --uf RJ
python -m pytest -q
python -m src.build_article</code></pre><p>O relatório <code>etl_report.json</code> registra contagens do processamento, versões de bibliotecas e hashes SHA-256 dos arquivos de entrada. Os testes automatizados usam dados sintéticos e não substituem a validação da base oficial.</section>
<section><h2>8. Conclusão</h2><p>O projeto estabelece um fluxo reprodutível para organizar e explorar registros de acidentes em rodovias federais no RJ. A análise descritiva permite observar padrões nos registros e orientar investigações futuras. Conclusões sobre fatores de risco, causalidade ou diferenças urbano/rural exigem validação dos campos e, quando aplicável, dados adicionais de exposição.</section>
<section><h2>Referências</h2><ol><li>POLÍCIA RODOVIÁRIA FEDERAL. <i>Dados Abertos da PRF</i>. Portal oficial.</li><li>POLÍCIA RODOVIÁRIA FEDERAL. <i>Dicionário de acidentes</i>. Portal oficial.</li><li>SILVA, Pedro Henriques; COSTA, Carlos Eduardo Julio da. <i>Acidentes em Rodovias Federais (PRF)</i>. Projeto acadêmico, Unilasalle RJ, 2026.</li></ol><p><b>Autores:</b> Pedro Henriques Silva; Carlos Eduardo Julio da Costa.<br><b>Curso:</b> Bacharelado em Sistemas de Informação — Unilasalle RJ.<br><b>Disciplina:</b> Linguagens de Programação.<br><b>Docente:</b> Alexandre Louzada.</p></section>
</main><footer>Artigo gerado automaticamente a partir da base processada · Dados abertos da PRF.</footer></body></html>"""
    (DOCS / "index.html").write_text(html_doc, encoding="utf-8")
    print(f"Artigo gerado: {DOCS / 'index.html'} | gráficos: {sum(len(v) for v in charts.values())}")

if __name__ == "__main__":
    main()
