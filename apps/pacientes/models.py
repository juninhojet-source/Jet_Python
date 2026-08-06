"""Cadastro de pacientes — cadastro único com os campos exigidos pelo BPA."""
from datetime import date

from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords

from apps.core.models import Municipio, TimeStampedModel
from apps.core.validators import validar_cns, validar_cpf


class Sexo(models.TextChoices):
    MASCULINO = "M", "Masculino"
    FEMININO = "F", "Feminino"


class RacaCor(models.TextChoices):
    # Códigos conforme o BPA / e-SUS.
    BRANCA = "01", "Branca"
    PRETA = "02", "Preta"
    PARDA = "03", "Parda"
    AMARELA = "04", "Amarela"
    INDIGENA = "05", "Indígena"
    SEM_INFO = "99", "Sem informação"


class Paciente(TimeStampedModel):
    # --- Identificação ---
    nome = models.CharField("Nome completo", max_length=150)
    cns = models.CharField(
        "Cartão SUS (CNS)",
        max_length=15,
        unique=True,
        null=True,
        blank=True,
        validators=[validar_cns],
        help_text="15 dígitos. Usado no BPA e para evitar duplicidade.",
    )
    cpf = models.CharField(
        "CPF",
        max_length=11,
        unique=True,
        null=True,
        blank=True,
        validators=[validar_cpf],
    )
    data_nascimento = models.DateField("Data de nascimento")
    sexo = models.CharField("Sexo", max_length=1, choices=Sexo.choices)
    raca_cor = models.CharField(
        "Raça/Cor", max_length=2, choices=RacaCor.choices, default=RacaCor.SEM_INFO
    )
    etnia = models.CharField(
        "Etnia", max_length=80, blank=True, help_text="Quando indígena (BPA)."
    )
    nacionalidade = models.CharField("Nacionalidade", max_length=60, default="Brasileira")

    # --- Endereço (campos do BPA) ---
    cep = models.CharField("CEP", max_length=8, blank=True)
    logradouro = models.CharField("Logradouro", max_length=150, blank=True)
    numero = models.CharField("Número", max_length=10, blank=True)
    complemento = models.CharField("Complemento", max_length=60, blank=True)
    bairro = models.CharField("Bairro", max_length=80, blank=True)
    municipio = models.ForeignKey(
        Municipio,
        verbose_name="Município",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="pacientes",
    )

    # --- Contato ---
    telefone_principal = models.CharField("Telefone principal", max_length=20)
    telefone_secundario = models.CharField("Telefone secundário", max_length=20, blank=True)

    observacoes = models.TextField("Observações", blank=True)
    ativo = models.BooleanField("Ativo", default=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"
        ordering = ["nome"]
        indexes = [
            models.Index(fields=["nome"]),
            models.Index(fields=["cpf"]),
            models.Index(fields=["cns"]),
        ]

    def __str__(self):
        return self.nome

    def get_absolute_url(self):
        return reverse("pacientes:detail", args=[self.pk])

    @property
    def idade(self):
        """Idade calculada automaticamente a partir da data de nascimento."""
        if not self.data_nascimento:
            return None
        hoje = date.today()
        return (
            hoje.year
            - self.data_nascimento.year
            - ((hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day))
        )

    @property
    def endereco_resumido(self):
        partes = [p for p in [self.logradouro, self.numero, self.bairro] if p]
        return ", ".join(partes)
