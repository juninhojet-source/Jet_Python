from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path(
        "municipios/rapido/",
        views.MunicipioQuickCreateView.as_view(),
        name="municipio_quick_create",
    ),
    path("config/", views.ConfiguracoesView.as_view(), name="configuracoes"),
    path("config/backup/", views.BackupView.as_view(), name="backup"),
    path("config/lgpd/", views.LGPDView.as_view(), name="lgpd"),
]
