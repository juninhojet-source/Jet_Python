"""Envio do comprovante (recibo) de inscrição por e-mail ao requerente."""

from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMessage

from . import relatorios


def enviar_recibo(inscricao) -> str:
    """Envia o recibo (PDF) para o e-mail do requerente. Devolve o destinatário.

    Levanta ValueError se não houver e-mail ou se o envio não estiver configurado.
    """
    destino = (inscricao.email or "").strip()
    if not destino:
        raise ValueError("O requerente não tem e-mail cadastrado.")
    if not getattr(settings, "MCMV_EMAIL_ATIVO", False):
        raise ValueError(
            "Envio de e-mail não configurado. Defina DJANGO_EMAIL_HOST e afins no .env."
        )

    protocolo = inscricao.protocolo or inscricao.numero_inscricao
    pdf = relatorios.recibo_pdf(inscricao).content
    assunto = f"Comprovante de inscrição — MCMV {protocolo}"
    corpo = (
        f"Olá, {inscricao.requerente.nome}.\n\n"
        "Segue em anexo o comprovante da sua inscrição no Programa Minha Casa, "
        "Minha Vida (MCMV) — Edital de Chamamento nº 001/2026.\n"
        f"Protocolo: {inscricao.protocolo or '—'}\n\n"
        "A inscrição e a eventual classificação não geram direito à contratação, "
        "financiamento ou aquisição de unidade habitacional, conforme o edital. "
        "Acompanhe as publicações oficiais.\n\n"
        "Prefeitura Municipal de Barão de Cocais/MG\n"
        "Assistência Social - 31-3837-7608"
    )
    msg = EmailMessage(assunto, corpo, settings.DEFAULT_FROM_EMAIL, [destino])
    msg.attach(f"recibo_{protocolo}.pdf", pdf, "application/pdf")
    msg.send(fail_silently=False)
    return destino
