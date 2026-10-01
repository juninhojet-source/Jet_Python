"""Popula a frota padrão da Garagem (baseada no modelo de mapa de viagem)."""
from django.core.management.base import BaseCommand

from apps.veiculos.models import TipoVeiculo, Veiculo

FROTA = (
    [(f"CARRO {n}", TipoVeiculo.UTILITARIO) for n in range(1, 18)]
    + [(f"INTERNO {n}", TipoVeiculo.UTILITARIO) for n in (2, 3)]
    + [(f"AMBULÂNCIA {n}", TipoVeiculo.AMBULANCIA) for n in range(1, 10)]
    + [("MICRO ITABIRA", TipoVeiculo.MICRO)]
    + [("VAN ITABIRA", TipoVeiculo.VAN), ("VAN BH", TipoVeiculo.VAN)]
)


class Command(BaseCommand):
    help = "Cadastra a frota padrão da Garagem (carros, ambulâncias, micro e vans)."

    def handle(self, *args, **options):
        criados = 0
        for nome, tipo in FROTA:
            _, created = Veiculo.objects.get_or_create(nome=nome, defaults={"tipo": tipo})
            criados += int(created)
        self.stdout.write(
            self.style.SUCCESS(f"Veículos: {criados} novo(s), {len(FROTA)} no total.")
        )
