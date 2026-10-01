from django import forms

from .models import Veiculo


class VeiculoForm(forms.ModelForm):
    class Meta:
        model = Veiculo
        fields = ["nome", "tipo", "placa", "ativo", "observacoes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            if isinstance(campo.widget, forms.CheckboxInput):
                campo.widget.attrs.setdefault("class", "campo-check")
            else:
                campo.widget.attrs.setdefault("class", "campo")

    def clean_nome(self):
        nome = self.cleaned_data["nome"].strip()
        # Impede identificação duplicada, ignorando maiúsculas/minúsculas.
        existentes = Veiculo.objects.filter(nome__iexact=nome)
        if self.instance.pk:
            existentes = existentes.exclude(pk=self.instance.pk)
        if existentes.exists():
            raise forms.ValidationError(f"Já existe um veículo com a identificação “{nome}”.")
        return nome
