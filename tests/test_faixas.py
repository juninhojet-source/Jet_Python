"""Testes das faixas de pontuação nas bordas exatas (itens 8.7 e 8.8).

O maior risco do sistema é errar um operador de borda (<= vs <). Cada fronteira
de faixa é testada no valor exato e logo acima/abaixo.
"""

from decimal import Decimal

import pytest

from motor.parametros import carregar_parametros
from motor.pontuacao import pontos_por_faixa

P = carregar_parametros()


def D(v):
    return Decimal(str(v))


# ---- Renda per capita (item 8.7.1) ----
@pytest.mark.parametrize(
    "valor,esperado",
    [
        ("0.00", 15),
        ("810.49", 15),
        ("810.50", 15),   # borda: "igual ou inferior a 810,50"
        ("810.51", 10),
        ("1621.00", 10),  # borda: "igual ou inferior a 1.621,00"
        ("1621.01", 5),
        ("2431.50", 5),   # borda: "igual ou inferior a 2.431,50"
        ("2431.51", 0),
        ("9999.99", 0),
    ],
)
def test_faixa_per_capita(valor, esperado):
    assert pontos_por_faixa(D(valor), P.faixas_per_capita) == esperado


# ---- Comprometimento com aluguel (item 8.8.2) ----
@pytest.mark.parametrize(
    "pct,esperado",
    [
        ("0", 0),
        ("19.99", 0),
        ("20.00", 1),    # "igual ou superior a 20%"
        ("25.00", 1),    # "e igual ou inferior a 25%"
        ("25.01", 3),    # "superior a 25%"
        ("30.00", 3),
        ("30.01", 6),
        ("35.00", 6),
        ("35.01", 8),
        ("40.00", 8),
        ("40.01", 10),
        ("45.00", 10),
        ("45.01", 13),
        ("50.00", 13),
        ("50.01", 15),   # "superior a 50%"
        ("99.99", 15),
    ],
)
def test_faixa_aluguel(pct, esperado):
    assert pontos_por_faixa(D(pct), P.faixas_aluguel) == esperado


@pytest.mark.parametrize("faixas_attr", ["faixas_per_capita", "faixas_aluguel"])
@pytest.mark.parametrize("valor", ["0", "20.00", "25.00", "810.50", "1621.00", "5000"])
def test_faixas_sao_exclusivas_e_cobrem_tudo(faixas_attr, valor):
    # Cada valor deve cair em exatamente uma faixa (sem sobreposição nem lacuna).
    from motor.pontuacao import _faixa_contem

    faixas = getattr(P, faixas_attr)
    assert sum(1 for f in faixas if _faixa_contem(D(valor), f)) == 1
