"""Telas de operação dos servidores (Fase 3)."""

from __future__ import annotations

import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from . import requisitos, services
from .forms import (
    DocumentoForm,
    InscricaoAnaliseForm,
    MembroForm,
    RendaForm,
    RequerenteInscricaoForm,
)
from .models import Documento, Inscricao, MembroNucleo


def _bloqueio_guard(request, inscricao) -> bool:
    """Retorna True (e avisa) se a inscrição estiver bloqueada para edição."""
    if inscricao.bloqueada:
        messages.warning(
            request,
            "Inscrição finalizada e bloqueada (Anexo II). Alterações exigem "
            "procedimento administrativo autorizado.",
        )
        return True
    return False


@login_required
def dashboard(request):
    qs = Inscricao.objects.all()
    contagem = {s.value: 0 for s in Inscricao.Status}
    for linha in qs.values("status").annotate(n=Count("id")):
        contagem[linha["status"]] = linha["n"]
    linhas = [(rotulo, contagem[valor]) for valor, rotulo in Inscricao.Status.choices]
    ctx = {
        "total": qs.count(),
        "linhas": linhas,
        "com_deficiencia": qs.filter(membros__pessoa__pcd=True).distinct().count(),
        "com_risco": qs.filter(habitacao_precaria_ou_risco=True).count(),
    }
    return render(request, "cadastro/dashboard.html", ctx)


