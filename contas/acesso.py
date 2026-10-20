"""Controle de acesso por perfil (item 6 do edital / item 17 dos requisitos).

Os perfis são Grupos do Django. ``Administrador`` e superusuário têm acesso
total. As funções abaixo são usadas por decoradores nas views e pelos templates
para mostrar apenas as ações permitidas a cada servidor.
"""

from __future__ import annotations

from functools import wraps

from django.core.exceptions import PermissionDenied

ADMIN = "Administrador"
ATENDENTE = "Atendente"
ANALISTA = "Analista"
COMISSAO = "Comissao"
CONSULTA = "Consulta"


def perfis_do(user) -> set[str]:
    if not user.is_authenticated:
        return set()
    return set(user.groups.values_list("name", flat=True))


def em_perfil(user, *nomes: str) -> bool:
    """True se o usuário tem algum dos perfis (Administrador/superuser sempre)."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    p = perfis_do(user)
    if ADMIN in p:
        return True
    return bool(p.intersection(nomes))


def perfil_requerido(*nomes: str):
    """Decorador de view: exige um dos perfis; caso contrário, 403."""

    def decorador(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not em_perfil(request.user, *nomes):
                raise PermissionDenied("Seu perfil não permite esta ação.")
            return view(request, *args, **kwargs)

        return wrapper

    return decorador
