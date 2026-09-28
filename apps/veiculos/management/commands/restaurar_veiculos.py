"""Restaura veiculos excluidos, a partir do historico (django-simple-history).

Recria cada veiculo que foi EXCLUIDO no periodo exatamente como estava
(mesmo id, nome, tipo, placa, ativo, observacoes), usando o snapshot que o
proprio sistema guardou no momento da exclusao. Nenhum agendamento e alterado
- eles continuam apontando (por texto) para o nome do carro.

Por seguranca, por padrao apenas MOSTRA o que seria restaurado (simulacao).
Para efetivar, use --confirmar.

Uso:
    python manage.py restaurar_veiculos            (simulacao, nao grava)
    python manage.py restaurar_veiculos --confirmar (restaura de verdade)
    python manage.py restaurar_veiculos --dias 30 --confirmar
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.veiculos.models import Veiculo

CAMPOS = ["nome", "tipo", "placa", "ativo", "observacoes"]


class Command(BaseCommand):
    help = "Restaura veiculos excluidos a partir do historico (simula por padrao)."

    def add_arguments(self, parser):
        parser.add_argument("--dias", type=int, default=90)
        parser.add_argument(
            "--confirmar",
            action="store_true",
            help="Efetiva a restauracao. Sem esta opcao, apenas simula.",
        )

    def handle(self, *args, **options):
        limite = timezone.now() - timedelta(days=options["dias"])
        confirmar = options["confirmar"]

        # Ultima exclusao registrada de cada veiculo (history_type "-") no periodo.
        exclusoes = (
            Veiculo.history.filter(history_type="-", history_date__gte=limite)
            .order_by("id", "-history_date")
        )

        vistos = set()
        a_restaurar = []
        for h in exclusoes:
            if h.id in vistos:
                continue
            vistos.add(h.id)
            a_restaurar.append(h)

        if not a_restaurar:
            self.stdout.write("Nenhum veiculo excluido no periodo. Nada a restaurar.")
            return

        self.stdout.write(
            f"{'RESTAURANDO' if confirmar else 'SIMULACAO (nada sera gravado)'}: "
            f"{len(a_restaurar)} veiculo(s) excluido(s) no periodo.\n"
        )

        restaurados, pulados = 0, 0
        with transaction.atomic():
            for h in a_restaurar:
                # Ja existe um veiculo com esse id? (ex.: recriado a mao)
                if Veiculo.objects.filter(pk=h.id).exists():
                    self.stdout.write(
                        f"  - PULADO id={h.id} nome={h.nome!r}: ja existe (mesmo id)."
                    )
                    pulados += 1
                    continue
                # Ja existe outro veiculo com o mesmo nome? (nome e unico)
                if Veiculo.objects.filter(nome=h.nome).exists():
                    self.stdout.write(
                        f"  - PULADO id={h.id} nome={h.nome!r}: ja existe outro "
                        f"veiculo com esse nome."
                    )
                    pulados += 1
                    continue

                dados = {c: getattr(h, c) for c in CAMPOS}
                if confirmar:
                    Veiculo.objects.create(pk=h.id, **dados)
                self.stdout.write(
                    f"  - {'RESTAURADO' if confirmar else 'restauraria'} "
                    f"id={h.id} nome={h.nome!r} tipo={h.tipo}"
                )
                restaurados += 1

            if not confirmar:
                transaction.set_rollback(True)

        self.stdout.write("")
        self.stdout.write("===== RESUMO =====")
        verbo = "Restaurados" if confirmar else "Seriam restaurados"
        self.stdout.write(f"{verbo}: {restaurados}")
        self.stdout.write(f"Pulados (ja existiam): {pulados}")
        if not confirmar:
            self.stdout.write(
                "\nNada foi gravado (simulacao). Para efetivar, rode de novo com "
                "--confirmar."
            )
        else:
            self.stdout.write(
                f"\nPronto. Veiculos existentes agora: {Veiculo.objects.count()}"
            )
