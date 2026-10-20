"""Testes do motor de pontuação completo — Critérios Legais, Complementares,
total e desempate. Inclui o exemplo de aceitação de docs/04 (= 141 pontos).
"""

from datetime import date
from decimal import Decimal

import pytest

from motor.modelos import Aluguel, Membro, NucleoFamiliar, Renda
from motor.parametros import carregar_parametros
from motor.pontuacao import calcular_pontuacao, chave_ordenacao

P = carregar_parametros()
REF = date(2026, 9, 15)  # data de referência fixa para as idades (D-1)


def nascido_com(idade: int) -> date:
    return date(REF.year - idade, REF.month, REF.day)


def membro(idade=40, sexo="M", arrimo=False, renda="0", computavel=True, **kw):
    return Membro(
        data_nascimento=nascido_com(idade),
        sexo=sexo,
        arrimo=arrimo,
        rendas=[Renda("teste", Decimal(str(renda)), computavel)] if renda != "0" else [],
        **kw,
    )


def nucleo(membros, **kw):
    kw.setdefault("data_referencia", REF)
    return NucleoFamiliar(membros=membros, **kw)


# --------------------------------------------------------------------------- #
# Critérios Legais
# --------------------------------------------------------------------------- #
def test_cl_i_habitacao_precaria():
    r = calcular_pontuacao(nucleo([membro()], habitacao_precaria_ou_risco=True), P)
    assert r.detalhe_legais["CL_I"] == {"atendido": True, "pontos": 40}


def test_cl_i_ausente_zera():
    r = calcular_pontuacao(nucleo([membro()], habitacao_precaria_ou_risco=False), P)
    assert r.detalhe_legais["CL_I"]["pontos"] == 0


def test_cl_ii_exige_crianca_e_matricula():
    crianca = membro(idade=5)
    # criança + matrícula → 40
    r = calcular_pontuacao(nucleo([crianca], matricula_comprovada=True), P)
    assert r.detalhe_legais["CL_II"]["pontos"] == 40
    # criança sem matrícula → 0
    r = calcular_pontuacao(nucleo([crianca], matricula_comprovada=False), P)
    assert r.detalhe_legais["CL_II"]["pontos"] == 0
    # sem criança, mesmo com matrícula → 0
    r = calcular_pontuacao(nucleo([membro(idade=40)], matricula_comprovada=True), P)
    assert r.detalhe_legais["CL_II"]["pontos"] == 0


def test_cl_ii_borda_12_anos():
    # 12 anos ainda é criança (0 a 12, inclusive); 13 não.
    r12 = calcular_pontuacao(nucleo([membro(idade=12)], matricula_comprovada=True), P)
    r13 = calcular_pontuacao(nucleo([membro(idade=13)], matricula_comprovada=True), P)
    assert r12.detalhe_legais["CL_II"]["pontos"] == 40
    assert r13.detalhe_legais["CL_II"]["pontos"] == 0


def test_cl_iii_arrimo_mulher():
    r = calcular_pontuacao(nucleo([membro(sexo="F", arrimo=True)]), P)
    assert r.detalhe_legais["CL_III"]["pontos"] == 40


def test_cl_iii_arrimo_idoso_homem():
    r = calcular_pontuacao(nucleo([membro(idade=65, sexo="M", arrimo=True)]), P)
    assert r.detalhe_legais["CL_III"]["pontos"] == 40


def test_cl_iii_arrimo_homem_nao_idoso_zera():
    r = calcular_pontuacao(nucleo([membro(idade=40, sexo="M", arrimo=True)]), P)
    assert r.detalhe_legais["CL_III"]["pontos"] == 0


@pytest.mark.parametrize(
    "renda,esperado",
    [("4862.99", 40), ("4863.00", 40), ("4863.01", 0)],  # borda "inferior ou igual"
)
def test_cl_iv_borda_renda(renda, esperado):
    r = calcular_pontuacao(nucleo([membro(renda=renda)]), P)
    assert r.detalhe_legais["CL_IV"]["pontos"] == esperado


def test_cl_maximo_160():
    n = nucleo(
        [
            membro(idade=5),  # criança
            membro(idade=65, sexo="F", arrimo=True, renda="3000"),  # arrimo mulher idosa
        ],
        habitacao_precaria_ou_risco=True,
        matricula_comprovada=True,
    )
    r = calcular_pontuacao(n, P)
    assert r.pontos_legais == 160  # 40 x 4


