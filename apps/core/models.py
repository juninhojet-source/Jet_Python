"""Modelos base e tabelas de apoio compartilhadas."""
from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """Base com carimbo de criação/atualização e autoria.

    A trilha de auditoria detalhada (valor anterior/novo) fica a cargo do
    django-simple-history, declarado nos modelos concretos.
    """

    criado_em = models.DateTimeField("Criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("Atualizado em", auto_now=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Criado por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        editable=False,
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Atualizado por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        editable=False,
    )

    class Meta:
        abstract = True


class Municipio(models.Model):
    """Município com código IBGE — exigido no preenchimento do BPA."""

    codigo_ibge = models.CharField("Código IBGE", max_length=7, unique=True)
    nome = models.CharField("Nome", max_length=120)
    uf = models.CharField("UF", max_length=2, default="MG")

    class Meta:
        verbose_name = "Município"
        verbose_name_plural = "Municípios"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome}/{self.uf}"
