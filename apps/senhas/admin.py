from django.contrib import admin

from .models import Painel, Senha


@admin.register(Senha)
class SenhaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "data", "status", "guiche", "criada_em", "chamada_em")
    list_filter = ("status", "data")
    date_hierarchy = "data"


@admin.register(Painel)
class PainelAdmin(admin.ModelAdmin):
    list_display = ("__str__", "senha_atual", "sequencia", "atualizado_em")
