"""Testes de perfis e restrição de acesso."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class PerfilRecepcaoTest(TestCase):
    def setUp(self):
        self.recepcao = User.objects.create_user(
            username="recep", password="Sigtrans@2026", perfil="RECEPCAO"
        )
        self.client.force_login(self.recepcao)

    def test_acessa_painel_de_senhas(self):
        self.assertEqual(self.client.get(reverse("senhas:operador")).status_code, 200)

    def test_pode_chamar_senha(self):
        from apps.senhas import services
        services.emitir_senha("TRANSPORTE")
        r = self.client.post(reverse("senhas:operador"), {"acao": "chamar", "fila": "TRANSPORTE"})
        self.assertEqual(r.status_code, 302)

    def test_redirecionado_de_pacientes_para_senhas(self):
        r = self.client.get(reverse("pacientes:list"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], reverse("senhas:operador"))

    def test_redirecionado_do_dashboard(self):
        r = self.client.get(reverse("core:dashboard"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], reverse("senhas:operador"))

    def test_redirecionado_de_relatorios_e_auditoria(self):
        for nome in ("relatorios:index", "agendamentos:agenda", "destinos:list"):
            r = self.client.get(reverse(nome))
            self.assertEqual(r["Location"], reverse("senhas:operador"))

    def test_nao_pode_editar_pacientes(self):
        self.assertFalse(self.recepcao.pode_editar)
        self.assertTrue(self.recepcao.pode_operar_senha)


class OutrosPerfisNaoRestritosTest(TestCase):
    def test_atendente_acessa_pacientes(self):
        u = User.objects.create_user(username="at", password="x", perfil="ATENDENTE")
        self.client.force_login(u)
        self.assertEqual(self.client.get(reverse("pacientes:list")).status_code, 200)


class LogoutTest(TestCase):
    """Logout via POST (Django 5 não aceita GET no LogoutView)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="u", password="Sigtrans@2026", perfil="ATENDENTE"
        )
        self.client.force_login(self.user)

    def test_get_nao_e_permitido(self):
        r = self.client.get(reverse("accounts:logout"))
        self.assertEqual(r.status_code, 405)

    def test_post_desloga_e_redireciona(self):
        r = self.client.post(reverse("accounts:logout"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], reverse("accounts:login"))
        # Sessão encerrada: dashboard passa a exigir login.
        self.assertEqual(self.client.get(reverse("core:dashboard")).status_code, 302)

    def test_recepcao_consegue_deslogar(self):
        recep = User.objects.create_user(
            username="rec", password="Sigtrans@2026", perfil="RECEPCAO"
        )
        self.client.force_login(recep)
        r = self.client.post(reverse("accounts:logout"))
        self.assertEqual(r.status_code, 302)


class AlterarSenhaTest(TestCase):
    """Usuário troca a própria senha dentro do sistema."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="u", password="Sigtrans@2026", perfil="ATENDENTE"
        )
        self.client.force_login(self.user)

    def test_pagina_carrega(self):
        self.assertEqual(self.client.get(reverse("accounts:alterar_senha")).status_code, 200)

    def test_troca_senha_com_sucesso(self):
        resp = self.client.post(reverse("accounts:alterar_senha"), {
            "old_password": "Sigtrans@2026",
            "new_password1": "NovaSenha#2027",
            "new_password2": "NovaSenha#2027",
        })
        self.assertEqual(resp.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NovaSenha#2027"))
        from apps.auditoria.models import Acao, RegistroAuditoria
        self.assertTrue(RegistroAuditoria.objects.filter(acao=Acao.SENHA).exists())

    def test_senha_atual_errada_rejeitada(self):
        resp = self.client.post(reverse("accounts:alterar_senha"), {
            "old_password": "errada",
            "new_password1": "NovaSenha#2027",
            "new_password2": "NovaSenha#2027",
        })
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Sigtrans@2026"))  # não mudou

    def test_senha_fraca_rejeitada(self):
        resp = self.client.post(reverse("accounts:alterar_senha"), {
            "old_password": "Sigtrans@2026",
            "new_password1": "12345678", "new_password2": "12345678",
        })
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Sigtrans@2026"))

    def test_exige_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("accounts:alterar_senha")).status_code, 302)
