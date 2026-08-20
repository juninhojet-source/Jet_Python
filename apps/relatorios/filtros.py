"""Construção dos filtros dos relatórios sobre os agendamentos."""
from datetime import datetime

from django.db.models import Q

from apps.agendamentos.models import Agendamento, StatusAgendamento


def _data(texto):
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _mes(texto):
    try:
        return datetime.strptime(texto, "%Y-%m").date()
    except (TypeError, ValueError):
        return None


def filtrar(params, incluir_cancelados=False):
    """Aplica os filtros da querystring e retorna (queryset, resumo)."""
    qs = Agendamento.objects.select_related(
        "paciente", "paciente__municipio", "destino", "destino__municipio"
    )
    resumo = []

    if not incluir_cancelados:
        qs = qs.exclude(status=StatusAgendamento.CANCELADO)

    dia = _data(params.get("dia", ""))
    if dia:
        qs = qs.filter(data=dia)
        resumo.append(("Dia", dia.strftime("%d/%m/%Y")))

    mes = _mes(params.get("mes", ""))
    if mes:
        qs = qs.filter(data__year=mes.year, data__month=mes.month)
        resumo.append(("Mês", mes.strftime("%m/%Y")))

    ini = _data(params.get("data_inicio", ""))
    fim = _data(params.get("data_fim", ""))
    if ini:
        qs = qs.filter(data__gte=ini)
        resumo.append(("De", ini.strftime("%d/%m/%Y")))
    if fim:
        qs = qs.filter(data__lte=fim)
        resumo.append(("Até", fim.strftime("%d/%m/%Y")))

    nome = params.get("q", "").strip()
    if nome:
        qs = qs.filter(paciente__nome__icontains=nome)
        resumo.append(("Nome", nome))

    municipio = params.get("municipio", "").strip()
    if municipio.isdigit():
        qs = qs.filter(destino__municipio_id=int(municipio))

    destino = params.get("destino", "").strip()
    if destino.isdigit():
        qs = qs.filter(destino_id=int(destino))

    procedimento = params.get("procedimento", "").strip()
    if procedimento:
        qs = qs.filter(procedimento__icontains=procedimento)
        resumo.append(("Procedimento", procedimento))

    status = params.get("status", "").strip()
    if status:
        qs = qs.filter(status=status)
        resumo.append(("Status", dict(StatusAgendamento.choices).get(status, status)))

    return qs.order_by("data", "horario"), resumo
