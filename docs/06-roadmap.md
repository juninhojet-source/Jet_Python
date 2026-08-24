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

## Fase 3 — Cadastro ✅
- [x] Login e layout base (templates + CSS próprio, sem CDN) — `templates/`, `static/`
- [x] Painel de indicadores (M1) — `dashboard`
- [x] Lista com busca e filtro por situação — `inscricao_list`
- [x] Cadastro do requerente + inscrição (M2) — `inscricao_nova`/`inscricao_editar`
- [x] Composição familiar (M3) e renda por integrante (M4) — `membro_novo`/`renda_nova`
- [x] Documentos (M5) com upload e **download controlado por view autenticada** (acesso logado)
- [x] Validação de requisitos (M6) com 🟢/🔴 e **marcação "não apto" com confirmação** (`requisitos.py`)
- [x] Painel de pontuação e ação "recalcular" (M7)
- [x] **Finalização + bloqueio** da inscrição (Anexo II)
- [x] Classificação com desempate e empates marcados para sorteio (M8)
- [x] Testes de views + requisitos (total: 15 testes Django)

## Fase 4 — Fluxo de homologação e permissões por perfil ✅
- [x] `contas/acesso.py` — `em_perfil()` e decorador `perfil_requerido()` (Administrador/superuser sempre)
- [x] `cadastro/fluxo.py` — máquina de transições de situação por perfil, registrada na auditoria
- [x] Homologação **Atendente → Analista → Comissão** com botões contextuais na tela
- [x] Regra: só vira **APTO** quando todos os requisitos estão atendidos
- [x] Separação contato (bloqueia após finalização) × avaliação da análise (autorizada e auditada)
- [x] Ações mutáveis protegidas por perfil (criar/editar/documentos/recalcular/inaptidão/classificar)
- [x] Comando `python manage.py criar_servidor <login> --perfil <Perfil> --senha <senha>`
- [x] Testes de acesso e fluxo (total: 25 testes Django)

Nota: a integração do motor (M7) e a classificação/desempate (M8) foram entregues nas Fases 2/3.

## Fase 5 — Relatórios, exportação e dashboard ✅
- [x] `cadastro/relatorios.py` — utilitários de Excel (openpyxl) e PDF (reportlab)
- [x] Ficha individual em **PDF** (por inscrição)
- [x] Classificação em **PDF** e **Excel**
- [x] Exportações **Excel**: base com filtros (situação, faixa de pontos, PcD, crianças,
      idosos, risco), aptos, indeferidos/não aptos (com motivo), documentação pendente,
      empates para sorteio e auditoria
- [x] Central de relatórios (`/relatorios/`) e link "Ficha (PDF)" em cada inscrição
- [x] Dashboard (M1) com KPIs e distribuição por faixa de pontuação
- [x] Testes gerando .xlsx e .pdf reais (total: 19 testes Django)

## Fase 6 — Endurecimento e implantação ✅
- [x] `settings` por ambiente (`.env` opcional): `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`,
      `CSRF_TRUSTED_ORIGINS`, PostgreSQL com `sslmode`/`CONN_MAX_AGE`
- [x] Guarda que **recusa iniciar** em produção com a `SECRET_KEY` de desenvolvimento
- [x] Cabeçalhos de segurança (HSTS, cookies Secure, nosniff, X-Frame-Options DENY,
      Referrer-Policy) e `SECURE_PROXY_SSL_HEADER` atrás de proxy
- [x] Logging com rotação de arquivo em produção
- [x] `.env.example` e `docs/07-implantacao.md` (gunicorn + nginx, HTTPS, LGPD/retenção)
- [x] Backup **criptografado** (GPG) do banco + documentos: `scripts/backup.sh` / `restore.sh`
- [x] `python manage.py check --deploy` sem alertas

Ver [07-implantacao.md](07-implantacao.md).

## Princípio transversal
Toda regra do edital é **parâmetro**, não código. Mudou o edital → muda o YAML e os testes;
o motor permanece.
