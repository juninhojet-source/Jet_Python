"""Backup consistente do Sistema MCMV: banco + documentos (mídia).

Gera um arquivo ``mcmv-backup-AAAAMMDD-HHMMSS.zip`` contendo:
  - ``db.sqlite3``  — cópia CONSISTENTE via API de backup do SQLite (não precisa
    parar o serviço; usa snapshot transacional);
  - ``media/``      — os documentos anexados (MEDIA_ROOT);
  - ``manifesto.json`` — metadados (data, versão, tamanhos, contagem de registros).

Aplica retenção (remove backups mais antigos que ``MCMV_BACKUP_RETENCAO_DIAS``).

Uso:
    python manage.py backup                 # usa settings.MCMV_BACKUP_DIR
    python manage.py backup --destino D:\\seguro\\mcmv
    python manage.py backup --reter 60      # mantém 60 dias

Para PostgreSQL, use ``pg_dump`` (ver docs/10-backup-restauracao.md); este
comando cobre o cenário padrão em SQLite.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

PREFIXO = "mcmv-backup-"


class Command(BaseCommand):
    help = "Gera um backup consistente (banco + documentos) e aplica a retenção."

    def add_arguments(self, parser):
        parser.add_argument("--destino", default=None, help="pasta de saída (padrão: MCMV_BACKUP_DIR)")
        parser.add_argument("--reter", type=int, default=None, help="dias de retenção (padrão: MCMV_BACKUP_RETENCAO_DIAS)")

    def handle(self, *args, **opts):
        if connection.vendor != "sqlite":
            raise CommandError(
                "Este comando faz backup de SQLite. Para PostgreSQL use pg_dump "
                "(ver docs/10-backup-restauracao.md)."
            )

        destino = Path(opts["destino"] or settings.MCMV_BACKUP_DIR)
        destino.mkdir(parents=True, exist_ok=True)
        reter = opts["reter"] if opts["reter"] is not None else settings.MCMV_BACKUP_RETENCAO_DIAS

        carimbo = datetime.now().strftime("%Y%m%d-%H%M%S")
        alvo = destino / f"{PREFIXO}{carimbo}.zip"

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            # 1) Cópia CONSISTENTE do banco via API de backup do SQLite.
            db_copia = tmp / "db.sqlite3"
            self._backup_sqlite(db_copia)

            # 2) Coleta a mídia (documentos) e conta registros para o manifesto.
            media_root = Path(settings.MEDIA_ROOT)
            n_docs = self._contar_documentos()

            manifesto = {
                "sistema": "MCMV — Cadastro Habitacional (Barão de Cocais/MG)",
                "gerado_em": datetime.now().isoformat(timespec="seconds"),
                "banco": "sqlite",
                "tamanho_db_bytes": db_copia.stat().st_size,
                "documentos_registrados": n_docs,
                "media_incluida": media_root.exists(),
            }

            # 3) Compacta tudo num único .zip.
            with zipfile.ZipFile(alvo, "w", zipfile.ZIP_DEFLATED) as z:
                z.write(db_copia, "db.sqlite3")
                z.writestr("manifesto.json", json.dumps(manifesto, ensure_ascii=False, indent=2))
                if media_root.exists():
                    for arq in media_root.rglob("*"):
                        if arq.is_file():
                            z.write(arq, Path("media") / arq.relative_to(media_root))

        tam_mb = alvo.stat().st_size / (1024 * 1024)
        self.stdout.write(self.style.SUCCESS(f"Backup gerado: {alvo} ({tam_mb:.1f} MB)"))

        removidos = self._aplicar_retencao(destino, reter)
        if removidos:
            self.stdout.write(f"Retenção: {removidos} backup(s) antigo(s) removido(s) (> {reter} dias).")

    def _backup_sqlite(self, copia: Path) -> None:
        """Snapshot consistente do banco, mesmo com o sistema em uso.

        Usa a própria conexão do Django como origem (funciona tanto para o banco
        em arquivo de produção quanto para o banco de testes em memória).
        """
        connection.ensure_connection()
        dst = sqlite3.connect(str(copia))
        try:
            with dst:
                connection.connection.backup(dst)  # API atômica do SQLite
        finally:
            dst.close()

    def _contar_documentos(self) -> int:
        try:
            from cadastro.models import Documento

            return Documento.objects.count()
        except Exception:
            return -1

    def _aplicar_retencao(self, pasta: Path, dias: int) -> int:
        if dias <= 0:
            return 0
        limite = datetime.now() - timedelta(days=dias)
        removidos = 0
        for arq in pasta.glob(f"{PREFIXO}*.zip"):
            if datetime.fromtimestamp(arq.stat().st_mtime) < limite:
                arq.unlink()
                removidos += 1
        return removidos
