"""Agendamento de transporte — núcleo operacional (Fase 2).

A agenda organiza os agendamentos por data e horário (05:00–18:00, seg–sex,
sem limite diário). Os campos de embarque e o tipo de veículo são de
preenchimento manual, pois podem variar na hora da viagem.
"""
from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords

from apps.core.models import TimeStampedModel
from apps.core.validators import validar_dia_util, validar_horario_agenda
from apps.destinos.models import Destino
from apps.pacientes.models import Paciente


class StatusAgendamento(models.TextChoices):
    AGENDADO = "AGENDADO", "Agendado"
    CONFIRMADO = "CONFIRMADO", "Confirmado"
    EM_VIAGEM = "EM_VIAGEM", "Em viagem"
    FINALIZADO = "FINALIZADO", "Finalizado"
    CANCELADO = "CANCELADO", "Cancelado"
    FALTOU = "FALTOU", "Faltou"


class Embarque(models.TextChoices):
    PENDENTE = "PENDENTE", "Pendente"
    EMBARCOU = "EMBARCOU", "Embarcou"
    NAO_EMBARCOU = "NAO_EMBARCOU", "Não embarcou"


class Agendamento(TimeStampedModel):
    # --- Paciente e acompanhante ---
    paciente = models.ForeignKey(
        Paciente, verbose_name="Paciente", on_delete=models.PROTECT,
        related_name="agendamentos",
    )
    acompanhante = models.CharField("Acompanhante", max_length=150, blank=True)
    contato = models.CharField("Contato", max_length=40, blank=True)

    # --- Agenda ---
    data = models.DateField("Data", validators=[validar_dia_util])
    horario = models.TimeField("Horário", validators=[validar_horario_agenda])

    # --- Destino / consulta ---
    destino = models.ForeignKey(
        Destino, verbose_name="Destino", on_delete=models.PROTECT,
        related_name="agendamentos",
    )
    local_consulta = models.CharField("Local da consulta", max_length=150, blank=True)
    procedimento = models.CharField("Procedimento", max_length=150, blank=True)

    # --- Transporte (preenchimento manual — pode variar na hora) ---
    tipo_veiculo = models.CharField(
        "Tipo de veículo", max_length=60, blank=True,
        help_text="Preenchimento livre (pode mudar na hora da viagem).",
    )
    local_embarque = models.CharField(
        "Local de embarque", max_length=150, blank=True,
        help_text="Preenchimento livre.",
    )
    hora_embarque = models.TimeField("Horário de embarque", null=True, blank=True)

    observacoes = models.TextField("Observações", blank=True)
    status = models.CharField(
        "Status", max_length=12, choices=StatusAgendamento.choices,
        default=StatusAgendamento.AGENDADO,
    )

    # --- Confirmação da viagem (contato no dia anterior) ---
    confirmado_em = models.DateTimeField("Confirmado em", null=True, blank=True)

    # --- Controle de embarque ---
    embarque = models.CharField(
        "Embarque", max_length=12, choices=Embarque.choices, default=Embarque.PENDENTE,
    )
    hora_embarque_real = models.TimeField("Embarque realizado às", null=True, blank=True)
    hora_desembarque_real = models.TimeField("Desembarque às", null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Agendamento"
        verbose_name_plural = "Agendamentos"
        ordering = ["data", "horario"]
        indexes = [
            models.Index(fields=["data", "horario"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"#{self.pk} — {self.paciente} em {self.data:%d/%m/%Y} {self.horario:%H:%M}"

    def get_absolute_url(self):
        return reverse("agendamentos:detail", args=[self.pk])

    @property
    def numero(self):
        """Número do agendamento (identificador legível)."""
        return f"{self.pk:06d}" if self.pk else "—"

    @property
    def cancelado(self):
        return self.status == StatusAgendamento.CANCELADO
