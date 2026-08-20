"""Mixins reutilizáveis de views."""
from django.contrib import messages
from django.db.models import ProtectedError
from django.shortcuts import redirect


class SalvarAutorMixin:
    """Preenche automaticamente criado_por / atualizado_por no salvar."""

    def form_valid(self, form):
        if not form.instance.pk:
            form.instance.criado_por = self.request.user
        form.instance.atualizado_por = self.request.user
        return super().form_valid(form)


class ExclusaoProtegidaMixin:
    """Trata a exclusão de registros referenciados por outros (PROTECT).

    Em vez de erro, mostra mensagem orientando a inativar. Use em DeleteView.
    """

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            obj = self.get_object()
            messages.error(
                request,
                f"Não é possível excluir “{obj}”: há registros vinculados "
                f"(por exemplo, agendamentos). Considere inativar em vez de excluir.",
            )
            return redirect(self.get_success_url())
