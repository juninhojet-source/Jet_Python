"""Relatórios e consultas (Fase 4)."""
from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from apps.agendamentos.models import Agendamento, StatusAgendamento
from apps.auditoria.services import Acao, registrar
from apps.core.models import Municipio
from apps.destinos.models import Destino

from .exports import exportar_pdf, exportar_xlsx
from .filtros import filtrar


def _resposta_arquivo(conteudo, nome, tipo, request=None, detalhe=""):
    if request is not None:
        registrar(Acao.EXPORTACAO, detalhe=detalhe or nome, request=request)
    resp = HttpResponse(conteudo, content_type=tipo)
    resp["Content-Disposition"] = f'attachment; filename="{nome}"'
    return resp


class IndexView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, "relatorios/index.html", {})


# ------------------------------------------------------------------ Agendamentos
COLUNAS_AGEND = [
    "Nº", "Data", "Horário", "Paciente", "CPF", "CNS",
    "Município", "Destino", "Procedimento", "Status", "Embarque",
]


def _linhas_agend(qs):
    for a in qs:
        yield [
            a.numero, a.data.strftime("%d/%m/%Y"), a.horario.strftime("%H:%M"),
            a.paciente.nome, a.paciente.cpf or "", a.paciente.cns or "",
            str(a.destino.municipio), a.destino.nome, a.procedimento,
            a.get_status_display(), a.get_embarque_display(),
        ]


class AgendamentosView(LoginRequiredMixin, View):
    template_name = "relatorios/agendamentos.html"

    def get(self, request):
        qs, resumo = filtrar(request.GET, incluir_cancelados=True)
        export = request.GET.get("export")
        if export == "xlsx":
            dados = exportar_xlsx("Agendamentos", COLUNAS_AGEND, list(_linhas_agend(qs)))
            return _resposta_arquivo(
                dados, "agendamentos.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                request=request, detalhe="Relatório de Agendamentos (Excel)",
            )
        if export == "pdf":
            sub = " · ".join(f"{k}: {v}" for k, v in resumo) or "Todos os registros"
            dados = exportar_pdf("Relatório de Agendamentos", sub, COLUNAS_AGEND, list(_linhas_agend(qs)))
            return _resposta_arquivo(dados, "agendamentos.pdf", "application/pdf",
                                     request=request, detalhe="Relatório de Agendamentos (PDF)")

        ctx = {
            "agendamentos": qs[:300], "total": qs.count(), "resumo": resumo,
            "municipios": Municipio.objects.all(), "destinos": Destino.objects.filter(ativo=True),
            "status_choices": StatusAgendamento.choices, "params": request.GET,
        }
        return render(request, self.template_name, ctx)


# --------------------------------------------------------------------------- BPA
COLUNAS_BPA = [
    "Paciente", "CNS", "CPF", "Sexo", "Nascimento", "Raça/Cor",
    "Município", "IBGE", "Bairro", "Data atend.", "Procedimento", "Acompanhante",
]


def _linhas_bpa(qs):
    for a in qs:
        p = a.paciente
        mun = p.municipio or a.destino.municipio
        yield [
            p.nome, p.cns or "", p.cpf or "", p.get_sexo_display(),
            p.data_nascimento.strftime("%d/%m/%Y"), p.get_raca_cor_display(),
            str(mun) if mun else "", mun.codigo_ibge if mun else "", p.bairro,
            a.data.strftime("%d/%m/%Y"), a.procedimento, a.acompanhante,
        ]


class BPAView(LoginRequiredMixin, View):
    template_name = "relatorios/bpa.html"

    def get(self, request):
        qs, resumo = filtrar(request.GET, incluir_cancelados=False)
        export = request.GET.get("export")
        if export == "xlsx":
            dados = exportar_xlsx("BPA", COLUNAS_BPA, list(_linhas_bpa(qs)))
            return _resposta_arquivo(
                dados, "relatorio_bpa.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                request=request, detalhe="Relatório BPA (Excel)",
            )
        if export == "pdf":
            sub = " · ".join(f"{k}: {v}" for k, v in resumo) or "Todos os registros"
            dados = exportar_pdf("Relatório para o BPA", sub, COLUNAS_BPA, list(_linhas_bpa(qs)))
            return _resposta_arquivo(dados, "relatorio_bpa.pdf", "application/pdf",
                                     request=request, detalhe="Relatório BPA (PDF)")

        ctx = {
            "agendamentos": qs[:300], "total": qs.count(), "resumo": resumo,
            "municipios": Municipio.objects.all(), "destinos": Destino.objects.filter(ativo=True),
            "params": request.GET,
        }
        return render(request, self.template_name, ctx)


# ------------------------------------------------------------------- Indicadores
class IndicadoresView(LoginRequiredMixin, View):
    def get(self, request):
        hoje = timezone.localdate()
        base = Agendamento.objects.exclude(status=StatusAgendamento.CANCELADO)
        mes = base.filter(data__year=hoje.year, data__month=hoje.month)
        ctx = {
            "hoje": hoje,
            "total_dia": base.filter(data=hoje).count(),
            "total_mes": mes.count(),
            "faltas_mes": Agendamento.objects.filter(
                data__year=hoje.year, data__month=hoje.month, status=StatusAgendamento.FALTOU
            ).count(),
            "por_municipio": (
                mes.values("destino__municipio__nome")
                .annotate(t=Count("id")).order_by("-t")[:10]
            ),
            "por_destino": (
                mes.values("destino__nome").annotate(t=Count("id")).order_by("-t")[:10]
            ),
            "por_status": [
                {"status": dict(StatusAgendamento.choices).get(r["status"], r["status"]), "t": r["t"]}
                for r in mes.values("status").annotate(t=Count("id")).order_by("-t")
            ],
        }
        return render(request, "relatorios/indicadores.html", ctx)
