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
from .models import fila_config, tipos_ordenados


def _sala_label():
    return settings.SIGTRANS.get("SENHA_SALA_LABEL", "Sala")


def _tipo_valido(tipo, padrao=None):
    tipos = tipos_ordenados()
    if tipo in tipos:
        return tipo
    return padrao or settings.SIGTRANS.get("SENHA_FILA_PADRAO", tipos[0] if tipos else "TRANSPORTE")


def _filas_menu(tipo_atual=None):
    """Lista das filas para navegação (tipo, nome, sala, ativa)."""
    itens = []
    for t in tipos_ordenados():
        cfg = fila_config(t)
        itens.append({
            "tipo": t, "nome": cfg.get("nome", t), "sala": cfg.get("sala"),
            "ativa": t == tipo_atual,
        })
    return itens


def _fila_dict(e):
    atual = e["atual"]
    return {
        "tipo": e["tipo"],
        "nome": e["nome"],
        "sala": e["sala"],
        "sequencia": e["painel"].sequencia,
        "aguardando": e["aguardando"],
        "atual": {"codigo": atual.codigo, "guiche": atual.guiche} if atual else None,
        "ultimas": [{"codigo": s.codigo, "guiche": s.guiche} for s in e["ultimas"]],
    }


class OperadorView(EditorRequiredMixin, View):
    """Painel de controle usado pela atendente de uma sala."""

    def get(self, request):
        tipo = _tipo_valido(request.GET.get("fila"))
        ctx = services.estado(tipo)
        ctx["sala_label"] = _sala_label()
        ctx["fila"] = tipo
        ctx["filas_menu"] = _filas_menu(tipo)
        return render(request, "senhas/operador.html", ctx)

    def post(self, request):
        tipo = _tipo_valido(request.POST.get("fila"))
        acao = request.POST.get("acao")
        if acao == "emitir":
            services.emitir_senha(tipo)
        elif acao == "chamar":
            services.chamar_proximo(tipo)
        elif acao == "repetir":
            services.repetir(tipo)
        elif acao == "voltar":
            services.navegar(tipo, -1)
        elif acao == "avancar":
            services.navegar(tipo, +1)
        elif acao == "finalizar":
            services.finalizar_atual(tipo)
        return redirect(reverse("senhas:operador") + f"?fila={tipo}")


class PainelTVView(View):
    """Exibição pública para a TV da recepção (todas as salas)."""

    def get(self, request):
        return render(request, "senhas/painel_tv.html", {"sala_label": _sala_label()})


class EstadoJSONView(View):
    """Estado de todas as filas para atualização em tempo real (polling)."""

    def get(self, request):
        filas = [_fila_dict(e) for e in services.estado_todas()]
        return JsonResponse({
            "sala_label": _sala_label(),
            "seq_total": sum(f["sequencia"] for f in filas),
            "filas": filas,
        })


class KioskView(View):
    """Emissão de senha pelo próprio paciente (escolhe o serviço/fila)."""

    def get(self, request):
        return render(request, "senhas/kiosk.html", {"filas": _filas_menu()})

    def post(self, request):
        tipo = _tipo_valido(request.POST.get("fila"))
        senha = services.emitir_senha(tipo)
        ctx = {
            "filas": _filas_menu(),
            "emitida": senha,
            "fila_nome": fila_config(tipo).get("nome", tipo),
            "sala_label": _sala_label(),
            "sala": fila_config(tipo).get("sala"),
            "agora": timezone.now(),
        }
        return render(request, "senhas/kiosk.html", ctx)
