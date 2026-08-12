"""Views do núcleo: dashboard inicial e cadastros auxiliares."""
from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from apps.accounts.mixins import EditorRequiredMixin
from apps.agendamentos.models import Agendamento, StatusAgendamento
from apps.destinos.models import Destino
from apps.pacientes.models import Paciente

from .forms import MunicipioForm


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


class MunicipioQuickCreateView(EditorRequiredMixin, View):
    """Cadastro rápido de município (via modal). Retorna JSON."""

    def post(self, request):
        form = MunicipioForm(request.POST)
        if form.is_valid():
            municipio = form.save()
            return JsonResponse(
                {"ok": True, "id": municipio.pk, "texto": str(municipio)}
            )
        return JsonResponse(
            {"ok": False, "errors": form.errors.get_json_data()}, status=400
        )
