"""Motor de pontuação e ordenação de classificação.

Regras: ``docs/04-regras-de-negocio.md``. Valores: ``regras/parametros_edital.yaml``.
Todas as comparações de borda usam ``Decimal`` e **não** arredondam antes de comparar
(decisão D-3), para não empurrar um valor através de uma fronteira de faixa.
"""

from __future__ import annotations

from decimal import Decimal

from .modelos import NucleoFamiliar, ResultadoPontuacao
from .parametros import Parametros, carregar_parametros


def _faixa_contem(valor: Decimal, faixa: dict) -> bool:
    """Testa se ``valor`` cai na faixa, respeitando as bordas inclusivas/exclusivas."""
    mn = faixa.get("min")
    mx = faixa.get("max")
    if mn is not None:
        if faixa.get("min_inclusivo", False):
            if valor < mn:
                return False
        elif valor <= mn:
            return False
    if mx is not None:
        if faixa.get("max_inclusivo", False):
            if valor > mx:
                return False
        elif valor >= mx:
            return False
    return True


def pontos_por_faixa(valor: Decimal, faixas: list[dict]) -> int:
    """Devolve os pontos da primeira faixa que contém o valor (faixas exclusivas)."""
    for faixa in faixas:
        if _faixa_contem(valor, faixa):
            return int(faixa["pontos"])
    return 0


# --------------------------------------------------------------------------- #
# Critérios Legais (item 8.5)
# --------------------------------------------------------------------------- #
def _pontuar_legais(nucleo: NucleoFamiliar, p: Parametros) -> dict[str, dict]:
    pts = p.pontos_por_inciso
    max_c = p.crianca_max_anos
    idoso = p.idoso_min_anos

    existe_crianca = nucleo.contar_criancas_ate(max_c) > 0

    atende = {
        # I — situações diferentes no mesmo inciso não somam (8.5.2.1): é um booleano.
        "CL_I": bool(nucleo.habitacao_precaria_ou_risco),
        # II — exige criança 0–12 E matrícula comprovada.
        "CL_II": existe_crianca and bool(nucleo.matricula_comprovada),
        # III — arrimo mulher ou pessoa idosa.
        "CL_III": nucleo.arrimo_mulher_ou_idoso(idoso),
        # IV — renda bruta computável <= limite fixo.
        "CL_IV": nucleo.renda_bruta_computavel() <= p.limite_renda_cl_iv,
    }
    return {
        inciso: {"atendido": ok, "pontos": pts if ok else 0}
        for inciso, ok in atende.items()
    }


# --------------------------------------------------------------------------- #
# Critérios Complementares (itens 8.7 e 8.8)
# --------------------------------------------------------------------------- #
def _pontuar_per_capita(nucleo: NucleoFamiliar, p: Parametros) -> tuple[Decimal, int]:
    renda = nucleo.renda_bruta_computavel()
    divisor = Decimal(nucleo.integrantes_considerados())
    per_capita = renda / divisor
    return per_capita, pontos_por_faixa(per_capita, p.faixas_per_capita)


def _pontuar_aluguel(
    nucleo: NucleoFamiliar, p: Parametros
) -> tuple[Decimal | None, int]:
    aluguel = nucleo.aluguel
    if aluguel is None:
        return None, 0
    if aluguel.cedido_ou_emprestado:  # item 8.8.6
        return Decimal("0"), p.aluguel_cedido_pontos

    renda = nucleo.renda_bruta_computavel()
    if renda <= 0:
        return None, 0
    percentual = (aluguel.media() / renda) * Decimal("100")
    return percentual, pontos_por_faixa(percentual, p.faixas_aluguel)


# --------------------------------------------------------------------------- #
# API pública
# --------------------------------------------------------------------------- #
def calcular_pontuacao(
    nucleo: NucleoFamiliar, parametros: Parametros | None = None
) -> ResultadoPontuacao:
    """Calcula CL, CC, P e as chaves de desempate de um núcleo familiar."""
    p = parametros or carregar_parametros()

    detalhe_legais = _pontuar_legais(nucleo, p)
    cl = min(sum(d["pontos"] for d in detalhe_legais.values()), p.limite_legais)

    per_capita, pontos_pc = _pontuar_per_capita(nucleo, p)
    percentual_aluguel, pontos_al = _pontuar_aluguel(nucleo, p)
    cc = min(pontos_pc + pontos_al, p.limite_complementares)

    return ResultadoPontuacao(
        pontos_legais=cl,
        pontos_complementares=cc,
        pontuacao_total=cl + cc,
        detalhe_legais=detalhe_legais,
        renda_per_capita=per_capita,
        pontos_per_capita=pontos_pc,
        percentual_aluguel=percentual_aluguel,
        pontos_aluguel=pontos_al,
        dependentes_ate_12=nucleo.contar_criancas_ate(p.crianca_max_anos),
        idosos=nucleo.contar_idosos(p.idoso_min_anos),
    )


def chave_ordenacao(resultado: ResultadoPontuacao) -> tuple:
    """Chave de ordenação decrescente para classificação (item 8.10).

    Ordena por: pontuação total → filhos/dependentes ≤ 12 → idosos.
    O 3º critério (sorteio) não é automatizável: empates que sobreviverem a esta
    chave devem ser marcados para sorteio público. Use com ``reverse=True``.
    """
    return (
        resultado.pontuacao_total,
        resultado.dependentes_ate_12,
        resultado.idosos,
    )
