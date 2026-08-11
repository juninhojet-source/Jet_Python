from django.urls import path

from . import views

app_name = "destinos"

urlpatterns = [
    path("", views.DestinoListView.as_view(), name="list"),
    path("novo/", views.DestinoCreateView.as_view(), name="create"),
    path("rapido/", views.DestinoQuickCreateView.as_view(), name="quick_create"),
    path("<int:pk>/editar/", views.DestinoUpdateView.as_view(), name="update"),
]
