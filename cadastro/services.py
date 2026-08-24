"""Ponte entre os modelos do banco e o motor de pontuação (``motor/``).

- ``calcular_e_salvar(inscricao)``: recalcula a pontuação de uma inscrição a
  partir dos seus dados e persiste o *snapshot* (Inscrição, CriterioLegal,
  CriterioComplementar, Classificacao).
- ``classificar_todos()``: ordena as inscrições aptas e grava posição e os
  empates que restam para sorteio público (item 8.10).
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import transaction

from motor import (
    Aluguel,
    Membro,
    NucleoFamiliar,
    ResultadoPontuacao,
    calcular_pontuacao,
    carregar_parametros,
    chave_ordenacao,
)
from motor import Renda as RendaMotor

from .models import (
    Classificacao,
    CriterioComplementar,
    CriterioLegal,
    Inscricao,
)

_PARAMETROS = None


def parametros():
    global _PARAMETROS
    if _PARAMETROS is None:
        _PARAMETROS = carregar_parametros(settings.PARAMETROS_EDITAL)
    return _PARAMETROS


def montar_nucleo(inscricao: Inscricao) -> NucleoFamiliar:
    """Converte uma Inscrição (com relacionamentos) num NucleoFamiliar do motor."""
    ref = inscricao.data_referencia or inscricao.data_inscricao.date()

    membros = []
    for m in inscricao.membros.select_related("pessoa").prefetch_related("rendas"):
        rendas = [
            RendaMotor(tipo=r.tipo, valor=r.valor, computavel=r.computavel)
            for r in m.rendas.all()
        ]
        membros.append(
            Membro(
                data_nascimento=m.pessoa.data_nascimento,
                sexo=m.pessoa.sexo,
                parentesco=m.parentesco,
                dependente=m.dependente,
                arrimo=m.arrimo,
                pcd=m.pessoa.pcd,
                considerado_apuracao_renda=m.considerado_apuracao_renda,
                rendas=rendas,
            )
        )

    valores = [
        v
        for v in (inscricao.aluguel_mes_1, inscricao.aluguel_mes_2, inscricao.aluguel_mes_3)
        if v is not None
    ]
    aluguel = None
    if valores or inscricao.aluguel_cedido:
        aluguel = Aluguel(
            valores_mensais=[Decimal(str(v)) for v in valores],
            cedido_ou_emprestado=inscricao.aluguel_cedido,
        )

    return NucleoFamiliar(
        membros=membros,
        data_referencia=ref,
        habitacao_precaria_ou_risco=inscricao.habitacao_precaria_ou_risco,
        matricula_comprovada=inscricao.matricula_comprovada,
        aluguel=aluguel,
    )


@transaction.atomic
def calcular_e_salvar(inscricao: Inscricao) -> ResultadoPontuacao:
    """Recalcula e persiste o snapshot de pontuação da inscrição."""
    nucleo = montar_nucleo(inscricao)
    r = calcular_pontuacao(nucleo, parametros())

    inscricao.renda_bruta_computavel = nucleo.renda_bruta_computavel()
    inscricao.renda_per_capita = r.renda_per_capita
    inscricao.aluguel_medio = nucleo.aluguel.media() if nucleo.aluguel else None
    inscricao.percentual_aluguel = (
        None if r.percentual_aluguel is None else round(r.percentual_aluguel, 2)
    )
    inscricao.pontos_legais = r.pontos_legais
    inscricao.pontos_complementares = r.pontos_complementares
    inscricao.pontuacao_total = r.pontuacao_total
    inscricao._alteracao_autorizada = True  # snapshot é recomputação, não edição de cadastro
    inscricao.save()

    for inciso, dados in r.detalhe_legais.items():
        CriterioLegal.objects.update_or_create(
            inscricao=inscricao,
            inciso=inciso,
            defaults={
                "atendido": dados["atendido"],
                "comprovado": dados["atendido"],
                "pontos": dados["pontos"],
            },
        )

    CriterioComplementar.objects.update_or_create(
        inscricao=inscricao,
        defaults={
            "renda_per_capita": r.renda_per_capita,
            "pontos_renda": r.pontos_per_capita,
            "aluguel_medio": inscricao.aluguel_medio,
            "percentual": inscricao.percentual_aluguel,
            "pontos_aluguel": r.pontos_aluguel,
        },
    )

    Classificacao.objects.update_or_create(
        inscricao=inscricao,
        defaults={
            "pontuacao": r.pontuacao_total,
            "dependentes_ate_12": r.dependentes_ate_12,
            "idosos": r.idosos,
        },
    )
    return r


# Situações que participam da classificação final.
STATUS_CLASSIFICAVEIS = (
    Inscricao.Status.APTO,
    Inscricao.Status.HOMOLOGADO,
    Inscricao.Status.CLASSIFICADO,
    Inscricao.Status.ENCAMINHADO_CAIXA,
)


@transaction.atomic
def classificar_todos() -> list[Classificacao]:
    """Ordena as inscrições aptas e grava posição + marcação de empate p/ sorteio."""
    itens = list(
        Classificacao.objects.select_related("inscricao").filter(
            inscricao__status__in=STATUS_CLASSIFICAVEIS
        )
    )

    def chave(c: Classificacao):
        return (c.pontuacao, c.dependentes_ate_12, c.idosos)

    itens.sort(key=chave, reverse=True)

    for posicao, c in enumerate(itens, start=1):
        # Empate remanescente: mesma chave completa que o anterior ou o próximo.
        empate = False
        if posicao > 1 and chave(itens[posicao - 2]) == chave(c):
            empate = True
        if posicao < len(itens) and chave(itens[posicao]) == chave(c):
            empate = True
        c.posicao = posicao
        c.empate_pendente_sorteio = empate
        c._alteracao_autorizada = True
        c.save()

    return itens
