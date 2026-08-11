"""Views de cadastro e consulta de pacientes."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from django.http import JsonResponse
from django.views import View

from apps.accounts.mixins import EditorRequiredMixin
from apps.core.mixins import SalvarAutorMixin
from apps.core.validators import apenas_digitos

from .forms import PacienteForm, PacienteRapidoForm
from .models import Paciente


class PacienteListView(LoginRequiredMixin, ListView):
    model = Paciente
    template_name = "pacientes/paciente_list.html"
    context_object_name = "pacientes"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("municipio")
        termo = self.request.GET.get("q", "").strip()
        if termo:
            digitos = apenas_digitos(termo)
            filtro = Q(nome__icontains=termo) | Q(telefone_principal__icontains=termo)
            if digitos:
                filtro |= Q(cpf__icontains=digitos) | Q(cns__icontains=digitos)
            qs = qs.filter(filtro)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class PacienteDetailView(LoginRequiredMixin, DetailView):
    model = Paciente
    template_name = "pacientes/paciente_detail.html"
    context_object_name = "paciente"


class PacienteCreateView(EditorRequiredMixin, SalvarAutorMixin, CreateView):
    model = Paciente
    form_class = PacienteForm
    template_name = "pacientes/paciente_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Paciente cadastrado com sucesso.")
        return super().form_valid(form)


class PacienteUpdateView(EditorRequiredMixin, SalvarAutorMixin, UpdateView):
    model = Paciente
    form_class = PacienteForm
    template_name = "pacientes/paciente_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Cadastro atualizado com sucesso.")
        return super().form_valid(form)


class PacienteQuickCreateView(EditorRequiredMixin, View):
    """Cadastro rápido de paciente (via modal do agendamento). Retorna JSON."""

    def post(self, request):
        form = PacienteRapidoForm(request.POST)
        if form.is_valid():
            paciente = form.save(commit=False)
            paciente.criado_por = request.user
            paciente.atualizado_por = request.user
            paciente.save()
            return JsonResponse({"ok": True, "id": paciente.pk, "texto": str(paciente)})
        return JsonResponse({"ok": False, "errors": form.errors.get_json_data()}, status=400)
