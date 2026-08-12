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
]
