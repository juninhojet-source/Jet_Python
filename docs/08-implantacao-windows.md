# 08 — Implantação em Windows Server 2012 R2 (teste prático)

Guia para subir o sistema em **Windows Server 2012 R2 Standard** para o teste
prático na rede interna. Usa **Waitress** (servidor WSGI para Windows — o
`gunicorn` não roda em Windows) e **WhiteNoise** (serve os estáticos sem
precisar de IIS). Banco em **SQLite** para começar; PostgreSQL é opcional.

> Resumo: instalar Python → `.env` → `instalar.bat` → `iniciar.bat` → acessar
> `http://IP-DO-SERVIDOR:8000/`. Depois, opcionalmente, rodar como **serviço**
> com NSSM e/ou colocar **HTTPS** via IIS.

## 1. Instalar o Python

- Baixe o **Python 3.12 (Windows installer, 64-bit)** em python.org.
  - ⚠️ Em 2012 R2, **não** use Python 3.13+ (exige Windows 10/Server 2016+).
    3.12 e 3.11 são compatíveis com 2012 R2.
- Na instalação, marque **"Add python.exe to PATH"** e instale para todos os usuários.
- **Gotcha do 2012 R2:** se o Python não abrir (erro de DLL `api-ms-win-crt-*`),
  instale o **"Update for Universal C Runtime" (KB2999226)** do Windows Update /
  catálogo da Microsoft e reinicie.
- Confirme no **Prompt de Comando**: `py -3.12 --version`.

## 2. Obter o projeto

Copie o projeto para, por exemplo, `C:\mcmv\Jet_Python` (via `git clone` da branch,
ou descompactando um ZIP do repositório). Os comandos abaixo assumem essa pasta.

## 3. Configurar o `.env`

Copie o modelo e edite:

```bat
cd C:\mcmv\Jet_Python
copy .env.windows.example .env
notepad .env
```

Ajuste no mínimo:
- `DJANGO_SECRET_KEY` — gere depois de instalar (passo 4) com
  `python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"`
- `DJANGO_ALLOWED_HOSTS` — inclua o **IP e/ou nome do servidor** (ex.: `192.168.0.10,servidor-habitacao`).
- `DJANGO_CSRF_TRUSTED_ORIGINS` — as URLs usadas no navegador (ex.: `http://192.168.0.10:8000`).
- Deixe `DJANGO_SSL_REDIRECT=0` e `DJANGO_BEHIND_PROXY=0` enquanto o teste for por **HTTP**.
- `MCMV_MEDIA_ROOT` e `MCMV_LOG_DIR` — pastas fora da web (ex.: `C:\mcmv\media`, `C:\mcmv\logs`).

## 4. Instalar dependências e preparar o banco

Rode (como Administrador) o script de instalação:

```bat
cd C:\mcmv\Jet_Python
scripts\windows\instalar.bat
```

Ele cria o virtualenv `.venv`, instala `requirements-windows.txt` (Django, Waitress,
WhiteNoise, openpyxl, reportlab…), aplica as migrações, coleta os estáticos e pede a
criação do **usuário administrador**.

> Se o `pip` falhar por rede/TLS em 2012 R2, garanta o **TLS 1.2** habilitado no
> sistema (o Python recente já usa TLS próprio, então normalmente funciona).

Crie os servidores com seus perfis e (opcional) dados de demonstração:

```bat
.venv\Scripts\activate.bat
python manage.py criar_servidor maria --perfil Analista --senha "SenhaForte#1"
python manage.py seed_demo          REM (opcional) núcleos de exemplo
```

## 5. Rodar e acessar

```bat
scripts\windows\iniciar.bat
```

No próprio servidor: `http://localhost:8000/`. De outra máquina na rede:
`http://IP-DO-SERVIDOR:8000/`.

**Liberar a porta no Firewall do Windows** (uma vez, como Administrador):

```bat
netsh advfirewall firewall add rule name="MCMV 8000" dir=in action=allow protocol=TCP localport=8000
```

## 6. Rodar como Serviço do Windows (NSSM) — recomendado

Para o sistema subir sozinho com o servidor e reiniciar em caso de falha.

