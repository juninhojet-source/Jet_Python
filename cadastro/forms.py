"""Formulários das telas de operação (Fase 3)."""

from __future__ import annotations

from django import forms

from .models import Documento, Inscricao, MembroNucleo, Pessoa, Renda

_CTRL = {"class": "campo"}


class PessoaForm(forms.ModelForm):
    class Meta:
        model = Pessoa
        fields = ["nome", "cpf", "data_nascimento", "sexo", "estado_civil", "brasileiro", "pcd"]
        widgets = {"data_nascimento": forms.DateInput(attrs={"type": "date", **_CTRL})}


class RequerenteInscricaoForm(forms.Form):
    """Cria o requerente (Pessoa) e a Inscrição em uma tela só."""

    nome = forms.CharField(label="Nome completo", max_length=200)
    cpf = forms.CharField(label="CPF", max_length=14)
    data_nascimento = forms.DateField(
        label="Data de nascimento", widget=forms.DateInput(attrs={"type": "date"})
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
    cep = forms.CharField(label="CEP", max_length=9, required=False)

    def clean_cpf(self):
        cpf = self.cleaned_data["cpf"].strip()
        if Pessoa.objects.filter(cpf=cpf).exists():
            raise forms.ValidationError(
                "Já existe pessoa cadastrada com este CPF. Uma inscrição por núcleo (itens 3.2/3.3.4)."
            )
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
            numero=d["numero"], complemento=d["complemento"], bairro=d["bairro"], cep=d["cep"],
        )
        # O requerente também é o primeiro membro do núcleo.
        MembroNucleo.objects.create(
            inscricao=inscricao, pessoa=pessoa, parentesco=MembroNucleo.Parentesco.REQUERENTE
        )
        return inscricao


class InscricaoAnaliseForm(forms.ModelForm):
    """Edição de contato/endereço, fatos dos Critérios Legais e aluguel."""

    class Meta:
        model = Inscricao
        fields = [
            "telefone", "email", "endereco", "numero", "complemento", "bairro", "cep",
            "data_referencia",
            "habitacao_precaria_ou_risco", "matricula_comprovada",
            "residencia_5anos_comprovada", "nao_proprietario_declarado", "nao_beneficiado_declarado",
            "aluguel_mes_1", "aluguel_mes_2", "aluguel_mes_3", "aluguel_cedido",
        ]
        widgets = {"data_referencia": forms.DateInput(attrs={"type": "date"})}


class MembroForm(forms.Form):
    """Cria/edita um integrante (Pessoa + vínculo no núcleo)."""

    nome = forms.CharField(label="Nome completo", max_length=200)
    cpf = forms.CharField(label="CPF", max_length=14)
    data_nascimento = forms.DateField(
        label="Data de nascimento", widget=forms.DateInput(attrs={"type": "date"})
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
        cpf = self.cleaned_data["cpf"].strip()
        qs = Pessoa.objects.filter(cpf=cpf)
        if qs.exists():
            pessoa = qs.first()
            if self.inscricao and pessoa.participacoes.filter(inscricao=self.inscricao).exists():
                raise forms.ValidationError("Esta pessoa já é membro deste núcleo.")
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


class DocumentoForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = ["tipo", "pessoa", "obrigatorio", "arquivo", "status", "observacao"]

    def __init__(self, *args, inscricao=None, **kwargs):
        super().__init__(*args, **kwargs)
        if inscricao is not None:
            # Restringe as pessoas às do núcleo.
            self.fields["pessoa"].queryset = Pessoa.objects.filter(
                participacoes__inscricao=inscricao
            ).distinct()
