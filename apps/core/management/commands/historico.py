"""Diagnóstico do histórico (django-simple-history): exclusões e alterações.

Somente leitura — não altera nada. Mostra o que foi criado/alterado/excluído
em veículos e agendamentos, com data/hora e usuário responsável.

Uso: python manage.py historico [--dias 60]
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.agendamentos.models import Agendamento
from apps.veiculos.models import Veiculo

TIPO = {"+": "criado", "~": "alterado", "-": "EXCLUIDO"}


def _quem(h):
    u = getattr(h, "history_user", None)
    return u.get_username() if u else "?"


class Command(BaseCommand):
    help = "Mostra o historico recente de veiculos e agendamentos (so leitura)."

    def add_arguments(self, parser):
        parser.add_argument("--dias", type=int, default=60)

    def handle(self, *args, **options):
        limite = timezone.now() - timedelta(days=options["dias"])
        dias = options["dias"]

        self.stdout.write(f"===== VEICULOS - historico dos ultimos {dias} dias =====")
        vh = Veiculo.history.filter(history_date__gte=limite).order_by("history_date")
        if not vh:
            self.stdout.write("(nenhuma alteracao registrada)")
        for h in vh:
            self.stdout.write(
                f"{h.history_date:%d/%m/%Y %H:%M} | {TIPO.get(h.history_type, h.history_type):9} "
                f"| id={h.id} | nome={h.nome!r} | por {_quem(h)}"
            )

        self.stdout.write("")
        self.stdout.write(f"===== AGENDAMENTOS EXCLUIDOS - ultimos {dias} dias =====")
        dels = Agendamento.history.filter(
            history_type="-", history_date__gte=limite
        ).order_by("history_date")
        n = 0
        for h in dels:
            n += 1
            self.stdout.write(
                f"{h.history_date:%d/%m/%Y %H:%M} | agendamento #{h.id} "
                f"| {h.data} {h.horario} | paciente_id={h.paciente_id} "
                f"| destino_id={h.destino_id} | veiculo_id={h.veiculo_id} | por {_quem(h)}"
            )

        self.stdout.write("")
        self.stdout.write("===== RESUMO =====")
        self.stdout.write(f"Agendamentos EXCLUIDOS no periodo : {n}")
        self.stdout.write(f"Agendamentos existentes agora     : {Agendamento.objects.count()}")
        self.stdout.write(f"Veiculos existentes agora          : {Veiculo.objects.count()}")
        veic_excluidos = Veiculo.history.filter(
            history_type="-", history_date__gte=limite
        ).count()
        self.stdout.write(f"Veiculos EXCLUIDOS no periodo      : {veic_excluidos}")
