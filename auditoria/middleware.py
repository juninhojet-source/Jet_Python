"""Captura o usuário e o IP da requisição atual em um armazenamento por thread,
para que os modelos possam registrar *quem* fez cada alteração na auditoria.
"""

from __future__ import annotations

import threading

_local = threading.local()


def usuario_atual():
    return getattr(_local, "usuario", None)


def ip_atual():
    return getattr(_local, "ip", None)


def definir_contexto(usuario=None, ip=None):
    """Permite definir o contexto fora de uma requisição (ex.: comandos, testes)."""
    _local.usuario = usuario
    _local.ip = ip


class UsuarioAtualMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, "user", None)
        if usuario is not None and not usuario.is_authenticated:
            usuario = None
        _local.usuario = usuario
        _local.ip = self._ip(request)
        try:
            return self.get_response(request)
        finally:
            _local.usuario = None
            _local.ip = None

    @staticmethod
    def _ip(request):
        encaminhado = request.META.get("HTTP_X_FORWARDED_FOR")
        if encaminhado:
            return encaminhado.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
