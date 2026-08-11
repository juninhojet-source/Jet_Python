"""Testes do cadastro de pacientes."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.validators import validar_cpf
from django.core.exceptions import ValidationError

from .models import Paciente

User = get_user_model()


class ValidadorCPFTest(TestCase):
    def test_cpf_valido(self):
        validar_cpf("529.982.247-25")  # não deve levantar

    def test_cpf_invalido(self):
        with self.assertRaises(ValidationError):
            validar_cpf("111.111.111-11")


class PacienteModelTest(TestCase):
    def test_idade_calculada(self):
        p = Paciente(nome="Teste", data_nascimento=date(2000, 1, 1))
        esperado = date.today().year - 2000 - (
            (date.today().month, date.today().day) < (1, 1)
        )
        self.assertEqual(p.idade, esperado)


class PacienteFluxoTest(TestCase):
    def setUp(self):
        self.atendente = User.objects.create_user(
            username="atend", password="Sigtrans@2026", perfil="ATENDENTE"
        )
        self.consulta = User.objects.create_user(
            username="leitor", password="Sigtrans@2026", perfil="CONSULTA"
        )

    def test_lista_exige_login(self):
        resp = self.client.get(reverse("pacientes:list"))
        self.assertEqual(resp.status_code, 302)

    def test_cadastro_exige_cpf_ou_cns(self):
        self.client.force_login(self.atendente)
        resp = self.client.post(
            reverse("pacientes:create"),
            {
                "nome": "Maria",
                "data_nascimento": "1990-05-10",
                "sexo": "F",
                "raca_cor": "03",
                "nacionalidade": "Brasileira",
                "telefone_principal": "31999990000",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ao menos um identificador")
        self.assertEqual(Paciente.objects.count(), 0)

    def test_cadastro_valido(self):
        self.client.force_login(self.atendente)
        resp = self.client.post(
            reverse("pacientes:create"),
            {
                "nome": "João Silva",
                "cpf": "529.982.247-25",
                "data_nascimento": "1985-03-20",
                "sexo": "M",
                "raca_cor": "01",
                "nacionalidade": "Brasileira",
                "telefone_principal": "31988887777",
            },
        )
        self.assertEqual(resp.status_code, 302)
        p = Paciente.objects.get()
        self.assertEqual(p.cpf, "52998224725")
        self.assertEqual(p.criado_por, self.atendente)

    def test_perfil_consulta_nao_cadastra(self):
        self.client.force_login(self.consulta)
        resp = self.client.get(reverse("pacientes:create"))
        self.assertEqual(resp.status_code, 403)


class PacienteRapidoTest(TestCase):
    """Cadastro rápido de paciente a partir da tela de agendamento (JSON)."""

    def setUp(self):
        self.atendente = User.objects.create_user(
            username="atend", password="Sigtrans@2026", perfil="ATENDENTE"
        )
        self.consulta = User.objects.create_user(
            username="leitor", password="Sigtrans@2026", perfil="CONSULTA"
        )

    def test_cria_e_retorna_json(self):
        self.client.force_login(self.atendente)
        resp = self.client.post(
            reverse("pacientes:quick_create"),
            {
                "nome": "Ana Souza",
                "cpf": "529.982.247-25",
                "data_nascimento": "1992-07-15",
                "sexo": "F",
                "raca_cor": "03",
                "telefone_principal": "31999990000",
            },
        )
        self.assertEqual(resp.status_code, 200)
        dados = resp.json()
        self.assertTrue(dados["ok"])
        p = Paciente.objects.get()
        self.assertEqual(dados["id"], p.pk)
        self.assertEqual(p.criado_por, self.atendente)

    def test_sem_identificador_retorna_erro_json(self):
        self.client.force_login(self.atendente)
        resp = self.client.post(
            reverse("pacientes:quick_create"),
            {
                "nome": "Sem Documento",
                "data_nascimento": "1990-01-01",
                "sexo": "M",
                "raca_cor": "01",
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["ok"])
        self.assertEqual(Paciente.objects.count(), 0)

    def test_perfil_consulta_nao_pode(self):
        self.client.force_login(self.consulta)
        resp = self.client.post(reverse("pacientes:quick_create"), {"nome": "X"})
        self.assertEqual(resp.status_code, 403)
