"""Testes do cadastro de destinos, incluindo cadastro rápido via agendamento."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.models import Municipio

from .models import Destino, TipoDestino

User = get_user_model()


class DestinoRapidoTest(TestCase):
    """Cadastro rápido de destino a partir da tela de agendamento (JSON)."""

    def setUp(self):
        self.atendente = User.objects.create_user(
            username="atend", password="Sigtrans@2026", perfil="ATENDENTE"
        )
        self.consulta = User.objects.create_user(
            username="leitor", password="Sigtrans@2026", perfil="CONSULTA"
        )
        self.municipio = Municipio.objects.create(
            codigo_ibge="3105002", nome="Barão de Cocais"
        )

    def test_cria_e_retorna_json(self):
        self.client.force_login(self.atendente)
        resp = self.client.post(
            reverse("destinos:quick_create"),
            {
                "nome": "Hospital Regional",
                "tipo": TipoDestino.HOSPITAL,
                "municipio": self.municipio.pk,
                "ativo": "on",
            },
        )
        self.assertEqual(resp.status_code, 200)
        dados = resp.json()
        self.assertTrue(dados["ok"])
        d = Destino.objects.get()
        self.assertEqual(dados["id"], d.pk)
        self.assertEqual(dados["texto"], d.nome)
        self.assertEqual(d.criado_por, self.atendente)

    def test_sem_municipio_retorna_erro_json(self):
        self.client.force_login(self.atendente)
        resp = self.client.post(
            reverse("destinos:quick_create"),
            {"nome": "Sem Município", "tipo": TipoDestino.CLINICA},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["ok"])
        self.assertEqual(Destino.objects.count(), 0)

    def test_perfil_consulta_nao_pode(self):
        self.client.force_login(self.consulta)
        resp = self.client.post(reverse("destinos:quick_create"), {"nome": "X"})
        self.assertEqual(resp.status_code, 403)
