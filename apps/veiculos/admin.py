from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Veiculo


@admin.register(Veiculo)
class VeiculoAdmin(SimpleHistoryAdmin):
    list_display = ("nome", "tipo", "placa", "ativo")
    search_fields = ("nome", "placa")
    list_filter = ("tipo", "ativo")
    readonly_fields = ("criado_em", "atualizado_em", "criado_por", "atualizado_por")
