# 07 — Implantação e produção (Fase 6)

Guia para colocar o sistema em produção no servidor municipal com segurança e
conformidade com a LGPD.

## 1. Pré-requisitos

- Python 3.11+, PostgreSQL 14+, nginx, e (para backup) `gpg`.
- Um usuário de sistema dedicado (ex.: `mcmv`) sem shell de login.

## 2. Variáveis de ambiente

Copie `.env.example` para `.env` (ou configure no `systemd`) e ajuste. Gere a chave:

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

Mínimo para produção: `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`,
`DJANGO_CSRF_TRUSTED_ORIGINS` e as variáveis `POSTGRES_*`. Com `DJANGO_DEBUG=0` o sistema
**recusa** iniciar se a `SECRET_KEY` for a de desenvolvimento.

## 3. Banco de dados

```bash
sudo -u postgres createuser mcmv --pwprompt
sudo -u postgres createdb mcmv --owner=mcmv
pip install "psycopg[binary]>=3.1"   # driver PostgreSQL
python manage.py migrate
python manage.py createsuperuser
```

Crie os servidores com seus perfis:

```bash
python manage.py criar_servidor maria --perfil Analista --senha '***'
```

## 4. Arquivos estáticos e documentos

```bash
python manage.py collectstatic --noinput
```

- **Estáticos** (`STATIC_ROOT`): servidos pelo nginx em `/static/`.
- **Documentos** (`MEDIA_ROOT`, ex.: `/var/lib/mcmv/media`): **NÃO** exponha no nginx.
  São servidos apenas pela view autenticada `documento_download`, que registra o acesso.
  Permissões restritas: `chown -R mcmv:mcmv /var/lib/mcmv/media && chmod 750`.

## 5. Servir a aplicação (gunicorn + nginx)

```bash
pip install gunicorn
gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3
```

nginx (essencial): terminação **HTTPS** (certificado válido), `proxy_pass` para o gunicorn,
`location /static/` apontando para `STATIC_ROOT`, e **nenhum** `location` para a pasta de
documentos. Encaminhe `X-Forwarded-Proto` (o Django já está configurado para confiar nele
com `DJANGO_BEHIND_PROXY=1`).

Valide a configuração de segurança:

```bash
DJANGO_DEBUG=0 DJANGO_SECRET_KEY=... DJANGO_ALLOWED_HOSTS=exemplo python manage.py check --deploy
```

## 6. Backup criptografado

`scripts/backup.sh` gera dump do PostgreSQL + documentos, **cifrados com GPG**. Importe a
chave pública do destinatário no servidor e agende no cron (ex.: diário às 3h):

```
0 3 * * * cd /opt/mcmv && set -a && . ./.env && ./scripts/backup.sh >> /var/log/mcmv/backup.log 2>&1
```

Restauração: `scripts/restore.sh <arquivo>.gpg` (requer a chave privada). **Teste a
restauração** periodicamente — backup não testado não é backup.

## 7. LGPD — retenção e descarte (decisão D-6)

- Defina a **tabela de temporalidade**: por quanto tempo os documentos e dados pessoais
  ficam guardados após o encerramento do processo, e o procedimento de descarte seguro.
- O log de acesso a documentos (auditoria) é evidência do tratamento — preserve-o pelo
  prazo legal.
- Minimização: colete apenas o necessário ao processo seletivo.

## 8. Checklist de segurança

- [ ] `DJANGO_DEBUG=0` e `SECRET_KEY` própria (o sistema recusa iniciar sem isso)
- [ ] HTTPS obrigatório (HSTS ativo), cookies `Secure`/`HttpOnly`
- [ ] Documentos fora da raiz web; servidos só por view autenticada e logada
- [ ] PostgreSQL com usuário dedicado e senha forte; `sslmode` conforme a rede
- [ ] Backups criptografados agendados e restauração testada
- [ ] Perfis atribuídos (Administrador restrito a poucos); revisão periódica de acessos
- [ ] `python manage.py check --deploy` sem alertas críticos
