"""Conecta os eventos de autenticação à trilha de auditoria."""
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver

from .services import Acao, registrar


@receiver(user_logged_in)
def _log_login(sender, request, user, **kwargs):
    registrar(Acao.LOGIN, request=request, usuario=user)


@receiver(user_logged_out)
def _log_logout(sender, request, user, **kwargs):
    registrar(Acao.LOGOUT, request=request, usuario=user)


@receiver(user_login_failed)
def _log_login_failed(sender, credentials, request=None, **kwargs):
    usuario_nome = credentials.get("username", "") if credentials else ""
    registrar(Acao.LOGIN_FALHOU, detalhe=f"usuário: {usuario_nome}",
              request=request, usuario_nome=usuario_nome)
