"""Checklist da documentação exigida (item 4 do Edital 001/2026).

``exigidos(inscricao)`` devolve a lista de exigências documentais aplicáveis à
inscrição (considerando estado civil, PcD, aluguel, moradia em risco e mulher
responsável) e se cada uma já foi atendida — um documento do(s) tipo(s) aceito(s)
registrado e não rejeitado.

Serve à detecção de pendências e ao checklist na etapa de documentos, atendendo
ao item 4.2 (apresentação integral da documentação).
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Documento

T = Documento.Tipo


@dataclass
class Exigencia:
    codigo: str          # item do edital (ex.: "4.1.1")
    rotulo: str          # descrição amigável
    tipos: tuple         # tipos que satisfazem (qualquer um)
    ok: bool             # já atendida?
    detalhe: str = ""    # observação (ex.: nomes sem RG/CPF)


def _presentes(inscricao) -> set[str]:
    """Tipos de documento registrados e não rejeitados."""
    return {
        d.tipo
        for d in inscricao.documentos.all()
        if d.status != Documento.Status.REJEITADO
    }


def _certidao_estado_civil(estado_civil: str) -> tuple[tuple, str]:
    """Tipos de certidão aceitos conforme o estado civil (item 4.1.2)."""
    mapa = {
        "CASADO": ((T.CERT_CASAMENTO,), "Certidão de Casamento"),
        "DIVORCIADO": ((T.CERT_CASAMENTO_DIVORCIO,), "Certidão de Casamento c/ averbação de divórcio"),
        "SEPARADO": ((T.CERT_CASAMENTO_DIVORCIO,), "Certidão de Casamento c/ averbação de divórcio"),
        "VIUVO": ((T.CERT_CASAMENTO_OBITO, T.CERT_OBITO), "Certidão de Casamento c/ óbito ou Certidão de Óbito"),
        "SOLTEIRO": ((T.CERT_NASCIMENTO,), "Certidão de Nascimento"),
        "UNIAO_ESTAVEL": ((T.UNIAO_ESTAVEL,), "Escritura/Declaração de União Estável"),
    }
    return mapa.get(estado_civil, ((), ""))


def exigidos(inscricao) -> list[Exigencia]:
    presentes = _presentes(inscricao)
    membros = [m.pessoa for m in inscricao.membros.select_related("pessoa").all()]
    if inscricao.requerente not in membros:
        membros = [inscricao.requerente, *membros]
    algum_pcd = any(getattr(p, "pcd", False) for p in membros)

    def item(codigo, rotulo, tipos, detalhe=""):
        ok = any(t in presentes for t in tipos)
        return Exigencia(codigo, rotulo, tuple(tipos), ok, detalhe)

    itens: list[Exigencia] = []

    # 4.1.1 — RG e CPF (de todos os membros do núcleo).
    itens.append(item("4.1.1", "RG (todos os membros)", (T.RG,)))
    itens.append(item("4.1.1", "CPF (todos os membros)", (T.CPF,)))

    # 4.1.2 — Comprovante de estado civil (conforme o do requerente).
    tipos_ec, rot_ec = _certidao_estado_civil(inscricao.requerente.estado_civil)
    if tipos_ec:
        itens.append(item("4.1.2", f"Estado civil: {rot_ec}", tipos_ec))
    else:
        itens.append(Exigencia("4.1.2", "Comprovante de estado civil", (), False,
                               "defina o estado civil do requerente"))

    # 4.1.3 — Comprovante de endereço (+ declaração/contrato se não for próprio).
    itens.append(item("4.1.3", "Comprovante de endereço (água/energia)", (T.COMP_ENDERECO,)))
    aluguel = any([inscricao.aluguel_mes_1, inscricao.aluguel_mes_2,
                   inscricao.aluguel_mes_3, inscricao.aluguel_cedido])
    if aluguel:
        itens.append(item("4.1.3", "Declaração de moradia ou contrato de locação (imóvel não próprio)",
                          (T.DECL_MORADIA, T.CONTRATO_LOCACAO)))

    # 4.1.4 — Comprovante de renda (qualquer uma das formas).
    itens.append(item("4.1.4", "Comprovante de renda (contracheque, extrato/IR ou INSS)",
                      (T.RENDA_CONTRACHEQUE, T.RENDA_EXTRATO, T.RENDA_INSS)))

    # 4.1.5 — Residência no município há 5 anos (qualquer um dos meios).
    itens.append(item("4.1.5", "Comprovante de residência no município há 5 anos",
                      (T.RES5_SAUDE, T.RES5_CONCESSIONARIA, T.RES5_ESCOLAR, T.RES5_CTPS, T.RES5_OUTRO)))

    # 4.1.6 / 4.1.7 — Declarações (Anexos II e III).
    itens.append(item("4.1.6", "Declaração de Inscrição e Anuência (Anexo II)", (T.ANEXO_II,)))
    itens.append(item("4.1.7", "Declaração Negativa de Propriedade (Anexo III)", (T.ANEXO_III,)))

    # 4.1.8 — Laudo de deficiência (se houver PcD no núcleo).
    if algum_pcd:
        itens.append(item("4.1.8", "Laudo médico de deficiência (PcD no núcleo)", (T.LAUDO_PCD,)))

    # 4.1.9 — Comprovação de moradia precária/risco (se marcado).
    if inscricao.habitacao_precaria_ou_risco:
        itens.append(item("4.1.9", "Comprovação de moradia precária/risco (Defesa Civil/laudo)",
                          (T.MORADIA_RISCO,)))

    # 4.1.10 — CadÚnico (se mulher responsável pelo núcleo).
    mulher_responsavel = inscricao.membros.filter(
        arrimo=True, pessoa__sexo="F"
    ).exists() or inscricao.requerente.sexo == "F"
    if mulher_responsavel:
        itens.append(item("4.1.10", "Declaração do CadÚnico (mulher responsável)", (T.CADUNICO,)))

    return itens


def faltantes(inscricao) -> list[Exigencia]:
    return [e for e in exigidos(inscricao) if not e.ok]
