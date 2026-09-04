"""Telas de operação dos servidores (Fase 3)."""

from __future__ import annotations

import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.http import require_POST
from django.utils import timezone

from contas.acesso import ADMIN, ANALISTA, ATENDENTE, COMISSAO, em_perfil, perfil_requerido

from . import fluxo, requisitos, services, wizard
from .forms import (
    AvaliacaoForm,
    DocumentoForm,
    InscricaoContatoForm,
    MembroEditForm,
    MembroForm,
    PessoaForm,
    RendaForm,
    RendaWizardForm,
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
    faixas = [
        ("Sem pontos / não calculado", qs.filter(pontuacao_total__isnull=True).count()
         + qs.filter(pontuacao_total=0).count()),
        ("1 a 100", qs.filter(pontuacao_total__gte=1, pontuacao_total__lte=100).count()),
        ("101 a 160", qs.filter(pontuacao_total__gte=101, pontuacao_total__lte=160).count()),
        ("161 a 190", qs.filter(pontuacao_total__gte=161, pontuacao_total__lte=190).count()),
    ]
    ctx = {
        "total": qs.count(),
        "linhas": linhas,
        "faixas": faixas,
        "com_deficiencia": qs.filter(membros__pessoa__pcd=True).distinct().count(),
        "com_risco": qs.filter(habitacao_precaria_ou_risco=True).count(),
        "com_mulher_arrimo": qs.filter(
            membros__arrimo=True, membros__pessoa__sexo="F"
        ).distinct().count(),
        "empates": Inscricao.objects.filter(
            classificacao__empate_pendente_sorteio=True
        ).count(),
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

    # Ordem de inscrição (000001, 000002, ...) e paginação.
    inscricoes = inscricoes.order_by("numero_inscricao")
    paginator = Paginator(inscricoes, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Pontuação exibida: usa o snapshot salvo (inclusive 0); quando ainda não foi
    # calculado (None), calcula ao vivo para não exibir "—" indevidamente.
    from motor import calcular_pontuacao

    lista = list(page_obj.object_list)
    for i in lista:
        if i.pontuacao_total is not None:
            i.pontos_exibicao = i.pontuacao_total
        else:
            try:
                i.pontos_exibicao = calcular_pontuacao(
                    services.montar_nucleo(i), services.parametros()
                ).pontuacao_total
            except Exception:
                i.pontos_exibicao = None

    # Querystring dos filtros (para preservar na navegação de páginas).
    filtros = urlencode({k: v for k, v in (("q", q), ("status", status)) if v})

    ctx = {
        "inscricoes": lista,
        "page_obj": page_obj,
        "paginator": paginator,
        "filtros": filtros,
        "q": q,
        "status": status,
        "status_choices": Inscricao.Status.choices,
        "pode_excluir": em_perfil(request.user, ADMIN),
    }
    return render(request, "cadastro/inscricao_list.html", ctx)


@login_required
@perfil_requerido(ATENDENTE, ANALISTA)
def inscricao_nova(request):
    if request.method == "POST":
        form = RequerenteInscricaoForm(request.POST)
        if form.is_valid():
            inscricao = form.salvar()
            messages.success(request, f"Inscrição {inscricao.numero_inscricao} criada.")
            # Entra no assistente de cadastro (etapa 1).
            return redirect("cadastro:wizard", pk=inscricao.pk, etapa="requerente")
    else:
        form = RequerenteInscricaoForm()
    return render(request, "cadastro/inscricao_form.html", {"form": form, "novo": True})


@login_required
@perfil_requerido(ATENDENTE, ANALISTA)
def wizard_cadastro(request, pk, etapa):
    """Assistente de cadastro por etapas, com voltar/avançar e pendências."""
    inscricao = get_object_or_404(Inscricao, pk=pk)
    if etapa not in wizard.SLUGS:
        raise Http404("Etapa inválida.")
    if inscricao.bloqueada:
        messages.warning(request, "Inscrição finalizada e bloqueada — cadastro somente leitura.")
        return redirect("cadastro:inscricao_detalhe", pk=pk)

    anterior = wizard.anterior(etapa)
    proxima = wizard.proxima(etapa)

    def url_etapa(slug):
        return None if slug is None else reverse("cadastro:wizard", args=[pk, slug])

    def avancar_ou_ficar():
        destino = proxima if request.POST.get("acao") == "avancar" and proxima else etapa
        return redirect("cadastro:wizard", pk=pk, etapa=destino)

    ctx = {
        "inscricao": inscricao,
        "etapa": etapa,
        "passos": wizard.passos(etapa),
        "url_anterior": url_etapa(anterior),
        "url_proxima": url_etapa(proxima),
    }

    if etapa == "requerente":
        if request.method == "POST":
            fp = PessoaForm(request.POST, instance=inscricao.requerente)
            fc = InscricaoContatoForm(request.POST, instance=inscricao)
            if fp.is_valid() and fc.is_valid():
                fp.save()
                fc.save()
                messages.success(request, "Dados do requerente salvos.")
                return avancar_ou_ficar()
        else:
            fp = PessoaForm(instance=inscricao.requerente)
            fc = InscricaoContatoForm(instance=inscricao)
        ctx.update(form_pessoa=fp, form_contato=fc)
        return render(request, "cadastro/wizard_requerente.html", ctx)

    if etapa == "nucleo":
        if request.method == "POST":
            form = MembroForm(request.POST, inscricao=inscricao)
            if form.is_valid():
                form.salvar()
                messages.success(request, "Integrante adicionado.")
                return redirect("cadastro:wizard", pk=pk, etapa="nucleo")
        else:
            form = MembroForm(inscricao=inscricao)
        ctx.update(form=form, membros=inscricao.membros.select_related("pessoa"))
        return render(request, "cadastro/wizard_nucleo.html", ctx)

    if etapa == "renda":
        if request.method == "POST":
            form = RendaWizardForm(request.POST, inscricao=inscricao)
            if form.is_valid():
                form.salvar()
                messages.success(request, "Renda registrada.")
                return redirect("cadastro:wizard", pk=pk, etapa="renda")
        else:
            form = RendaWizardForm(inscricao=inscricao)
        ctx.update(
            form=form,
            membros=inscricao.membros.select_related("pessoa").prefetch_related("rendas"),
        )
        return render(request, "cadastro/wizard_renda.html", ctx)

    if etapa == "documentos":
        from . import documentos as _docs

        if request.method == "POST" and request.POST.get("acao") == "checklist":
            # Marcação rápida: documentos entregues na secretaria (sem anexo).
            _docs.marcar_entregues(
                inscricao, request.POST.getlist("entregue"), usuario=request.user
            )
            messages.success(request, "Checklist de documentos atualizado.")
            return redirect("cadastro:wizard", pk=pk, etapa="documentos")

        if request.method == "POST":
            form = DocumentoForm(request.POST, request.FILES, inscricao=inscricao)
            if form.is_valid():
                doc = form.save(commit=False)
                doc.inscricao = inscricao
                if doc.status != Documento.Status.PENDENTE:
                    doc.conferido_por = request.user
                    doc.data_conferencia = timezone.now()
                doc.save()
                messages.success(request, "Documento registrado.")
                return redirect("cadastro:wizard", pk=pk, etapa="documentos")
        else:
            form = DocumentoForm(inscricao=inscricao)

        ctx.update(
            form=form,
            documentos=inscricao.documentos.select_related("pessoa"),
            checklist=_docs.exigidos(inscricao),
        )
        return render(request, "cadastro/wizard_documentos.html", ctx)

    if etapa == "avaliacao":
        if request.method == "POST":
            form = AvaliacaoForm(request.POST, instance=inscricao)
            if form.is_valid():
                obj = form.save(commit=False)
                obj._alteracao_autorizada = True
                obj._justificativa_auditoria = "Cadastro (assistente) - avaliação"
                obj.save()
                services.calcular_e_salvar(obj)
                messages.success(request, "Avaliação salva e pontuação recalculada.")
                return avancar_ou_ficar()
        else:
            form = AvaliacaoForm(instance=inscricao)
        ctx.update(form=form)
        return render(request, "cadastro/wizard_avaliacao.html", ctx)

    # revisao
    services.calcular_e_salvar(inscricao)
    inscricao.refresh_from_db()
    itens_req = requisitos.avaliar(inscricao)
    ctx.update(
        pendencias=wizard.pendencias(inscricao),
        requisitos=itens_req,
        apto=requisitos.apto(itens_req),
    )
    return render(request, "cadastro/wizard_revisao.html", ctx)


@login_required
@perfil_requerido(ADMIN)
def inscricao_excluir(request, pk):
    """Exclui uma inscrição (e seus dados vinculados). Apenas Administrador."""
    inscricao = get_object_or_404(Inscricao, pk=pk)
    if request.method == "POST":
        from .models import Pessoa

        numero = inscricao.numero_inscricao
        # Pessoas envolvidas (requerente + integrantes) antes de excluir.
        pessoas_ids = {inscricao.requerente_id}
        pessoas_ids.update(inscricao.membros.values_list("pessoa_id", flat=True))

        with transaction.atomic():
            inscricao._justificativa_auditoria = request.POST.get("motivo", "Exclusão administrativa")
            inscricao.delete()
            # Remove pessoas que ficaram sem vínculo com qualquer núcleo/inscrição,
            # liberando o CPF para nova inscrição.
            for pid in pessoas_ids:
                p = Pessoa.objects.filter(pk=pid).first()
                if p and not p.participacoes.exists() and not p.inscricoes_como_requerente.exists():
                    p.delete()

        messages.success(request, f"Inscrição {numero} excluída.")
        return redirect("cadastro:inscricao_list")
    return redirect("cadastro:inscricao_detalhe", pk=pk)


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
        "transicoes": fluxo.transicoes_disponiveis(inscricao, request.user),
        "pode_cadastrar": em_perfil(request.user, ATENDENTE, ANALISTA),
        "pode_avaliar": em_perfil(request.user, ANALISTA, COMISSAO),
        "pode_excluir": em_perfil(request.user, ADMIN),
        "email_ativo": getattr(settings, "MCMV_EMAIL_ATIVO", False),
    }
    return render(request, "cadastro/inscricao_detalhe.html", ctx)


@login_required
@perfil_requerido(ATENDENTE, ANALISTA)
def inscricao_editar(request, pk):
    """Edita dados declarados (contato/endereço) — bloqueado após finalização."""
    inscricao = get_object_or_404(Inscricao, pk=pk)
    if _bloqueio_guard(request, inscricao):
        return redirect("cadastro:inscricao_detalhe", pk=pk)
    if request.method == "POST":
        form = InscricaoContatoForm(request.POST, instance=inscricao)
        if form.is_valid():
            form.save()
            messages.success(request, "Dados atualizados.")
            return redirect("cadastro:inscricao_detalhe", pk=pk)
    else:
        form = InscricaoContatoForm(instance=inscricao)
    return render(
        request, "cadastro/inscricao_form.html",
        {"form": form, "inscricao": inscricao, "titulo": "Editar contato/endereço"},
    )


@login_required
@perfil_requerido(ANALISTA, COMISSAO)
def avaliar(request, pk):
    """Fatos apurados pela análise (Critérios Legais, requisitos, aluguel).

    Permitido mesmo com a inscrição finalizada: é análise, não alteração dos
    dados declarados pelo candidato. A gravação é autorizada e auditada.
    """
    inscricao = get_object_or_404(Inscricao, pk=pk)
    if request.method == "POST":
        form = AvaliacaoForm(request.POST, instance=inscricao)
        if form.is_valid():
            avaliada = form.save(commit=False)
            avaliada._alteracao_autorizada = True
            avaliada._justificativa_auditoria = "Avaliação da análise"
            avaliada.save()
            services.calcular_e_salvar(avaliada)
            messages.success(request, "Avaliação registrada e pontuação recalculada.")
            return redirect("cadastro:inscricao_detalhe", pk=pk)
    else:
        form = AvaliacaoForm(instance=inscricao)
    return render(
        request, "cadastro/inscricao_form.html",
        {"form": form, "inscricao": inscricao, "titulo": "Avaliação da análise"},
    )


@login_required
def transicionar(request, pk):
    """Aplica uma transição de situação (fluxo de homologação)."""
    inscricao = get_object_or_404(Inscricao, pk=pk)
    if request.method == "POST":
        destino = request.POST.get("destino", "")
        # Regra: só se torna APTO quando todos os requisitos estão atendidos.
        if destino == Inscricao.Status.APTO and not requisitos.apto(
            requisitos.avaliar(inscricao)
        ):
            messages.error(
                request,
                "Não é possível marcar APTO: há requisito não atendido. "
                "Complete a avaliação ou marque como NÃO APTO.",
            )
            return redirect("cadastro:inscricao_detalhe", pk=pk)
        try:
            fluxo.aplicar(inscricao, destino, request.user)
            messages.success(request, f"Situação atualizada: {inscricao.get_status_display()}.")
        except PermissionDenied as exc:
            messages.error(request, str(exc))
    return redirect("cadastro:inscricao_detalhe", pk=pk)


@login_required
@perfil_requerido(ATENDENTE, ANALISTA)
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
@perfil_requerido(ATENDENTE, ANALISTA)
def membro_editar(request, membro_pk):
    membro = get_object_or_404(
        MembroNucleo.objects.select_related("inscricao__requerente", "pessoa"), pk=membro_pk
    )
    inscricao = membro.inscricao
    if _bloqueio_guard(request, inscricao):
        return redirect("cadastro:inscricao_detalhe", pk=inscricao.pk)
    if request.method == "POST":
        form = MembroEditForm(request.POST, membro=membro)
        if form.is_valid():
            form.salvar()
            messages.success(request, "Integrante atualizado.")
            return redirect("cadastro:wizard", pk=inscricao.pk, etapa="nucleo")
    else:
        form = MembroEditForm(membro=membro)
    return render(
        request, "cadastro/membro_editar.html",
        {"form": form, "inscricao": inscricao, "membro": membro},
    )


@login_required
@perfil_requerido(ATENDENTE, ANALISTA)
@require_POST
def membro_excluir(request, membro_pk):
    membro = get_object_or_404(
        MembroNucleo.objects.select_related("inscricao", "pessoa"), pk=membro_pk
    )
    inscricao = membro.inscricao
    if _bloqueio_guard(request, inscricao):
        return redirect("cadastro:inscricao_detalhe", pk=inscricao.pk)
    if membro.pessoa_id == inscricao.requerente_id:
        messages.error(request, "O requerente não pode ser removido do núcleo.")
        return redirect("cadastro:wizard", pk=inscricao.pk, etapa="nucleo")
    pessoa = membro.pessoa
    with transaction.atomic():
        membro.delete()
        # Remove a Pessoa órfã (sem outros vínculos), liberando o CPF.
        orfa = (
            not pessoa.participacoes.exists()
            and not Inscricao.objects.filter(requerente=pessoa).exists()
        )
        if orfa:
            pessoa.delete()
    messages.success(request, "Integrante removido.")
    return redirect("cadastro:wizard", pk=inscricao.pk, etapa="nucleo")


@login_required
@perfil_requerido(ATENDENTE, ANALISTA)
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
@perfil_requerido(ATENDENTE, ANALISTA)
def renda_editar(request, renda_pk):
    from .models import Renda

    renda = get_object_or_404(
        Renda.objects.select_related("membro__inscricao", "membro__pessoa"), pk=renda_pk
    )
    inscricao = renda.membro.inscricao
    if _bloqueio_guard(request, inscricao):
        return redirect("cadastro:inscricao_detalhe", pk=inscricao.pk)
    if request.method == "POST":
        form = RendaForm(request.POST, instance=renda)
        if form.is_valid():
            form.save()
            messages.success(request, "Renda atualizada.")
            return redirect("cadastro:wizard", pk=inscricao.pk, etapa="renda")
    else:
        form = RendaForm(instance=renda)
    return render(request, "cadastro/renda_editar.html", {
        "form": form, "inscricao": inscricao, "renda": renda,
    })


@login_required
@perfil_requerido(ATENDENTE, ANALISTA)
@require_POST
def renda_excluir(request, renda_pk):
    from .models import Renda

    renda = get_object_or_404(Renda.objects.select_related("membro__inscricao"), pk=renda_pk)
    inscricao = renda.membro.inscricao
    if _bloqueio_guard(request, inscricao):
        return redirect("cadastro:inscricao_detalhe", pk=inscricao.pk)
    renda.delete()
    messages.success(request, "Renda removida.")
    return redirect("cadastro:wizard", pk=inscricao.pk, etapa="renda")


@login_required
def documentos(request, pk):
    inscricao = get_object_or_404(Inscricao, pk=pk)
    if request.method == "POST":
        if not em_perfil(request.user, ATENDENTE, ANALISTA):
            raise PermissionDenied("Seu perfil não permite registrar documentos.")
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
@perfil_requerido(ATENDENTE, ANALISTA, COMISSAO)
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
@perfil_requerido(ANALISTA, COMISSAO)
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
@perfil_requerido(ATENDENTE, ANALISTA)
def finalizar(request, pk):
    inscricao = get_object_or_404(Inscricao, pk=pk)
    if request.method == "POST":
        if inscricao.bloqueada:
            messages.info(request, "Inscrição já estava finalizada.")
            return redirect("cadastro:inscricao_detalhe", pk=pk)
        services.calcular_e_salvar(inscricao)  # snapshot final
        inscricao.refresh_from_db()
        agora = timezone.now()
        inscricao.status = Inscricao.Status.RECEBIDA
        inscricao.data_finalizacao = agora
        inscricao.finalizado_por = request.user
        inscricao.bloqueada = True
        if not inscricao.protocolo:
            inscricao.protocolo = f"MCMV-{agora:%Y}-{inscricao.numero_inscricao}"
        inscricao._alteracao_autorizada = True
        inscricao.save()
        messages.success(
            request,
            f"Inscrição finalizada. Protocolo {inscricao.protocolo}. "
            "Imprima o recibo para entregar ao requerente.",
        )
    return redirect("cadastro:inscricao_detalhe", pk=pk)


@login_required
@perfil_requerido(ADMIN)
def classificacao(request):
    if request.method == "POST":
        itens = services.classificar_todos()
        empates = sum(1 for c in itens if c.empate_pendente_sorteio)
        messages.success(
            request, f"{len(itens)} classificada(s); {empates} em empate para sorteio."
        )
        return redirect("cadastro:classificacao")
    itens = services.ordenar_classificaveis()
    # A lista já mostra as inscrições classificáveis em ordem (inclusive as
    # recém-finalizadas). Se a posição oficial gravada divergir da ordem atual
    # — nova inscrição sem posição, ou ordem desatualizada — a classificação
    # oficial precisa ser (re)gerada.
    pendente_geracao = any(c.posicao != c.posicao_persistida for c in itens)
    return render(request, "cadastro/classificacao.html", {
        "itens": itens,
        "pendente_geracao": pendente_geracao,
        "pode_classificar": True,  # a view já é restrita ao Administrador
    })


# --------------------------------------------------------------------------- #
# Relatórios e exportação (Fase 5)
# --------------------------------------------------------------------------- #
from . import relatorios  # noqa: E402
from .models import Classificacao  # noqa: E402


@login_required
def relatorios_index(request):
    return render(request, "cadastro/relatorios.html", {
        "status_choices": Inscricao.Status.choices,
    })


def _linha_inscricao(i):
    from decimal import ROUND_HALF_UP, Decimal

    from motor import calcular_pontuacao

    membros = list(i.membros.all())
    pcd = sum(1 for m in membros if m.pessoa.pcd)
    pos = getattr(getattr(i, "classificacao", None), "posicao", None)

    # Recalcula ao vivo (não depende do snapshot salvo, que pode estar
    # desatualizado/zerado se a pontuação não foi recalculada após a digitação).
    nucleo = services.montar_nucleo(i)
    r = calcular_pontuacao(nucleo, services.parametros())

    def _2(v):
        if v is None:
            return 0
        return Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return [
        i.numero_inscricao, i.requerente.nome, i.requerente.cpf, i.get_status_display(),
        len(membros), r.dependentes_ate_12, r.idosos, pcd,
        _2(nucleo.renda_bruta_computavel()), _2(r.renda_per_capita), _2(r.percentual_aluguel),
        r.pontos_legais, r.pontos_complementares, r.pontuacao_total,
        pos or "",
    ]


CAB_BASE = [
    "Nº", "Requerente", "CPF", "Situação", "Integrantes", "≤12 anos", "Idosos", "PcD",
    "Renda computável", "Per capita", "% aluguel", "CL", "CC", "Total", "Posição",
]


@login_required
@perfil_requerido(ADMIN)
def rel_base(request):
    qs = Inscricao.objects.select_related("requerente").prefetch_related("membros__pessoa")
    status = request.GET.get("status", "").strip()
    if status:
        qs = qs.filter(status=status)
    if request.GET.get("risco"):
        qs = qs.filter(habitacao_precaria_ou_risco=True)
    pmin = request.GET.get("pmin", "").strip()
    pmax = request.GET.get("pmax", "").strip()
    if pmin:
        qs = qs.filter(pontuacao_total__gte=int(pmin))
    if pmax:
        qs = qs.filter(pontuacao_total__lte=int(pmax))

    linhas = [_linha_inscricao(i) for i in qs]
    if request.GET.get("pcd"):
        linhas = [l for l in linhas if l[7]]  # coluna PcD
    if request.GET.get("criancas"):
        linhas = [l for l in linhas if l[5]]  # coluna ≤12
    if request.GET.get("idosos"):
        linhas = [l for l in linhas if l[6]]  # coluna idosos
    return relatorios.planilha_response("base_mcmv.xlsx", CAB_BASE, linhas)


@login_required
@perfil_requerido(ADMIN)
def rel_classificacao_xlsx(request):
    itens = Classificacao.objects.select_related("inscricao__requerente").filter(
        posicao__isnull=False
    )
    cab = ["Posição", "Nº", "Requerente", "CPF", "CL", "CC", "Total", "≤12", "Idosos", "Empate/Sorteio"]
    linhas = [
        [c.posicao, c.inscricao.numero_inscricao, c.inscricao.requerente.nome,
         c.inscricao.requerente.cpf, c.inscricao.pontos_legais or 0,
         c.inscricao.pontos_complementares or 0, c.pontuacao, c.dependentes_ate_12,
         c.idosos, "Sim" if c.empate_pendente_sorteio else "Não"]
        for c in itens
    ]
    return relatorios.planilha_response("classificacao.xlsx", cab, linhas)


@login_required
@perfil_requerido(ADMIN)
def rel_classificacao_pdf(request):
    itens = Classificacao.objects.select_related("inscricao__requerente").filter(
        posicao__isnull=False
    )
    return relatorios.classificacao_pdf(itens)


@login_required
def rel_ordem_cadastro_pdf(request):
    """Relação geral das inscrições por ordem de cadastro (PDF)."""
    inscricoes = (
        Inscricao.objects.select_related("requerente").order_by("numero_inscricao")
    )
    return relatorios.lista_ordem_cadastro_pdf(inscricoes)


@login_required
def rel_ficha_pdf(request, pk):
    inscricao = get_object_or_404(
        Inscricao.objects.select_related("requerente").prefetch_related(
            "membros__pessoa", "criterios_legais"
        ),
        pk=pk,
    )
    return relatorios.ficha_pdf(inscricao)


@login_required
def rel_recibo_pdf(request, pk):
    """Comprovante de inscrição (recibo) — disponível após a finalização."""
    inscricao = get_object_or_404(
        Inscricao.objects.select_related("requerente"), pk=pk
    )
    if not inscricao.protocolo:
        messages.info(request, "O recibo fica disponível após finalizar a inscrição.")
        return redirect("cadastro:inscricao_detalhe", pk=pk)
    return relatorios.recibo_pdf(inscricao)


@login_required
@require_POST
def rel_recibo_email(request, pk):
    """Envia o recibo por e-mail ao requerente (após a finalização)."""
    inscricao = get_object_or_404(Inscricao.objects.select_related("requerente"), pk=pk)
    if not inscricao.protocolo:
        messages.info(request, "O recibo fica disponível após finalizar a inscrição.")
        return redirect("cadastro:inscricao_detalhe", pk=pk)
    from . import emails

    try:
        destino = emails.enviar_recibo(inscricao)
        messages.success(request, f"Recibo enviado por e-mail para {destino}.")
    except ValueError as exc:
        messages.error(request, str(exc))
    except Exception as exc:  # falha de SMTP/rede
        messages.error(request, f"Não foi possível enviar o e-mail: {exc}")
    return redirect("cadastro:inscricao_detalhe", pk=pk)


@login_required
def rel_pendentes(request):
    docs = Documento.objects.select_related("inscricao__requerente", "pessoa").filter(
        obrigatorio=True
    ).exclude(status=Documento.Status.APROVADO)
    cab = ["Nº inscrição", "Requerente", "Documento", "Pessoa", "Situação"]
    linhas = [
        [d.inscricao.numero_inscricao, d.inscricao.requerente.nome, d.tipo,
         d.pessoa.nome if d.pessoa else "", d.get_status_display()]
        for d in docs
    ]
    return relatorios.planilha_response("documentacao_pendente.xlsx", cab, linhas)


@login_required
def rel_indeferidos(request):
    qs = Inscricao.objects.select_related("requerente").filter(
        status__in=[Inscricao.Status.INAPTO, Inscricao.Status.INDEFERIDO]
    )
    cab = ["Nº", "Requerente", "CPF", "Situação", "Motivo"]
    linhas = [
        [i.numero_inscricao, i.requerente.nome, i.requerente.cpf, i.get_status_display(),
         i.motivo_inaptidao]
        for i in qs
    ]
    return relatorios.planilha_response("indeferidos.xlsx", cab, linhas)


@login_required
def rel_aptos(request):
    qs = Inscricao.objects.select_related("requerente").prefetch_related("membros__pessoa").filter(
        status__in=services.STATUS_CLASSIFICAVEIS
    )
    linhas = [_linha_inscricao(i) for i in qs]
    return relatorios.planilha_response("aptos.xlsx", CAB_BASE, linhas)


@login_required
@perfil_requerido(ADMIN)
def rel_empates(request):
    itens = Classificacao.objects.select_related("inscricao__requerente").filter(
        empate_pendente_sorteio=True
    )
    cab = ["Posição", "Nº", "Requerente", "Pontos", "≤12", "Idosos"]
    linhas = [
        [c.posicao, c.inscricao.numero_inscricao, c.inscricao.requerente.nome,
         c.pontuacao, c.dependentes_ate_12, c.idosos]
        for c in itens
    ]
    return relatorios.planilha_response("empates_sorteio.xlsx", cab, linhas)


@login_required
def rel_auditoria(request):
    from auditoria.models import Auditoria

    regs = Auditoria.objects.select_related("usuario")[:5000]
    cab = ["Data/hora", "Usuário", "IP", "Operação", "Tabela", "Registro", "Campo",
           "Valor anterior", "Valor novo", "Justificativa"]
    linhas = [
        [timezone.localtime(r.data_hora).strftime("%d/%m/%Y %H:%M"), r.usuario.get_username() if r.usuario else "",
         r.ip or "", r.get_operacao_display(), r.tabela, r.registro_id, r.campo,
         r.valor_anterior, r.valor_novo, r.justificativa]
        for r in regs
    ]
    return relatorios.planilha_response("auditoria.xlsx", cab, linhas)


# --------------------------------------------------------------------------- #
# Backup e restauração manual (somente Administrador)
# --------------------------------------------------------------------------- #
@login_required
@perfil_requerido(ADMIN)
def admin_backup(request):
    from pathlib import Path

    from . import backup_utils

    destino = Path(settings.MCMV_BACKUP_DIR)
    backups = []
    if destino.exists():
        for arq in sorted(destino.glob(f"{backup_utils.PREFIXO}*.zip"), reverse=True)[:10]:
            backups.append({
                "nome": arq.name,
                "tamanho_mb": arq.stat().st_size / (1024 * 1024),
                "data": timezone.datetime.fromtimestamp(arq.stat().st_mtime),
            })
    return render(request, "cadastro/admin_backup.html", {
        "backups": backups,
        "pasta_backup": str(destino),
    })


@login_required
@perfil_requerido(ADMIN)
def backup_baixar(request):
    """Gera um backup consistente (salva em MCMV_BACKUP_DIR) e o envia para download."""
    from pathlib import Path

    from . import backup_utils

    alvo = Path(settings.MCMV_BACKUP_DIR) / backup_utils.nome_backup()
    backup_utils.gerar_zip(alvo)
    return FileResponse(
        open(alvo, "rb"), as_attachment=True, filename=alvo.name,
        content_type="application/zip",
    )


@login_required
@perfil_requerido(ADMIN)
@require_POST
def backup_restaurar(request):
    """Restaura o sistema a partir de um .zip de backup (destrutivo — só Admin)."""
    from . import backup_utils

    arquivo = request.FILES.get("arquivo")
    if not arquivo:
        messages.error(request, "Selecione o arquivo de backup (.zip) a restaurar.")
        return redirect("cadastro:admin_backup")
    if request.POST.get("confirmar") != "on":
        messages.error(request, "Marque a confirmação: a restauração substitui os dados atuais.")
        return redirect("cadastro:admin_backup")
    try:
        info = backup_utils.restaurar_zip(arquivo)
    except Exception as exc:
        messages.error(request, f"Falha na restauração: {exc}")
        return redirect("cadastro:admin_backup")

    from pathlib import Path

    messages.success(
        request,
        "Backup restaurado com sucesso. Cópia de segurança do estado anterior: "
        f"{Path(info['copia_seguranca']).name}. Talvez seja necessário entrar novamente.",
    )
    return redirect("cadastro:admin_backup")


@login_required
@perfil_requerido(ADMIN)
@require_POST
def numeracao_resetar(request):
    """Reinicia a numeração das inscrições em 000001 (só Admin, banco sem inscrições).

    Roda dentro do serviço em execução — garante que o reinício atinge o mesmo
    banco usado pelo sistema (evita o problema de rodar o comando num ambiente
    ou diretório diferente).
    """
    from io import StringIO

    from django.core.management import CommandError, call_command

    saida = StringIO()
    try:
        call_command("resetar_numeracao", stdout=saida)
    except CommandError as exc:
        messages.error(request, str(exc))
        return redirect("cadastro:admin_backup")
    messages.success(
        request, "Numeração reiniciada. A próxima inscrição cadastrada será 000001."
    )
    return redirect("cadastro:admin_backup")


@login_required
@perfil_requerido(ADMIN)
@require_POST
def cpf_liberar(request):
    """Libera um CPF preso por uma Pessoa órfã (só Admin). Roda no serviço em uso."""
    from io import StringIO

    from django.core.management import CommandError, call_command

    cpf = (request.POST.get("cpf") or "").strip()
    if not cpf:
        messages.error(request, "Informe o CPF a liberar.")
        return redirect("cadastro:admin_backup")
    saida = StringIO()
    try:
        call_command("liberar_cpf", cpf, stdout=saida)
    except CommandError as exc:
        messages.error(request, str(exc))
        return redirect("cadastro:admin_backup")
    messages.success(request, saida.getvalue().strip() or "CPF liberado.")
    return redirect("cadastro:admin_backup")
