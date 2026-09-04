"""Rotas do projeto."""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import TemplateView

admin.site.site_header = "MCMV — Cadastro Habitacional (Barão de Cocais/MG)"
admin.site.site_title = "MCMV Admin"
admin.site.index_title = "Administração do processo seletivo"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("entrar/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("sair/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    # Política de Privacidade / LGPD — página pública (sem exigir login).
    path("privacidade/", TemplateView.as_view(template_name="privacidade.html"), name="privacidade"),
    path("", include("cadastro.urls")),
]
