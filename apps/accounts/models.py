"""Usuário do sistema com perfil de acesso (login próprio)."""
from django.contrib.auth.models import AbstractUser
from django.db import models
from simple_history.models import HistoricalRecords


class Perfil(models.TextChoices):
    ADMIN = "ADMIN", "Administrador"
    ATENDENTE = "ATENDENTE", "Atendente"
    COORDENACAO = "COORDENACAO", "Coordenação"
    CONSULTA = "CONSULTA", "Consulta"
    RECEPCAO = "RECEPCAO", "Recepção (Senhas)"


class User(AbstractUser):
    """Conta de usuário própria do sistema.

    O perfil define o nível de acesso, seguindo o princípio do menor
    privilégio previsto no escopo (LGPD).
    """

    perfil = models.CharField(
        "Perfil",
        max_length=20,
        choices=Perfil.choices,
        default=Perfil.ATENDENTE,
    )
    telefone = models.CharField("Telefone", max_length=20, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        ordering = ["first_name", "username"]

    def __str__(self):
        return self.get_full_name() or self.username

    # --- Conveniências de perfil ---------------------------------------
    @property
    def is_admin(self):
        return self.perfil == Perfil.ADMIN or self.is_superuser

    @property
    def pode_editar(self):
        """Perfis que podem cadastrar/editar (não somente leitura)."""
        return self.is_admin or self.perfil in {Perfil.ATENDENTE, Perfil.COORDENACAO}

    @property
    def so_senhas(self):
        """Perfil restrito ao painel de senhas (recepção)."""
        return self.perfil == Perfil.RECEPCAO

    @property
    def pode_operar_senha(self):
        """Perfis que podem operar o painel de senhas."""
        return self.is_admin or self.perfil in {
            Perfil.ATENDENTE, Perfil.COORDENACAO, Perfil.RECEPCAO
        }
