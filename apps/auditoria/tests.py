"""Testes de auditoria e segurança (LGPD)."""
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.validators import SenhaForteValidator

from .models import Acao, RegistroAuditoria

User = get_user_model()


class AuditoriaLoginTest(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="op", password="Sigtrans@2026", perfil="ATENDENTE")

    def test_login_registra_auditoria(self):
        self.client.post(reverse("accounts:login"), {"username": "op", "password": "Sigtrans@2026"})
        self.assertTrue(RegistroAuditoria.objects.filter(acao=Acao.LOGIN, usuario=self.user).exists())

    def test_login_falho_registra(self):
        self.client.post(reverse("accounts:login"), {"username": "op", "password": "errada"})
        self.assertTrue(RegistroAuditoria.objects.filter(acao=Acao.LOGIN_FALHOU).exists())

    @override_settings(LOGIN_MAX_TENTATIVAS=3)
    def test_bloqueio_por_tentativas(self):
        for _ in range(3):
            self.client.post(reverse("accounts:login"), {"username": "op", "password": "x"})
        # A 4ª tentativa é bloqueada mesmo com a senha correta.
        self.client.post(reverse("accounts:login"), {"username": "op", "password": "Sigtrans@2026"})
        self.assertFalse("_auth_user_id" in self.client.session)
        self.assertTrue(RegistroAuditoria.objects.filter(acao=Acao.BLOQUEIO).exists())


class SenhaForteTest(TestCase):
    def test_rejeita_sem_numero(self):
        with self.assertRaises(ValidationError):
            SenhaForteValidator().validate("somenteletras")

    def test_aceita_forte(self):
        SenhaForteValidator().validate("Sigtrans2026")


class InatividadeTest(TestCase):
    @override_settings(IDLE_TIMEOUT_SECONDS=1)
    def test_logout_por_inatividade(self):
        user = User.objects.create_user(username="op2", password="Sigtrans@2026", perfil="ATENDENTE")
        self.client.force_login(user)
        s = self.client.session
        s["ultima_atividade"] = time.time() - 10  # 10s atrás, além do limite de 1s
        s.save()
        resp = self.client.get(reverse("core:dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], reverse("accounts:login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class AuditoriaAcessoTest(TestCase):
    def test_lista_restrita_admin(self):
        atendente = User.objects.create_user(username="at", password="x", perfil="ATENDENTE")
        self.client.force_login(atendente)
        self.assertEqual(self.client.get(reverse("auditoria:lista")).status_code, 403)

    def test_admin_acessa(self):
        admin = User.objects.create_superuser("adm", "", "Sigtrans@2026")
        admin.perfil = "ADMIN"; admin.save()
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse("auditoria:lista")).status_code, 200)


class BackupTest(TestCase):
    def test_backup_gera_arquivo(self):
        User.objects.create_user(username="op3", password="Sigtrans@2026")
        with TemporaryDirectory() as d:
            call_command("backup", dir=d)
            arquivos = list(Path(d).glob("sigtrans_*.json.gz"))
            self.assertEqual(len(arquivos), 1)
            self.assertGreater(arquivos[0].stat().st_size, 0)
