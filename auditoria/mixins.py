"""Mixin que torna um modelo auditável: cada criação, alteração (campo a campo)
e exclusão gera registro(s) na tabela :class:`auditoria.models.Auditoria`.

Limitação conhecida: operações em massa de QuerySet (``.update()`` / ``.delete()``)
não passam por ``save()``/``delete()`` e, portanto, não são auditadas. No sistema,
alterações de cadastro devem passar pelos formulários/admin (que chamam ``save()``).
"""

from __future__ import annotations

from django.db import models

from .middleware import ip_atual, usuario_atual


class ModeloAuditavel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        justificativa = kwargs.pop(
            "justificativa", getattr(self, "_justificativa_auditoria", "")
        )
        from .models import Auditoria

        criando = self._state.adding or self.pk is None
        antigo = None
        if not criando:
            antigo = type(self).objects.filter(pk=self.pk).first()

        super().save(*args, **kwargs)

        usuario, ip, tabela = usuario_atual(), ip_atual(), self._meta.label

        if criando or antigo is None:
            Auditoria.objects.create(
                usuario=usuario,
                ip=ip,
                operacao=Auditoria.Operacao.CRIACAO,
                tabela=tabela,
                registro_id=str(self.pk),
                justificativa=justificativa,
            )
            return

        for campo in self._meta.concrete_fields:
            if campo.primary_key:
                continue
            antes = getattr(antigo, campo.attname)
            depois = getattr(self, campo.attname)
            if antes != depois:
                Auditoria.objects.create(
                    usuario=usuario,
                    ip=ip,
                    operacao=Auditoria.Operacao.ALTERACAO,
                    tabela=tabela,
                    registro_id=str(self.pk),
                    campo=campo.name,
                    valor_anterior="" if antes is None else str(antes),
                    valor_novo="" if depois is None else str(depois),
                    justificativa=justificativa,
                )

    def delete(self, *args, **kwargs):
        from .models import Auditoria

        pk, tabela = self.pk, self._meta.label
        justificativa = getattr(self, "_justificativa_auditoria", "")
        resultado = super().delete(*args, **kwargs)
        Auditoria.objects.create(
            usuario=usuario_atual(),
            ip=ip_atual(),
            operacao=Auditoria.Operacao.EXCLUSAO,
            tabela=tabela,
            registro_id=str(pk),
            justificativa=justificativa,
        )
        return resultado
