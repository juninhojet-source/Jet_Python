"""Gera um backup do banco de dados (dumpdata comprimido).

Uso: python manage.py backup [--dir CAMINHO]

Em produção com PostgreSQL, este backup lógico (JSON) complementa — não
substitui — o pg_dump recomendado pela equipe de TI (ver docs/MANUAL_BACKUP.md).
"""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

# Apps não exportados (recriados pelas migrações / sessão).
EXCLUIR = [
    "contenttypes",
    "auth.permission",
    "sessions.session",
    "admin.logentry",
]


class Command(BaseCommand):
    help = "Gera um backup do banco (dumpdata JSON comprimido em .gz)."

    def add_arguments(self, parser):
        parser.add_argument("--dir", default=str(Path(settings.BASE_DIR) / "backups"))

    def handle(self, *args, **options):
        destino = Path(options["dir"])
        destino.mkdir(parents=True, exist_ok=True)
        nome = f"sigtrans_{timezone.now():%Y%m%d_%H%M%S}.json.gz"
        caminho = destino / nome

        call_command(
            "dumpdata",
            *[f"--exclude={e}" for e in EXCLUIR],
            natural_foreign=True,
            natural_primary=True,
            indent=2,
            output=str(caminho),
            verbosity=0,
        )

        tamanho = caminho.stat().st_size
        # Registra o backup na trilha de auditoria.
        try:
            from apps.auditoria.services import Acao, registrar
            registrar(Acao.BACKUP, detalhe=f"{nome} ({tamanho} bytes)")
        except Exception:
            pass

        self.stdout.write(self.style.SUCCESS(f"Backup gerado: {caminho} ({tamanho} bytes)"))
