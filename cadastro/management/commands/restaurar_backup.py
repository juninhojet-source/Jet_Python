"""Restaura um backup gerado pelo comando ``backup`` (banco + documentos).

ATENÇÃO: a restauração SOBRESCREVE o banco e a pasta de documentos atuais.
Pare o serviço antes (o script restaurar.bat faz isso) e confirme com --confirmar.

Uso:
    python manage.py restaurar_backup --arquivo C:\\mcmv\\backups\\mcmv-backup-...zip --confirmar
    python manage.py restaurar_backup --ultimo --confirmar      # o backup mais recente

Antes de sobrescrever, salva uma cópia de segurança do banco atual como
``db.sqlite3.pre-restauracao`` ao lado do banco.
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

PREFIXO = "mcmv-backup-"


class Command(BaseCommand):
    help = "Restaura um backup (banco + documentos). Sobrescreve os dados atuais."

    def add_arguments(self, parser):
        parser.add_argument("--arquivo", default=None, help="caminho do .zip de backup")
        parser.add_argument("--ultimo", action="store_true", help="usa o backup mais recente de MCMV_BACKUP_DIR")
        parser.add_argument("--confirmar", action="store_true", help="confirma a sobrescrita dos dados atuais")

    def handle(self, *args, **opts):
        if connection.vendor != "sqlite":
            raise CommandError("Restauração automática cobre SQLite. Para PostgreSQL use pg_restore/psql.")

        if opts["ultimo"]:
            pasta = Path(settings.MCMV_BACKUP_DIR)
            candidatos = sorted(pasta.glob(f"{PREFIXO}*.zip"))
            if not candidatos:
                raise CommandError(f"Nenhum backup encontrado em {pasta}.")
            arquivo = candidatos[-1]
        elif opts["arquivo"]:
            arquivo = Path(opts["arquivo"])
        else:
            raise CommandError("Informe --arquivo <zip> ou --ultimo.")

        if not arquivo.exists():
            raise CommandError(f"Backup não encontrado: {arquivo}")
        if not zipfile.is_zipfile(arquivo):
            raise CommandError(f"Arquivo inválido (não é um .zip de backup): {arquivo}")

        if not opts["confirmar"]:
            self.stdout.write(self.style.WARNING(
                f"Isto vai SOBRESCREVER o banco e os documentos com: {arquivo}\n"
                "Pare o serviço (net stop MCMV) e rode de novo com --confirmar."
            ))
            return

        db_atual = Path(connection.settings_dict["NAME"])
        media_root = Path(settings.MEDIA_ROOT)

        with zipfile.ZipFile(arquivo) as z:
            nomes = z.namelist()
            if "db.sqlite3" not in nomes:
                raise CommandError("Backup sem 'db.sqlite3' — arquivo corrompido ou incompatível.")

            # Salvaguarda do banco atual antes de sobrescrever.
            if db_atual.exists():
                seguro = db_atual.with_suffix(db_atual.suffix + ".pre-restauracao")
                shutil.copy2(db_atual, seguro)
                self.stdout.write(f"Banco atual salvo em: {seguro}")

            # 1) Restaura o banco.
            db_atual.parent.mkdir(parents=True, exist_ok=True)
            with z.open("db.sqlite3") as fsrc, open(db_atual, "wb") as fdst:
                shutil.copyfileobj(fsrc, fdst)

            # 2) Restaura os documentos (substitui a pasta de mídia).
            tem_media = any(n.startswith("media/") for n in nomes)
            if tem_media:
                if media_root.exists():
                    shutil.rmtree(media_root)
                media_root.mkdir(parents=True, exist_ok=True)
                for n in nomes:
                    if n.startswith("media/") and not n.endswith("/"):
                        destino = media_root / Path(n).relative_to("media")
                        destino.parent.mkdir(parents=True, exist_ok=True)
                        with z.open(n) as fsrc, open(destino, "wb") as fdst:
                            shutil.copyfileobj(fsrc, fdst)

        self.stdout.write(self.style.SUCCESS(
            f"Restauração concluída a partir de {arquivo.name}. "
            "Inicie o serviço novamente (net start MCMV)."
        ))
