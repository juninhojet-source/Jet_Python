from django.urls import path

from . import views

app_name = "veiculos"

urlpatterns = [
    path("", views.VeiculoListView.as_view(), name="list"),
    path("novo/", views.VeiculoCreateView.as_view(), name="create"),
    path("rapido/", views.VeiculoQuickCreateView.as_view(), name="quick_create"),
    path("<int:pk>/editar/", views.VeiculoUpdateView.as_view(), name="update"),
]
