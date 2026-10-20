"""Context processors de acesso, disponíveis em todos os templates."""

from __future__ import annotations

from .acesso import ADMIN, em_perfil


def perfis(request):
    """Expõe ``eh_admin`` aos templates (menu/telas restritas ao Administrador)."""
    user = getattr(request, "user", None)
    return {"eh_admin": em_perfil(user, ADMIN) if user is not None else False}
