"""Testes dos relatórios (agendamentos, BPA, indicadores e exportação)."""
from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.agendamentos.models import Agendamento, StatusAgendamento
from apps.core.models import Municipio
from apps.destinos.models import Destino
from apps.pacientes.models import Paciente

from .filtros import filtrar

User = get_user_model()


def proxima_sexta(base=None):
    d = base or date.today()
    while d.weekday() != 4:
        d += timedelta(days=1)
    return d


class BaseDados(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="c", password="x", perfil="CONSULTA")
        self.mun = Municipio.objects.create(codigo_ibge="3131307", nome="Itabira")
        self.pac = Paciente.objects.create(
            nome="Maria", cpf="52998224725", data_nascimento=date(1970, 1, 1),
            sexo="F", telefone_principal="31999990000", municipio=self.mun, raca_cor="03",
        )
        self.dst = Destino.objects.create(nome="Hospital X", municipio=self.mun)
        self.dia = proxima_sexta()
        self.ag = Agendamento.objects.create(
            paciente=self.pac, destino=self.dst, data=self.dia, horario=time(7, 0),
            procedimento="Cardiologia", status=StatusAgendamento.FINALIZADO,
        )
        Agendamento.objects.create(
            paciente=self.pac, destino=self.dst, data=self.dia, horario=time(8, 0),
            status=StatusAgendamento.CANCELADO,
        )


class FiltroTest(BaseDados):
    def test_filtra_por_dia(self):
        qs, resumo = filtrar({"dia": self.dia.strftime("%Y-%m-%d")}, incluir_cancelados=True)
        self.assertEqual(qs.count(), 2)

    def test_exclui_cancelados_por_padrao(self):
        qs, _ = filtrar({}, incluir_cancelados=False)
        self.assertEqual(qs.count(), 1)

    def test_filtra_por_nome_e_procedimento(self):
        qs, _ = filtrar({"q": "mar", "procedimento": "cardio"}, incluir_cancelados=True)
        self.assertEqual(qs.count(), 1)


class ViewsTest(BaseDados):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_paginas_carregam(self):
        for nome in ["index", "agendamentos", "bpa", "indicadores"]:
            self.assertEqual(self.client.get(reverse(f"relatorios:{nome}")).status_code, 200)

    def test_exige_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("relatorios:agendamentos")).status_code, 302)

    def test_export_xlsx(self):
        r = self.client.get(reverse("relatorios:agendamentos"), {"export": "xlsx"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("spreadsheet", r["Content-Type"])
        self.assertEqual(r.content[:2], b"PK")  # xlsx é um zip

    def test_export_pdf_bpa(self):
        r = self.client.get(reverse("relatorios:bpa"), {"export": "pdf", "mes": self.dia.strftime("%Y-%m")})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))
