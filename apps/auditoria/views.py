"""Consulta da trilha de auditoria (restrita a administradores)."""
from django.views.generic import ListView

from apps.accounts.mixins import AdminRequiredMixin

from .models import Acao, RegistroAuditoria


class AuditoriaListView(AdminRequiredMixin, ListView):
    model = RegistroAuditoria
    template_name = "auditoria/lista.html"
    context_object_name = "registros"
    paginate_by = 40

    def get_queryset(self):
        qs = super().get_queryset().select_related("usuario")
        self.acao = self.request.GET.get("acao", "").strip()
        if self.acao:
            qs = qs.filter(acao=self.acao)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["acao_sel"] = self.acao
        ctx["acoes"] = Acao.choices
        return ctx
