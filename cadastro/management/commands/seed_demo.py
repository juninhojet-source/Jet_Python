"""Popula o banco com Núcleos Familiares de exemplo para demonstração.

Uso:
    python manage.py seed_demo          # cria os dados de exemplo
    python manage.py seed_demo --reset  # remove os dados de exemplo antes

Os registros de demonstração usam CPFs com prefixo '900' para facilitar a
identificação e a remoção. NÃO use em produção com dados reais.
"""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from cadastro import services
from cadastro.models import Inscricao, MembroNucleo, Pessoa, Renda

REF = date(2026, 9, 15)
PREFIXO = "900"  # CPFs de demonstração


def nasc(idade: int) -> date:
    return date(REF.year - idade, REF.month, REF.day)


class Command(BaseCommand):
    help = "Cria Núcleos Familiares de exemplo para demonstração."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Remove os dados de exemplo antes de criar.")

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["reset"]:
            self._remover()

        if Pessoa.objects.filter(cpf__startswith=PREFIXO).exists():
            self.stdout.write(self.style.WARNING(
                "Já existem dados de demonstração. Use --reset para recriar."
            ))
            return

        n = 0
        # (nome, risco, matricula_crianca, arrimo_mulher, renda, aluguel, filhos<=12, idosos)
        cenarios = [
            ("Maria Aparecida",  True,  True,  True,  "1800", "1000", 2, 0),
            ("João Batista",     True,  True,  False, "2600", "900",  1, 1),
            ("Ana Paula",        False, True,  True,  "3200", "700",  1, 0),
            # C e D — empatam (mesma pontuação e mesmos critérios de desempate)
            ("Cláudia Souza",    True,  True,  True,  "2000", "1100", 1, 0),
            ("Denise Ramos",     True,  True,  True,  "2000", "1100", 1, 0),
            ("Eduardo Lima",     False, False, False, "4500", "0",    0, 0),
        ]
        for i, (nome, risco, matr, arrimo_mulher, renda, aluguel, filhos, idosos) in enumerate(cenarios):
            self._criar(i, nome, risco, matr, arrimo_mulher, renda, aluguel, filhos, idosos)
            n += 1

        itens = services.classificar_todos()
        empates = sum(1 for c in itens if c.empate_pendente_sorteio)
        self.stdout.write(self.style.SUCCESS(
            f"{n} núcleos de demonstração criados e classificados "
            f"({empates} em empate para sorteio)."
        ))

    # ------------------------------------------------------------------ #
    def _criar(self, i, nome, risco, matr, arrimo_mulher, renda, aluguel, filhos, idosos):
        base = f"{PREFIXO}{i:02d}"
        req = Pessoa.objects.create(
            nome=nome, cpf=f"{base}-000", data_nascimento=nasc(45),
            sexo="F" if arrimo_mulher else "M",
        )
        insc = Inscricao.objects.create(
            requerente=req, data_referencia=REF, status=Inscricao.Status.APTO,
            habitacao_precaria_ou_risco=risco, matricula_comprovada=matr,
            residencia_5anos_comprovada=True, nao_proprietario_declarado=True,
            nao_beneficiado_declarado=True,
            aluguel_mes_1=Decimal(aluguel) or None,
            aluguel_mes_2=Decimal(aluguel) or None,
            aluguel_mes_3=Decimal(aluguel) or None,
            aluguel_cedido=(aluguel == "0"),
        )
        m = MembroNucleo.objects.create(
            inscricao=insc, pessoa=req, parentesco="REQUERENTE",
            arrimo=arrimo_mulher,
        )
        Renda.objects.create(membro=m, tipo="FORMAL", valor=Decimal(renda))

        for f in range(filhos):
            filho = Pessoa.objects.create(
                nome=f"{nome} — filho {f + 1}", cpf=f"{base}-f{f}",
                data_nascimento=nasc(6 + f), sexo="M",
            )
            MembroNucleo.objects.create(inscricao=insc, pessoa=filho, parentesco="FILHO")

        for v in range(idosos):
            idoso = Pessoa.objects.create(
                nome=f"{nome} — idoso {v + 1}", cpf=f"{base}-i{v}",
                data_nascimento=nasc(68 + v), sexo="F",
            )
            MembroNucleo.objects.create(inscricao=insc, pessoa=idoso, parentesco="MAE")

        services.calcular_e_salvar(insc)

    def _remover(self):
        ids = list(
            Inscricao.objects.filter(requerente__cpf__startswith=PREFIXO)
            .values_list("id", flat=True)
        )
        Inscricao.objects.filter(id__in=ids).delete()
        Pessoa.objects.filter(cpf__startswith=PREFIXO).delete()
        self.stdout.write(self.style.WARNING(f"Removidas {len(ids)} inscrições de demonstração."))
