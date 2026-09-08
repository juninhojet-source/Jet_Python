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


class TelefoneESexoTest(TestCase):
    """Formatação de telefone, opções de sexo e máscara de CEP."""

    def setUp(self):
        self.atendente = User.objects.create_user(
            username="at", password="Sigtrans@2026", perfil="ATENDENTE"
        )
        self.client.force_login(self.atendente)

    def test_telefone_formatado_e_so_digitos(self):
        from apps.pacientes.forms import PacienteForm
        f = PacienteForm({
            "nome": "Zé", "cpf": "529.982.247-25", "data_nascimento": "1980-01-01",
            "sexo": "M", "raca_cor": "01", "nacionalidade": "Brasileira",
            "telefone_principal": "31989708854", "cep": "35970-000",
        })
        self.assertTrue(f.is_valid(), f.errors)
        self.assertEqual(f.cleaned_data["telefone_principal"], "(31) 98970-8854")
        self.assertEqual(f.cleaned_data["cep"], "35970000")

    def test_telefone_fixo_10_digitos(self):
        from apps.core.validators import formatar_telefone
        self.assertEqual(formatar_telefone("3138377661"), "(31) 3837-7661")

    def test_telefone_invalido_rejeitado(self):
        from apps.core.validators import formatar_telefone
        with self.assertRaises(ValidationError):
            formatar_telefone("123")

    def test_sexo_tem_outro_e_nao_informado(self):
        from .models import Sexo
        valores = dict(Sexo.choices)
        self.assertIn("O", valores)
        self.assertIn("N", valores)


class ExclusaoAdminTest(TestCase):
    """Exclusão de cadastros restrita ao administrador."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="adm", password="Sigtrans@2026", perfil="ADMIN"
        )
        self.atendente = User.objects.create_user(
            username="at", password="Sigtrans@2026", perfil="ATENDENTE"
        )
        self.pac = Paciente.objects.create(
            nome="Excluível", cpf="52998224725", data_nascimento=date(1980, 1, 1),
            sexo="M", raca_cor="01", telefone_principal="31999990000",
        )

    def test_atendente_nao_pode_excluir(self):
        self.client.force_login(self.atendente)
        self.assertEqual(
            self.client.get(reverse("pacientes:delete", args=[self.pac.pk])).status_code, 403
        )

    def test_admin_exclui(self):
        self.client.force_login(self.admin)
        resp = self.client.post(reverse("pacientes:delete", args=[self.pac.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Paciente.objects.filter(pk=self.pac.pk).exists())

    def test_exclusao_bloqueada_se_vinculado(self):
        from datetime import time, timedelta
        from apps.core.models import Municipio
        from apps.destinos.models import Destino
        from apps.agendamentos.models import Agendamento
        mun = Municipio.objects.create(codigo_ibge="3106200", nome="Belo Horizonte")
        dst = Destino.objects.create(nome="Hosp", municipio=mun)
        dia = date.today() + timedelta(days=(4 - date.today().weekday()) % 7)
        Agendamento.objects.create(
            paciente=self.pac, destino=dst, data=dia, horario=time(8, 0)
        )
        self.client.force_login(self.admin)
        resp = self.client.post(reverse("pacientes:delete", args=[self.pac.pk]))
        self.assertEqual(resp.status_code, 302)  # redireciona com mensagem
        self.assertTrue(Paciente.objects.filter(pk=self.pac.pk).exists())  # não excluiu


class CpfDuplicadoTest(TestCase):
    """CPF duplicado: mensagem no servidor e verificação imediata (AJAX)."""

    def setUp(self):
        self.atendente = User.objects.create_user(
            username="at", password="Sigtrans@2026", perfil="ATENDENTE"
        )
        self.existente = Paciente.objects.create(
            nome="Maria Existente", cpf="52998224725", data_nascimento=date(1980, 1, 1),
            sexo="F", raca_cor="01", telefone_principal="(31) 99999-0000",
        )
        self.client.force_login(self.atendente)

    def test_cadastro_com_cpf_duplicado_informa_mensagem(self):
        resp = self.client.post(reverse("pacientes:create"), {
            "nome": "Outra Pessoa", "cpf": "529.982.247-25",
            "data_nascimento": "1990-05-10", "sexo": "M", "raca_cor": "01",
            "nacionalidade": "Brasileira", "telefone_principal": "31988887777",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "CPF já cadastrado")
        self.assertEqual(Paciente.objects.filter(cpf="52998224725").count(), 1)

    def test_verificar_cpf_endpoint(self):
        r = self.client.get(reverse("pacientes:verificar_cpf"), {"cpf": "529.982.247-25"})
        self.assertEqual(r.status_code, 200)
        j = r.json()
        self.assertTrue(j["existe"])
        self.assertEqual(j["nome"], "Maria Existente")
        # CPF não cadastrado
        r2 = self.client.get(reverse("pacientes:verificar_cpf"), {"cpf": "111.444.777-35"})
        self.assertFalse(r2.json()["existe"])

    def test_verificar_cpf_exclui_o_proprio_na_edicao(self):
        r = self.client.get(reverse("pacientes:verificar_cpf"),
                             {"cpf": "52998224725", "excluir": str(self.existente.pk)})
        self.assertFalse(r.json()["existe"])
