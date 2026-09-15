from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Paciente


@admin.register(Paciente)
class PacienteAdmin(SimpleHistoryAdmin):
    list_display = ("nome", "cpf", "cns", "idade", "telefone_principal", "municipio", "ativo")
    search_fields = ("nome", "cpf", "cns", "telefone_principal")
    list_filter = ("ativo", "sexo", "raca_cor", "municipio")
    autocomplete_fields = ("municipio",)
    readonly_fields = ("criado_em", "atualizado_em", "criado_por", "atualizado_por")
