"""Popula a tabela de municípios com destinos frequentes da região."""
from django.core.management.base import BaseCommand

from apps.core.models import Municipio

MUNICIPIOS = [
    ("3105002", "Barão de Cocais", "MG"),
    ("3131307", "Itabira", "MG"),
    ("3106200", "Belo Horizonte", "MG"),
    ("3122306", "Coronel Fabriciano", "MG"),
    ("3126109", "Governador Valadares", "MG"),
    ("3143906", "Nova Era", "MG"),
    ("3131703", "Itabirito", "MG"),
    ("3153608", "Santa Bárbara", "MG"),
    ("3164704", "São Gonçalo do Rio Abaixo", "MG"),
    ("3106705", "Betim", "MG"),
    ("3136702", "Juiz de Fora", "MG"),
    ("3170206", "Uberlândia", "MG"),
]


class Command(BaseCommand):
    help = "Cadastra municípios frequentes (código IBGE) usados nos destinos."

    def handle(self, *args, **options):
        criados = 0
        for codigo, nome, uf in MUNICIPIOS:
            _, created = Municipio.objects.get_or_create(
                codigo_ibge=codigo, defaults={"nome": nome, "uf": uf}
            )
            criados += int(created)
        self.stdout.write(
            self.style.SUCCESS(f"Municípios: {criados} novo(s), {len(MUNICIPIOS)} no total.")
        )
