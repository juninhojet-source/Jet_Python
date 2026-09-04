"""Validadores de dados do cadastro."""

from __future__ import annotations

import re


def so_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def formatar_cpf(cpf: str) -> str:
    """Formata como 000.000.000-00. Se não tiver 11 dígitos, devolve como está."""
    d = so_digitos(cpf)
    if len(d) != 11:
        return cpf or ""
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


def cpf_valido(cpf: str) -> bool:
    """Valida CPF pelo algoritmo dos dígitos verificadores (Receita Federal)."""
    cpf = so_digitos(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in (9, 10):
        soma = sum(int(cpf[n]) * ((i + 1) - n) for n in range(i))
        digito = ((soma * 10) % 11) % 10
        if digito != int(cpf[i]):
            return False
    return True
