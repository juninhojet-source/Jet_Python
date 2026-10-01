"""Disponibiliza a identidade institucional (branding) em todos os templates."""
from django.conf import settings


def branding(request):
    return {"ORGAO": settings.ORGAO}
