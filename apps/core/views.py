"""Views do núcleo: dashboard inicial, cadastros auxiliares e configurações."""
import gzip
import io
from datetime import date

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.mixins import AdminRequiredMixin, EditorRequiredMixin
from apps.agendamentos.models import Agendamento, StatusAgendamento
from apps.destinos.models import Destino
from apps.pacientes.models import Paciente

from .forms import MunicipioForm

# Apps não exportados no backup (recriados pelas migrações / sessão).
BACKUP_EXCLUIR = ["contenttypes", "auth.permission", "sessions.session", "admin.logentry"]


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


# ------------------------------------------------------------ Configurações
class ConfiguracoesView(AdminRequiredMixin, TemplateView):
    """Índice do menu de Configurações (somente administrador)."""

    template_name = "core/configuracoes.html"


class LGPDView(AdminRequiredMixin, TemplateView):
    """Informações sobre segurança da informação e LGPD."""

    template_name = "core/lgpd.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["idle_min"] = settings.IDLE_TIMEOUT_SECONDS // 60
        ctx["login_max"] = settings.LOGIN_MAX_TENTATIVAS
        return ctx


class BackupView(AdminRequiredMixin, View):
    """Backup do banco: página informativa (GET) e download (POST)."""

    template_name = "core/backup.html"

    def get(self, request):
        return render(request, self.template_name, {})

    def post(self, request):
        buffer = io.StringIO()
        call_command(
            "dumpdata",
            *[f"--exclude={e}" for e in BACKUP_EXCLUIR],
            natural_foreign=True,
            natural_primary=True,
            indent=2,
            stdout=buffer,
            verbosity=0,
        )
        conteudo = gzip.compress(buffer.getvalue().encode("utf-8"))
        nome = f"sigtrans_{timezone.now():%Y%m%d_%H%M%S}.json.gz"

        from apps.auditoria.services import Acao, registrar
        registrar(Acao.BACKUP, detalhe=f"{nome} ({len(conteudo)} bytes)", request=request)

        resp = HttpResponse(conteudo, content_type="application/gzip")
        resp["Content-Disposition"] = f'attachment; filename="{nome}"'
        return resp
