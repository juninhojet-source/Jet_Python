"""Testes do cadastro de veículos e do cadastro rápido via agendamento."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import TipoVeiculo, Veiculo

User = get_user_model()


class VeiculoFluxoTest(TestCase):
    def setUp(self):
        self.atendente = User.objects.create_user(
            username="atend", password="Sigtrans@2026", perfil="ATENDENTE"
        )
        self.consulta = User.objects.create_user(
            username="leitor", password="Sigtrans@2026", perfil="CONSULTA"
        )

    def test_lista_exige_login(self):
        self.assertEqual(self.client.get(reverse("veiculos:list")).status_code, 302)

    def test_cadastro_valido(self):
        self.client.force_login(self.atendente)
        resp = self.client.post(
            reverse("veiculos:create"),
            {"nome": "CARRO 1", "tipo": TipoVeiculo.UTILITARIO, "ativo": "on"},
        )
        self.assertEqual(resp.status_code, 302)
        v = Veiculo.objects.get()
        self.assertEqual(v.nome, "CARRO 1")
        self.assertEqual(v.criado_por, self.atendente)

    def test_nome_unico(self):
        Veiculo.objects.create(nome="CARRO 1")
        self.client.force_login(self.atendente)
        resp = self.client.post(
            reverse("veiculos:create"),
            {"nome": "CARRO 1", "tipo": TipoVeiculo.UTILITARIO},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Veiculo.objects.count(), 1)

    def test_perfil_consulta_nao_cadastra(self):
        self.client.force_login(self.consulta)
        self.assertEqual(self.client.get(reverse("veiculos:create")).status_code, 403)


class VeiculoRapidoTest(TestCase):
    """Cadastro rápido de veículo a partir da tela de agendamento (JSON)."""

    def setUp(self):
        self.atendente = User.objects.create_user(
            username="atend", password="Sigtrans@2026", perfil="ATENDENTE"
        )

    def test_cria_e_retorna_json(self):
        self.client.force_login(self.atendente)
        resp = self.client.post(
            reverse("veiculos:quick_create"),
            {"nome": "AMBULÂNCIA 3", "tipo": TipoVeiculo.AMBULANCIA, "ativo": "on"},
        )
        self.assertEqual(resp.status_code, 200)
        dados = resp.json()
        self.assertTrue(dados["ok"])
        v = Veiculo.objects.get()
        self.assertEqual(dados["id"], v.pk)
        self.assertEqual(dados["texto"], "AMBULÂNCIA 3")

    def test_nome_vazio_retorna_erro_json(self):
        self.client.force_login(self.atendente)
        resp = self.client.post(reverse("veiculos:quick_create"), {"tipo": TipoVeiculo.VAN})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["ok"])
        self.assertEqual(Veiculo.objects.count(), 0)


class SeedVeiculosTest(TestCase):
    def test_seed_cria_frota_padrao(self):
        from django.core.management import call_command
        call_command("seed_veiculos")
        self.assertTrue(Veiculo.objects.filter(nome="CARRO 1").exists())
        self.assertTrue(Veiculo.objects.filter(nome="AMBULÂNCIA 1", tipo=TipoVeiculo.AMBULANCIA).exists())
        self.assertTrue(Veiculo.objects.filter(nome="MICRO ITABIRA", tipo=TipoVeiculo.MICRO).exists())
        # Idempotente: rodar de novo não duplica.
        total = Veiculo.objects.count()
        call_command("seed_veiculos")
        self.assertEqual(Veiculo.objects.count(), total)
