from django.urls import path

from . import views

app_name = "pacientes"

urlpatterns = [
    path("", views.PacienteListView.as_view(), name="list"),
    path("novo/", views.PacienteCreateView.as_view(), name="create"),
    path("rapido/", views.PacienteQuickCreateView.as_view(), name="quick_create"),
    path("<int:pk>/", views.PacienteDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", views.PacienteUpdateView.as_view(), name="update"),
    path("<int:pk>/excluir/", views.PacienteDeleteView.as_view(), name="delete"),
]
