"""Fluxo de homologação — máquina de transições de situação da inscrição.

Fluxo (item 13 dos requisitos; encaminhamento conforme item 9 do edital):

    RASCUNHO --finalizar--> RECEBIDA --> EM_ANALISE --> DOC_VALIDADA --> APTO
             --> HOMOLOGADO --> CLASSIFICADO --> ENCAMINHADO_CAIXA

Ramos: EM_ANALISE -> PENDENCIA -> EM_ANALISE; e a inaptidão (item 6) via
``views.marcar_inapto`` (exige motivo). Cada transição respeita o perfil do
servidor e é registrada na auditoria.
"""

from __future__ import annotations

from django.core.exceptions import PermissionDenied

from contas.acesso import ANALISTA, COMISSAO, em_perfil

from .models import Inscricao

S = Inscricao.Status

# situação_atual -> lista de (destino, perfis_autorizados, rótulo)
TRANSICOES: dict[str, list[tuple[str, list[str], str]]] = {
    S.RECEBIDA: [(S.EM_ANALISE, [ANALISTA], "Iniciar análise")],
    S.EM_ANALISE: [
        (S.DOC_VALIDADA, [ANALISTA], "Validar documentação"),
        (S.PENDENCIA, [ANALISTA], "Registrar pendência"),
    ],
    S.PENDENCIA: [(S.EM_ANALISE, [ANALISTA], "Retomar análise (regularizado)")],
    S.DOC_VALIDADA: [(S.APTO, [ANALISTA, COMISSAO], "Marcar apto")],
    S.APTO: [(S.HOMOLOGADO, [COMISSAO], "Homologar")],
    S.HOMOLOGADO: [(S.CLASSIFICADO, [COMISSAO], "Marcar classificado")],
    S.CLASSIFICADO: [(S.ENCAMINHADO_CAIXA, [COMISSAO], "Encaminhar à CAIXA")],
    S.INAPTO: [(S.EM_ANALISE, [COMISSAO], "Reabrir análise")],
}


def transicoes_disponiveis(inscricao, user) -> list[tuple[str, str]]:
    """(destino, rótulo) permitidos ao usuário a partir da situação atual."""
    return [
        (destino, rotulo)
        for destino, perfis, rotulo in TRANSICOES.get(inscricao.status, [])
        if em_perfil(user, *perfis)
    ]


def pode_transicionar(inscricao, destino, user) -> bool:
    return any(
        d == destino and em_perfil(user, *perfis)
        for d, perfis, _ in TRANSICOES.get(inscricao.status, [])
    )


def aplicar(inscricao, destino, user, justificativa: str = "") -> None:
    """Aplica a transição, se permitida, registrando na auditoria."""
    if not pode_transicionar(inscricao, destino, user):
        raise PermissionDenied(
            f"Transição de {inscricao.status} para {destino} não permitida "
            "para o seu perfil ou situação atual."
        )
    inscricao.status = destino
    # A homologação ocorre após a finalização (inscrição bloqueada): é
    # procedimento administrativo autorizado e fica registrado.
    inscricao._alteracao_autorizada = True
    inscricao._justificativa_auditoria = justificativa or f"Transição para {destino}"
    inscricao.save()
