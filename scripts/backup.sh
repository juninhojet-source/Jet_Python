#!/usr/bin/env bash
# Backup criptografado do sistema MCMV: dump do PostgreSQL + documentos (MEDIA),
# cifrados com GPG (chave pública do destinatário). Rode via cron diariamente.
#
# Requisitos: pg_dump, tar, gpg. Variáveis (ver .env.example):
#   POSTGRES_DB, POSTGRES_USER, POSTGRES_HOST, POSTGRES_PORT, PGPASSWORD
#   MCMV_MEDIA_ROOT, BACKUP_DIR, BACKUP_GPG_RECIPIENT
set -euo pipefail

: "${BACKUP_DIR:?defina BACKUP_DIR}"
: "${BACKUP_GPG_RECIPIENT:?defina BACKUP_GPG_RECIPIENT}"
: "${POSTGRES_DB:?defina POSTGRES_DB}"

STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 1) Banco de dados → .sql.gz → .gpg
pg_dump \
  --host="${POSTGRES_HOST:-localhost}" \
  --port="${POSTGRES_PORT:-5432}" \
  --username="${POSTGRES_USER:-mcmv}" \
  "$POSTGRES_DB" \
  | gzip \
  | gpg --batch --yes --encrypt --recipient "$BACKUP_GPG_RECIPIENT" \
        --output "$BACKUP_DIR/db-$STAMP.sql.gz.gpg"

# 2) Documentos (MEDIA) → .tar.gz → .gpg
if [ -n "${MCMV_MEDIA_ROOT:-}" ] && [ -d "$MCMV_MEDIA_ROOT" ]; then
  tar -czf - -C "$MCMV_MEDIA_ROOT" . \
    | gpg --batch --yes --encrypt --recipient "$BACKUP_GPG_RECIPIENT" \
          --output "$BACKUP_DIR/media-$STAMP.tar.gz.gpg"
fi

# 3) Retenção: mantém os últimos 30 arquivos de cada tipo.
ls -1t "$BACKUP_DIR"/db-*.sql.gz.gpg 2>/dev/null   | tail -n +31 | xargs -r rm -f
ls -1t "$BACKUP_DIR"/media-*.tar.gz.gpg 2>/dev/null | tail -n +31 | xargs -r rm -f

echo "Backup concluído: $BACKUP_DIR (db-$STAMP, media-$STAMP)"
