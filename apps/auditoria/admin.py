from django.contrib import admin

from .models import RegistroAuditoria


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("criado_em", "acao", "usuario_nome", "ip", "detalhe")
    list_filter = ("acao", "criado_em")
    search_fields = ("usuario_nome", "detalhe", "ip")
    date_hierarchy = "criado_em"

    # Trilha imutável: não pode ser adicionada, alterada ou excluída pela interface.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
