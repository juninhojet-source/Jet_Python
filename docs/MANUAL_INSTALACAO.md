# Manual de Instalação — SIGTRANS Saúde

Sistema de Gestão de Transporte de Pacientes — Prefeitura Municipal de Barão de Cocais/MG
Departamento de Informática e Tecnologia · Responsável: Aristides Ferreira Junior · (31) 3837-7661

## 1. Requisitos

- **Servidor:** Windows Server (ou Linux).
- **Python** 3.11 ou superior.
- **PostgreSQL** 13+ (produção). Em desenvolvimento, SQLite é usado automaticamente.
- Navegadores suportados: Google Chrome, Microsoft Edge, Mozilla Firefox.

## 2. Preparação do ambiente

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## 3. Configuração (arquivo .env)

Copie `.env.example` para `.env` e ajuste:

```
SECRET_KEY=<gerar uma chave longa e aleatória>
DEBUG=False
ALLOWED_HOSTS=sigtrans.baraodecocais.mg.gov.br,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://sigtrans.baraodecocais.mg.gov.br

POSTGRES_DB=sigtrans
POSTGRES_USER=sigtrans
POSTGRES_PASSWORD=<senha forte>
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

> Se `POSTGRES_DB` não estiver definido, o sistema usa SQLite (apenas para testes/dev).

## 4. Banco de dados e dados iniciais

```bash
python manage.py migrate
python manage.py seed_municipios
python manage.py criar_admin --username admin --nome "Aristides Ferreira Junior"
python manage.py collectstatic --noinput
```

## 5. Execução em produção (Windows Server)

Servidor de aplicação **Waitress**, com IIS ou Nginx como proxy reverso (HTTPS):

```bash
waitress-serve --listen=127.0.0.1:8000 config.wsgi:application
```

Configure o proxy reverso para encaminhar o domínio HTTPS para `127.0.0.1:8000`
e servir com certificado TLS.

## 6. Verificação

- Acesse a URL configurada e faça login com o usuário administrador.
- Confirme o funcionamento de: cadastro de paciente, agenda, cartão de embarque (PDF),
  painel de senhas e relatórios.

## 7. Atualização de versão

```bash
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
# reinicie o serviço Waitress
```
