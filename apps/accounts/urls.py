from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("entrar/", views.SigtransLoginView.as_view(), name="login"),
    path("sair/", views.SigtransLogoutView.as_view(), name="logout"),
    path("alterar-senha/", views.AlterarSenhaView.as_view(), name="alterar_senha"),
    path("usuarios/", views.UsuarioListView.as_view(), name="usuario_list"),
    path("usuarios/novo/", views.UsuarioCreateView.as_view(), name="usuario_create"),
    path("usuarios/<int:pk>/editar/", views.UsuarioUpdateView.as_view(), name="usuario_update"),
]
