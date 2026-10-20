"""Backup e restauração manual (SQLite) — usados pela tela do Administrador.

- ``gerar_zip`` cria um .zip consistente com o banco (snapshot transacional do
  SQLite) + a mídia (documentos) + um manifesto.
- ``restaurar_zip`` valida e restaura um .zip de backup, sempre gravando antes
  uma cópia de segurança do estado atual.

Somente SQLite. Para PostgreSQL, usar pg_dump/pg_restore (docs/10-backup-restauracao.md).
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.db import connection

PREFIXO = "mcmv-backup-"
_SQLITE_MAGIC = b"SQLite format 3\x00"


def nome_backup(carimbo: str | None = None) -> str:
    carimbo = carimbo or datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{PREFIXO}{carimbo}.zip"


def snapshot_db(dst_path: Path) -> None:
    """Cópia CONSISTENTE do banco via API de backup do SQLite (não precisa parar
    o serviço; funciona também com o banco de testes)."""
    connection.ensure_connection()
    dst = sqlite3.connect(str(dst_path))
    try:
        with dst:
            connection.connection.backup(dst)  # API atômica do SQLite
    finally:
        dst.close()


def _contar_documentos() -> int:
    try:
        from cadastro.models import Documento

        return Documento.objects.count()
    except Exception:
        return -1


def gerar_zip(dst_zip: Path) -> Path:
    """Gera o .zip de backup (banco + mídia + manifesto) no caminho indicado."""
    dst_zip = Path(dst_zip)
    dst_zip.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        db_copia = tmp / "db.sqlite3"
        snapshot_db(db_copia)

        media_root = Path(settings.MEDIA_ROOT)
        manifesto = {
            "sistema": "MCMV — Cadastro Habitacional (Barão de Cocais/MG)",
            "gerado_em": datetime.now().isoformat(timespec="seconds"),
            "banco": "sqlite",
            "tamanho_db_bytes": db_copia.stat().st_size,
            "documentos_registrados": _contar_documentos(),
            "media_incluida": media_root.exists(),
        }
        with zipfile.ZipFile(dst_zip, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(db_copia, "db.sqlite3")
            z.writestr("manifesto.json", json.dumps(manifesto, ensure_ascii=False, indent=2))
            if media_root.exists():
                for arq in media_root.rglob("*"):
                    if arq.is_file():
                        z.write(arq, str(Path("media") / arq.relative_to(media_root)))
    return dst_zip


def _validar_sqlite(path: Path) -> None:
    """Confere se é um banco SQLite válido e compatível (tem a tabela principal)."""
    with open(path, "rb") as fh:
        if fh.read(16) != _SQLITE_MAGIC:
            raise ValueError("Arquivo de banco inválido (não é um banco SQLite).")
    con = sqlite3.connect(str(path))
    try:
        tabelas = {
            r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    finally:
        con.close()
    if "cadastro_inscricao" not in tabelas:
        raise ValueError(
            "Backup incompatível: não contém as tabelas do sistema MCMV."
        )


def restaurar_zip(fileobj) -> dict:
    """Restaura banco (e mídia) a partir de um .zip de backup.

    Antes de sobrescrever, grava uma cópia de segurança do estado atual em
    ``MCMV_BACKUP_DIR``. Retorna infos da operação.
    """
    if connection.vendor != "sqlite":
        raise ValueError(
            "Restauração automática disponível apenas para SQLite. "
            "Para PostgreSQL, use pg_restore."
        )
    db_path = Path(settings.DATABASES["default"]["NAME"])

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        up = tmp / "upload.zip"
        with open(up, "wb") as fh:
            for chunk in fileobj.chunks():
                fh.write(chunk)

        ext = tmp / "ext"
        ext.mkdir()
        try:
            with zipfile.ZipFile(up) as z:
                base = ext.resolve()
                for nome in z.namelist():
                    destino = (ext / nome).resolve()
                    if not str(destino).startswith(str(base)):
                        raise ValueError("Arquivo de backup inválido (caminho suspeito).")
                z.extractall(ext)
        except zipfile.BadZipFile:
            raise ValueError("O arquivo enviado não é um .zip de backup válido.")

        db_novo = ext / "db.sqlite3"
        if not db_novo.exists():
            raise ValueError("O backup não contém o banco (db.sqlite3).")
        _validar_sqlite(db_novo)

        # 1) Cópia de segurança do estado atual (antes de sobrescrever).
        seg_dir = Path(settings.MCMV_BACKUP_DIR)
        seg = seg_dir / f"pre-restauracao-{datetime.now():%Y%m%d-%H%M%S}.zip"
        gerar_zip(seg)

        # 2) Restaura o banco: origem (upload) -> destino ao vivo, via API do
        #    SQLite (segura quanto a travas de arquivo, inclusive no Windows).
        connection.close()
        src = sqlite3.connect(str(db_novo))
        dest = sqlite3.connect(str(db_path))
        try:
            with dest:
                src.backup(dest)
        finally:
            src.close()
            dest.close()

        # 3) Restaura a mídia (documentos), se presente no backup.
        restaurou_media = False
        media_zip = ext / "media"
        if media_zip.exists():
            media_root = Path(settings.MEDIA_ROOT)
            media_root.mkdir(parents=True, exist_ok=True)
            for arq in media_zip.rglob("*"):
                if arq.is_file():
                    alvo = media_root / arq.relative_to(media_zip)
                    alvo.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(arq, alvo)
            restaurou_media = True

    return {"copia_seguranca": str(seg), "media_restaurada": restaurou_media}
