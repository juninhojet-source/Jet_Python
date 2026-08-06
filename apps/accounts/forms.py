"""Formulários de autenticação e gestão de usuários."""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()

CAMPO = "campo"


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"class": CAMPO, "autofocus": True, "placeholder": "Usuário"}
        )
        self.fields["password"].widget.attrs.update(
            {"class": CAMPO, "placeholder": "Senha"}
        )


class UsuarioCreateForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "telefone", "perfil")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs.setdefault("class", CAMPO)


class UsuarioUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "telefone", "perfil", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome, campo in self.fields.items():
            if nome == "is_active":
                campo.widget.attrs.setdefault("class", "campo-check")
            else:
                campo.widget.attrs.setdefault("class", CAMPO)
