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
