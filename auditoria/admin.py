from django.contrib import admin

from .models import Auditoria


@admin.register(Auditoria)
class AuditoriaAdmin(admin.ModelAdmin):
    list_display = (
        "data_hora",
        "usuario",
        "operacao",
        "tabela",
        "registro_id",
        "campo",
        "valor_anterior",
        "valor_novo",
    )
    list_filter = ("operacao", "tabela", "data_hora")
    search_fields = ("registro_id", "campo", "justificativa", "usuario__username")
    date_hierarchy = "data_hora"

    # Auditoria é somente-leitura na interface.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
