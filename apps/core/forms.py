"""Formulários do núcleo (cadastros auxiliares)."""
from django import forms

from .models import Municipio
from .validators import apenas_digitos


class MunicipioForm(forms.ModelForm):
    class Meta:
        model = Municipio
        fields = ["nome", "uf", "codigo_ibge"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["uf"].initial = "MG"
        self.fields["codigo_ibge"].help_text = "7 dígitos. Necessário para o BPA."
        for campo in self.fields.values():
            campo.widget.attrs.setdefault("class", "campo")

    def clean_nome(self):
        return self.cleaned_data["nome"].strip()

    def clean_uf(self):
        return self.cleaned_data["uf"].strip().upper()

    def clean_codigo_ibge(self):
        codigo = apenas_digitos(self.cleaned_data.get("codigo_ibge"))
        if len(codigo) != 7:
            raise forms.ValidationError("O código IBGE deve ter 7 dígitos.")
        return codigo

    def clean(self):
        cleaned = super().clean()
        nome = cleaned.get("nome")
        uf = cleaned.get("uf")
        # Impede município duplicado (mesmo nome + UF), ignorando maiúsculas.
        if nome and uf:
            existentes = Municipio.objects.filter(nome__iexact=nome, uf__iexact=uf)
            if self.instance.pk:
                existentes = existentes.exclude(pk=self.instance.pk)
            if existentes.exists():
                self.add_error("nome", f"O município “{nome}/{uf}” já está cadastrado.")
        return cleaned