1. Baixe o **NSSM** (https://nssm.cc/download), extraia o `win64\nssm.exe` e
   copie para a pasta do projeto (`C:\mcmv\Jet_Python`) ou para `C:\mcmv\`.
2. Instale o serviço com um comando (Prompt **como Administrador**):

   ```bat
   cd C:\mcmv\Jet_Python
   scripts\windows\instalar-servico.bat
   ```

   O script localiza o `nssm.exe`, cria o serviço `MCMV` apontando para o
   `run_waitress.py` (que aplica migrações e coleta estáticos antes de servir),
   configura início automático, log rotativo em `C:\mcmv\logs\servico.log` e
   inicia o serviço. As configurações continuam vindo do `.env` (via
   `AppDirectory`).
3. Parar/iniciar: `net stop MCMV` / `net start MCMV`.
4. Remover o serviço: `scripts\windows\remover-servico.bat`.

> Ao usar o serviço, **não** rode também o `iniciar.bat` ao mesmo tempo — os
> dois tentariam usar a mesma porta.

## 7. HTTPS (opcional, recomendado antes de dados reais)

Para o teste em rede interna, HTTP basta. Ao publicar com dados reais, coloque
**HTTPS**. A forma mais comum no Windows é o **IIS como proxy reverso**:

1. Instale o IIS com os módulos **URL Rewrite** e **Application Request Routing (ARR)**.
2. Crie um site com um **certificado** (o da Prefeitura ou um interno).
3. Configure uma regra de reescrita encaminhando para `http://127.0.0.1:8000/`,
   repassando o cabeçalho `X-Forwarded-Proto: https`.
4. No `.env`, passe a usar: `DJANGO_SSL_REDIRECT=1`, `DJANGO_BEHIND_PROXY=1`,
   e ajuste `DJANGO_ALLOWED_HOSTS`/`DJANGO_CSRF_TRUSTED_ORIGINS` para `https://...`.
5. Faça o Waitress escutar só localmente: `MCMV_HOST=127.0.0.1` no `.env`.

## 7.1. Publicar no IIS por hostname (proxy reverso) — script pronto

Para acessar por `http://mcmv.baraodecocais.mg.gov.br` (após o DNS apontar o
hostname para o IP do servidor, ex.: `172.16.64.9`), há um script que configura
o IIS como proxy reverso para o Waitress:

```bat
REM 1) O Waitress deve rodar em 127.0.0.1:8000 (serviço MCMV/NSSM ou iniciar.bat)
REM 2) Execute o PowerShell COMO ADMINISTRADOR:
cd C:\mcmv\Jet_Python\deploy\windows\iis
powershell -ExecutionPolicy Bypass -File .\configurar-iis.ps1 -ProjetoDir C:\mcmv\Jet_Python
```

O script: instala os recursos do IIS, verifica os módulos **URL Rewrite** e
**ARR** (se faltarem, informa os links; com internet, use `-BaixarModulos` para
instalar automaticamente), habilita o proxy do ARR, cria o site com o
*host header* `mcmv.baraodecocais.mg.gov.br` na porta 80, libera a porta no
firewall e ajusta o `.env` (ALLOWED_HOSTS/CSRF/BEHIND_PROXY, e Waitress em
127.0.0.1:8000). Depois, **reinicie o Waitress** e acesse o hostname.

Parâmetros úteis: `-Hostname`, `-Porta`, `-Backend`, `-BaixarModulos`.

**HTTPS (recomendado antes de dados reais):** emita/instale o certificado no
site do IIS (binding 443), altere no `web.config` o `X-Forwarded-Proto` para
`https` e no `.env` `DJANGO_SSL_REDIRECT=1`; reinicie o Waitress.

## 7.2. HTTPS automático — script pronto

Há um script que faz todo o HTTPS de uma vez: garante os módulos, publica o
`web.config` de HTTPS (redireciona HTTP→HTTPS e repassa `X-Forwarded-Proto: https`),
**gera um certificado autoassinado** para o hostname/IP (ou importa um `.pfx`),
vincula na porta 443, libera o firewall e ajusta o `.env`.

```bat
REM O Waitress (servico MCMV) deve estar rodando em 127.0.0.1:8000.
cd C:\mcmv\Jet_Python\deploy\windows\iis

REM Autoassinado (com internet para baixar os modulos, se faltarem):
powershell -ExecutionPolicy Bypass -File .\configurar-https.ps1 -ProjetoDir C:\mcmv\Jet_Python -BaixarModulos

REM Depois, reinicie o Waitress para aplicar o .env:
net stop MCMV && net start MCMV
```

Acesse `https://mcmv.baraodecocais.mg.gov.br` (ou `https://172.16.64.9`).

- **Certificado oficial (.pfx):** acrescente `-Pfx C:\certs\mcmv.pfx -SenhaPfx "senha"`.
- **Autoassinado + aviso do navegador:** o script exporta o certificado público
  em `C:\mcmv\mcmv-cert.cer`. Instale-o nas máquinas clientes em **Autoridades de
  Certificação Raiz Confiáveis** (ou distribua por **GPO** no domínio) para o
  aviso "Não seguro" desaparecer.
- ⚠️ **O certificado do `New-SelfSignedCertificate` do 2012 R2 é SHA-1 e não
  serve para acesso por IP** — o Chrome recusa (segue "Não seguro" mesmo
  instalado). Gere um certificado decente (SHA-256, com DNS **e** IP no SAN):

  ```bat
  .venv\Scripts\activate.bat
  python scripts\windows\gerar_certificado.py --hostname mcmv.baraodecocais.mg.gov.br --ip 172.16.64.9 --senha mcmv123 --saida C:\mcmv
  REM vincula o novo certificado no IIS:
  powershell -ExecutionPolicy Bypass -File deploy\windows\iis\configurar-https.ps1 -ProjetoDir C:\mcmv\Jet_Python -Pfx C:\mcmv\mcmv.pfx -SenhaPfx mcmv123
  net stop MCMV & net start MCMV
  ```

  Depois instale `C:\mcmv\mcmv-cert.cer` nas **Autoridades de Certificação Raiz
  Confiáveis** dos clientes (ou por GPO). Aí o cadeado aparece — por nome e por IP.
- **HSTS:** o `configurar-https.ps1` só liga HSTS com a opção `-HSTS` (use apenas
  com certificado oficial e confiável; com autoassinado, deixe desligado).
- **Instalar o certificado nas estações:** copie `mcmv-cert.cer` e
  `deploy/windows/estacao/instalar-certificado.bat` para `C:\mcmv` da estação e
  rode o `.bat` **como Administrador** (ele faz `certutil -addstore -f Root` e
  fecha o navegador). Para muitas máquinas de uma vez, prefira **GPO**:
  Configuração do Computador → Políticas → Configurações do Windows →
  Configurações de Segurança → Diretivas de Chave Pública → Autoridades de
  Certificação Raiz Confiáveis → **Importar** o `mcmv-cert.cer`.
- **Rollback (voltar para HTTP em `:8000`):** no `.env`, `DJANGO_SSL_REDIRECT=0`,
  `MCMV_HOST=0.0.0.0`, e reinicie o Waitress.

## 7.3. E-mail do recibo (opcional)

Para enviar o comprovante (recibo) por e-mail ao requerente, preencha o SMTP da
Prefeitura no `.env` e reinicie o serviço:

```
DJANGO_EMAIL_HOST=smtp.baraodecocais.mg.gov.br
DJANGO_EMAIL_PORT=587
DJANGO_EMAIL_USER=mcmv@baraodecocais.mg.gov.br
DJANGO_EMAIL_PASSWORD=...              REM senha do e-mail
DJANGO_EMAIL_USE_TLS=1
DJANGO_EMAIL_FROM=mcmv@baraodecocais.mg.gov.br
```

Com o host configurado, aparece o botão **"✉ Enviar por e-mail"** na tela da
inscrição (após finalizar, e se o requerente tiver e-mail). Sem `DJANGO_EMAIL_HOST`,
o botão fica oculto. Teste enviando para um e-mail seu antes de usar com o público.

## 8. Banco de dados

- **Teste prático:** SQLite (padrão) — nada a instalar; o arquivo é `db.sqlite3`.
- **Produção:** PostgreSQL para Windows. Instale, crie o banco/usuário, rode
  `pip install "psycopg[binary]"` no venv e defina as variáveis `POSTGRES_*` no `.env`.

## 9. Backup (Windows)

- **SQLite:** pare o serviço (`net stop MCMV`), copie `db.sqlite3` e a pasta
  `MCMV_MEDIA_ROOT` para um destino seguro, reinicie (`net start MCMV`). Agende com o
  **Agendador de Tarefas**.
- **PostgreSQL:** use `pg_dump` (agende no Agendador de Tarefas) + cópia da pasta de mídia.
- Guarde os backups fora do servidor e **teste a restauração**.

## 10. Atualizar o sistema

```bat
cd C:\mcmv\Jet_Python
net stop MCMV
git pull
.venv\Scripts\activate.bat
pip install -r requirements-windows.txt
net start MCMV
```

> `migrate` e `collectstatic` são aplicados automaticamente ao iniciar (pelo
> `run_waitress.py`). Se preferir, ainda pode rodá-los à mão antes do
> `net start`.

## 11. Problemas comuns

| Sintoma | Causa / solução |
|---|---|
| `DisallowedHost` ao abrir | Falta o host em `DJANGO_ALLOWED_HOSTS`. Inclua `127.0.0.1,localhost` **e** o IP/nome do servidor. Reinicie o Waitress após editar o `.env` |
| **403** ao enviar formulário | Adicione a URL em `DJANGO_CSRF_TRUSTED_ORIGINS` |
| Página sem estilo (CSS 404) | Rode `python manage.py collectstatic --noinput` |
| Redireciona para `https://` e não abre | No teste HTTP, defina `DJANGO_SSL_REDIRECT=0` |
| Python não inicia (erro de DLL) | Instale o **UCRT (KB2999226)** e reinicie |
| Porta 8000 ocupada | Altere `MCMV_PORT` no `.env` e libere no Firewall |
| `check --deploy` acusa cookies inseguros | Esperado em HTTP; some ao ativar HTTPS (`DJANGO_SSL_REDIRECT=1`) |
| **IIS retorna 500 em tudo** (log IIS mostra `500 50 33`) | O `win32 33` (LOCK_VIOLATION) indica que a definição de *server variables* está travada. Desbloqueie e reinicie o IIS: `C:\Windows\System32\inetsrv\appcmd.exe unlock config /section:system.webServer/rewrite/allowedServerVariables` e depois `iisreset`. Os scripts `configurar-iis.ps1`/`configurar-https.ps1` já fazem isso |
| `DisallowedHost` só depois de rodar um script `.ps1` | O `.env` foi gravado com BOM (PowerShell 5.1). Rode `python scripts\windows\definir_secret.py` (limpa o BOM e garante a `SECRET_KEY`) e reinicie o serviço |
