from django.urls import path

from . import views

app_name = "senhas"

urlpatterns = [
    path("", views.OperadorView.as_view(), name="operador"),
    path("painel/", views.PainelTVView.as_view(), name="painel_tv"),
    path("painel/estado/", views.EstadoJSONView.as_view(), name="estado"),
    path("emitir/", views.KioskView.as_view(), name="kiosk"),
]
