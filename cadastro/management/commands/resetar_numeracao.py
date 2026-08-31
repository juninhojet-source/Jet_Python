"""Reinicia a numeração das inscrições (numero_inscricao) em 000001.

O número da inscrição deriva do id (chave primária) da tabela. Ao apagar as
inscrições, o contador de auto-incremento do banco NÃO é zerado — por isso a
numeração continua de onde parou. Este comando reinicia esse contador.

Por segurança, só reinicia quando NÃO há inscrições no banco (evita colisão de
números com registros existentes).

Uso:
    python manage.py resetar_numeracao
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from cadastro.models import Inscricao


class Command(BaseCommand):
    help = "Reinicia a numeração das inscrições em 000001 (somente com o banco sem inscrições)."

    def handle(self, *args, **opts):
        n = Inscricao.objects.count()
        if n:
            raise CommandError(
                f"Há {n} inscrição(ões) cadastrada(s). Exclua todas antes de "
                "reiniciar a numeração (o reinício com registros existentes "
                "causaria colisão de números)."
            )

        vendor = connection.vendor
        tabela = Inscricao._meta.db_table  # "cadastro_inscricao"
        with connection.cursor() as cur:
            if vendor == "sqlite":
                existe = cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'"
                ).fetchone()
                if existe:
                    cur.execute("DELETE FROM sqlite_sequence WHERE name=%s", [tabela])
            elif vendor == "postgresql":
                cur.execute(
                    f'ALTER SEQUENCE "{tabela}_id_seq" RESTART WITH 1'
                )
            else:
                raise CommandError(
                    f"Reinício automático não suportado para o banco '{vendor}'."
                )

        self.stdout.write(self.style.SUCCESS(
            "Numeração reiniciada. A próxima inscrição cadastrada será 000001."
        ))
