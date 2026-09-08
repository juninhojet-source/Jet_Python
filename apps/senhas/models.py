"""Painel de senhas — filas de atendimento por sala (Fase 3+).

Cada fila (ex.: Transporte → Sala 02; Consultas e Exames → Sala 01) tem
prefixo, sala e numeração próprios, com reinício após o máximo e reinício
diário. As filas são configuradas em settings.SIGTRANS["SENHA_FILAS"].
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


def filas_config():
    return settings.SIGTRANS.get("SENHA_FILAS", {})


def fila_config(tipo):
    return filas_config().get(tipo, {})


def tipos_ordenados():
    """Tipos de fila ordenados pelo número da sala (01, 02, ...)."""
    cfg = filas_config()
    return sorted(cfg.keys(), key=lambda t: cfg[t].get("sala", 99))


class StatusSenha(models.TextChoices):
    AGUARDANDO = "AGUARDANDO", "Aguardando"
    CHAMADA = "CHAMADA", "Chamada"
    FINALIZADA = "FINALIZADA", "Finalizada"


class Senha(models.Model):
    tipo = models.CharField("Fila", max_length=20, default="TRANSPORTE")
    numero = models.PositiveSmallIntegerField("Número")
    data = models.DateField("Data", default=timezone.localdate)
    status = models.CharField(
        "Status", max_length=12, choices=StatusSenha.choices, default=StatusSenha.AGUARDANDO
    )
    guiche = models.PositiveSmallIntegerField("Sala", null=True, blank=True)
    criada_em = models.DateTimeField("Emitida em", auto_now_add=True)
    chamada_em = models.DateTimeField("Chamada em", null=True, blank=True)
    finalizada_em = models.DateTimeField("Finalizada em", null=True, blank=True)

    class Meta:
        verbose_name = "Senha"
        verbose_name_plural = "Senhas"
        ordering = ["-criada_em"]
        indexes = [models.Index(fields=["tipo", "data", "status"])]

    def __str__(self):
        return self.codigo

    @property
    def prefixo(self):
        return fila_config(self.tipo).get("prefixo", "MT")

    @property
    def codigo(self):
        return f"{self.prefixo}-{self.numero:02d}"


class Painel(models.Model):
    """Estado do painel por fila (uma linha por tipo de fila)."""

    tipo = models.CharField("Fila", max_length=20, unique=True, default="TRANSPORTE")
    senha_atual = models.ForeignKey(
        Senha, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    # Incrementa a cada chamada/repetição — dispara o alerta sonoro no painel.
    sequencia = models.PositiveIntegerField(default=0)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Painel"
        verbose_name_plural = "Painel"

    def __str__(self):
        return f"Painel {self.tipo} (seq {self.sequencia})"

    @classmethod
    def carregar(cls, tipo):
        obj, _ = cls.objects.get_or_create(tipo=tipo)
        return obj
