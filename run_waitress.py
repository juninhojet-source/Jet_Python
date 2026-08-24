"""Servidor WSGI para Windows (Waitress).

Uso (com o virtualenv ativo e as variáveis de ambiente/.env definidas):

    python run_waitress.py

Host/porta/threads podem ser ajustados por variáveis de ambiente:
    MCMV_HOST (padrão 0.0.0.0), MCMV_PORT (padrão 8000), MCMV_THREADS (padrão 8)
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from waitress import serve  # noqa: E402

from config.wsgi import application  # noqa: E402


def main() -> None:
    host = os.environ.get("MCMV_HOST", "0.0.0.0")
    port = int(os.environ.get("MCMV_PORT", "8000"))
    threads = int(os.environ.get("MCMV_THREADS", "8"))
    print(f"Servindo MCMV em http://{host}:{port} (threads={threads})")
    serve(application, host=host, port=port, threads=threads)


if __name__ == "__main__":
    main()
