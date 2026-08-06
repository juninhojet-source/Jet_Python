"""Painel de senhas — fila de atendimento (Fase 3).

Emite senhas MT-01 a MT-50 (reinício após 50 e reinício diário) e mantém
o estado do painel exibido na recepção (senha atual e guichê).
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


def _prefixo():
    return settings.SIGTRANS.get("SENHA_PREFIXO", "MT")


class StatusSenha(models.TextChoices):
    AGUARDANDO = "AGUARDANDO", "Aguardando"
    CHAMADA = "CHAMADA", "Chamada"
    FINALIZADA = "FINALIZADA", "Finalizada"


class Senha(models.Model):
    numero = models.PositiveSmallIntegerField("Número")
    data = models.DateField("Data", default=timezone.localdate)
    status = models.CharField(
        "Status", max_length=12, choices=StatusSenha.choices, default=StatusSenha.AGUARDANDO
    )
    guiche = models.PositiveSmallIntegerField("Guichê", null=True, blank=True)
    criada_em = models.DateTimeField("Emitida em", auto_now_add=True)
    chamada_em = models.DateTimeField("Chamada em", null=True, blank=True)
    finalizada_em = models.DateTimeField("Finalizada em", null=True, blank=True)

    class Meta:
        verbose_name = "Senha"
        verbose_name_plural = "Senhas"
        ordering = ["-criada_em"]
        indexes = [models.Index(fields=["data", "status"])]

    def __str__(self):
        return self.codigo

    @property
    def codigo(self):
        return f"{_prefixo()}-{self.numero:02d}"


class Painel(models.Model):
    """Estado singleton do painel exibido na recepção."""

    senha_atual = models.ForeignKey(
        Senha, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    # Incrementa a cada chamada/repetição — usado para disparar o alerta sonoro no painel.
    sequencia = models.PositiveIntegerField(default=0)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Painel"
        verbose_name_plural = "Painel"

    def __str__(self):
        return f"Painel (seq {self.sequencia})"

    @classmethod
    def carregar(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
