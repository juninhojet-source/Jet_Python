"""Testes do núcleo: cadastro rápido de município."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Municipio

User = get_user_model()


class MunicipioRapidoTest(TestCase):
    def setUp(self):
        self.atendente = User.objects.create_user(
            username="atend", password="Sigtrans@2026", perfil="ATENDENTE"
        )
        self.consulta = User.objects.create_user(
            username="leitor", password="Sigtrans@2026", perfil="CONSULTA"
        )
        self.url = reverse("core:municipio_quick_create")

    def test_cria_e_retorna_json(self):
        self.client.force_login(self.atendente)
        resp = self.client.post(
            self.url, {"nome": "Santa Bárbara", "uf": "mg", "codigo_ibge": "3153608"}
        )
        self.assertEqual(resp.status_code, 200)
        dados = resp.json()
        self.assertTrue(dados["ok"])
        m = Municipio.objects.get()
        self.assertEqual(dados["id"], m.pk)
        self.assertEqual(m.uf, "MG")  # normalizado para maiúsculas
        self.assertEqual(dados["texto"], "Santa Bárbara/MG")

    def test_codigo_ibge_invalido(self):
        self.client.force_login(self.atendente)
        resp = self.client.post(self.url, {"nome": "X", "uf": "MG", "codigo_ibge": "123"})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["ok"])
        self.assertIn("codigo_ibge", resp.json()["errors"])
        self.assertEqual(Municipio.objects.count(), 0)

    def test_codigo_ibge_duplicado(self):
        Municipio.objects.create(nome="Itabira", uf="MG", codigo_ibge="3131307")
        self.client.force_login(self.atendente)
        resp = self.client.post(
            self.url, {"nome": "Outro", "uf": "MG", "codigo_ibge": "3131307"}
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Municipio.objects.count(), 1)

    def test_perfil_consulta_nao_pode(self):
        self.client.force_login(self.consulta)
        resp = self.client.post(
            self.url, {"nome": "Y", "uf": "MG", "codigo_ibge": "3100000"}
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(Municipio.objects.count(), 0)
