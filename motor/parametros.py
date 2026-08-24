"""Carregamento dos parâmetros do edital a partir do YAML.

Converte números monetários/percentuais para ``Decimal`` para evitar erros de
ponto flutuante nas comparações de borda das faixas de pontuação.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import yaml

# Caminho padrão: regras/parametros_edital.yaml na raiz do repositório.
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMINHO_PADRAO = os.path.join(_RAIZ, "regras", "parametros_edital.yaml")


def _to_decimal(valor: Any) -> Any:
    """Converte int/float para Decimal via str (preserva o valor nominal)."""
    if isinstance(valor, bool) or valor is None:
        return valor
    if isinstance(valor, (int, float)):
        return Decimal(str(valor))
    return valor


def _decimalizar_faixas(faixas: list[dict]) -> list[dict]:
    saida = []
    for f in faixas:
        nova = dict(f)
        for chave in ("min", "max"):
            if chave in nova:
                nova[chave] = _to_decimal(nova[chave])
        saida.append(nova)
    return saida


@dataclass(frozen=True)
class Parametros:
    """Visão tipada e conveniente dos parâmetros do edital."""

    bruto: dict

    # ---- Referência ----
    @property
    def limite_legais(self) -> int:
        return int(self.bruto["criterios_legais"]["limite"])

    @property
    def limite_complementares(self) -> int:
        return int(self.bruto["criterios_complementares"]["limite"])

    @property
    def pontos_por_inciso(self) -> int:
        return int(self.bruto["criterios_legais"]["pontos_por_inciso"])

    # ---- Critério Legal IV ----
    @property
    def limite_renda_cl_iv(self) -> Decimal:
        for inc in self.bruto["criterios_legais"]["incisos"]:
            if inc["id"] == "CL_IV":
                return _to_decimal(inc["limite_renda"])
        raise KeyError("CL_IV não encontrado nos parâmetros")

    # ---- Faixas complementares ----
    @property
    def faixas_per_capita(self) -> list[dict]:
        return _decimalizar_faixas(
            self.bruto["criterios_complementares"]["renda_per_capita"]["faixas"]
        )

    @property
    def faixas_aluguel(self) -> list[dict]:
        return _decimalizar_faixas(
            self.bruto["criterios_complementares"]["aluguel"]["faixas"]
        )

    @property
    def aluguel_cedido_pontos(self) -> int:
        return int(
            self.bruto["criterios_complementares"]["aluguel"]["cedido_ou_emprestado_pontos"]
        )

    # ---- Faixas etárias ----
    @property
    def crianca_max_anos(self) -> int:
        return int(self.bruto["faixas_etarias"]["crianca_max_anos"])

    @property
    def idoso_min_anos(self) -> int:
        return int(self.bruto["faixas_etarias"]["idoso_min_anos"])


def carregar_parametros(caminho: str | None = None) -> Parametros:
    """Lê o YAML do edital e devolve um :class:`Parametros`."""
    with open(caminho or CAMINHO_PADRAO, "r", encoding="utf-8") as fh:
        bruto = yaml.safe_load(fh)
    return Parametros(bruto=bruto)