@login_required
def inscricao_list(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    inscricoes = Inscricao.objects.select_related("requerente")
    if q:
        inscricoes = inscricoes.filter(
            Q(numero_inscricao__icontains=q)
            | Q(requerente__nome__icontains=q)
            | Q(requerente__cpf__icontains=q)
        )
    if status:
        inscricoes = inscricoes.filter(status=status)
    ctx = {
        "inscricoes": inscricoes,
        "q": q,
        "status": status,
        "status_choices": Inscricao.Status.choices,
    }
    return render(request, "cadastro/inscricao_list.html", ctx)


@login_required
def inscricao_nova(request):
    if request.method == "POST":
        form = RequerenteInscricaoForm(request.POST)
        if form.is_valid():
            inscricao = form.salvar()
            messages.success(request, f"Inscrição {inscricao.numero_inscricao} criada.")
            return redirect("cadastro:inscricao_detalhe", pk=inscricao.pk)
    else:
        form = RequerenteInscricaoForm()
    return render(request, "cadastro/inscricao_form.html", {"form": form, "novo": True})


@login_required
def inscricao_detalhe(request, pk):
    inscricao = get_object_or_404(
        Inscricao.objects.select_related("requerente"), pk=pk
    )
    membros = inscricao.membros.select_related("pessoa").prefetch_related("rendas")
    itens_req = requisitos.avaliar(inscricao)
    ctx = {
        "inscricao": inscricao,
        "membros": membros,
        "documentos": inscricao.documentos.all(),
        "criterios_legais": inscricao.criterios_legais.all(),
        "complementar": getattr(inscricao, "criterio_complementar", None),
        "requisitos": itens_req,
        "apto": requisitos.apto(itens_req),
    }
    return render(request, "cadastro/inscricao_detalhe.html", ctx)


@login_required
def inscricao_editar(request, pk):
    inscricao = get_object_or_404(Inscricao, pk=pk)
    if _bloqueio_guard(request, inscricao):
        return redirect("cadastro:inscricao_detalhe", pk=pk)
    if request.method == "POST":
        form = InscricaoAnaliseForm(request.POST, instance=inscricao)
        if form.is_valid():
            form.save()
            messages.success(request, "Dados atualizados.")
            return redirect("cadastro:inscricao_detalhe", pk=pk)
    else:
        form = InscricaoAnaliseForm(instance=inscricao)
    return render(
        request, "cadastro/inscricao_form.html", {"form": form, "inscricao": inscricao}
    )


@login_required
def membro_novo(request, pk):
    inscricao = get_object_or_404(Inscricao, pk=pk)
    if _bloqueio_guard(request, inscricao):
        return redirect("cadastro:inscricao_detalhe", pk=pk)
    if request.method == "POST":
        form = MembroForm(request.POST, inscricao=inscricao)
        if form.is_valid():
            form.salvar()
            messages.success(request, "Integrante adicionado.")
            return redirect("cadastro:inscricao_detalhe", pk=pk)
    else:
        form = MembroForm(inscricao=inscricao)
    return render(
        request, "cadastro/membro_form.html", {"form": form, "inscricao": inscricao}
    )


@login_required
def renda_nova(request, membro_pk):
    membro = get_object_or_404(MembroNucleo.objects.select_related("inscricao", "pessoa"), pk=membro_pk)
    if _bloqueio_guard(request, membro.inscricao):
        return redirect("cadastro:inscricao_detalhe", pk=membro.inscricao_id)
    if request.method == "POST":
        form = RendaForm(request.POST)
        if form.is_valid():
            renda = form.save(commit=False)
            renda.membro = membro
            renda.save()
            messages.success(request, "Renda registrada.")
            return redirect("cadastro:inscricao_detalhe", pk=membro.inscricao_id)
    else:
        form = RendaForm()
    return render(
        request, "cadastro/renda_form.html", {"form": form, "membro": membro}
    )


@login_required
def documentos(request, pk):
    inscricao = get_object_or_404(Inscricao, pk=pk)
    if request.method == "POST":
        if _bloqueio_guard(request, inscricao):
            return redirect("cadastro:documentos", pk=pk)
        form = DocumentoForm(request.POST, request.FILES, inscricao=inscricao)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.inscricao = inscricao
            if doc.status != Documento.Status.PENDENTE:
                doc.conferido_por = request.user
                doc.data_conferencia = timezone.now()
            doc.save()
            messages.success(request, "Documento registrado.")
            return redirect("cadastro:documentos", pk=pk)
    else:
        form = DocumentoForm(inscricao=inscricao)
    ctx = {
        "inscricao": inscricao,
        "documentos": inscricao.documentos.select_related("pessoa"),
        "form": form,
    }
    return render(request, "cadastro/documentos.html", ctx)


@login_required
def documento_download(request, pk):
    """Serve o arquivo somente a usuários autenticados, fora da raiz web, e registra o acesso."""
    doc = get_object_or_404(Documento, pk=pk)
    if not doc.arquivo:
        raise Http404("Documento sem arquivo.")
    caminho = doc.arquivo.path
    if not os.path.exists(caminho):
        raise Http404("Arquivo não encontrado.")
    # Log de acesso ao documento (LGPD).
    from auditoria.models import Auditoria

    Auditoria.objects.create(
        usuario=request.user if request.user.is_authenticated else None,
        operacao=Auditoria.Operacao.ALTERACAO,
        tabela="cadastro.Documento",
        registro_id=str(doc.pk),
        campo="acesso",
        valor_novo="download",
    )
    return FileResponse(open(caminho, "rb"), as_attachment=True, filename=os.path.basename(caminho))


@login_required
def recalcular(request, pk):
    inscricao = get_object_or_404(Inscricao, pk=pk)
    r = services.calcular_e_salvar(inscricao)
    messages.success(
        request,
        f"Pontuação recalculada: CL={r.pontos_legais} + CC={r.pontos_complementares} "
        f"= {r.pontuacao_total} pontos.",
    )
    return redirect("cadastro:inscricao_detalhe", pk=pk)


@login_required
def marcar_inapto(request, pk):
    inscricao = get_object_or_404(Inscricao, pk=pk)
    if request.method == "POST":
        motivo = request.POST.get("motivo", "").strip()
        if not motivo:
            messages.error(request, "Informe o motivo da inaptidão (exige confirmação humana).")
            return redirect("cadastro:inscricao_detalhe", pk=pk)
        inscricao.status = Inscricao.Status.INAPTO
        inscricao.motivo_inaptidao = motivo
        inscricao._alteracao_autorizada = True
        inscricao.save()
        messages.warning(request, "Inscrição marcada como NÃO APTA.")
    return redirect("cadastro:inscricao_detalhe", pk=pk)


@login_required
def finalizar(request, pk):
    inscricao = get_object_or_404(Inscricao, pk=pk)
    if request.method == "POST":
        if inscricao.bloqueada:
            messages.info(request, "Inscrição já estava finalizada.")
            return redirect("cadastro:inscricao_detalhe", pk=pk)
        services.calcular_e_salvar(inscricao)  # snapshot final
        inscricao.refresh_from_db()
        inscricao.status = Inscricao.Status.RECEBIDA
        inscricao.data_finalizacao = timezone.now()
        inscricao.bloqueada = True
        inscricao._alteracao_autorizada = True
        inscricao.save()
        messages.success(request, "Inscrição finalizada e bloqueada.")
    return redirect("cadastro:inscricao_detalhe", pk=pk)


@login_required
def classificacao(request):
    if request.method == "POST":
        itens = services.classificar_todos()
        empates = sum(1 for c in itens if c.empate_pendente_sorteio)
        messages.success(
            request, f"{len(itens)} classificada(s); {empates} em empate para sorteio."
        )
        return redirect("cadastro:classificacao")
    from .models import Classificacao

    itens = Classificacao.objects.select_related("inscricao__requerente").filter(
        posicao__isnull=False
    )
    return render(request, "cadastro/classificacao.html", {"itens": itens})
