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


class ConfiguracoesTest(TestCase):
    """Menu de Configurações, Backup e LGPD (somente administrador)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="adm", password="Sigtrans@2026", perfil="ADMIN"
        )
        self.atendente = User.objects.create_user(
            username="at", password="Sigtrans@2026", perfil="ATENDENTE"
        )

    def test_paginas_admin(self):
        self.client.force_login(self.admin)
        for nome in ("core:configuracoes", "core:backup", "core:lgpd"):
            self.assertEqual(self.client.get(reverse(nome)).status_code, 200, nome)

    def test_nao_admin_bloqueado(self):
        self.client.force_login(self.atendente)
        for nome in ("core:configuracoes", "core:backup", "core:lgpd"):
            self.assertEqual(self.client.get(reverse(nome)).status_code, 403, nome)

    def test_exige_login(self):
        for nome in ("core:configuracoes", "core:backup", "core:lgpd"):
            self.assertEqual(self.client.get(reverse(nome)).status_code, 302, nome)

    def test_backup_download(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("core:backup"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/gzip")
        self.assertIn("attachment", r["Content-Disposition"])
        self.assertIn(".json.gz", r["Content-Disposition"])
        # Conteúdo é um gzip válido e não-vazio.
        import gzip
        conteudo = gzip.decompress(r.content).decode("utf-8")
        self.assertTrue(conteudo.strip().startswith("["))

    def test_backup_registra_auditoria(self):
        from apps.auditoria.models import Acao, RegistroAuditoria
        self.client.force_login(self.admin)
        self.client.post(reverse("core:backup"))
        self.assertTrue(RegistroAuditoria.objects.filter(acao=Acao.BACKUP).exists())
