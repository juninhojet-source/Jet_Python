"""Assistente de cadastro por etapas (wizard).

Define a sequência de etapas do cadastro, a navegação (voltar/avançar) e a
detecção de pendências (campos esperados que ficaram em branco), usada tanto na
etapa de revisão quanto no relatório da ficha individual.
"""

from __future__ import annotations

# (slug, rótulo) — ordem do assistente
ETAPAS: list[tuple[str, str]] = [
    ("requerente", "Requerente"),
    ("nucleo", "Núcleo Familiar"),
    ("renda", "Renda"),
    ("documentos", "Documentos"),
    ("avaliacao", "Avaliação"),
    ("revisao", "Revisão"),
]

SLUGS = [s for s, _ in ETAPAS]


def indice(slug: str) -> int:
    return SLUGS.index(slug)


def anterior(slug: str) -> str | None:
    i = indice(slug)
    return SLUGS[i - 1] if i > 0 else None


def proxima(slug: str) -> str | None:
    i = indice(slug)
    return SLUGS[i + 1] if i < len(SLUGS) - 1 else None


def passos(slug_atual: str) -> list[dict]:
    """Dados para renderizar a barra de progresso."""
    atual = indice(slug_atual)
    return [
        {
            "slug": slug,
            "rotulo": rotulo,
            "numero": i + 1,
            "atual": i == atual,
            "concluida": i < atual,
        }
        for i, (slug, rotulo) in enumerate(ETAPAS)
    ]


def pendencias(inscricao) -> list[str]:
    """Lista de campos esperados que ficaram em branco/incompletos.

    Não bloqueia o cadastro — apenas registra o que falta, para o relatório e
    para orientar a Comissão antes da homologação.
    """
    itens: list[str] = []
    req = inscricao.requerente

    faltando = []
    if not inscricao.telefone:
        faltando.append("telefone")
    if not inscricao.email:
        faltando.append("e-mail")
    if not inscricao.endereco:
        faltando.append("endereço")
    if not inscricao.bairro:
        faltando.append("bairro")
    if not inscricao.cep:
        faltando.append("CEP")
    if not req.estado_civil:
        faltando.append("estado civil")
    if faltando:
        itens.append("Requerente sem: " + ", ".join(faltando))

    membros = list(inscricao.membros.select_related("pessoa").prefetch_related("rendas"))
    if len(membros) <= 1:
        itens.append("Núcleo Familiar: nenhum integrante além do requerente")

    sem_renda = [m.pessoa.nome for m in membros if not m.rendas.all()]
    if sem_renda:
        itens.append("Sem renda registrada para: " + ", ".join(sem_renda))

    if not inscricao.documentos.exists():
        itens.append("Documentos: nenhum documento anexado")

    if inscricao.data_referencia is None:
        itens.append("Avaliação: data de referência não definida")

    return itens
