"""Regras de negócio do painel de senhas."""
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Painel, Senha, StatusSenha


def _max():
    return settings.SIGTRANS.get("SENHA_MAX", 50)


def proximo_numero(data):
    """Próximo número do dia: sequencial de 1 a MAX, reiniciando após o MAX."""
    ultima = Senha.objects.filter(data=data).order_by("-criada_em", "-id").first()
    if not ultima:
        return 1
    return 1 if ultima.numero >= _max() else ultima.numero + 1


@transaction.atomic
def emitir_senha():
    hoje = timezone.localdate()
    return Senha.objects.create(numero=proximo_numero(hoje), data=hoje)


def _chamadas_do_dia(data):
    return list(
        Senha.objects.filter(data=data, chamada_em__isnull=False).order_by("chamada_em", "id")
    )


@transaction.atomic
def chamar_proximo(guiche):
    hoje = timezone.localdate()
    senha = (
        Senha.objects.select_for_update()
        .filter(data=hoje, status=StatusSenha.AGUARDANDO)
        .order_by("criada_em", "id")
        .first()
    )
    if not senha:
        return None
    senha.status = StatusSenha.CHAMADA
    senha.guiche = guiche
    senha.chamada_em = timezone.now()
    senha.save()
    painel = Painel.carregar()
    painel.senha_atual = senha
    painel.sequencia += 1
    painel.save()
    return senha


@transaction.atomic
def repetir():
    painel = Painel.carregar()
    if painel.senha_atual:
        painel.sequencia += 1
        painel.save()
    return painel.senha_atual


@transaction.atomic
def navegar(delta):
    """Move o painel para a chamada anterior (-1) ou seguinte (+1)."""
    painel = Painel.carregar()
    chamadas = _chamadas_do_dia(timezone.localdate())
    if not chamadas:
        return None
    if painel.senha_atual in chamadas:
        idx = chamadas.index(painel.senha_atual)
    else:
        idx = len(chamadas) - 1
    idx = max(0, min(len(chamadas) - 1, idx + delta))
    painel.senha_atual = chamadas[idx]
    painel.sequencia += 1
    painel.save()
    return painel.senha_atual


@transaction.atomic
def finalizar_atual():
    painel = Painel.carregar()
    senha = painel.senha_atual
    if senha and senha.status != StatusSenha.FINALIZADA:
        senha.status = StatusSenha.FINALIZADA
        senha.finalizada_em = timezone.now()
        senha.save()
    return senha


def estado():
    """Snapshot do painel para exibição/pooling."""
    painel = Painel.carregar()
    hoje = timezone.localdate()
    atual = painel.senha_atual if painel.senha_atual and painel.senha_atual.data == hoje else None
    ultimas = (
        Senha.objects.filter(data=hoje, chamada_em__isnull=False)
        .order_by("-chamada_em")[:6]
    )
    aguardando = Senha.objects.filter(data=hoje, status=StatusSenha.AGUARDANDO).count()
    return {"painel": painel, "atual": atual, "ultimas": ultimas, "aguardando": aguardando}