def test_rendas_nao_computaveis_excluidas_do_cl_iv():
    # Renda formal 4000 (computável) + Bolsa Família 2000 (não computável).
    # Só 4000 conta → <= 4863 → CL_IV = 40.
    m = Membro(
        data_nascimento=nascido_com(40),
        rendas=[Renda("formal", 4000, True), Renda("bolsa_familia", 2000, False)],
    )
    r = calcular_pontuacao(nucleo([m]), P)
    assert r.detalhe_legais["CL_IV"]["pontos"] == 40
    assert r.renda_per_capita == Decimal("4000")


# --------------------------------------------------------------------------- #
# Complementares
# --------------------------------------------------------------------------- #
def test_per_capita_divide_por_integrantes_considerados():
    membros = [membro(renda="3000"), membro(), membro(idade=5), membro(idade=8)]
    r = calcular_pontuacao(nucleo(membros), P)
    assert r.renda_per_capita == Decimal("750")  # 3000 / 4
    assert r.pontos_per_capita == 15  # <= 810,50


def test_aluguel_cedido_zera():
    n = nucleo([membro(renda="3000")], aluguel=Aluguel([], cedido_ou_emprestado=True))
    r = calcular_pontuacao(n, P)
    assert r.pontos_aluguel == 0


def test_aluguel_media_tres_meses():
    n = nucleo(
        [membro(renda="3000")],
        aluguel=Aluguel([Decimal("1000"), Decimal("1100"), Decimal("1000")]),
    )
    r = calcular_pontuacao(n, P)
    # média 1033,33 / 3000 * 100 = 34,44% → faixa (30,35] → 6 pontos
    assert round(r.percentual_aluguel, 2) == Decimal("34.44")
    assert r.pontos_aluguel == 6


def test_cc_maximo_30():
    n = nucleo(
        [membro(renda="500")],  # per capita 500 → 15
        aluguel=Aluguel([Decimal("300")]),  # 300/500*100 = 60% → 15
    )
    r = calcular_pontuacao(n, P)
    assert r.pontos_complementares == 30


# --------------------------------------------------------------------------- #
# Aceitação (docs/04, seção F) — deve dar exatamente 141 pontos
# --------------------------------------------------------------------------- #
def test_exemplo_aceitacao_141_pontos():
    membros = [
        membro(idade=40, sexo="M", arrimo=True, renda="3000"),  # arrimo homem não idoso
        membro(idade=38, sexo="F"),
        membro(idade=5),
        membro(idade=8),
    ]
    n = nucleo(
        membros,
        habitacao_precaria_ou_risco=True,   # CL_I  = 40
        matricula_comprovada=True,          # CL_II = 40
        aluguel=Aluguel([Decimal("1000"), Decimal("1100"), Decimal("1000")]),
    )
    r = calcular_pontuacao(n, P)
    assert r.pontos_legais == 120           # 40 + 40 + 0 + 40
    assert r.pontos_complementares == 21    # 15 (per capita) + 6 (aluguel)
    assert r.pontuacao_total == 141
    assert r.dependentes_ate_12 == 2
    assert r.idosos == 0


# --------------------------------------------------------------------------- #
# Desempate (item 8.10)
# --------------------------------------------------------------------------- #
def test_ordenacao_e_desempate():
    # A e B empatam em pontos; A tem mais filhos <=12 → A na frente.
    base = dict(habitacao_precaria_ou_risco=True, matricula_comprovada=True)
    a = calcular_pontuacao(nucleo([membro(idade=5), membro(idade=8)], **base), P)
    b = calcular_pontuacao(nucleo([membro(idade=5)], **base), P)
    ordenados = sorted([b, a], key=chave_ordenacao, reverse=True)
    assert ordenados[0] is a


def test_empate_remanescente_iguais():
    # Núcleos idênticos → chave de ordenação igual → empate a resolver por sorteio.
    base = dict(habitacao_precaria_ou_risco=True, matricula_comprovada=True)
    a = calcular_pontuacao(nucleo([membro(idade=5)], **base), P)
    b = calcular_pontuacao(nucleo([membro(idade=6)], **base), P)
    assert chave_ordenacao(a) == chave_ordenacao(b)
