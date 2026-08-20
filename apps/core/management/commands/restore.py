"""Restaura um backup gerado por `manage.py backup`.

Uso: python manage.py restore backups/sigtrans_AAAAMMDD_HHMMSS.json.gz

ATENÇÃO: a restauração sobrescreve os dados existentes com os do arquivo.
Execute em ambiente controlado e com backup atual, conforme docs/MANUAL_BACKUP.md.
"""
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Restaura o banco a partir de um arquivo de backup (.json ou .json.gz)."

    def add_arguments(self, parser):
        parser.add_argument("arquivo")
        parser.add_argument(
            "--sim", action="store_true", help="Confirma a restauração sem perguntar."
        )

    def handle(self, *args, **options):
        arquivo = Path(options["arquivo"])
        if not arquivo.exists():
            raise CommandError(f"Arquivo não encontrado: {arquivo}")

        if not options["sim"]:
            resp = input(
                f"Restaurar '{arquivo.name}'? Isso sobrescreve os dados atuais. [s/N] "
            )
            if resp.strip().lower() not in ("s", "sim", "y", "yes"):
                self.stdout.write("Operação cancelada.")
                return

        call_command("loaddata", str(arquivo))
        self.stdout.write(self.style.SUCCESS(f"Restauração concluída a partir de {arquivo}."))
