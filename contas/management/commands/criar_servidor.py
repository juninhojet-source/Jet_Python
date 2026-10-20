"""Cria um usuário servidor e atribui um perfil (Grupo).

Uso:
    python manage.py criar_servidor joao --perfil Analista --senha segredo
"""

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError

from contas.perfis import NOMES_PERFIS


class Command(BaseCommand):
    help = "Cria um servidor e atribui um perfil de acesso."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--perfil", required=True, choices=NOMES_PERFIS)
        parser.add_argument("--senha", required=True)
        parser.add_argument("--email", default="")
        parser.add_argument(
            "--nome", default="",
            help="Nome completo do servidor (usado no comprovante de inscrição).",
        )

    def handle(self, *args, **opts):
        if User.objects.filter(username=opts["username"]).exists():
            raise CommandError("Já existe usuário com este login.")
        user = User.objects.create_user(
            opts["username"], email=opts["email"], password=opts["senha"], is_staff=True
        )
        nome = opts["nome"].strip()
        if nome:
            partes = nome.split()
            user.first_name = partes[0][:150]
            user.last_name = " ".join(partes[1:])[:150]
            user.save(update_fields=["first_name", "last_name"])
        user.groups.add(Group.objects.get(name=opts["perfil"]))
        self.stdout.write(
            self.style.SUCCESS(
                f"Servidor '{user.username}' criado com perfil {opts['perfil']}."
            )
        )
