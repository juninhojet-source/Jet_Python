"""Modelos do cadastro habitacional — Edital 001/2026 (Barão de Cocais/MG).

Ver docs/03-modelo-de-dados.md. Regras de pontuação NÃO vivem aqui: são
calculadas pelo motor (``motor/``) via ``cadastro.services``. Idades nunca são
armazenadas — derivam de ``data_nascimento``.
"""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from auditoria.mixins import ModeloAuditavel


class Pessoa(ModeloAuditavel):
    class Sexo(models.TextChoices):
        FEMININO = "F", "Feminino"
        MASCULINO = "M", "Masculino"

    class EstadoCivil(models.TextChoices):
        SOLTEIRO = "SOLTEIRO", "Solteiro(a)"
        CASADO = "CASADO", "Casado(a)"
        SEPARADO = "SEPARADO", "Separado(a)"
        DIVORCIADO = "DIVORCIADO", "Divorciado(a)"
        VIUVO = "VIUVO", "Viúvo(a)"
        UNIAO_ESTAVEL = "UNIAO_ESTAVEL", "União estável"

    nome = models.CharField("nome completo", max_length=200)
    cpf = models.CharField("CPF", max_length=14, unique=True)
    data_nascimento = models.DateField("data de nascimento")
    sexo = models.CharField(max_length=1, choices=Sexo.choices, default=Sexo.FEMININO)
    estado_civil = models.CharField(
        max_length=20, choices=EstadoCivil.choices, blank=True
    )
    pcd = models.BooleanField("pessoa com deficiência", default=False)
    brasileiro = models.BooleanField("brasileiro(a) nato/naturalizado(a)", default=True)

    class Meta:
        verbose_name = "pessoa"
        verbose_name_plural = "pessoas"
        ordering = ("nome",)

    def __str__(self):
        return f"{self.nome} ({self.cpf})"


