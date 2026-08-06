"""Testes do painel de senhas."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from . import services
from .models import Painel, Senha, StatusSenha

User = get_user_model()


class NumeracaoTest(TestCase):
    def test_primeira_senha_do_dia(self):
        self.assertEqual(services.proximo_numero(timezone.localdate()), 1)

    def test_sequencia(self):
        services.emitir_senha()
        services.emitir_senha()
        s3 = services.emitir_senha()
        self.assertEqual(s3.numero, 3)

    def test_reinicio_apos_maximo(self):
        hoje = timezone.localdate()
        Senha.objects.create(numero=50, data=hoje)
        self.assertEqual(services.proximo_numero(hoje), 1)

    def test_reinicio_diario(self):
        ontem = timezone.localdate() - timedelta(days=1)
        Senha.objects.create(numero=37, data=ontem)
        # A numeração de hoje ignora as senhas de ontem.
        self.assertEqual(services.proximo_numero(timezone.localdate()), 1)


class FluxoPainelTest(TestCase):
    def test_chamar_proximo_pega_mais_antiga(self):
        s1 = services.emitir_senha()
        services.emitir_senha()
        chamada = services.chamar_proximo(guiche=2)
        self.assertEqual(chamada.pk, s1.pk)
        self.assertEqual(chamada.status, StatusSenha.CHAMADA)
        self.assertEqual(chamada.guiche, 2)
        painel = Painel.carregar()
        self.assertEqual(painel.senha_atual_id, s1.pk)
        self.assertEqual(painel.sequencia, 1)

    def test_repetir_incrementa_sequencia(self):
        services.emitir_senha()
        services.chamar_proximo(1)
        seq = Painel.carregar().sequencia
        services.repetir()
        self.assertEqual(Painel.carregar().sequencia, seq + 1)

    def test_navegar_entre_chamadas(self):
        services.emitir_senha(); services.emitir_senha()
        a = services.chamar_proximo(1)
        b = services.chamar_proximo(1)
        self.assertEqual(Painel.carregar().senha_atual_id, b.pk)
        services.navegar(-1)
        self.assertEqual(Painel.carregar().senha_atual_id, a.pk)
        services.navegar(+1)
        self.assertEqual(Painel.carregar().senha_atual_id, b.pk)

    def test_finalizar(self):
        services.emitir_senha()
        services.chamar_proximo(1)
        services.finalizar_atual()
        self.assertEqual(Painel.carregar().senha_atual.status, StatusSenha.FINALIZADA)

    def test_codigo(self):
        s = Senha.objects.create(numero=7, data=timezone.localdate())
        self.assertEqual(s.codigo, "MT-07")


class ViewsTest(TestCase):
    def test_operador_exige_login(self):
        self.assertEqual(self.client.get(reverse("senhas:operador")).status_code, 302)

    def test_painel_e_estado_publicos(self):
        self.assertEqual(self.client.get(reverse("senhas:painel_tv")).status_code, 200)
        r = self.client.get(reverse("senhas:estado"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("sequencia", r.json())

    def test_kiosk_emite(self):
        r = self.client.post(reverse("senhas:kiosk"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Senha.objects.count(), 1)

    def test_operador_chama(self):
        user = User.objects.create_user(username="a", password="x", perfil="ATENDENTE")
        self.client.force_login(user)
        services.emitir_senha()
        r = self.client.post(reverse("senhas:operador"), {"acao": "chamar", "guiche": 3})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Painel.carregar().senha_atual.guiche, 3)
