"""Testes do ETL com dados sintéticos (não dependem de download).

Rodar: python -m pytest -q   (ou: python tests/test_etl.py)
"""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from src import etl  # noqa: E402

HEADER = (
    "id;data_inversa;dia_semana;horario;uf;br;km;municipio;causa_acidente;tipo_acidente;"
    "classificacao_acidente;fase_dia;sentido_via;condicao_metereologica;tipo_pista;"
    "tracado_via;uso_solo;pessoas;mortos;feridos_leves;feridos_graves;ilesos;ignorados;"
    "feridos;veiculos;latitude;longitude;regional;delegacia;uop"
)

ROWS = [
    # válida, com acentos e vírgula decimal
    "1;2023-01-07;sábado;22:30:00;RJ;101;321,5;NITERÓI;Falta de atenção;Colisão traseira;"
    "Com Vítimas Feridas;Plena Noite;Crescente;Céu Claro;Dupla;Reta;Sim;3;0;1;1;1;0;2;2;"
    "-22,8859;-43,1153;SR-RJ;DEL1;UOP1",
    # duplicata exata da anterior
    "1;2023-01-07;sábado;22:30:00;RJ;101;321,5;NITERÓI;Falta de atenção;Colisão traseira;"
    "Com Vítimas Feridas;Plena Noite;Crescente;Céu Claro;Dupla;Reta;Sim;3;0;1;1;1;0;2;2;"
    "-22,8859;-43,1153;SR-RJ;DEL1;UOP1",
    # coordenada fora do Brasil + km absurdo + espaços extras + contagem inconsistente
    "2;2023-01-08;domingo;03:05:00;  rj ;116;99999;  RIO   DE JANEIRO ;Ingestão de álcool;"
    "Saída de leito carroçável;Com Vítimas Fatais;Plena Noite;Decrescente;Chuva;Simples;Curva;"
    "Não;2;1;0;0;0;0;0;1;40,5;-43,2;SR-RJ;DEL2;UOP2",
    # data inválida -> rejeitada
    "3;31/02/2023;segunda;10:00:00;RJ;040;10;PETRÓPOLIS;Outra;Outra;Sem Vítimas;Pleno dia;"
    "Crescente;Céu Claro;Simples;Reta;Sim;1;0;0;0;1;0;0;1;-22,5;-43,1;SR-RJ;DEL3;UOP3",
    # outra UF, horário ausente
    "4;2023-02-01;quarta;NA;SP;116;50,2;SÃO PAULO;Outra;Outra;Sem Vítimas;Pleno dia;"
    "Crescente;Céu Claro;Simples;Reta;Sim;1;0;0;0;1;0;0;1;-23,5;-46,6;SR-SP;DEL4;UOP4",
]


def _write_fixture(tmp: Path) -> Path:
    path = tmp / "datatran_teste.csv"
    path.write_bytes(("\n".join([HEADER] + ROWS) + "\n").encode("latin-1"))
    return path


def test_pipeline_end_to_end():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        src = _write_fixture(tmp)
        report = etl.run([str(src)], tmp / "out" / "acidentes.csv.gz", fmt="csv.gz")

        assert report["linhas_entrada"] == 5
        assert report["duplicatas_exatas_removidas"] == 1
        assert report["rejeitadas_data_invalida"] == 1
        assert report["coordenadas_fora_do_brasil_para_nan"] == 1
        assert report["km_fora_do_intervalo_para_nan"] == 1
        assert report["linhas_com_inconsistencia_contagem"] == 1
        assert report["linhas_saida"] == 3

        out = pd.read_csv(tmp / "out" / "acidentes.csv.gz")
        assert set(out["id"]) == {1, 2, 4}
        row1 = out.loc[out["id"] == 1].iloc[0]
        assert row1["municipio"] == "NITERÓI"          # acento preservado (latin-1 lido certo)
        assert abs(row1["km"] - 321.5) < 1e-9           # vírgula decimal convertida
        assert row1["periodo_dia"] == "noite"
        assert row1["total_vitimas"] == 2
        row2 = out.loc[out["id"] == 2].iloc[0]
        assert row2["uf"] == "RJ" and row2["municipio"] == "RIO DE JANEIRO"
        assert pd.isna(row2["latitude"]) and pd.isna(row2["km"])
        assert bool(row2["tem_morte"]) is True
        assert pd.isna(out.loc[out["id"] == 4].iloc[0]["hora"])

        assert (tmp / "out" / "acidentes_rejeitados.csv.gz").exists()
        assert (tmp / "out" / "etl_report.json").exists()


def test_filtro_uf_e_idempotencia():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        src = _write_fixture(tmp)
        etl.run([str(src)], tmp / "a" / "acidentes.csv.gz", fmt="csv.gz", uf="rj")
        etl.run([str(src)], tmp / "b" / "acidentes.csv.gz", fmt="csv.gz", uf="rj")
        a = pd.read_csv(tmp / "a" / "acidentes.csv.gz")
        b = pd.read_csv(tmp / "b" / "acidentes.csv.gz")
        assert set(a["uf"]) == {"RJ"} and len(a) == 2
        pd.testing.assert_frame_equal(a, b)  # determinístico


if __name__ == "__main__":
    test_pipeline_end_to_end()
    test_filtro_uf_e_idempotencia()
    print("OK")
