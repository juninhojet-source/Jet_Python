# 06 — Roadmap de Desenvolvimento

Fases sugeridas. A ordem prioriza a parte **legalmente sensível** (motor de pontuação) e a
**auditoria** desde o início.

## Fase 0 — Design (atual)
- [x] Diagnóstico do edital + documento de requisitos
- [x] Especificação funcional
- [x] Modelo de dados
- [x] Matriz de regras parametrizada (`regras/parametros_edital.yaml`)
- [x] Requisitos de segurança/LGPD
- [ ] **Validação das decisões pendentes D-1..D-6 com a Comissão de Inscrição**

## Fase 1 — Motor de pontuação (núcleo) ✅
Módulo Python puro (`motor/`), sem Django, que lê `parametros_edital.yaml` e, dado um núcleo
familiar, retorna `CL`, `CC`, `P`, a faixa de cada complementar e as chaves de desempate.
- [x] `motor/modelos.py` — `NucleoFamiliar`, `Membro`, `Renda`, `Aluguel`, `ResultadoPontuacao`
- [x] `motor/parametros.py` — carrega o YAML com `Decimal` (sem erro de ponto flutuante)
- [x] `motor/pontuacao.py` — `calcular_pontuacao()` + `chave_ordenacao()` (desempate)
- [x] Testes unitários em **todas as bordas** de faixa — `tests/test_faixas.py`
- [x] Testes do motor + desempate + aceitação (= 141 pts) — `tests/test_pontuacao.py`
- [x] Exemplo executável — `examples/demo_pontuacao.py`

Rodar os testes: `pip install -r requirements-dev.txt && python -m pytest` (56 testes).

## Fase 2 — Fundação Django + modelos ✅
- [x] Projeto Django (`config/`), `settings` com SQLite (dev) e PostgreSQL (prod) por env
- [x] Models do [03-modelo-de-dados](03-modelo-de-dados.md) (`cadastro/models.py`) + migrações
- [x] Django Admin com inlines e ações "recalcular pontuação" / "gerar classificação"
- [x] Perfis de acesso como Grupos (`contas/`) — Administrador, Atendente, Analista, Comissão, Consulta
- [x] **Auditoria append-only** (`auditoria/`): middleware de usuário/IP + mixin que
      registra criação, alteração campo a campo e exclusão
- [x] **Bloqueio pós-finalização** da inscrição (Anexo II) no `save()`
- [x] Ponte com o motor da Fase 1 (`cadastro/services.py`): recálculo e classificação
- [x] Testes de integração (`cadastro/tests.py`) — 9 testes

Rodar: `python manage.py migrate && python manage.py test` (9 testes Django).

## Fase 3 — Cadastro
- Telas M2 (requerente), M3 (composição), M4 (renda), M5 (documentos com upload controlado).
- Cálculos derivados exibidos; validações de requisito (M6) com sinalização "não apto".
- Fluxo de situações + **bloqueio pós-finalização**.

## Fase 4 — Análise, pontuação e classificação
- Integração do motor (Fase 1) com os dados (M7).
- Homologação (Atendente → Analista → Comissão).
- Classificação (M8): ordenação + desempate automático + marcação de empates para sorteio.

## Fase 5 — Relatórios, exportação e dashboard
- M9 (ficha PDF, classificação PDF/Excel, pendências, indeferidos, aptos, empates, auditoria).
- M1 (dashboard de indicadores).

## Fase 6 — Endurecimento e implantação
- Revisão de segurança/LGPD; HTTPS; backup criptografado.
- Migração para PostgreSQL; testes de restauração; homologação com a Comissão.

## Princípio transversal
Toda regra do edital é **parâmetro**, não código. Mudou o edital → muda o YAML e os testes;
o motor permanece.
