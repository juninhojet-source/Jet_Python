"""Registro de eventos de auditoria."""
from .models import Acao, RegistroAuditoria


def get_ip(request):
    if not request:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def registrar(acao, detalhe="", request=None, usuario=None, usuario_nome=""):
    """Cria um registro de auditoria imutável."""
    if usuario is None and request is not None:
        u = getattr(request, "user", None)
        if u is not None and u.is_authenticated:
            usuario = u
    nome = usuario_nome or (usuario.get_username() if usuario else "")
    RegistroAuditoria.objects.create(
        usuario=usuario if (usuario and usuario.pk) else None,
        usuario_nome=nome,
        acao=acao,
        detalhe=detalhe[:255],
        ip=get_ip(request),
    )


__all__ = ["registrar", "get_ip", "Acao"]
