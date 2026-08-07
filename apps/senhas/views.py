"""Views do painel de senhas: controle (operador), painel de TV e kiosque."""
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from apps.accounts.mixins import EditorRequiredMixin

from . import services


def _sala_fixa():
    return settings.SIGTRANS.get("SENHA_SALA_FIXA")


def _estado_dict():
    e = services.estado()
    atual = e["atual"]
    return {
        "sequencia": e["painel"].sequencia,
        "sala_label": settings.SIGTRANS.get("SENHA_SALA_LABEL", "Sala"),
        "atual": (
            {"codigo": atual.codigo, "guiche": atual.guiche} if atual else None
        ),
        "aguardando": e["aguardando"],
        "ultimas": [
            {"codigo": s.codigo, "guiche": s.guiche} for s in e["ultimas"]
        ],
    }


class OperadorView(EditorRequiredMixin, View):
    """Painel de controle usado pela atendente."""

    def get(self, request):
        ctx = services.estado()
        fixa = _sala_fixa()
        ctx["sala_fixa"] = fixa
        ctx["sala_label"] = settings.SIGTRANS.get("SENHA_SALA_LABEL", "Sala")
        ctx["guiche"] = fixa if fixa else request.session.get("guiche", 1)
        return render(request, "senhas/operador.html", ctx)

    def post(self, request):
        acao = request.POST.get("acao")
        if acao == "emitir":
            services.emitir_senha()
        elif acao == "chamar":
            fixa = _sala_fixa()
            if fixa:
                guiche = int(fixa)
            else:
                guiche = int(request.POST.get("guiche") or request.session.get("guiche", 1))
                request.session["guiche"] = guiche
            services.chamar_proximo(guiche)
        elif acao == "repetir":
            services.repetir()
        elif acao == "voltar":
            services.navegar(-1)
        elif acao == "avancar":
            services.navegar(+1)
        elif acao == "finalizar":
            services.finalizar_atual()
        return redirect(reverse("senhas:operador"))


class PainelTVView(View):
    """Exibição pública para a TV da recepção (sem dados pessoais)."""

    def get(self, request):
        return render(request, "senhas/painel_tv.html", services.estado())


class EstadoJSONView(View):
    """Estado do painel para atualização em tempo real (polling)."""

    def get(self, request):
        return JsonResponse(_estado_dict())


class KioskView(View):
    """Emissão de senha pelo próprio paciente (autoatendimento)."""

    def get(self, request):
        return render(request, "senhas/kiosk.html", {})

    def post(self, request):
        senha = services.emitir_senha()
        return render(request, "senhas/kiosk.html", {"emitida": senha, "agora": timezone.now()})
