from django.urls import path

from . import views

app_name = "cadastro"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("inscricoes/", views.inscricao_list, name="inscricao_list"),
    path("inscricoes/nova/", views.inscricao_nova, name="inscricao_nova"),
    path("inscricoes/<int:pk>/", views.inscricao_detalhe, name="inscricao_detalhe"),
    path("inscricoes/<int:pk>/editar/", views.inscricao_editar, name="inscricao_editar"),
    path("inscricoes/<int:pk>/membros/novo/", views.membro_novo, name="membro_novo"),
    path("membros/<int:membro_pk>/rendas/nova/", views.renda_nova, name="renda_nova"),
    path("inscricoes/<int:pk>/documentos/", views.documentos, name="documentos"),
    path("documentos/<int:pk>/download/", views.documento_download, name="documento_download"),
    path("inscricoes/<int:pk>/recalcular/", views.recalcular, name="recalcular"),
    path("inscricoes/<int:pk>/inapto/", views.marcar_inapto, name="marcar_inapto"),
    path("inscricoes/<int:pk>/finalizar/", views.finalizar, name="finalizar"),
    path("classificacao/", views.classificacao, name="classificacao"),
]
