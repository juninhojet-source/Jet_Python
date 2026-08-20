"""Autenticação e gestão de usuários."""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView, LogoutView
from django.core.cache import cache
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from apps.auditoria.services import Acao, get_ip, registrar

from .forms import LoginForm, UsuarioCreateForm, UsuarioUpdateForm
from .mixins import AdminRequiredMixin

User = get_user_model()


class SigtransLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    @property
    def _max_tentativas(self):
        return int(getattr(settings, "LOGIN_MAX_TENTATIVAS", 5))

    @property
    def _bloqueio_segundos(self):
        return int(getattr(settings, "LOGIN_BLOQUEIO_SEGUNDOS", 900))

    def _chave(self):
        ip = get_ip(self.request) or "?"
        return f"login_fail:{ip}"

    def post(self, request, *args, **kwargs):
        chave = self._chave()
        if cache.get(chave, 0) >= self._max_tentativas:
            registrar(Acao.BLOQUEIO, detalhe="Excesso de tentativas de login", request=request)
            messages.error(
                request,
                "Muitas tentativas de login. Tente novamente em alguns minutos.",
            )
            return self.render_to_response(self.get_context_data(form=self.get_form()))
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        cache.delete(self._chave())
        return super().form_valid(form)

    def form_invalid(self, form):
        chave = self._chave()
        try:
            cache.incr(chave)
        except ValueError:
            cache.set(chave, 1, timeout=self._bloqueio_segundos)
        return super().form_invalid(form)


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
