"""Cria (ou atualiza) um usuário administrador do SIGTRANS.

Uso:
    python manage.py criar_admin --username admin --nome "Aristides F. Junior"
A senha pode vir de --senha ou da variável de ambiente SIGTRANS_ADMIN_SENHA;
se nenhuma for informada, é solicitada interativamente.
"""
import getpass
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = "Cria ou atualiza um usuário administrador."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--nome", default="")
        parser.add_argument("--email", default="")
        parser.add_argument("--senha", default=None)

    def handle(self, *args, **options):
        username = options["username"]
        senha = options["senha"] or os.getenv("SIGTRANS_ADMIN_SENHA")
        if not senha:
            senha = getpass.getpass("Senha do administrador: ")
        if not senha or len(senha) < 8:
            raise CommandError("A senha deve ter ao menos 8 caracteres.")

        nome = options["nome"].strip()
        first, _, last = nome.partition(" ")
        user, created = User.objects.get_or_create(username=username)
        user.first_name = first
        user.last_name = last
        user.email = options["email"]
        user.perfil = "ADMIN"
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(senha)
        user.save()

        acao = "criado" if created else "atualizado"
        self.stdout.write(self.style.SUCCESS(f"Administrador '{username}' {acao} com sucesso."))
