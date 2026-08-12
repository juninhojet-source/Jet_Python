"""Views de cadastro e consulta de veículos."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.accounts.mixins import EditorRequiredMixin
from apps.core.mixins import SalvarAutorMixin

from .forms import VeiculoForm
from .models import Veiculo


class VeiculoListView(LoginRequiredMixin, ListView):
    model = Veiculo
    template_name = "veiculos/veiculo_list.html"
    context_object_name = "veiculos"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        termo = self.request.GET.get("q", "").strip()
        if termo:
            qs = qs.filter(Q(nome__icontains=termo) | Q(placa__icontains=termo))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class VeiculoCreateView(EditorRequiredMixin, SalvarAutorMixin, CreateView):
    model = Veiculo
    form_class = VeiculoForm
    template_name = "veiculos/veiculo_form.html"
    success_url = reverse_lazy("veiculos:list")

    def form_valid(self, form):
        messages.success(self.request, "Veículo cadastrado com sucesso.")
        return super().form_valid(form)


class VeiculoUpdateView(EditorRequiredMixin, SalvarAutorMixin, UpdateView):
    model = Veiculo
    form_class = VeiculoForm
    template_name = "veiculos/veiculo_form.html"
    success_url = reverse_lazy("veiculos:list")

    def form_valid(self, form):
        messages.success(self.request, "Veículo atualizado com sucesso.")
        return super().form_valid(form)


class VeiculoQuickCreateView(EditorRequiredMixin, View):
    """Cadastro rápido de veículo (via modal do agendamento). Retorna JSON."""

    def post(self, request):
        form = VeiculoForm(request.POST)
        if form.is_valid():
            veiculo = form.save(commit=False)
            veiculo.criado_por = request.user
            veiculo.atualizado_por = request.user
            veiculo.save()
            return JsonResponse({"ok": True, "id": veiculo.pk, "texto": veiculo.nome})
        return JsonResponse({"ok": False, "errors": form.errors.get_json_data()}, status=400)
