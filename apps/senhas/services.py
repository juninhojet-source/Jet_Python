"""Regras de negócio do painel de senhas (por fila/sala)."""
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import (
    Painel,
    Senha,
    StatusSenha,
    fila_config,
    tipos_ordenados,
)


def _max():
    return settings.SIGTRANS.get("SENHA_MAX", 50)


def _sala(tipo):
    return fila_config(tipo).get("sala")


def _painel_bloqueado(tipo):
    """Retorna o painel da fila com a linha bloqueada (evita perda de
    atualização quando vários operadores agem ao mesmo tempo)."""
    painel = Painel.carregar(tipo)  # garante a existência da linha
    return Painel.objects.select_for_update().get(pk=painel.pk)


def proximo_numero(tipo, data):
    """Próximo número da fila no dia: 1..MAX, reiniciando após o MAX."""
    ultima = (
        Senha.objects.filter(tipo=tipo, data=data).order_by("-criada_em", "-id").first()
    )
    if not ultima:
        return 1
    return 1 if ultima.numero >= _max() else ultima.numero + 1


@transaction.atomic
def emitir_senha(tipo):
    hoje = timezone.localdate()
    return Senha.objects.create(tipo=tipo, numero=proximo_numero(tipo, hoje), data=hoje)


def _chamadas_do_dia(tipo, data):
    return list(
        Senha.objects.filter(tipo=tipo, data=data, chamada_em__isnull=False)
        .order_by("chamada_em", "id")
    )


@transaction.atomic
def chamar_proximo(tipo):
    """Chama a próxima senha aguardando; se não houver, emite e chama a próxima."""
    hoje = timezone.localdate()
    senha = (
        Senha.objects.select_for_update()
        .filter(tipo=tipo, data=hoje, status=StatusSenha.AGUARDANDO)
        .order_by("criada_em", "id")
        .first()
    )
    if not senha:
        # Nenhuma senha na fila: gera o próximo número e chama direto.
        senha = Senha.objects.create(tipo=tipo, numero=proximo_numero(tipo, hoje), data=hoje)
    senha.status = StatusSenha.CHAMADA
    senha.guiche = _sala(tipo)
    senha.chamada_em = timezone.now()
    senha.save()
    painel = _painel_bloqueado(tipo)
    painel.senha_atual = senha
    painel.sequencia += 1
    painel.save()
    return senha


@transaction.atomic
def repetir(tipo):
    painel = _painel_bloqueado(tipo)
    if painel.senha_atual:
        painel.sequencia += 1
        painel.save()
    return painel.senha_atual


@transaction.atomic
def navegar(tipo, delta):
    """Move o painel da fila para a chamada anterior (-1) ou seguinte (+1)."""
    painel = _painel_bloqueado(tipo)
    chamadas = _chamadas_do_dia(tipo, timezone.localdate())
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
def reiniciar(tipo):
    """Zera a fila do dia: remove as senhas de hoje e reinicia a numeração em 01."""
    hoje = timezone.localdate()
    Senha.objects.filter(tipo=tipo, data=hoje).delete()
    painel = _painel_bloqueado(tipo)
    painel.senha_atual = None
    painel.sequencia += 1  # sinaliza a mudança para o painel de TV limpar
    painel.save()


@transaction.atomic
def finalizar_atual(tipo):
    painel = _painel_bloqueado(tipo)
    senha = painel.senha_atual
    if senha and senha.status != StatusSenha.FINALIZADA:
        senha.status = StatusSenha.FINALIZADA
        senha.finalizada_em = timezone.now()
        senha.save()
    return senha


def estado(tipo):
    """Snapshot de uma fila."""
    painel = Painel.carregar(tipo)
    hoje = timezone.localdate()
    atual = (
        painel.senha_atual
        if painel.senha_atual and painel.senha_atual.data == hoje
        else None
    )
    ultimas = (
        Senha.objects.filter(tipo=tipo, data=hoje, chamada_em__isnull=False)
        .order_by("-chamada_em")[:6]
    )
    aguardando = Senha.objects.filter(
        tipo=tipo, data=hoje, status=StatusSenha.AGUARDANDO
    ).count()
    cfg = fila_config(tipo)
    return {
        "tipo": tipo,
        "nome": cfg.get("nome", tipo),
        "sala": cfg.get("sala"),
        "painel": painel,
        "atual": atual,
        "ultimas": ultimas,
        "aguardando": aguardando,
    }


def estado_todas():
    """Snapshot de todas as filas, ordenadas por sala."""
    return [estado(tipo) for tipo in tipos_ordenados()]
