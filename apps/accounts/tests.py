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
