"""Views do núcleo: dashboard inicial."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.destinos.models import Destino
from apps.pacientes.models import Paciente


@login_required
def dashboard(request):
    contexto = {
        "total_pacientes": Paciente.objects.filter(ativo=True).count(),
        "total_destinos": Destino.objects.filter(ativo=True).count(),
        "ultimos_pacientes": Paciente.objects.order_by("-criado_em")[:8],
    }
    return render(request, "core/dashboard.html", contexto)
