"""Formulários das telas de operação (Fase 3)."""

from __future__ import annotations

from django import forms
from django.utils import timezone

from .models import Documento, Inscricao, MembroNucleo, Pessoa, Renda
from .validadores import cpf_valido, so_digitos

# DateInput compatível com <input type="date"> (valor em ISO YYYY-MM-DD),
# para que a data já preenchida apareça ao editar.
_DATA = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class DinheiroInput(forms.NumberInput):
    """Campo monetário: só aceita números (>= 0, 2 casas) e exibe prefixo R$.

    A classe ``dinheiro`` faz o template (_campos.html) desenhar o "R$" à frente.
    """

    def __init__(self, attrs=None):
        base = {
            "step": "0.01", "min": "0", "inputmode": "decimal",
            "class": "dinheiro", "placeholder": "0,00",
        }
        if attrs:
            base.update(attrs)
        super().__init__(base)


class PessoaForm(forms.ModelForm):
    class Meta:
        model = Pessoa
        fields = ["nome", "cpf", "data_nascimento", "sexo", "estado_civil", "brasileiro", "pcd"]
        widgets = {"data_nascimento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def clean_cpf(self):
        cpf = so_digitos(self.cleaned_data["cpf"])
        if not cpf_valido(cpf):
            raise forms.ValidationError("CPF inválido.")
        return cpf


class RequerenteInscricaoForm(forms.Form):
    """Cria o requerente (Pessoa) e a Inscrição em uma tela só."""

    nome = forms.CharField(label="Nome completo", max_length=200)
    cpf = forms.CharField(label="CPF", max_length=14)
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
    endereco = forms.CharField(label="Endereço", max_length=200, required=False)
    numero = forms.CharField(label="Número", max_length=20, required=False)
    complemento = forms.CharField(label="Complemento", max_length=100, required=False)
    bairro = forms.CharField(label="Bairro", max_length=100, required=False)
    cidade = forms.CharField(label="Cidade", max_length=100, required=False)
    uf = forms.CharField(label="UF", max_length=2, required=False)
    cep = forms.CharField(label="CEP", max_length=9, required=False)

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
        fields = ["telefone", "email", "endereco", "numero", "complemento", "bairro",
                  "cidade", "uf", "cep", "ciencia_lgpd"]
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
    cpf = forms.CharField(label="CPF", max_length=14)
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
