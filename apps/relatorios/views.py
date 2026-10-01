"""Relatórios e consultas (Fase 4)."""
from datetime import date, datetime, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from apps.agendamentos.models import Agendamento, StatusAgendamento
from apps.auditoria.services import Acao, registrar
from apps.core.models import Municipio
from apps.destinos.models import Destino
from apps.veiculos.models import Veiculo

from .exports import exportar_pdf, exportar_xlsx
from .filtros import filtrar
from .mapa import agrupar_por_veiculo, gerar_mapa_pdf_periodo, gerar_mapa_xlsx_periodo


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
    "Município", "Destino", "Procedimento", "KM", "Status", "Embarque",
]


def _linhas_agend(qs):
    for a in qs:
        yield [
            a.numero, a.data.strftime("%d/%m/%Y"), a.horario.strftime("%H:%M"),
            a.paciente.nome, a.paciente.cpf or "", a.paciente.cns or "",
            str(a.destino.municipio), a.destino.nome, a.procedimento,
            a.km_rodado if a.km_rodado is not None else "",
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
            "veiculos": Veiculo.objects.filter(ativo=True),
            "status_choices": StatusAgendamento.choices, "params": request.GET,
        }
        return render(request, self.template_name, ctx)


# --------------------------------------------------------------------------- BPA
COLUNAS_BPA = [
    "Paciente", "CNS", "CPF", "Sexo", "Nascimento", "Raça/Cor",
    "Município", "IBGE", "Bairro", "Data atend.", "Procedimento",
    "Cidade destino", "Acompanhante", "CPF acompanhante",
]


def _linhas_bpa(qs):
    for a in qs:
        p = a.paciente
        mun = p.municipio or a.destino.municipio
        cidade_destino = a.destino.municipio.nome if a.destino.municipio_id else ""
        yield [
            p.nome, p.cns or "", p.cpf or "", p.get_sexo_display(),
            p.data_nascimento.strftime("%d/%m/%Y"), p.get_raca_cor_display(),
            str(mun) if mun else "", mun.codigo_ibge if mun else "", p.bairro,
            a.data.strftime("%d/%m/%Y"), a.procedimento,
            cidade_destino, a.acompanhante, a.acompanhante_cpf or "",
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
            "veiculos": Veiculo.objects.filter(ativo=True),
            "params": request.GET,
        }
        return render(request, self.template_name, ctx)


# ---------------------------------------------------------------- Mapa de Viagem
class MapaViagemView(LoginRequiredMixin, View):
    """Mapa da Garagem: agendamentos agrupados por veículo, um dia ou um período.

    Período: cada dia sai separado (uma aba no Excel, uma página no PDF).
    """

    template_name = "relatorios/mapa_viagem.html"
    MAX_DIAS = 31  # limite do período, para não gerar arquivos gigantes

    @staticmethod
    def _data(texto):
        try:
            return datetime.strptime((texto or "").strip(), "%Y-%m-%d").date()
        except ValueError:
            return None

    def _periodo(self, request):
        """(início, fim, limitado). Aceita também o parâmetro antigo `data`."""
        ini = self._data(request.GET.get("data_inicio")) or self._data(request.GET.get("data"))
        fim = self._data(request.GET.get("data_fim"))
        ini = ini or fim or timezone.localdate()
        fim = fim or ini
        if fim < ini:
            ini, fim = fim, ini
        limitado = (fim - ini).days >= self.MAX_DIAS
        if limitado:
            fim = ini + timedelta(days=self.MAX_DIAS - 1)
        return ini, fim, limitado

    def get(self, request):
        ini, fim, limitado = self._periodo(request)
        periodo = fim != ini
        motorista = request.GET.get("motorista", "").strip()
        qs = (
            Agendamento.objects.filter(data__range=(ini, fim))
            .exclude(status=StatusAgendamento.CANCELADO)
            .select_related("paciente", "paciente__municipio", "destino",
                            "destino__municipio", "veiculo")
            .order_by("data", "horario")
        )

        # Filtros com seleção múltipla (vários municípios e/ou veículos).
        municipios_sel = [x for x in request.GET.getlist("municipio") if x.isdigit()]
        if municipios_sel:
            qs = qs.filter(destino__municipio_id__in=[int(x) for x in municipios_sel])

        raw_veiculos = request.GET.getlist("veiculo")
        veiculos_sel = [x for x in raw_veiculos if x.isdigit()]
        sem_veiculo = "sem" in raw_veiculos  # opção "A definir / sem veículo"
        condicoes = []
        if veiculos_sel:
            escolhidos = list(Veiculo.objects.filter(pk__in=[int(x) for x in veiculos_sel]))
            if escolhidos:
                # Pega o vínculo por cadastro (FK) e o nome no texto (tipo_veiculo).
                c = Q(veiculo_id__in=[v.id for v in escolhidos])
                for v in escolhidos:
                    c |= Q(tipo_veiculo__iexact=v.nome)
                condicoes.append(c)
        if sem_veiculo:
            # "A DEFINIR": sem veículo do cadastro e sem nome no texto.
            condicoes.append(
                Q(veiculo__isnull=True) & (Q(tipo_veiculo="") | Q(tipo_veiculo__regex=r"^\s+$"))
            )
        if condicoes:
            cond = condicoes[0]
            for c in condicoes[1:]:
                cond |= c
            qs = qs.filter(cond)

        # Um mapa por dia (só os dias que têm agendamento).
        por_data = {}
        for a in qs:
            por_data.setdefault(a.data, []).append(a)
        dias = [(d, agrupar_por_veiculo(lista)) for d, lista in sorted(por_data.items())]

        if periodo:
            rotulo = f"{ini:%d/%m/%Y} a {fim:%d/%m/%Y}"
            sufixo = f"{ini:%Y%m%d}_a_{fim:%Y%m%d}"
        else:
            rotulo, sufixo = f"{ini:%d/%m/%Y}", f"{ini:%Y%m%d}"

        export = request.GET.get("export")
        if export in ("xlsx", "pdf"):
            # Sem agendamentos: gera a folha do 1º dia com o aviso "nenhum".
            para_exportar = dias or [(ini, [])]
            if export == "xlsx":
                return _resposta_arquivo(
                    gerar_mapa_xlsx_periodo(para_exportar, motorista),
                    f"mapa_viagem_{sufixo}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    request=request, detalhe=f"Mapa de Viagem {rotulo} (Excel)",
                )
            return _resposta_arquivo(
                gerar_mapa_pdf_periodo(para_exportar, motorista),
                f"mapa_viagem_{sufixo}.pdf", "application/pdf",
                request=request, detalhe=f"Mapa de Viagem {rotulo} (PDF)",
            )

        dias_ctx = [
            {"dia": d, "grupos": g,
             "total": sum(1 for gr in g for lin in gr["linhas"] if not lin["ac"])}
            for d, g in dias
        ]
        ctx = {
            "ini": ini, "fim": fim, "periodo": periodo, "limitado": limitado,
            "max_dias": self.MAX_DIAS, "rotulo": rotulo,
            "motorista": motorista, "dias": dias_ctx,
            "total": sum(d["total"] for d in dias_ctx),
            "municipios": Municipio.objects.all(),
            "veiculos": Veiculo.objects.filter(ativo=True),
            "municipios_sel": municipios_sel,
            "veiculos_sel": veiculos_sel,
            "sem_veiculo_sel": sem_veiculo,
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
