# Sistema MCMV — Cadastro Habitacional / Barão de Cocais/MG

Sistema interno para operacionalizar o **Edital de Chamamento nº 001/2026** — inscrição,
análise, pontuação e classificação de Núcleos Familiares candidatos a subsídios do
Programa Minha Casa, Minha Vida (Faixa 02), nos termos da Lei Municipal nº 2.064/2023.

> **Status atual:** fase de *design*. Este repositório contém, por ora, os documentos
> de especificação, o modelo de dados e a **matriz de regras parametrizada** do edital.
> O código da aplicação (Django) será construído sobre esta fundação.

## Por que design primeiro

O edital converte-se em **regras de negócio precisas** (faixas de pontuação, limites de
renda, critérios de desempate, valores fixos ancorados na data de publicação). Errar uma
faixa ou um operador de comparação (`≤` vs `<`) muda a classificação final de um processo
público — com risco de impugnação. Por isso as regras vivem primeiro como especificação
e como parâmetros versionados (`regras/parametros_edital.yaml`), e só então viram código.
Se o edital mudar, altera-se o parâmetro — não o motor.

## Documentos

| Documento | Conteúdo |
|-----------|----------|
| [`docs/01-diagnostico.md`](docs/01-diagnostico.md) | Leitura crítica do edital + do documento de requisitos; riscos e decisões pendentes |
| [`docs/02-especificacao-funcional.md`](docs/02-especificacao-funcional.md) | Módulos, telas, fluxos e perfis de acesso |
| [`docs/03-modelo-de-dados.md`](docs/03-modelo-de-dados.md) | Tabelas, campos, relacionamentos e diagrama ER |
| [`docs/04-regras-de-negocio.md`](docs/04-regras-de-negocio.md) | Matriz completa de regras do edital (requisitos, pontuação, desempate) |
| [`docs/05-seguranca-lgpd.md`](docs/05-seguranca-lgpd.md) | Controle de acesso, auditoria, LGPD e guarda de documentos |
| [`docs/06-roadmap.md`](docs/06-roadmap.md) | Fases de desenvolvimento sugeridas |
| [`regras/parametros_edital.yaml`](regras/parametros_edital.yaml) | **Parâmetros do edital em formato legível por máquina** (fonte única da verdade para o motor de pontuação) |

## Stack (definida)

- **Backend:** Python + Django
- **Banco:** SQLite em desenvolvimento → PostgreSQL em produção (troca via `settings`)
- **Front-end:** Django Templates + Bootstrap
- **Documentos:** armazenados **fora** da raiz web, servidos apenas mediante autorização

## Próximo passo

Fechados e validados os documentos de design com a Comissão de Inscrição, o desenvolvimento
começa pelo **motor de pontuação** (módulo Python puro, testado contra todas as faixas do
edital) e pelos **models** do banco. Ver [`docs/06-roadmap.md`](docs/06-roadmap.md).
