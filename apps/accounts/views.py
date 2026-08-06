"""Autenticação e gestão de usuários."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from .forms import LoginForm, UsuarioCreateForm, UsuarioUpdateForm
from .mixins import AdminRequiredMixin

User = get_user_model()


class SigtransLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class SigtransLogoutView(LogoutView):
    pass


class UsuarioListView(AdminRequiredMixin, ListView):
    model = User
    template_name = "accounts/usuario_list.html"
    context_object_name = "usuarios"
    paginate_by = 20


class UsuarioCreateView(AdminRequiredMixin, CreateView):
    model = User
    form_class = UsuarioCreateForm
    template_name = "accounts/usuario_form.html"
    success_url = reverse_lazy("accounts:usuario_list")

    def form_valid(self, form):
        messages.success(self.request, "Usuário criado com sucesso.")
        return super().form_valid(form)


class UsuarioUpdateView(AdminRequiredMixin, UpdateView):
    model = User
    form_class = UsuarioUpdateForm
    template_name = "accounts/usuario_form.html"
    success_url = reverse_lazy("accounts:usuario_list")

    def form_valid(self, form):
        messages.success(self.request, "Usuário atualizado com sucesso.")
        return super().form_valid(form)
