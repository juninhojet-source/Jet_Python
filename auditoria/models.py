"""Trilha de auditoria — tabela *append-only* (item 6 do edital / LGPD).

Registra criação, alteração (campo a campo) e exclusão dos cadastros, com o
responsável, data/hora, IP e justificativa. Não há update/delete de registros
de auditoria: uma vez gravado, permanece.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models


class Auditoria(models.Model):
    class Operacao(models.TextChoices):
        CRIACAO = "CREATE", "Criação"
        ALTERACAO = "UPDATE", "Alteração"
        EXCLUSAO = "DELETE", "Exclusão"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="auditorias",
        verbose_name="responsável",
    )
    data_hora = models.DateTimeField(auto_now_add=True, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    operacao = models.CharField(max_length=10, choices=Operacao.choices)
    tabela = models.CharField(max_length=100, db_index=True)
    registro_id = models.CharField(max_length=64, db_index=True)
    campo = models.CharField(max_length=100, blank=True)
    valor_anterior = models.TextField(blank=True)
    valor_novo = models.TextField(blank=True)
    justificativa = models.TextField(blank=True)

    class Meta:
        verbose_name = "registro de auditoria"
        verbose_name_plural = "auditoria"
        ordering = ("-data_hora", "-id")

    def __str__(self):
        return f"[{self.data_hora:%d/%m/%Y %H:%M}] {self.operacao} {self.tabela}#{self.registro_id} {self.campo}"

    # A auditoria é imutável: bloqueia alteração e exclusão de registros já gravados.
    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise RuntimeError("Registros de auditoria são imutáveis (append-only).")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Registros de auditoria não podem ser excluídos.")
