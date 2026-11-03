"""Avaliação dos requisitos eliminatórios (itens 3.1 e 6.1 do edital).

Lógica isolada e testável. Os requisitos automáticos (idade, nacionalidade,
faixa de renda) são calculados; os documentais (residência de 5 anos, não ser
proprietário, não ter sido beneficiado) dependem de confirmação da análise.

Regra da decisão D-5: o sistema apenas **sinaliza** "não apto"; o indeferimento
depende de confirmação humana.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from . import services


@dataclass
class ItemRequisito:
    codigo: str
    descricao: str
    ok: bool
    automatico: bool


def _idade(nascimento, ref) -> int:
    return ref.year - nascimento.year - (
        (ref.month, ref.day) < (nascimento.month, nascimento.day)
    )


def avaliar(inscricao) -> list[ItemRequisito]:
    p = services.parametros()
    ref = inscricao.data_referencia or inscricao.data_inscricao.date()
    req = inscricao.requerente
    idade = _idade(req.data_nascimento, ref)

    renda = services.montar_nucleo(inscricao).renda_bruta_computavel()
    r_cfg = p.bruto["requisitos"]["renda_familiar"]
    minima = Decimal(str(r_cfg["minima"]))
    maxima = Decimal(str(r_cfg["maxima"]))
    idade_min = int(p.bruto["requisitos"]["idade_minima_anos"])
    anos_res = int(p.bruto["requisitos"]["anos_residencia_municipio"])

    return [
        ItemRequisito("R1", f"Requerente ≥ {idade_min} anos", idade >= idade_min, True),
        ItemRequisito(
            "R2",
            f"Reside há ≥ {anos_res} anos no município",
            inscricao.residencia_5anos_comprovada,
            False,
        ),
        ItemRequisito("R3", "Brasileiro nato/naturalizado", req.brasileiro, True),
        ItemRequisito("R4", f"Renda bruta ≥ R$ {minima:.2f}", renda >= minima, True),
        ItemRequisito("R5", f"Renda bruta ≤ R$ {maxima:.2f}", renda <= maxima, True),
        ItemRequisito("R6", "Não é proprietário de imóvel", inscricao.nao_proprietario_declarado, False),
        ItemRequisito(
            "R7",
            "Nunca beneficiado por programa habitacional",
            inscricao.nao_beneficiado_declarado,
            False,
        ),
    ]


def apto(itens: list[ItemRequisito]) -> bool:
    return all(i.ok for i in itens)
