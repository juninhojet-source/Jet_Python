"""Validadores de documentos brasileiros (CPF, CNS) usados nos cadastros."""
import re

from django.core.exceptions import ValidationError


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
