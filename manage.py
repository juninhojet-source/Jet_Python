#!/usr/bin/env python
"""Utilitário de linha de comando do Django para o SIGTRANS Saúde."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Não foi possível importar o Django. Verifique se ele está instalado "
            "e disponível na variável PYTHONPATH, e se o ambiente virtual está ativo."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
