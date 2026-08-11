"""Views de cadastro e consulta de destinos."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.accounts.mixins import EditorRequiredMixin
from apps.core.mixins import SalvarAutorMixin

from .forms import DestinoForm
from .models import Destino


class DestinoListView(LoginRequiredMixin, ListView):
    model = Destino
    template_name = "destinos/destino_list.html"
    context_object_name = "destinos"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("municipio")
        termo = self.request.GET.get("q", "").strip()
        if termo:
            qs = qs.filter(Q(nome__icontains=termo) | Q(municipio__nome__icontains=termo))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class DestinoCreateView(EditorRequiredMixin, SalvarAutorMixin, CreateView):
    model = Destino
    form_class = DestinoForm
    template_name = "destinos/destino_form.html"
    success_url = reverse_lazy("destinos:list")

    def form_valid(self, form):
        messages.success(self.request, "Destino cadastrado com sucesso.")
        return super().form_valid(form)


class DestinoUpdateView(EditorRequiredMixin, SalvarAutorMixin, UpdateView):
    model = Destino
    form_class = DestinoForm
    template_name = "destinos/destino_form.html"
    success_url = reverse_lazy("destinos:list")

    def form_valid(self, form):
        messages.success(self.request, "Destino atualizado com sucesso.")
        return super().form_valid(form)


class DestinoQuickCreateView(EditorRequiredMixin, View):
    """Cadastro rápido de destino (via modal do agendamento). Retorna JSON."""

    def post(self, request):
        from django.http import JsonResponse
        form = DestinoForm(request.POST)
        if form.is_valid():
            destino = form.save(commit=False)
            destino.criado_por = request.user
            destino.atualizado_por = request.user
            destino.save()
            return JsonResponse({"ok": True, "id": destino.pk, "texto": destino.nome})
        return JsonResponse({"ok": False, "errors": form.errors.get_json_data()}, status=400)
