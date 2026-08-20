from django.urls import path

from . import views

app_name = "agendamentos"

urlpatterns = [
    path("", views.AgendaDiaView.as_view(), name="agenda"),
    path("lista/", views.AgendamentoListView.as_view(), name="list"),
    path("novo/", views.AgendamentoCreateView.as_view(), name="create"),
    path("<int:pk>/", views.AgendamentoDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", views.AgendamentoUpdateView.as_view(), name="update"),
    path("<int:pk>/excluir/", views.AgendamentoDeleteView.as_view(), name="delete"),
    path("<int:pk>/confirmar/", views.ConfirmarAgendamentoView.as_view(), name="confirmar"),
    path("<int:pk>/embarque/", views.EmbarqueUpdateView.as_view(), name="embarque"),
    path("<int:pk>/cartao.pdf", views.CartaoEmbarquePDFView.as_view(), name="cartao_pdf"),
]
