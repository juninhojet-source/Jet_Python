"""Formulário de cadastro de paciente com validações e deduplicação."""
from django import forms

from apps.core.validators import apenas_digitos, formatar_telefone

from .models import Paciente


class PacienteForm(forms.ModelForm):
    # Aceitam máscara/pontuação; são normalizados para dígitos no clean.
    cpf = forms.CharField(label="CPF", required=False, max_length=14)
    cns = forms.CharField(
        label="Cartão SUS (CNS)",
        required=False,
        max_length=18,
        help_text="15 dígitos. Usado no BPA e para evitar duplicidade.",
    )
    # Aceita a máscara "NNNNN-NNN"; é normalizado para 8 dígitos no clean.
    cep = forms.CharField(label="CEP", required=False, max_length=9)

    class Meta:
        model = Paciente
        fields = [
            "nome", "cns", "cpf", "data_nascimento", "sexo", "raca_cor", "etnia",
            "nacionalidade", "cep", "logradouro", "numero", "complemento", "bairro",
            "municipio", "telefone_principal", "telefone_secundario", "observacoes",
            "ativo",
        ]
        widgets = {
            "data_nascimento": forms.DateInput(
                attrs={"type": "date"}, format="%Y-%m-%d"
            ),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["data_nascimento"].input_formats = ["%Y-%m-%d"]
        for nome, campo in self.fields.items():
            if isinstance(campo.widget, forms.CheckboxInput):
                campo.widget.attrs.setdefault("class", "campo-check")
            elif isinstance(campo.widget, forms.Select):
                campo.widget.attrs.setdefault("class", "campo")
            else:
                campo.widget.attrs.setdefault("class", "campo")

    def clean_cpf(self):
        cpf = apenas_digitos(self.cleaned_data.get("cpf"))
        if not cpf:
            return None
        existe = Paciente.objects.filter(cpf=cpf)
        if self.instance.pk:
            existe = existe.exclude(pk=self.instance.pk)
        if existe.exists():
            raise forms.ValidationError("CPF já cadastrado.")
        return cpf

    def clean_cns(self):
        cns = apenas_digitos(self.cleaned_data.get("cns"))
        if not cns:
            return None
        existe = Paciente.objects.filter(cns=cns)
        if self.instance.pk:
            existe = existe.exclude(pk=self.instance.pk)
        if existe.exists():
            raise forms.ValidationError("Cartão SUS (CNS) já cadastrado.")
        return cns

    def clean_cep(self):
        return apenas_digitos(self.cleaned_data.get("cep"))[:8]

    def clean_telefone_principal(self):
        return formatar_telefone(self.cleaned_data.get("telefone_principal"))

    def clean_telefone_secundario(self):
        return formatar_telefone(self.cleaned_data.get("telefone_secundario"))

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("cpf") and not cleaned.get("cns"):
            raise forms.ValidationError(
                "Informe ao menos um identificador: CPF ou Cartão SUS (CNS)."
            )
        return cleaned


class PacienteRapidoForm(PacienteForm):
    """Versão enxuta para cadastro rápido a partir do agendamento."""

    class Meta(PacienteForm.Meta):
        fields = [
            "nome", "data_nascimento", "sexo", "raca_cor",
            "telefone_principal", "municipio",
        ]
