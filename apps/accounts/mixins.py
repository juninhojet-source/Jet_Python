"""Mixins de controle de acesso por perfil."""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


class EditorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Exige perfil com permissão de escrita (não somente leitura)."""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.pode_editar

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("Seu perfil não permite esta operação.")
        return super().handle_no_permission()


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Exige perfil administrador."""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_admin

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("Acesso restrito a administradores.")
        return super().handle_no_permission()


class SenhaOperadorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Exige perfil autorizado a operar o painel de senhas."""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.pode_operar_senha

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("Seu perfil não permite operar as senhas.")
        return super().handle_no_permission()
