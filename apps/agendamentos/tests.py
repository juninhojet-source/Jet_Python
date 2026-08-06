"""Testes do núcleo operacional (agenda, agendamento, embarque, cartão)."""
from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.core.models import Municipio
from apps.core.validators import validar_dia_util, validar_horario_agenda
from apps.destinos.models import Destino
from apps.pacientes.models import Paciente

from .models import Agendamento, Embarque, StatusAgendamento

User = get_user_model()


def proxima_sexta():
    d = date.today()
    while d.weekday() != 4:  # 4 = sexta
        d += timedelta(days=1)
    return d


def proximo_domingo():
    d = date.today()
    while d.weekday() != 6:
        d += timedelta(days=1)
    return d


class ValidadoresAgendaTest(TestCase):
    def test_horario_fora_da_janela(self):
        with self.assertRaises(ValidationError):
            validar_horario_agenda(time(4, 30))  # antes das 05:00
        with self.assertRaises(ValidationError):
            validar_horario_agenda(time(18, 30))  # depois das 18:00
        validar_horario_agenda(time(5, 0))   # ok
        validar_horario_agenda(time(18, 0))  # ok

    def test_dia_nao_util(self):
        with self.assertRaises(ValidationError):
            validar_dia_util(proximo_domingo())
        validar_dia_util(proxima_sexta())  # ok


class AgendamentoFluxoTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="atend", password="Sigtrans@2026", perfil="ATENDENTE"
        )
        mun = Municipio.objects.create(codigo_ibge="3105002", nome="Barão de Cocais")
        self.paciente = Paciente.objects.create(
            nome="Maria", cpf="52998224725", data_nascimento=date(1980, 1, 1),
            sexo="F", telefone_principal="31999990000",
        )
        self.destino = Destino.objects.create(nome="Hospital X", municipio=mun)
        self.client.force_login(self.user)

    def _dados(self, **extra):
        base = {
            "paciente": self.paciente.pk,
            "data": proxima_sexta().strftime("%Y-%m-%d"),
            "horario": "07:30",
            "destino": self.destino.pk,
            "status": StatusAgendamento.AGENDADO,
        }
        base.update(extra)
        return base

    def test_criar_agendamento(self):
        resp = self.client.post(reverse("agendamentos:create"), self._dados())
        self.assertEqual(resp.status_code, 302)
        ag = Agendamento.objects.get()
        self.assertEqual(ag.horario, time(7, 30))
        # contato preenchido a partir do telefone do paciente
        self.assertEqual(ag.contato, "31999990000")

    def test_horario_invalido_rejeitado(self):
        resp = self.client.post(reverse("agendamentos:create"), self._dados(horario="19:00"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Agendamento.objects.count(), 0)

    def test_fim_de_semana_rejeitado(self):
        resp = self.client.post(
            reverse("agendamentos:create"),
            self._dados(data=proximo_domingo().strftime("%Y-%m-%d")),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Agendamento.objects.count(), 0)

    def test_registrar_embarque_muda_status(self):
        ag = Agendamento.objects.create(
            paciente=self.paciente, destino=self.destino,
            data=proxima_sexta(), horario=time(8, 0),
        )
        resp = self.client.post(
            reverse("agendamentos:embarque", args=[ag.pk]),
            {"embarque": Embarque.EMBARCOU, "hora_embarque_real": "08:05"},
        )
        self.assertEqual(resp.status_code, 302)
        ag.refresh_from_db()
        self.assertEqual(ag.embarque, Embarque.EMBARCOU)
        self.assertEqual(ag.status, StatusAgendamento.EM_VIAGEM)

    def test_cartao_pdf(self):
        ag = Agendamento.objects.create(
            paciente=self.paciente, destino=self.destino,
            data=proxima_sexta(), horario=time(9, 0),
        )
        resp = self.client.get(reverse("agendamentos:cartao_pdf", args=[ag.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertTrue(resp.content.startswith(b"%PDF"))
