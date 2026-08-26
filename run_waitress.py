"""Servidor WSGI para Windows (Waitress).

Uso (com o virtualenv ativo e as variáveis de ambiente/.env definidas):

    python run_waitress.py

Antes de servir, prepara o ambiente automaticamente: aplica as migrações do
banco e coleta os estáticos (idempotente). Isso evita erros após um ``git pull``
quando se esquece de rodar ``migrate``/``collectstatic`` — útil quando o sistema
sobe como serviço do Windows. Para pular esse preparo, defina MCMV_SKIP_PREPARE=1.

Host/porta/threads podem ser ajustados por variáveis de ambiente:
    MCMV_HOST (padrão 0.0.0.0), MCMV_PORT (padrão 8000), MCMV_THREADS (padrão 8)
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402
from waitress import serve  # noqa: E402


def preparar() -> None:
    """Aplica migrações e coleta estáticos antes de servir (idempotente)."""
    if os.environ.get("MCMV_SKIP_PREPARE") == "1":
        return
    from django.core.management import call_command

    try:
        call_command("migrate", interactive=False, verbosity=1)
    except Exception as exc:  # nunca serve com o schema desatualizado sem avisar
        print(f"[run_waitress] AVISO: falha ao migrar o banco: {exc}")
    try:
        call_command("collectstatic", interactive=False, verbosity=0)
    except Exception as exc:  # estático faltante não deve impedir o start
        print(f"[run_waitress] AVISO: falha no collectstatic: {exc}")


def main() -> None:
    django.setup()
    preparar()
    host = os.environ.get("MCMV_HOST", "0.0.0.0")
    port = int(os.environ.get("MCMV_PORT", "8000"))
    threads = int(os.environ.get("MCMV_THREADS", "8"))
    print(f"Servindo MCMV em http://{host}:{port} (threads={threads})")

    from config.wsgi import application

    opcoes = {"host": host, "port": port, "threads": threads}

    # Atrás de um proxy reverso (IIS/nginx), confia nos cabeçalhos X-Forwarded-*
    # vindos do proxy local. Sem isto, o Waitress 2.x DESCARTA o X-Forwarded-Proto
    # (clear_untrusted_proxy_headers=True por padrão) e o Django nunca sabe que a
    # requisição chegou por HTTPS -> entra em loop de redirect (301). Configurável
    # por MCMV_TRUSTED_PROXY (vazio desativa; padrão 127.0.0.1).
    proxy = os.environ.get("MCMV_TRUSTED_PROXY", "127.0.0.1").strip()
    if proxy:
        opcoes["trusted_proxy"] = proxy
        opcoes["trusted_proxy_headers"] = {
            "x-forwarded-for",
            "x-forwarded-proto",
            "x-forwarded-host",
        }
        opcoes["clear_untrusted_proxy_headers"] = True

    serve(application, **opcoes)


if __name__ == "__main__":
    main()
