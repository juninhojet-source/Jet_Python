"""Envia um e-mail de teste usando a configuração atual (valida o SMTP).

Uso:
    python manage.py email_teste destinatario@exemplo.com
"""

from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Envia um e-mail de teste para validar a configuração de SMTP."

    def add_arguments(self, parser):
        parser.add_argument("destino", help="e-mail de destino do teste")

    def handle(self, *args, **opts):
        destino = opts["destino"]
        self.stdout.write(
            f"Backend: {settings.EMAIL_BACKEND}\n"
            f"Host: {getattr(settings, 'EMAIL_HOST', '') or '(vazio)'}:{getattr(settings, 'EMAIL_PORT', '')} "
            f"TLS={getattr(settings, 'EMAIL_USE_TLS', False)} SSL={getattr(settings, 'EMAIL_USE_SSL', False)}\n"
            f"De: {settings.DEFAULT_FROM_EMAIL}\n"
        )
        msg = EmailMessage(
            "Teste de e-mail — Sistema MCMV",
            "Este é um e-mail de teste do Sistema MCMV (Barão de Cocais/MG). "
            "Se você recebeu, o envio está configurado corretamente.",
            settings.DEFAULT_FROM_EMAIL,
            [destino],
        )
        try:
            enviados = msg.send(fail_silently=False)
        except Exception as exc:
            raise CommandError(f"Falha ao enviar: {exc}")
        self.stdout.write(self.style.SUCCESS(f"OK — {enviados} mensagem(ns) enviada(s) para {destino}."))
