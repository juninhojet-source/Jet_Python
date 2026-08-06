from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Destino


@admin.register(Destino)
class DestinoAdmin(SimpleHistoryAdmin):
    list_display = ("nome", "tipo", "municipio", "telefone", "ativo")
    search_fields = ("nome", "municipio__nome")
    list_filter = ("tipo", "ativo", "municipio")
    autocomplete_fields = ("municipio",)
    readonly_fields = ("criado_em", "atualizado_em", "criado_por", "atualizado_por")
