"""Validadores de documentos brasileiros (CPF, CNS) e da agenda."""
import re
from datetime import time

from django.conf import settings
from django.core.exceptions import ValidationError


def _hora(texto):
    h, m = texto.split(":")
    return time(int(h), int(m))


def janela_agenda():
    """Retorna (hora_inicio, hora_fim) da janela de atendimento configurada."""
    cfg = settings.SIGTRANS
    return _hora(cfg["AGENDA_HORA_INICIO"]), _hora(cfg["AGENDA_HORA_FIM"])


def validar_horario_agenda(valor):
    """Garante que o horário esteja dentro da janela de atendimento."""
    inicio, fim = janela_agenda()
    if valor < inicio or valor > fim:
        raise ValidationError(
            f"Horário deve estar entre {inicio:%H:%M} e {fim:%H:%M}."
        )


def validar_dia_util(valor):
    """Garante que a data caia em um dia útil configurado (seg–sex)."""
    if valor.weekday() not in settings.SIGTRANS["AGENDA_DIAS_UTEIS"]:
        raise ValidationError("A agenda funciona apenas de segunda a sexta-feira.")


def apenas_digitos(valor):
    return re.sub(r"\D", "", valor or "")


def validar_cpf(valor):
    """Valida um CPF pelos dígitos verificadores."""
    cpf = apenas_digitos(valor)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        raise ValidationError("CPF inválido.")
    for i in range(9, 11):
        soma = sum(int(cpf[num]) * ((i + 1) - num) for num in range(i))
        digito = ((soma * 10) % 11) % 10
        if digito != int(cpf[i]):
            raise ValidationError("CPF inválido.")


def validar_cns(valor):
    """Valida o Cartão Nacional de Saúde (15 dígitos, com dígito verificador)."""
    cns = apenas_digitos(valor)
    if len(cns) != 15:
        raise ValidationError("CNS deve conter 15 dígitos.")
    if cns[0] in ("1", "2"):
        soma = sum(int(cns[i]) * (15 - i) for i in range(15))
        if soma % 11 != 0:
            raise ValidationError("CNS inválido.")
    elif cns[0] in ("7", "8", "9"):
        soma = sum(int(cns[i]) * (15 - i) for i in range(15))
        if soma % 11 != 0:
            raise ValidationError("CNS inválido.")
    else:
        raise ValidationError("CNS inválido.")
