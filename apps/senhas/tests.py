"""Testes do painel de senhas (múltiplas filas/salas)."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from . import services
from .models import Painel, Senha, StatusSenha

User = get_user_model()

TRANSPORTE = "TRANSPORTE"
CONSULTAS = "CONSULTAS"


class NumeracaoPorFilaTest(TestCase):
    def test_numeracao_independente_por_fila(self):
        services.emitir_senha(TRANSPORTE)   # MT-01
        services.emitir_senha(TRANSPORTE)   # MT-02
        c1 = services.emitir_senha(CONSULTAS)  # MC-01 (independente)
        self.assertEqual(c1.numero, 1)
        self.assertEqual(c1.codigo, "MC-01")
        t3 = services.emitir_senha(TRANSPORTE)  # MT-03
        self.assertEqual(t3.numero, 3)
        self.assertEqual(t3.codigo, "MT-03")

    def test_reinicio_apos_maximo(self):
        hoje = timezone.localdate()
        Senha.objects.create(tipo=CONSULTAS, numero=50, data=hoje)
        self.assertEqual(services.proximo_numero(CONSULTAS, hoje), 1)

    def test_reinicio_diario(self):
        ontem = timezone.localdate() - timedelta(days=1)
        Senha.objects.create(tipo=TRANSPORTE, numero=30, data=ontem)
        self.assertEqual(services.proximo_numero(TRANSPORTE, timezone.localdate()), 1)


class ChamadaPorSalaTest(TestCase):
    def test_transporte_vai_para_sala_2(self):
        services.emitir_senha(TRANSPORTE)
        s = services.chamar_proximo(TRANSPORTE)
        self.assertEqual(s.guiche, 2)
        self.assertEqual(Painel.carregar(TRANSPORTE).senha_atual_id, s.pk)

    def test_consultas_vai_para_sala_1(self):
        services.emitir_senha(CONSULTAS)
        s = services.chamar_proximo(CONSULTAS)
        self.assertEqual(s.guiche, 1)

    def test_filas_nao_interferem(self):
        services.emitir_senha(TRANSPORTE)
        services.emitir_senha(CONSULTAS)
        services.chamar_proximo(TRANSPORTE)
        # Chamar transporte não afeta a fila de consultas.
        self.assertIsNone(Painel.carregar(CONSULTAS).senha_atual)

    def test_estado_todas_ordena_por_sala(self):
        salas = [e["sala"] for e in services.estado_todas()]
        self.assertEqual(salas, sorted(salas))
        self.assertEqual(salas[0], 1)  # Consultas (Sala 01) vem primeiro


class ViewsTest(TestCase):
    def test_operador_exige_login(self):
        self.assertEqual(self.client.get(reverse("senhas:operador")).status_code, 302)

    def test_painel_e_estado_publicos(self):
        self.assertEqual(self.client.get(reverse("senhas:painel_tv")).status_code, 200)
        r = self.client.get(reverse("senhas:estado"))
        self.assertEqual(r.status_code, 200)
        dados = r.json()
        self.assertIn("filas", dados)
        self.assertEqual(len(dados["filas"]), 2)

    def test_kiosk_emite_para_fila_escolhida(self):
        r = self.client.post(reverse("senhas:kiosk"), {"fila": CONSULTAS})
        self.assertEqual(r.status_code, 200)
        s = Senha.objects.get()
        self.assertEqual(s.tipo, CONSULTAS)
        self.assertEqual(s.codigo, "MC-01")

    def test_operador_chama_na_sala_da_fila(self):
        user = User.objects.create_user(username="a", password="x", perfil="ATENDENTE")
        self.client.force_login(user)
        services.emitir_senha(CONSULTAS)
        r = self.client.post(reverse("senhas:operador"), {"acao": "chamar", "fila": CONSULTAS})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Painel.carregar(CONSULTAS).senha_atual.guiche, 1)
