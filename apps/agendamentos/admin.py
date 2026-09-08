from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Agendamento


@admin.register(Agendamento)
class AgendamentoAdmin(SimpleHistoryAdmin):
    list_display = ("numero", "data", "horario", "paciente", "destino", "status", "embarque")
    list_filter = ("status", "embarque", "data")
    search_fields = ("paciente__nome", "destino__nome")
    date_hierarchy = "data"
    autocomplete_fields = ("paciente", "destino")
    readonly_fields = ("criado_em", "atualizado_em", "criado_por", "atualizado_por", "confirmado_em")
