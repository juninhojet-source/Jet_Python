"""Popula destinos frequentes (baseados no mapa de viagem da Garagem).

Cadastra os estabelecimentos de destino mais usados, cada um já vinculado à
sua cidade. Cria o município (por código IBGE) caso ainda não exista.
"""
from django.core.management.base import BaseCommand

from apps.core.models import Municipio
from apps.destinos.models import Destino, TipoDestino

H = TipoDestino.HOSPITAL
C = TipoDestino.CLINICA

# (nome do destino, tipo, nome da cidade, UF, código IBGE)
DESTINOS = [
    ("Hospital da Baleia", H, "Belo Horizonte", "MG", "3106200"),
    ("Hospital Luxemburgo", H, "Belo Horizonte", "MG", "3106200"),
    ("Hospital das Clínicas (UFMG)", H, "Belo Horizonte", "MG", "3106200"),
    ("Hospital Júlia Kubitschek", H, "Belo Horizonte", "MG", "3106200"),
    ("Hospital Belo Horizonte", H, "Belo Horizonte", "MG", "3106200"),
    ("Mater Dei Contorno", H, "Belo Horizonte", "MG", "3106200"),
    ("CEM - Centro de Especialidades Médicas", C, "Belo Horizonte", "MG", "3106200"),
    ("CEM IPSEMG", C, "Belo Horizonte", "MG", "3106200"),
    ("HMCC", H, "Itabira", "MG", "3131307"),
    ("Policlínica de Itabira", C, "Itabira", "MG", "3131307"),
    ("Clínica Nexoo", C, "Itabira", "MG", "3131307"),
    ("ELO / HNSD", C, "Itabira", "MG", "3131307"),
    ("CISCEL", C, "Itabira", "MG", "3131307"),
    ("Clínica DMX", C, "Itabira", "MG", "3131307"),
    ("Hospital São Sebastião", H, "Raul Soares", "MG", "3154150"),
]


class Command(BaseCommand):
    help = "Cadastra destinos frequentes (hospitais e clínicas de referência)."

    def handle(self, *args, **options):
        criados = 0
        for nome, tipo, cidade, uf, ibge in DESTINOS:
            municipio, _ = Municipio.objects.get_or_create(
                codigo_ibge=ibge, defaults={"nome": cidade, "uf": uf}
            )
            _, created = Destino.objects.get_or_create(
                nome=nome, municipio=municipio, defaults={"tipo": tipo}
            )
            criados += int(created)
        self.stdout.write(
            self.style.SUCCESS(f"Destinos: {criados} novo(s), {len(DESTINOS)} no total.")
        )
