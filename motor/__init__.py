"""Motor de pontuação e classificação — Edital 001/2026 (Barão de Cocais/MG).

Módulo Python puro (sem Django). Recebe um Núcleo Familiar e devolve a
pontuação dos Critérios Legais (CL), dos Complementares (CC), o total (P),
as faixas apuradas e as chaves de desempate.

As regras vivem em ``regras/parametros_edital.yaml`` (fonte única da verdade).
"""

from .modelos import Aluguel, Membro, NucleoFamiliar, Renda, ResultadoPontuacao
from .parametros import Parametros, carregar_parametros
from .pontuacao import calcular_pontuacao, chave_ordenacao

__all__ = [
    "Aluguel",
    "Membro",
    "NucleoFamiliar",
    "Renda",
    "ResultadoPontuacao",
    "Parametros",
    "carregar_parametros",
    "calcular_pontuacao",
    "chave_ordenacao",
]
