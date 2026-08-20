from django.urls import path

from . import views

app_name = "relatorios"

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("agendamentos/", views.AgendamentosView.as_view(), name="agendamentos"),
    path("mapa-viagem/", views.MapaViagemView.as_view(), name="mapa_viagem"),
    path("bpa/", views.BPAView.as_view(), name="bpa"),
    path("indicadores/", views.IndicadoresView.as_view(), name="indicadores"),
]
