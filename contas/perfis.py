"""Perfis de acesso do sistema (item 6 do edital / item 17 dos requisitos).

Implementados como Grupos do Django. As permissões finas por modelo serão
atribuídas na Fase 3, quando existirem as telas; aqui ficam os grupos criados.
"""

from __future__ import annotations

PERFIS = [
    ("Administrador", "Acesso total, incluindo usuários e parâmetros do edital"),
    ("Atendente", "Cadastra e edita inscrições em rascunho; anexa documentos"),
    ("Analista", "Analisa documentação, valida critérios, aprova/rejeita documentos"),
    ("Comissao", "Homologa, revisa e valida a classificação; registra sorteio"),
    ("Consulta", "Somente leitura e relatórios"),
]

NOMES_PERFIS = [nome for nome, _ in PERFIS]
