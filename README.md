# SIGTRANS Saúde

Sistema de Gestão de Transporte de Pacientes — **Prefeitura Municipal de Barão de Cocais / MG**
Secretaria Municipal de Saúde · Departamento de Informática e Tecnologia
Responsável: Aristides Ferreira Junior · (31) 3837-7661

> Documentação de escopo, arquitetura e apresentação em [`docs/`](docs/).

## Stack

- **Python + Django + Django REST Framework**
- **PostgreSQL** (produção) / SQLite (desenvolvimento)
- **django-simple-history** (auditoria — LGPD)
- **WhiteNoise** (estáticos) · **Waitress** (WSGI no Windows Server)
- Interface: Django Templates (sem framework JS externo)

## Estrutura

```
config/            Configurações do projeto (settings, urls, wsgi/asgi)
apps/
  core/            Base (TimeStamped, Município, dashboard, validadores)
  accounts/        Usuário próprio + perfis + controle de acesso
  pacientes/       Cadastro de pacientes (campos do BPA)
  destinos/        Cadastro de estabelecimentos de destino
templates/         Templates HTML
static/            CSS e imagens (brasão em static/img/logo-prefeitura.png)
docs/              Escopo, arquitetura e apresentação
```

## Ambiente de desenvolvimento

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_municipios     # municípios frequentes (código IBGE)
python manage.py criar_admin --username admin --nome "Aristides Ferreira Junior"

python manage.py runserver
```

Acesse http://127.0.0.1:8000/ — sem arquivo `.env`, o sistema usa **SQLite** e `DEBUG=True`.

## Produção (Windows Server + PostgreSQL)

1. Copie `.env.example` para `.env` e preencha (SECRET_KEY, POSTGRES_*, ALLOWED_HOSTS, `DEBUG=False`).
2. `python manage.py migrate && python manage.py collectstatic --noinput`
3. Sirva com Waitress (proxy reverso via IIS/Nginx):
   ```bash
   waitress-serve --listen=127.0.0.1:8000 config.wsgi:application
   ```

## Perfis de acesso

| Perfil | Acesso |
|--------|--------|
| Administrador | Total, incluindo gestão de usuários |
| Atendente | Cadastra e edita pacientes/destinos |
| Coordenação | Cadastra, edita e consulta |
| Consulta | Somente leitura |

## Fase 1 — entregue

- [x] Projeto Django + PostgreSQL/SQLite, WhiteNoise, Waitress
- [x] Usuário próprio com perfis e controle de acesso por perfil
- [x] Auditoria automática (histórico com valor anterior/novo)
- [x] Cadastro de **Paciente** com os campos do BPA (CNS, CPF, raça/cor, IBGE...)
- [x] Cadastro único: valida CPF/CNS e evita duplicidade
- [x] Cadastro de **Destinos** e **Municípios**
- [x] Dashboard, pesquisa e paginação · testes automatizados

## Fase 2 — entregue

- [x] **Agendamento** por horário (05:00–18:00, seg–sex, **sem limite diário**)
- [x] **Agenda do dia / Lista do Dia** — agendamentos por data, em ordem de horário
- [x] **Cartão de Embarque em PDF** no modelo da Prefeitura (ReportLab)
- [x] **Controle de embarque** (embarcou/faltou + horários) e confirmação da viagem
- [x] Campos de **embarque** e **tipo de veículo** de preenchimento manual/livre
- [x] Filtros de agendamento (data, status, paciente/destino) · testes automatizados

### Próximas fases

- **Fase 3:** Painel de Senhas (MT-01..50 + painel de TV).
- **Fase 4:** Relatórios (por agendamento, dia, mês, nome...) e BPA.
- **Fase 5:** Endurecimento LGPD, backup/restore, documentação e treinamento.

## Substituir a logo

O cabeçalho usa `static/img/logo-prefeitura.png` (hoje um **placeholder**).
Substitua pelo brasão oficial do Departamento de Informática, mantendo o nome do arquivo.
