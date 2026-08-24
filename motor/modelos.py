"""Estruturas de entrada e saída do motor de pontuação.

São *dataclasses* puras — independem de Django. Na Fase 2, os models do banco
serão convertidos para estes objetos antes de chamar o motor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class Renda:
    """Uma fonte de renda de um integrante do núcleo."""

    tipo: str
    valor: Decimal
    computavel: bool = True  # BPC, Bolsa Família etc. entram como False (item 3.1.4.1)

    def __post_init__(self) -> None:
        self.valor = Decimal(str(self.valor))


@dataclass
class Membro:
    """Um integrante do Núcleo Familiar."""

    data_nascimento: date
    sexo: str = "M"  # "F" ou "M"
    parentesco: str = "Outro"
    dependente: bool = False
    arrimo: bool = False
    pcd: bool = False
    # Se entra no divisor da renda per capita (decisão D-2; padrão: todos).
    considerado_apuracao_renda: bool = True
    rendas: list[Renda] = field(default_factory=list)

    def idade_em(self, referencia: date) -> int:
        """Idade completa (anos) na data de referência."""
        r, n = referencia, self.data_nascimento
        return r.year - n.year - ((r.month, r.day) < (n.month, n.day))

    def renda_computavel(self) -> Decimal:
        return sum((r.valor for r in self.rendas if r.computavel), Decimal("0"))


@dataclass
class Aluguel:
    """Aluguel pago pelo núcleo (média dos meses de referência — item 8.8.8)."""

    valores_mensais: list[Decimal] = field(default_factory=list)
    cedido_ou_emprestado: bool = False  # item 8.8.6 → 0 pontos

    def __post_init__(self) -> None:
        self.valores_mensais = [Decimal(str(v)) for v in self.valores_mensais]

    def media(self) -> Decimal:
        if not self.valores_mensais:
            return Decimal("0")
        return sum(self.valores_mensais, Decimal("0")) / Decimal(len(self.valores_mensais))


@dataclass
class NucleoFamiliar:
    """Entrada do motor: um núcleo com os dados necessários à pontuação.

    Os fatos que dependem de análise documental (habitação precária, matrícula
    comprovada) entram como marcações da Comissão, não são inferidos.
    """

    membros: list[Membro] = field(default_factory=list)
    data_referencia: date | None = None  # decisão D-1; se None, usa a inscrição/hoje

    # Critério Legal I (item 8.5 I) — determinação da análise
    habitacao_precaria_ou_risco: bool = False
    # Critério Legal II (item 8.5 II) — a existência de criança 0–12 é calculada;
    # a matrícula é fato documental marcado pela análise.
    matricula_comprovada: bool = False

    aluguel: Aluguel | None = None

    # ---- Derivados a partir dos membros ----
    def _ref(self) -> date:
        return self.data_referencia or date.today()

    def renda_bruta_computavel(self) -> Decimal:
        return sum((m.renda_computavel() for m in self.membros), Decimal("0"))

    def integrantes_considerados(self) -> int:
        n = sum(1 for m in self.membros if m.considerado_apuracao_renda)
        return n or len(self.membros)  # nunca divide por zero

    def contar_criancas_ate(self, max_anos: int) -> int:
        ref = self._ref()
        return sum(1 for m in self.membros if m.idade_em(ref) <= max_anos)

    def contar_idosos(self, min_anos: int) -> int:
        ref = self._ref()
        return sum(1 for m in self.membros if m.idade_em(ref) >= min_anos)

    def arrimo_mulher_ou_idoso(self, idoso_min_anos: int) -> bool:
        ref = self._ref()
        for m in self.membros:
            if m.arrimo and (m.sexo.upper() == "F" or m.idade_em(ref) >= idoso_min_anos):
                return True
        return False


@dataclass
class ResultadoPontuacao:
    """Saída do motor — rastreável e recomputável."""

    pontos_legais: int
    pontos_complementares: int
    pontuacao_total: int
    detalhe_legais: dict[str, dict]  # inciso -> {"atendido": bool, "pontos": int}
    renda_per_capita: Decimal
    pontos_per_capita: int
    percentual_aluguel: Decimal | None
    pontos_aluguel: int
    # Chaves de desempate (item 8.10)
    dependentes_ate_12: int
    idosos: int
