"""Cria os Grupos de perfil de acesso."""

from django.db import migrations

from contas.perfis import PERFIS


def criar_perfis(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for nome, _descricao in PERFIS:
        Group.objects.get_or_create(name=nome)


def remover_perfis(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=[nome for nome, _ in PERFIS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(criar_perfis, remover_perfis),
    ]
