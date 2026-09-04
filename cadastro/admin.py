from django.contrib import admin, messages

from . import services
from .models import (
    Classificacao,
    CriterioComplementar,
    CriterioLegal,
    Documento,
    Inscricao,
    MembroNucleo,
    Pessoa,
    Renda,
)


class RendaInline(admin.TabularInline):
    model = Renda
    extra = 0


class MembroNucleoInline(admin.TabularInline):
    model = MembroNucleo
    extra = 0
    autocomplete_fields = ("pessoa",)


class DocumentoInline(admin.TabularInline):
    model = Documento
    extra = 0
    fields = ("tipo", "pessoa", "obrigatorio", "arquivo", "status", "conferido_por", "data_conferencia")


class CriterioLegalInline(admin.TabularInline):
    model = CriterioLegal
    extra = 0
    readonly_fields = ("inciso", "atendido", "pontos")
    can_delete = False


class CriterioComplementarInline(admin.StackedInline):
    model = CriterioComplementar
    extra = 0
    readonly_fields = ("renda_per_capita", "pontos_renda", "aluguel_medio", "percentual", "pontos_aluguel")
    can_delete = False


@admin.register(Pessoa)
class PessoaAdmin(admin.ModelAdmin):
    list_display = ("nome", "cpf", "data_nascimento", "sexo", "pcd")
    search_fields = ("nome", "cpf")
    list_filter = ("sexo", "pcd", "brasileiro")


@admin.register(Inscricao)
class InscricaoAdmin(admin.ModelAdmin):
    list_display = (
        "numero_inscricao",
        "requerente",
        "status",
        "pontos_legais",
        "pontos_complementares",
        "pontuacao_total",
        "bloqueada",
    )
    list_filter = ("status", "bloqueada", "habitacao_precaria_ou_risco")
    search_fields = ("numero_inscricao", "requerente__nome", "requerente__cpf")
    autocomplete_fields = ("requerente",)
    readonly_fields = (
        "numero_inscricao",
        "data_inscricao",
        "renda_bruta_computavel",
        "aluguel_medio",
        "renda_per_capita",
        "percentual_aluguel",
        "pontos_legais",
        "pontos_complementares",
        "pontuacao_total",
    )
    inlines = [
        MembroNucleoInline,
        DocumentoInline,
        CriterioLegalInline,
        CriterioComplementarInline,
    ]
    actions = ["acao_recalcular", "acao_classificar"]

    @admin.action(description="Recalcular pontuação das inscrições selecionadas")
    def acao_recalcular(self, request, queryset):
        for inscricao in queryset:
            services.calcular_e_salvar(inscricao)
        self.message_user(
            request, f"Pontuação recalculada para {queryset.count()} inscrição(ões).",
            messages.SUCCESS,
        )

    @admin.action(description="Gerar classificação geral (todas as inscrições aptas)")
    def acao_classificar(self, request, queryset):
        itens = services.classificar_todos()
        empates = sum(1 for c in itens if c.empate_pendente_sorteio)
        self.message_user(
            request,
            f"{len(itens)} inscrição(ões) classificada(s). "
            f"{empates} em empate pendente de sorteio.",
            messages.SUCCESS,
        )


@admin.register(MembroNucleo)
class MembroNucleoAdmin(admin.ModelAdmin):
    list_display = ("pessoa", "inscricao", "parentesco", "arrimo", "dependente")
    search_fields = ("pessoa__nome", "pessoa__cpf", "inscricao__numero_inscricao")
    autocomplete_fields = ("pessoa", "inscricao")
    inlines = [RendaInline]


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ("tipo", "inscricao", "pessoa", "obrigatorio", "status")
    list_filter = ("status", "obrigatorio")
    search_fields = ("tipo", "inscricao__numero_inscricao")


@admin.register(Classificacao)
class ClassificacaoAdmin(admin.ModelAdmin):
    list_display = (
        "posicao",
        "inscricao",
        "pontuacao",
        "dependentes_ate_12",
        "idosos",
        "empate_pendente_sorteio",
    )
    list_filter = ("empate_pendente_sorteio",)
    ordering = ("posicao",)
