"""Rotas do projeto. Fase 2: apenas o Django Admin (as telas vêm na Fase 3)."""

from django.contrib import admin
from django.urls import path

admin.site.site_header = "MCMV — Cadastro Habitacional (Barão de Cocais/MG)"
admin.site.site_title = "MCMV Admin"
admin.site.index_title = "Administração do processo seletivo"

urlpatterns = [
    path("admin/", admin.site.urls),
]
