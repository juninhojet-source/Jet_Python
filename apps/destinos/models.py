"""Cadastro de destinos: estabelecimentos de saúde de destino do transporte."""
from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords

from apps.core.models import Municipio, TimeStampedModel


class TipoDestino(models.TextChoices):
    HOSPITAL = "HOSPITAL", "Hospital"
    CLINICA = "CLINICA", "Clínica"
    UPA = "UPA", "UPA / Pronto Atendimento"
    LABORATORIO = "LABORATORIO", "Laboratório"
    OUTRO = "OUTRO", "Outro"


class Destino(TimeStampedModel):
    nome = models.CharField("Nome / Estabelecimento", max_length=150)
    tipo = models.CharField(
        "Tipo", max_length=20, choices=TipoDestino.choices, default=TipoDestino.HOSPITAL
    )
    municipio = models.ForeignKey(
        Municipio,
        verbose_name="Município",
        on_delete=models.PROTECT,
        related_name="destinos",
    )
    endereco = models.CharField("Endereço", max_length=180, blank=True)
    telefone = models.CharField("Telefone", max_length=20, blank=True)
    ativo = models.BooleanField("Ativo", default=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Destino"
        verbose_name_plural = "Destinos"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.municipio})"

    def get_absolute_url(self):
        return reverse("destinos:list")
