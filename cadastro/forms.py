"""Formulários das telas de operação (Fase 3)."""

from __future__ import annotations

from django import forms
from django.utils import timezone

from .models import Documento, Inscricao, MembroNucleo, Pessoa, Renda
from .validadores import cpf_valido, so_digitos

# DateInput compatível com <input type="date"> (valor em ISO YYYY-MM-DD),
# para que a data já preenchida apareça ao editar.
_DATA = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class DinheiroInput(forms.TextInput):
    """Campo monetário no formato brasileiro (1.500,50) com prefixo R$.

    - Exibe o valor como 1.234,56 (milhar com ponto, decimal com vírgula);
    - Aceita a digitação em português e normaliza para o Decimal ao salvar;
    - A classe ``dinheiro`` faz o template desenhar o "R$" e o JS aplicar a máscara.
    """

    def __init__(self, attrs=None):
        base = {"class": "dinheiro", "inputmode": "decimal", "placeholder": "0,00"}
        if attrs:
            base.update(attrs)
        super().__init__(base)

    def format_value(self, value):
        if value in (None, ""):
            return ""
        try:
            from decimal import Decimal

            d = Decimal(str(value).replace(",", "."))
        except Exception:
            return super().format_value(value)
        # 1234.56 -> "1.234,56"
        return f"{d:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def value_from_datadict(self, data, files, name):
        v = super().value_from_datadict(data, files, name)
        if isinstance(v, str) and "," in v:
            # formato BR: remove milhar (.) e usa ponto como decimal
            v = v.replace(".", "").replace(",", ".")
        return v.strip() if isinstance(v, str) else v


# Atributos do campo de CPF (máscara 000.000.000-00 aplicada pelo JS).
_CPF_ATTRS = {"class": "cpf", "maxlength": "14", "inputmode": "numeric",
              "placeholder": "000.000.000-00"}
# Atributos do campo de CEP (máscara 00000-000 pelo JS; ViaCEP no cep.js).
_CEP_ATTRS = {"class": "cep", "maxlength": "9", "inputmode": "numeric",
              "placeholder": "00000-000"}


class PessoaForm(forms.ModelForm):
    class Meta:
        model = Pessoa
        fields = ["nome", "cpf", "data_nascimento", "sexo", "estado_civil", "brasileiro", "pcd"]
        widgets = {
            "data_nascimento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "cpf": forms.TextInput(attrs=_CPF_ATTRS),
        }

    def clean_cpf(self):
        cpf = so_digitos(self.cleaned_data["cpf"])
        if not cpf_valido(cpf):
            raise forms.ValidationError("CPF inválido.")
        return cpf


