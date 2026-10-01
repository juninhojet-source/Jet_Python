"""Validador de política de senha forte."""
from django.core.exceptions import ValidationError


class SenhaForteValidator:
    """Exige que a senha contenha letras e números."""

    def validate(self, password, user=None):
        if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
            raise ValidationError(
                "A senha deve conter letras e números.", code="senha_sem_letra_ou_numero"
            )

    def get_help_text(self):
        return "A senha deve conter letras e números."
