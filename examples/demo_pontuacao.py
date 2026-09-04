"""Demonstração do motor de pontuação (Fase 1).

Executar da raiz do repositório:

    python examples/demo_pontuacao.py

Reproduz o exemplo verificável de docs/04-regras-de-negocio.md (= 141 pontos).
"""

import os
import sys
from datetime import date
from decimal import Decimal

# Permite executar o script diretamente (python examples/demo_pontuacao.py).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor import (  # noqa: E402
    Aluguel,
    Membro,
    NucleoFamiliar,
    Renda,
    calcular_pontuacao,
    carregar_parametros,
)

REF = date(2026, 9, 15)


def nasc(idade: int) -> date:
    return date(REF.year - idade, REF.month, REF.day)


def main() -> None:
    nucleo = NucleoFamiliar(
        data_referencia=REF,
        habitacao_precaria_ou_risco=True,  # Critério Legal I
        matricula_comprovada=True,         # parte do Critério Legal II
        membros=[
            Membro(nasc(40), "M", "Requerente", arrimo=True,
                   rendas=[Renda("emprego_formal", Decimal("3000"))]),
            Membro(nasc(38), "F", "Companheira"),
            Membro(nasc(5), "M", "Filho"),
            Membro(nasc(8), "F", "Filha"),
        ],
        aluguel=Aluguel([Decimal("1000"), Decimal("1100"), Decimal("1000")]),
    )

    r = calcular_pontuacao(nucleo, carregar_parametros())

    print("=== Pontuação do Núcleo Familiar ===")
    for inciso, d in r.detalhe_legais.items():
        marca = "✓" if d["atendido"] else "·"
        print(f"  {inciso}  [{marca}]  {d['pontos']:>3} pts")
    print(f"  Renda per capita ..... R$ {r.renda_per_capita:.2f}  -> {r.pontos_per_capita} pts")
    print(f"  Aluguel .............. {r.percentual_aluguel:.2f}%      -> {r.pontos_aluguel} pts")
    print("  " + "-" * 34)
    print(f"  CL = {r.pontos_legais}   CC = {r.pontos_complementares}   P = {r.pontuacao_total}")
    print(f"  Desempate: filhos<=12={r.dependentes_ate_12}  idosos={r.idosos}")

    assert r.pontuacao_total == 141, "Exemplo de aceitação deveria somar 141"
    print("\nOK — exemplo de aceitação confere (141 pontos).")


if __name__ == "__main__":
    main()
