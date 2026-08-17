"""Gera o arquivo .env de produção do SIGTRANS Saúde.

Chamado pelos scripts do Windows (configurar-env.bat / iniciar-producao.bat).
Feito em Python para evitar problemas de aspas/escape no cmd do Windows.

- Cria SECRET_KEY aleatória, DEBUG=False, o domínio em ALLOWED_HOSTS/CSRF e
  cookies seguros. Mantém SQLite (não define POSTGRES_*), preservando os dados.
- Não sobrescreve um .env já existente (a menos que passe --force).
"""
import secrets
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

CONTEUDO = """\
# SIGTRANS Saude - configuracao de PRODUCAO (gerada automaticamente)
# NAO compartilhe este arquivo: a SECRET_KEY e sensivel.
SECRET_KEY={secret}
DEBUG=False
ALLOWED_HOSTS=sigtrans.baraodecocais.mg.gov.br,172.16.64.8,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://sigtrans.baraodecocais.mg.gov.br
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
ATRAS_DE_PROXY=True
"""


def main():
    forcar = "--force" in sys.argv
    if ENV_PATH.exists() and not forcar:
        print(f"O arquivo .env ja existe ({ENV_PATH}) - nada foi alterado.")
        print("Para refazer do zero, apague o .env e rode de novo.")
        return 0

    ENV_PATH.write_text(CONTEUDO.format(secret=secrets.token_urlsafe(64)), encoding="utf-8")
    print("[OK] Arquivo .env de producao criado.")
    print(f"     Local: {ENV_PATH}")
    print("     Banco de dados: SQLite (mantem os dados atuais).")
    print("     Para usar PostgreSQL, edite o .env conforme .env.example.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
