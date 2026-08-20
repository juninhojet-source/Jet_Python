from django import forms

from .models import Destino


class DestinoForm(forms.ModelForm):
    class Meta:
        model = Destino
        fields = ["nome", "tipo", "municipio", "endereco", "telefone", "ativo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            if isinstance(campo.widget, forms.CheckboxInput):
                campo.widget.attrs.setdefault("class", "campo-check")
            else:
                campo.widget.attrs.setdefault("class", "campo")

    def clean_nome(self):
        return self.cleaned_data["nome"].strip()

    def clean(self):
        cleaned = super().clean()
        nome = cleaned.get("nome")
        municipio = cleaned.get("municipio")
        # Impede destino duplicado (mesmo nome + município), ignorando
        # diferenças de maiúsculas/minúsculas e espaços.
        if nome and municipio:
            existentes = Destino.objects.filter(nome__iexact=nome, municipio=municipio)
            if self.instance.pk:
                existentes = existentes.exclude(pk=self.instance.pk)
            if existentes.exists():
                self.add_error("nome", f"Já existe um destino “{nome}” em {municipio}.")
        return cleaned
