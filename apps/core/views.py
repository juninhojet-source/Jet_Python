"""Views do núcleo: dashboard inicial."""
from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.agendamentos.models import Agendamento, StatusAgendamento
from apps.destinos.models import Destino
from apps.pacientes.models import Paciente


@login_required
def dashboard(request):
    hoje = date.today()
    agenda_hoje = (
        Agendamento.objects.filter(data=hoje)
        .exclude(status=StatusAgendamento.CANCELADO)
        .select_related("paciente", "destino")
        .order_by("horario")
    )
    contexto = {
        "hoje": hoje,
        "total_pacientes": Paciente.objects.filter(ativo=True).count(),
        "total_destinos": Destino.objects.filter(ativo=True).count(),
        "total_agenda_hoje": agenda_hoje.count(),
        "agenda_hoje": agenda_hoje[:8],
    }
    return render(request, "core/dashboard.html", contexto)
