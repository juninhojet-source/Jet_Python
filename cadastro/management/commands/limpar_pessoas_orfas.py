"""Remove pessoas órfãs — sem vínculo com qualquer núcleo/inscrição.

Útil para limpar registros que ficaram órfãos por exclusões feitas antes da
correção que passou a remover as pessoas junto com a inscrição.

Uso:
    python manage.py limpar_pessoas_orfas            # mostra e remove
    python manage.py limpar_pessoas_orfas --dry-run  # apenas lista, não remove
    python manage.py limpar_pessoas_orfas --cpf 07065903680   # limita a um CPF
"""

from django.core.management.base import BaseCommand

from cadastro.models import Pessoa


class Command(BaseCommand):
    help = "Remove pessoas sem vínculo com qualquer núcleo/inscrição (libera o CPF)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Apenas lista, não remove.")
        parser.add_argument("--cpf", default="", help="Limita a um CPF específico.")

    def handle(self, *args, **opts):
        qs = Pessoa.objects.filter(participacoes__isnull=True, inscricoes_como_requerente__isnull=True)
        if opts["cpf"]:
            qs = qs.filter(cpf=opts["cpf"])

        orfas = list(qs)
        if not orfas:
            self.stdout.write(self.style.WARNING("Nenhuma pessoa órfã encontrada."))
            return

        for p in orfas:
            self.stdout.write(f"- {p.nome} (CPF {p.cpf})")

        if opts["dry_run"]:
            self.stdout.write(self.style.NOTICE(f"{len(orfas)} órfã(s). Nada removido (--dry-run)."))
            return

        for p in orfas:
            p.delete()
        self.stdout.write(self.style.SUCCESS(f"{len(orfas)} pessoa(s) órfã(s) removida(s)."))
