"""Cadastro de veículos da frota de transporte de pacientes.

Padroniza a identificação usada na agenda e no Mapa de Viagem (ex.: "CARRO 1",
"AMBULÂNCIA 2", "MICRO ITABIRA"). O veículo do agendamento é uma seleção deste
cadastro, mas pode ser trocado a qualquer momento (inclusive na hora da viagem).
"""
from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords

from apps.core.models import TimeStampedModel


class TipoVeiculo(models.TextChoices):
    UTILITARIO = "UTILITARIO", "Carro / Utilitário"
    AMBULANCIA = "AMBULANCIA", "Ambulância"
    MICRO = "MICRO", "Micro-ônibus"
    VAN = "VAN", "Van"
    OUTRO = "OUTRO", "Outro"


class Veiculo(TimeStampedModel):
    nome = models.CharField(
        "Identificação", max_length=40, unique=True,
        help_text="Nome usado na agenda e no mapa (ex.: CARRO 1, AMBULÂNCIA 2).",
    )
    tipo = models.CharField(
        "Tipo", max_length=12, choices=TipoVeiculo.choices, default=TipoVeiculo.UTILITARIO
    )
    placa = models.CharField("Placa", max_length=10, blank=True)
    ativo = models.BooleanField("Ativo", default=True)
    observacoes = models.CharField("Observações", max_length=150, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Veículo"
        verbose_name_plural = "Veículos"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def get_absolute_url(self):
        return reverse("veiculos:list")
