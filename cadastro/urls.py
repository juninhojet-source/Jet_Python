from django.urls import path

from . import views

app_name = "cadastro"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("inscricoes/", views.inscricao_list, name="inscricao_list"),
    path("inscricoes/nova/", views.inscricao_nova, name="inscricao_nova"),
    path("inscricoes/<int:pk>/cadastro/<str:etapa>/", views.wizard_cadastro, name="wizard"),
    path("inscricoes/<int:pk>/", views.inscricao_detalhe, name="inscricao_detalhe"),
    path("inscricoes/<int:pk>/excluir/", views.inscricao_excluir, name="inscricao_excluir"),
    path("inscricoes/<int:pk>/editar/", views.inscricao_editar, name="inscricao_editar"),
    path("inscricoes/<int:pk>/avaliar/", views.avaliar, name="avaliar"),
    path("inscricoes/<int:pk>/transicionar/", views.transicionar, name="transicionar"),
    path("inscricoes/<int:pk>/membros/novo/", views.membro_novo, name="membro_novo"),
    path("membros/<int:membro_pk>/editar/", views.membro_editar, name="membro_editar"),
    path("membros/<int:membro_pk>/excluir/", views.membro_excluir, name="membro_excluir"),
    path("membros/<int:membro_pk>/rendas/nova/", views.renda_nova, name="renda_nova"),
    path("inscricoes/<int:pk>/documentos/", views.documentos, name="documentos"),
    path("documentos/<int:pk>/download/", views.documento_download, name="documento_download"),
    path("inscricoes/<int:pk>/recalcular/", views.recalcular, name="recalcular"),
    path("inscricoes/<int:pk>/inapto/", views.marcar_inapto, name="marcar_inapto"),
    path("inscricoes/<int:pk>/finalizar/", views.finalizar, name="finalizar"),
    path("classificacao/", views.classificacao, name="classificacao"),
    # Backup e restauração manual (somente Administrador)
    path("admin-backup/", views.admin_backup, name="admin_backup"),
    path("admin-backup/baixar/", views.backup_baixar, name="backup_baixar"),
    path("admin-backup/restaurar/", views.backup_restaurar, name="backup_restaurar"),
    path("admin-backup/reiniciar-numeracao/", views.numeracao_resetar, name="numeracao_resetar"),
    path("admin-backup/liberar-cpf/", views.cpf_liberar, name="cpf_liberar"),
    # Relatórios e exportação (Fase 5)
    path("relatorios/", views.relatorios_index, name="relatorios"),
    path("relatorios/base.xlsx", views.rel_base, name="rel_base"),
    path("relatorios/classificacao.xlsx", views.rel_classificacao_xlsx, name="rel_classificacao_xlsx"),
    path("relatorios/classificacao.pdf", views.rel_classificacao_pdf, name="rel_classificacao_pdf"),
    path("relatorios/ordem-cadastro.pdf", views.rel_ordem_cadastro_pdf, name="rel_ordem_cadastro_pdf"),
    path("relatorios/pendentes.xlsx", views.rel_pendentes, name="rel_pendentes"),
    path("relatorios/indeferidos.xlsx", views.rel_indeferidos, name="rel_indeferidos"),
    path("relatorios/aptos.xlsx", views.rel_aptos, name="rel_aptos"),
    path("relatorios/empates.xlsx", views.rel_empates, name="rel_empates"),
    path("relatorios/auditoria.xlsx", views.rel_auditoria, name="rel_auditoria"),
    path("inscricoes/<int:pk>/ficha.pdf", views.rel_ficha_pdf, name="rel_ficha_pdf"),
    path("inscricoes/<int:pk>/recibo.pdf", views.rel_recibo_pdf, name="rel_recibo_pdf"),
    path("inscricoes/<int:pk>/recibo/email/", views.rel_recibo_email, name="rel_recibo_email"),
]
