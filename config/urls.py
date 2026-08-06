"""Roteamento principal do SIGTRANS Saúde."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.urls")),
    path("contas/", include("apps.accounts.urls")),
    path("agenda/", include("apps.agendamentos.urls")),
    path("senhas/", include("apps.senhas.urls")),
    path("relatorios/", include("apps.relatorios.urls")),
    path("pacientes/", include("apps.pacientes.urls")),
    path("destinos/", include("apps.destinos.urls")),
    path("admin/", admin.site.urls),
]

admin.site.site_header = "SIGTRANS Saúde — Administração"
admin.site.site_title = "SIGTRANS Saúde"
admin.site.index_title = "Painel administrativo"