class Inscricao(ModeloAuditavel):
    class Status(models.TextChoices):
        RASCUNHO = "RASCUNHO", "Rascunho"
        RECEBIDA = "RECEBIDA", "Inscrição recebida"
        EM_ANALISE = "EM_ANALISE", "Em análise"
        PENDENCIA = "PENDENCIA", "Pendência"
        DOC_VALIDADA = "DOC_VALIDADA", "Documentação validada"
        APTO = "APTO", "Apto"
        INAPTO = "INAPTO", "Não apto"
        INDEFERIDO = "INDEFERIDO", "Indeferido"
        HOMOLOGADO = "HOMOLOGADO", "Homologado"
        CLASSIFICADO = "CLASSIFICADO", "Classificado"
        ENCAMINHADO_CAIXA = "ENCAMINHADO_CAIXA", "Encaminhado à CAIXA"

    numero_inscricao = models.CharField(max_length=20, unique=True, blank=True)
    data_inscricao = models.DateTimeField(auto_now_add=True)
    requerente = models.ForeignKey(
        Pessoa, on_delete=models.PROTECT, related_name="inscricoes_como_requerente"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.RASCUNHO, db_index=True
    )

    # Contato/endereço do requerente
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    endereco = models.CharField(max_length=200, blank=True)
    numero = models.CharField(max_length=20, blank=True)
    complemento = models.CharField(max_length=100, blank=True)
    bairro = models.CharField(max_length=100, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    uf = models.CharField("UF", max_length=2, blank=True)
    cep = models.CharField(max_length=9, blank=True)

    # Data de referência para cálculo de idades (decisão D-1). Se vazia, usa a
    # data da inscrição.
    data_referencia = models.DateField(null=True, blank=True)

    # Fatos documentais dos Critérios Legais (marcados pela análise).
    habitacao_precaria_ou_risco = models.BooleanField(default=False)  # CL_I
    matricula_comprovada = models.BooleanField(default=False)  # parte do CL_II

    # Requisitos eliminatórios documentais (itens 3.1/6.1), confirmados pela análise.
    residencia_5anos_comprovada = models.BooleanField("reside há ≥ 5 anos (comprovado)", default=False)
    nao_proprietario_declarado = models.BooleanField("não é proprietário de imóvel", default=False)
    nao_beneficiado_declarado = models.BooleanField("nunca beneficiado por prog. habitacional", default=False)

    # Registro de inaptidão (item 6): exige confirmação humana (decisão D-5).
    motivo_inaptidao = models.TextField(blank=True)

    # Aluguel (média dos 3 meses — item 8.8). Valores mensais em MembroNucleo? Não:
    # é do núcleo. Guardamos os meses como campos simples + flag de cedido.
    aluguel_mes_1 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    aluguel_mes_2 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    aluguel_mes_3 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    aluguel_cedido = models.BooleanField("imóvel cedido/emprestado", default=False)

    # Snapshot calculado pelo motor (recomputável a qualquer momento).
    renda_bruta_computavel = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    aluguel_medio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    renda_per_capita = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    percentual_aluguel = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    pontos_legais = models.PositiveIntegerField(null=True, blank=True)
    pontos_complementares = models.PositiveIntegerField(null=True, blank=True)
    pontuacao_total = models.PositiveIntegerField(null=True, blank=True, db_index=True)

    data_finalizacao = models.DateTimeField(null=True, blank=True)
    bloqueada = models.BooleanField(default=False)
    # Protocolo do comprovante de inscrição (gerado na finalização).
    protocolo = models.CharField(max_length=40, blank=True, db_index=True)

    # LGPD: registro da ciência/consentimento do requerente quanto ao
    # tratamento dos dados pessoais (data preenchida automaticamente).
    ciencia_lgpd = models.BooleanField(
        "declaração de ciência (LGPD)", default=False
    )
    ciencia_lgpd_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "inscrição"
        verbose_name_plural = "inscrições"
        ordering = ("-data_inscricao",)

    def __str__(self):
        return f"{self.numero_inscricao or 's/nº'} — {self.requerente.nome}"

    def save(self, *args, **kwargs):
        # LGPD: carimba a data da ciência quando o requerente a declara.
        if self.ciencia_lgpd and self.ciencia_lgpd_em is None:
            from django.utils import timezone

            self.ciencia_lgpd_em = timezone.now()
        elif not self.ciencia_lgpd:
            self.ciencia_lgpd_em = None
        # Bloqueio pós-finalização (Anexo II): alterações só com autorização
        # administrativa explícita, sempre registrada.
        if self.pk and self.bloqueada and not getattr(self, "_alteracao_autorizada", False):
            anterior = type(self).objects.filter(pk=self.pk).first()
            if anterior is not None and anterior.bloqueada:
                raise ValidationError(
                    "Inscrição bloqueada após finalização. Alterações exigem "
                    "procedimento administrativo autorizado."
                )
        if not self.numero_inscricao:
            super().save(*args, **kwargs)
            # Número no formato 000123 a partir do id.
            self.numero_inscricao = f"{self.pk:06d}"
            type(self).objects.filter(pk=self.pk).update(
                numero_inscricao=self.numero_inscricao
            )
            return
        super().save(*args, **kwargs)


class MembroNucleo(ModeloAuditavel):
    class Parentesco(models.TextChoices):
        REQUERENTE = "REQUERENTE", "Requerente"
        CONJUGE = "CONJUGE", "Cônjuge"
        COMPANHEIRO = "COMPANHEIRO", "Companheiro(a)"
        FILHO = "FILHO", "Filho(a)"
        ENTEADO = "ENTEADO", "Enteado(a)"
        PAI = "PAI", "Pai"
        MAE = "MAE", "Mãe"
        PADRASTO = "PADRASTO", "Padrasto"
        MADRASTA = "MADRASTA", "Madrasta"
        IRMAO = "IRMAO", "Irmão(ã)"
        TUTELADO = "TUTELADO", "Menor sob tutela"
        OUTRO = "OUTRO", "Outro"

    inscricao = models.ForeignKey(
        Inscricao, on_delete=models.CASCADE, related_name="membros"
    )
    pessoa = models.ForeignKey(Pessoa, on_delete=models.PROTECT, related_name="participacoes")
    parentesco = models.CharField(max_length=20, choices=Parentesco.choices)
    dependente = models.BooleanField(default=False)
    arrimo = models.BooleanField("arrimo do núcleo", default=False)
    considerado_apuracao_renda = models.BooleanField(default=True)

    class Meta:
        verbose_name = "membro do núcleo"
        verbose_name_plural = "membros do núcleo"
        constraints = [
            models.UniqueConstraint(
                fields=["inscricao", "pessoa"], name="pessoa_unica_por_inscricao"
            )
        ]

    def __str__(self):
        return f"{self.pessoa.nome} — {self.get_parentesco_display()}"


class Renda(ModeloAuditavel):
    class Tipo(models.TextChoices):
        FORMAL = "FORMAL", "Emprego formal"
        INFORMAL = "INFORMAL", "Trabalho informal"
        AUTONOMO = "AUTONOMO", "Autônomo"
        APOSENTADORIA = "APOSENTADORIA", "Aposentadoria"
        PENSAO = "PENSAO", "Pensão"
        BENEFICIO = "BENEFICIO", "Benefício"
        OUTRA = "OUTRA", "Outra"

    membro = models.ForeignKey(
        MembroNucleo, on_delete=models.CASCADE, related_name="rendas"
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    # BPC, Bolsa Família, Seguro-Desemprego etc. entram como não computáveis (3.1.4.1).
    computavel = models.BooleanField("computável para enquadramento", default=True)
    competencia = models.CharField("competência (MM/AAAA)", max_length=7, blank=True)

    class Meta:
        verbose_name = "renda"
        verbose_name_plural = "rendas"

    def __str__(self):
        return f"{self.get_tipo_display()}: R$ {self.valor}"


class Documento(ModeloAuditavel):
    class Status(models.TextChoices):
        PENDENTE = "PENDENTE", "Pendente"
        RECEBIDO = "RECEBIDO", "Recebido"
        EM_ANALISE = "EM_ANALISE", "Em análise"
        APROVADO = "APROVADO", "Aprovado"
        REJEITADO = "REJEITADO", "Rejeitado"
        SUBSTITUICAO = "SUBSTITUICAO", "Substituição solicitada"

    inscricao = models.ForeignKey(
        Inscricao, on_delete=models.CASCADE, related_name="documentos"
    )
    pessoa = models.ForeignKey(
        Pessoa, on_delete=models.SET_NULL, null=True, blank=True, related_name="documentos"
    )
    tipo = models.CharField(max_length=100)
    obrigatorio = models.BooleanField(default=True)
    # Guardado em MEDIA_ROOT (fora da raiz web); servido por view autenticada (Fase 3).
    arquivo = models.FileField(upload_to="documentos/%Y/%m/", null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDENTE
    )
    observacao = models.TextField(blank=True)
    conferido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_conferidos",
    )
    data_conferencia = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "documento"
        verbose_name_plural = "documentos"

    def __str__(self):
        return f"{self.tipo} — {self.get_status_display()}"


class CriterioLegal(ModeloAuditavel):
    class Inciso(models.TextChoices):
        CL_I = "CL_I", "I — Habitação precária/risco ou acessibilidade"
        CL_II = "CL_II", "II — Crianças 0–12 com matrícula"
        CL_III = "CL_III", "III — Arrimo mulher ou idoso"
        CL_IV = "CL_IV", "IV — Renda ≤ R$ 4.863,00"

    inscricao = models.ForeignKey(
        Inscricao, on_delete=models.CASCADE, related_name="criterios_legais"
    )
    inciso = models.CharField(max_length=6, choices=Inciso.choices)
    atendido = models.BooleanField(default=False)
    comprovado = models.BooleanField(default=False)
    pontos = models.PositiveIntegerField(default=0)
    documento_comprova = models.ForeignKey(
        Documento, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = "critério legal"
        verbose_name_plural = "critérios legais"
        constraints = [
            models.UniqueConstraint(
                fields=["inscricao", "inciso"], name="inciso_unico_por_inscricao"
            )
        ]

    def __str__(self):
        return f"{self.inciso}: {self.pontos} pts"


class CriterioComplementar(ModeloAuditavel):
    inscricao = models.OneToOneField(
        Inscricao, on_delete=models.CASCADE, related_name="criterio_complementar"
    )
    renda_per_capita = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    pontos_renda = models.PositiveIntegerField(default=0)
    aluguel_medio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    percentual = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    pontos_aluguel = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "critério complementar"
        verbose_name_plural = "critérios complementares"

    def __str__(self):
        return f"CC: {self.pontos_renda + self.pontos_aluguel} pts"


class Classificacao(ModeloAuditavel):
    inscricao = models.OneToOneField(
        Inscricao, on_delete=models.CASCADE, related_name="classificacao"
    )
    posicao = models.PositiveIntegerField(null=True, blank=True)
    pontuacao = models.PositiveIntegerField(default=0, db_index=True)
    dependentes_ate_12 = models.PositiveIntegerField(default=0)
    idosos = models.PositiveIntegerField(default=0)
    empate_pendente_sorteio = models.BooleanField(default=False)
    sorteio_ata = models.FileField(upload_to="sorteios/%Y/%m/", null=True, blank=True)

    class Meta:
        verbose_name = "classificação"
        verbose_name_plural = "classificações"
        ordering = ("posicao",)

    def __str__(self):
        return f"{self.posicao or '—'}º — {self.pontuacao} pts"
