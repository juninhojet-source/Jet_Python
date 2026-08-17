# Instalação no Windows (servidor) — passo a passo simples

Scripts para instalar e testar o SIGTRANS Saúde no Windows/Windows Server
sem precisar digitar comandos manualmente.

## Pré-requisitos (instalar uma vez no servidor)

1. **Python 3.12** — https://www.python.org/downloads/
   - No instalador, marque **"Add python.exe to PATH"**.
   - Recomendado o 3.12 (todas as bibliotecas têm versão pronta).
2. **Git** — https://git-scm.com/download/win (aceite as opções padrão).

## Baixar o sistema

Abra o **Prompt de Comando** (cmd) numa pasta de sua escolha e rode:

```
git clone -b claude/system-analysis-o0y6jp https://github.com/juninhojet-source/Jet_Python.git
cd Jet_Python
```

> Se pedir login, entre com a conta do GitHub.
> (Alternativa sem Git: baixe o ZIP da branch pelo GitHub e extraia.)

## Instalar (uma vez)

Dê **dois cliques** em `scripts\windows\instalar.bat`
(ou rode `scripts\windows\instalar.bat` no cmd, dentro da pasta do projeto).

O script cria o ambiente, instala tudo, prepara o banco e pede o usuário/senha
do administrador.

## Iniciar (sempre que quiser usar)

Dê **dois cliques** em `scripts\windows\iniciar.bat`.

- No próprio servidor: **http://localhost:8000**
- De outro computador na rede: **http://IP-DO-SERVIDOR:8000**
  (descubra o IP com `ipconfig`; pode ser necessário liberar a porta 8000 no
  Firewall do Windows).

Para parar, feche a janela ou pressione **Ctrl+C**.

## Produção: domínio + HTTPS

Para acessar por **https://sigtrans.baraodecocais.mg.gov.br** (sem a porta 8000)
e com certificado:

1. `scripts\windows\criar-certificado.bat` — gera o certificado interno gratuito.
2. `scripts\windows\iniciar-producao.bat` — sobe o sistema (Waitress) em produção.
3. Instale os módulos **URL Rewrite 2.1** e **ARR 3.0** no IIS (uma vez).
4. `scripts\windows\configurar-iis.bat` — configura o IIS (proxy + HTTPS)
   automaticamente. Depois, distribua `C:\certs\prefeitura-ca.crt` nas máquinas.

Detalhes e alternativa com nginx: `docs\MANUAL_PUBLICACAO_DOMINIO_HTTPS.md`.

## Observações

- Sem arquivo `.env`, o sistema usa **SQLite** — ótimo para testes, sem instalar
  banco de dados. Para **produção** (PostgreSQL + Waitress + HTTPS), veja
  `docs/MANUAL_INSTALACAO.md` e `docs/MANUAL_PUBLICACAO_DOMINIO_HTTPS.md`.
- Backup a qualquer momento: `.venv\Scripts\python.exe manage.py backup`.
- Atualizar para a versão mais nova: `git pull` e rode `instalar.bat` de novo.