class RequerenteInscricaoForm(forms.Form):
    """Cria o requerente (Pessoa) e a Inscrição em uma tela só."""

    nome = forms.CharField(label="Nome completo", max_length=200)
    cpf = forms.CharField(label="CPF", max_length=14,
                          widget=forms.TextInput(attrs=_CPF_ATTRS))
    data_nascimento = forms.DateField(
        label="Data de nascimento",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    sexo = forms.ChoiceField(label="Sexo", choices=Pessoa.Sexo.choices)
    estado_civil = forms.ChoiceField(
        label="Estado civil", choices=[("", "—")] + list(Pessoa.EstadoCivil.choices), required=False
    )
    brasileiro = forms.BooleanField(label="Brasileiro nato/naturalizado", required=False, initial=True)
    pcd = forms.BooleanField(label="Pessoa com deficiência", required=False)

    telefone = forms.CharField(label="Telefone", max_length=20, required=False)
    email = forms.EmailField(label="E-mail", required=False)
    # CEP antes do endereço: ao sair do campo, o ViaCEP preenche cidade/UF/endereço.
    cep = forms.CharField(label="CEP", max_length=9, required=False,
                          widget=forms.TextInput(attrs=_CEP_ATTRS))
    endereco = forms.CharField(label="Endereço", max_length=200, required=False)
    numero = forms.CharField(label="Número", max_length=20, required=False)
    complemento = forms.CharField(label="Complemento", max_length=100, required=False)
    bairro = forms.CharField(label="Bairro", max_length=100, required=False)
    cidade = forms.CharField(label="Cidade", max_length=100, required=False)
    uf = forms.CharField(label="UF", max_length=2, required=False)

    def clean_cpf(self):
        cpf = so_digitos(self.cleaned_data["cpf"])
        if not cpf_valido(cpf):
            raise forms.ValidationError("CPF inválido.")
        pessoa = Pessoa.objects.filter(cpf=cpf).first()
        if pessoa:
            part = pessoa.participacoes.select_related("inscricao__requerente").first()
            if part:
                i = part.inscricao
                raise forms.ValidationError(
                    f"CPF já vinculado à inscrição {i.numero_inscricao} "
                    f"(requerente: {i.requerente.nome}). É permitida uma única inscrição "
                    f"por núcleo familiar (itens 3.2/3.3.4)."
                )
            raise forms.ValidationError("Já existe pessoa cadastrada com este CPF.")
        return cpf

    def salvar(self) -> Inscricao:
        d = self.cleaned_data
        pessoa = Pessoa.objects.create(
            nome=d["nome"], cpf=d["cpf"], data_nascimento=d["data_nascimento"],
            sexo=d["sexo"], estado_civil=d["estado_civil"], brasileiro=d["brasileiro"], pcd=d["pcd"],
        )
        inscricao = Inscricao.objects.create(
            requerente=pessoa,
            telefone=d["telefone"], email=d["email"], endereco=d["endereco"],
            numero=d["numero"], complemento=d["complemento"], bairro=d["bairro"],
            cidade=d["cidade"], uf=d["uf"], cep=d["cep"],
        )
        # O requerente também é o primeiro membro do núcleo.
        MembroNucleo.objects.create(
            inscricao=inscricao, pessoa=pessoa, parentesco=MembroNucleo.Parentesco.REQUERENTE
        )
        return inscricao


class InscricaoContatoForm(forms.ModelForm):
    """Dados declarados de contato/endereço (bloqueados após a finalização)."""

    class Meta:
        model = Inscricao
        fields = ["telefone", "email", "cep", "endereco", "numero", "complemento",
                  "bairro", "cidade", "uf", "ciencia_lgpd"]
        widgets = {"cep": forms.TextInput(attrs=_CEP_ATTRS)}
        labels = {
            "ciencia_lgpd": "O requerente declara estar ciente do tratamento dos "
            "dados pessoais conforme a Política de Privacidade (LGPD).",
        }


class AvaliacaoForm(forms.ModelForm):
    """Fatos apurados pela análise: Critérios Legais, requisitos documentais e aluguel.

    Editável pela análise mesmo após a finalização (procedimento autorizado e
    registrado), pois não altera os dados declarados pelo candidato.
    """

    class Meta:
        model = Inscricao
        fields = [
            "data_referencia",
            "habitacao_precaria_ou_risco", "matricula_comprovada",
            "residencia_5anos_comprovada", "nao_proprietario_declarado", "nao_beneficiado_declarado",
            "aluguel_mes_1", "aluguel_mes_2", "aluguel_mes_3", "aluguel_cedido",
        ]
        widgets = {
            "data_referencia": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "aluguel_mes_1": DinheiroInput(),
            "aluguel_mes_2": DinheiroInput(),
            "aluguel_mes_3": DinheiroInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        insc = self.instance
        # Data de referência associada ao cadastramento: padrão = data do cadastro.
        if insc and insc.pk and getattr(insc, "data_inscricao", None):
            dt = timezone.localtime(insc.data_inscricao)
            self.fields["data_referencia"].help_text = (
                f"Padrão: data do cadastramento — {dt.strftime('%d/%m/%Y %H:%M')}."
            )
            if not insc.data_referencia and not self.initial.get("data_referencia"):
                self.initial["data_referencia"] = dt.date()

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("data_referencia"):
            insc = self.instance
            if insc and getattr(insc, "data_inscricao", None):
                cleaned["data_referencia"] = timezone.localtime(insc.data_inscricao).date()
        return cleaned


class MembroForm(forms.Form):
    """Cria/edita um integrante (Pessoa + vínculo no núcleo)."""

    nome = forms.CharField(label="Nome completo", max_length=200)
    cpf = forms.CharField(label="CPF", max_length=14,
                          widget=forms.TextInput(attrs=_CPF_ATTRS))
    data_nascimento = forms.DateField(
        label="Data de nascimento",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    sexo = forms.ChoiceField(label="Sexo", choices=Pessoa.Sexo.choices)
    pcd = forms.BooleanField(label="Pessoa com deficiência", required=False)
    parentesco = forms.ChoiceField(label="Parentesco", choices=MembroNucleo.Parentesco.choices)
    dependente = forms.BooleanField(label="Dependente", required=False)
    arrimo = forms.BooleanField(label="Arrimo do núcleo", required=False)
    considerado_apuracao_renda = forms.BooleanField(
        label="Considerar na apuração da renda per capita", required=False, initial=True
    )

    def __init__(self, *args, inscricao=None, **kwargs):
        self.inscricao = inscricao
        super().__init__(*args, **kwargs)
        # O requerente já é o titular do núcleo; não deve ser oferecido como
        # parentesco ao adicionar os demais integrantes.
        self.fields["parentesco"].choices = [
            c for c in MembroNucleo.Parentesco.choices
            if c[0] != MembroNucleo.Parentesco.REQUERENTE
        ]

    def clean_cpf(self):
        cpf = so_digitos(self.cleaned_data["cpf"])
        if not cpf_valido(cpf):
            raise forms.ValidationError("CPF inválido.")
        pessoa = Pessoa.objects.filter(cpf=cpf).first()
        if pessoa:
            for part in pessoa.participacoes.select_related("inscricao__requerente"):
                i = part.inscricao
                if self.inscricao and i.pk == self.inscricao.pk:
                    raise forms.ValidationError("Esta pessoa já é membro deste núcleo.")
                raise forms.ValidationError(
                    f"CPF já vinculado à inscrição {i.numero_inscricao} "
                    f"(requerente: {i.requerente.nome}). Cada pessoa pode integrar apenas um núcleo."
                )
        return cpf

    def salvar(self) -> MembroNucleo:
        d = self.cleaned_data
        pessoa, _ = Pessoa.objects.get_or_create(
            cpf=d["cpf"],
            defaults={
                "nome": d["nome"], "data_nascimento": d["data_nascimento"],
                "sexo": d["sexo"], "pcd": d["pcd"],
            },
        )
        return MembroNucleo.objects.create(
            inscricao=self.inscricao, pessoa=pessoa, parentesco=d["parentesco"],
            dependente=d["dependente"], arrimo=d["arrimo"],
            considerado_apuracao_renda=d["considerado_apuracao_renda"],
        )


class RendaForm(forms.ModelForm):
    class Meta:
        model = Renda
        fields = ["tipo", "valor", "computavel", "competencia"]
        widgets = {"valor": DinheiroInput()}


class RendaWizardForm(forms.ModelForm):
    """Renda com seleção do integrante (usada no assistente de cadastro)."""

    membro = forms.ModelChoiceField(queryset=MembroNucleo.objects.none(), label="Integrante")

    class Meta:
        model = Renda
        fields = ["membro", "tipo", "valor", "computavel", "competencia"]
        widgets = {"valor": DinheiroInput()}

    def __init__(self, *args, inscricao=None, **kwargs):
        super().__init__(*args, **kwargs)
        if inscricao is not None:
            self.fields["membro"].queryset = MembroNucleo.objects.filter(
                inscricao=inscricao
            ).select_related("pessoa")

    def salvar(self) -> Renda:
        renda = self.save(commit=False)
        renda.membro = self.cleaned_data["membro"]
        renda.save()
        return renda


class DocumentoForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = ["tipo", "pessoa", "obrigatorio", "arquivo", "status", "observacao"]

    def __init__(self, *args, inscricao=None, **kwargs):
        super().__init__(*args, **kwargs)
        # O anexo é opcional — pode-se apenas registrar o documento apresentado.
        self.fields["arquivo"].required = False
        self.fields["arquivo"].label = "Anexo (opcional)"
        self.fields["pessoa"].required = False
        if inscricao is not None:
            # Restringe as pessoas às do núcleo.
            self.fields["pessoa"].queryset = Pessoa.objects.filter(
                participacoes__inscricao=inscricao
            ).distinct()
