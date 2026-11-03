"""Libera um CPF preso por uma Pessoa "órfã" (sem vínculo com inscrição/núcleo).

Quando uma inscrição é excluída, o requerente/integrantes que ficam sem nenhum
vínculo são removidos automaticamente. Se, por algum motivo, uma Pessoa ficou
para trás segurando o CPF (impedindo um novo cadastro), este comando a remove —
de forma segura, apenas quando ela não estiver vinculada a nenhuma inscrição.

Uso:
    python manage.py liberar_cpf 15145092610
    python manage.py liberar_cpf 151.450.926-10
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from cadastro.models import Pessoa
from cadastro.validadores import so_digitos


class Command(BaseCommand):
    help = "Remove a Pessoa órfã de um CPF (sem vínculo), liberando-o para novo cadastro."

    def add_arguments(self, parser):
        parser.add_argument("cpf", help="CPF a liberar (com ou sem máscara).")

    def handle(self, *args, **opts):
        cpf = so_digitos(opts["cpf"])
        p = Pessoa.objects.filter(cpf=cpf).first()
        if not p:
            raise CommandError(f"Nenhuma pessoa encontrada com o CPF {cpf}.")

        tem_participacao = p.participacoes.exists()
        eh_requerente = p.inscricoes_como_requerente.exists()
        if tem_participacao or eh_requerente:
            raise CommandError(
                f"O CPF {cpf} ({p.nome}) ainda está vinculado a uma inscrição/núcleo. "
                "Exclua a inscrição correspondente primeiro; o CPF é liberado "
                "automaticamente na exclusão."
            )

        nome = p.nome
        p.delete()
        self.stdout.write(self.style.SUCCESS(
            f"CPF {cpf} ({nome}) liberado. Já é possível cadastrá-lo novamente."
        ))
