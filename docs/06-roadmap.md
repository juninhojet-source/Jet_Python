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

## Fase 1 — Motor de pontuação (núcleo)
Módulo Python puro, sem Django, que lê `parametros_edital.yaml` e, dado um núcleo familiar,
retorna `CL`, `CC`, `P`, a faixa de cada complementar e as chaves de desempate.
- Testes unitários em **todas as bordas** de faixa (per capita e aluguel).
- Teste de aceitação do exemplo da seção F de [04-regras](04-regras-de-negocio.md) (= 141 pts).

## Fase 2 — Fundação Django + modelos
- Projeto Django, `settings` com SQLite (dev) e PostgreSQL (prod) por variável de ambiente.
- Models do [03-modelo-de-dados](03-modelo-de-dados.md); migrações; Django Admin básico.
- Autenticação e perfis; middleware de **auditoria** (append-only).

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
