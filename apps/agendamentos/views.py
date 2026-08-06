"""Views do núcleo operacional: agenda, agendamentos, embarque e cartão PDF."""
from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.accounts.mixins import EditorRequiredMixin
from apps.core.mixins import SalvarAutorMixin

from .forms import AgendamentoForm, EmbarqueForm
from .models import Agendamento, StatusAgendamento
from .pdf import gerar_cartao_embarque


def _parse_data(texto, padrao=None):
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return padrao


class AgendaDiaView(LoginRequiredMixin, ListView):
    """Lista do Dia: agendamentos de uma data, em ordem de horário."""

    template_name = "agendamentos/agenda_dia.html"
    context_object_name = "agendamentos"

    def get_dia(self):
        return _parse_data(self.request.GET.get("data"), date.today())

    def get_queryset(self):
        return (
            Agendamento.objects.filter(data=self.get_dia())
            .exclude(status=StatusAgendamento.CANCELADO)
            .select_related("paciente", "destino")
            .order_by("horario")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dia"] = self.get_dia()
        return ctx


class AgendamentoListView(LoginRequiredMixin, ListView):
    model = Agendamento
    template_name = "agendamentos/agendamento_list.html"
    context_object_name = "agendamentos"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("paciente", "destino")
        self.q = self.request.GET.get("q", "").strip()
        self.status = self.request.GET.get("status", "").strip()
        self.data = self.request.GET.get("data", "").strip()
        if self.q:
            qs = qs.filter(
                Q(paciente__nome__icontains=self.q) | Q(destino__nome__icontains=self.q)
            )
        if self.status:
            qs = qs.filter(status=self.status)
        dia = _parse_data(self.data)
        if dia:
            qs = qs.filter(data=dia)
        return qs.order_by("-data", "horario")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "q": self.q, "status_sel": self.status, "data_sel": self.data,
            "status_choices": StatusAgendamento.choices,
        })
        return ctx


class AgendamentoDetailView(LoginRequiredMixin, DetailView):
    model = Agendamento
    template_name = "agendamentos/agendamento_detail.html"
    context_object_name = "ag"
    queryset = Agendamento.objects.select_related("paciente", "destino")


class AgendamentoCreateView(EditorRequiredMixin, SalvarAutorMixin, CreateView):
    model = Agendamento
    form_class = AgendamentoForm
    template_name = "agendamentos/agendamento_form.html"

    def get_initial(self):
        inicial = super().get_initial()
        dia = _parse_data(self.request.GET.get("data"))
        if dia:
            inicial["data"] = dia
        return inicial

    def form_valid(self, form):
        messages.success(self.request, "Agendamento criado com sucesso.")
        return super().form_valid(form)


class AgendamentoUpdateView(EditorRequiredMixin, SalvarAutorMixin, UpdateView):
    model = Agendamento
    form_class = AgendamentoForm
    template_name = "agendamentos/agendamento_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Agendamento atualizado com sucesso.")
        return super().form_valid(form)


class ConfirmarAgendamentoView(EditorRequiredMixin, View):
    """Registra a confirmação da viagem (contato no dia anterior)."""

    def post(self, request, pk):
        ag = get_object_or_404(Agendamento, pk=pk)
        ag.confirmado_em = timezone.now()
        if ag.status == StatusAgendamento.AGENDADO:
            ag.status = StatusAgendamento.CONFIRMADO
        ag.atualizado_por = request.user
        ag.save()
        messages.success(request, f"Agendamento {ag.numero} confirmado.")
        return redirect(request.META.get("HTTP_REFERER", ag.get_absolute_url()))


class EmbarqueUpdateView(EditorRequiredMixin, SalvarAutorMixin, UpdateView):
    model = Agendamento
    form_class = EmbarqueForm
    template_name = "agendamentos/embarque_form.html"
    context_object_name = "ag"

    def form_valid(self, form):
        messages.success(self.request, "Embarque registrado.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("agendamentos:agenda") + f"?data={self.object.data:%Y-%m-%d}"


class CartaoEmbarquePDFView(LoginRequiredMixin, View):
    def get(self, request, pk):
        ag = get_object_or_404(
            Agendamento.objects.select_related("paciente", "destino"), pk=pk
        )
        pdf = gerar_cartao_embarque(ag)
        from apps.auditoria.services import Acao, registrar
        registrar(Acao.IMPRESSAO, detalhe=f"Cartão de embarque {ag.numero}", request=request)
        resp = HttpResponse(pdf, content_type="application/pdf")
        resp["Content-Disposition"] = f'inline; filename="cartao_{ag.numero}.pdf"'
        return resp
