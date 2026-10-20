#!/usr/bin/env bash
# Restauração a partir de um backup criptografado (.gpg gerado por backup.sh).
# Requer a chave privada GPG correspondente importada no servidor.
#
# Uso:
#   scripts/restore.sh db-20260901-030000.sql.gz.gpg
#   scripts/restore.sh media-20260901-030000.tar.gz.gpg
set -euo pipefail

ARQ="${1:?informe o arquivo .gpg a restaurar}"
: "${POSTGRES_DB:?defina POSTGRES_DB}"

case "$ARQ" in
  *.sql.gz.gpg)
    echo "Restaurando banco $POSTGRES_DB a partir de $ARQ ..."
    gpg --batch --yes --decrypt "$ARQ" | gunzip \
      | psql --host="${POSTGRES_HOST:-localhost}" --port="${POSTGRES_PORT:-5432}" \
             --username="${POSTGRES_USER:-mcmv}" "$POSTGRES_DB"
    ;;
  *.tar.gz.gpg)
    : "${MCMV_MEDIA_ROOT:?defina MCMV_MEDIA_ROOT}"
    echo "Restaurando documentos em $MCMV_MEDIA_ROOT a partir de $ARQ ..."
    mkdir -p "$MCMV_MEDIA_ROOT"
    gpg --batch --yes --decrypt "$ARQ" | tar -xzf - -C "$MCMV_MEDIA_ROOT"
    ;;
  *)
    echo "Tipo de arquivo não reconhecido: $ARQ" >&2
    exit 1
    ;;
esac
echo "Restauração concluída."
