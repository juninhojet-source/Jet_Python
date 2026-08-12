"""Formulários de agendamento e do controle de embarque."""
from django import forms

from .models import Agendamento, Embarque, StatusAgendamento


class AgendamentoForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = [
            "paciente", "acompanhante", "contato", "data", "horario",
            "destino", "local_consulta", "procedimento",
            "veiculo", "tipo_veiculo", "local_embarque", "hora_embarque",
            "status", "observacoes",
        ]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "horario": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "hora_embarque": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["data"].input_formats = ["%Y-%m-%d"]
        self.fields["horario"].input_formats = ["%H:%M"]
        self.fields["hora_embarque"].input_formats = ["%H:%M"]
        self.fields["paciente"].queryset = self.fields["paciente"].queryset.filter(ativo=True)
        self.fields["destino"].queryset = self.fields["destino"].queryset.filter(ativo=True)
        self.fields["veiculo"].queryset = self.fields["veiculo"].queryset.filter(ativo=True)
        self.fields["veiculo"].empty_label = "A definir"
        for campo in self.fields.values():
            campo.widget.attrs.setdefault("class", "campo")

    def clean(self):
        cleaned = super().clean()
        # Preenche o contato a partir do telefone do paciente, se vazio.
        if not cleaned.get("contato") and cleaned.get("paciente"):
            cleaned["contato"] = cleaned["paciente"].telefone_principal
        return cleaned


class EmbarqueForm(forms.ModelForm):
    class Meta:
        model = Agendamento
        fields = ["embarque", "hora_embarque_real", "hora_desembarque_real", "observacoes"]
        widgets = {
            "hora_embarque_real": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "hora_desembarque_real": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "observacoes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["hora_embarque_real"].input_formats = ["%H:%M"]
        self.fields["hora_desembarque_real"].input_formats = ["%H:%M"]
        for campo in self.fields.values():
            campo.widget.attrs.setdefault("class", "campo")

    def save(self, commit=True):
        obj = super().save(commit=False)
        # Reflete o embarque no status do agendamento.
        if obj.embarque == Embarque.EMBARCOU and obj.status in {
            StatusAgendamento.AGENDADO, StatusAgendamento.CONFIRMADO,
        }:
            obj.status = StatusAgendamento.EM_VIAGEM
        elif obj.embarque == Embarque.NAO_EMBARCOU:
            obj.status = StatusAgendamento.FALTOU
        if commit:
            obj.save()
        return obj
