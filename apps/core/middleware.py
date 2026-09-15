"""Middlewares de segurança do SIGTRANS."""
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse


class RestricaoPerfilMiddleware:
    """Mantém o perfil de recepção (só senhas) restrito à área de senhas."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and getattr(user, "so_senhas", False):
            path = request.path
            liberados = ("/senhas/", "/contas/", "/static/", "/media/")
            if not path.startswith(liberados):
                return redirect(reverse("senhas:operador"))
        return self.get_response(request)


class IdleTimeoutMiddleware:
    """Encerra a sessão após um período de inatividade (LGPD)."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout = int(getattr(settings, "IDLE_TIMEOUT_SECONDS", 1800))

    def __call__(self, request):
        if request.user.is_authenticated:
            agora = time.time()
            ultima = request.session.get("ultima_atividade")
            if ultima and (agora - ultima) > self.timeout:
                logout(request)
                messages.info(request, "Sessão encerrada por inatividade. Entre novamente.")
                return redirect(reverse("accounts:login"))
            request.session["ultima_atividade"] = agora
        return self.get_response(request)
