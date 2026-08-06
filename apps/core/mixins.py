"""Mixins reutilizáveis de views."""


class SalvarAutorMixin:
    """Preenche automaticamente criado_por / atualizado_por no salvar."""

    def form_valid(self, form):
        if not form.instance.pk:
            form.instance.criado_por = self.request.user
        form.instance.atualizado_por = self.request.user
        return super().form_valid(form)
