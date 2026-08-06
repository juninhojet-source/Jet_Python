"""Trilha de auditoria de acessos e ações (LGPD).

Complementa o histórico de alterações de dados (django-simple-history),
registrando eventos de acesso e operações: login, logout, tentativas
falhas, exportações e impressões. Os registros não podem ser alterados
nem excluídos por usuários comuns.
"""
from django.conf import settings
from django.db import models


class Acao(models.TextChoices):
    LOGIN = "LOGIN", "Login"
    LOGOUT = "LOGOUT", "Logout"
    LOGIN_FALHOU = "LOGIN_FALHOU", "Tentativa de login falhou"
    BLOQUEIO = "BLOQUEIO", "Acesso bloqueado (tentativas)"
    EXPORTACAO = "EXPORTACAO", "Exportação de relatório"
    IMPRESSAO = "IMPRESSAO", "Impressão de documento"
    BACKUP = "BACKUP", "Backup do banco de dados"


class RegistroAuditoria(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="auditorias",
    )
    usuario_nome = models.CharField("Usuário", max_length=150, blank=True)
    acao = models.CharField("Ação", max_length=20, choices=Acao.choices)
    detalhe = models.CharField("Detalhe", max_length=255, blank=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)
    criado_em = models.DateTimeField("Data/hora", auto_now_add=True)

    class Meta:
        verbose_name = "Registro de auditoria"
        verbose_name_plural = "Registros de auditoria"
        ordering = ["-criado_em"]
        indexes = [models.Index(fields=["acao", "criado_em"])]

    def __str__(self):
        return f"{self.criado_em:%d/%m/%Y %H:%M} · {self.get_acao_display()} · {self.usuario_nome or '—'}"
