# SIGAZ — Sistema Integrado de Gestão Animal e Zoonoses

**Prefeitura Municipal de Barão de Cocais — MG**
**Secretaria Municipal de Saúde · Departamento de TI**

Sistema institucional para cadastro, controle sanitário e vigilância epidemiológica de animais do município. Construído com Node.js + Express + SQLite e frontend HTML/CSS/JS sem dependências externas pesadas.

---

## 📦 O que vem no pacote

### Módulos funcionais
- ✅ **Cadastro de Animais** com código único, foto e QR Code
- ✅ **Cadastro de Responsáveis** com validação real de CPF e busca de endereço por CEP
- ✅ **Agendamentos** (castrações, vacinações, visitas) com calendário visual
- ✅ **Controle de Vacinação, Vermifugação e Ectoparasitários**
- ✅ **Vigilância de Zoonoses** (Raiva, Leishmaniose, etc.)
- ✅ **Campanhas e Mutirões** com registro de atendimentos em lote
- ✅ **Denúncias de Maus-Tratos** com formulário público (anônimo opcional) e protocolo
- ✅ **Estoque de Insumos** (vacinas, vermífugos) com alerta de validade e saldo mínimo
- ✅ **Carteirinha Digital** com foto + QR Code + Termo de Posse Responsável em PDF
- ✅ **Consulta Pública** via QR Code
- ✅ **Dashboard** com indicadores e gráficos
- ✅ **Relatórios** com filtros e exportação CSV/PDF profissional
- ✅ **Importação em lote** via CSV (com preview, validação e detecção de erros)
- ✅ **Modo escuro** alternável (preferência salva por usuário)
- ✅ **PWA** — pode ser "instalado" no celular/desktop como app

### Segurança
- 🔒 Autenticação JWT com login por usuário ou e-mail
- 🔒 Política de senha forte configurável
- 🔒 Bloqueio automático após N tentativas falhas
- 🔒 Troca de senha obrigatória no 1º login e após reset
- 🔒 Reset de senha pelo admin (gera senha temporária)
- 🔒 Desbloqueio manual de usuários
- 🔒 Auditoria com diff (mostra o que mudou em cada atualização)
- 🔒 7 perfis de acesso

### Administração e operação
- 💾 Backup automático diário agendado (interno, sem cron externo)
- 💾 Retenção configurável (apaga backups antigos)
- 💾 Backup, download e restauração pela interface
- ⚙️ Configurações editáveis pelo admin
- 🪟 Instalação como serviço do Windows (sobe sozinho ao ligar a máquina)
- 📋 Log de auditoria filtrável

---

## 🚀 Instalação Rápida

### Pré-requisitos
- **Node.js 22 ou superior** (recomendado 22 LTS ou 24): https://nodejs.org
- npm (vem junto com o Node)

> 💡 **Não precisa de Python, Visual Studio Build Tools, nem SQLite separado.** O sistema usa o módulo SQLite **nativo do Node 22+**, então `npm install` é rápido e sem compilação de código nativo.

### Passo a passo

```bash
# 1. Instalar dependências (rápido — não compila nada)
npm install

# 2. Criar banco de dados e popular com dados de exemplo
npm run init-db

# 3. Iniciar o servidor
npm start
```

Acesse: **http://localhost:3000**

---

## 🔑 Credenciais de Acesso (Demonstração)

| Perfil       | Usuário        | Senha     |
|--------------|----------------|-----------|
| Administrador| `admin`        | `admin123`|
| Veterinário  | `veterinario`  | `vet123`  |

> 💡 O login aceita **usuário** OU **e-mail**, à escolha. Ex: `admin` ou `admin@bcocais.mg.gov.br`.

> ⚠️ **Altere as senhas após o primeiro login em produção.**

---

## 🗂️ Estrutura do Projeto

```
sigaz/
├── backend/
│   ├── server.js              # Servidor Express principal
│   ├── routes/                # Rotas da API REST
│   │   ├── auth.js            # Login / JWT
│   │   ├── animais.js         # CRUD de animais + QR Code
│   │   ├── responsaveis.js    # CRUD de tutores
│   │   ├── sanitario.js       # Vacinas, vermifugação, ectoparasitários
│   │   ├── zoonoses.js        # Notificações epidemiológicas
│   │   ├── dashboard.js       # Indicadores e relatórios
│   │   └── usuarios.js        # Gestão de acessos + auditoria
│   ├── middleware/
│   │   └── auth.js            # Autenticação e autorização JWT
│   ├── db/
│   │   ├── schema.sql         # Schema completo
│   │   ├── init.js            # Inicialização
│   │   ├── connection.js      # Conexão SQLite
│   │   └── sigaz.db           # Banco de dados (gerado)
│   └── utils/
│       ├── codigos.js         # Geração de códigos ANI-XXXX
│       └── logger.js          # Registro de auditoria
├── frontend/
│   ├── index.html             # Tela de login
│   ├── dashboard.html         # Painel inicial
│   ├── animais.html           # Listagem e cadastro de animais
│   ├── responsaveis.html      # Cadastro de tutores
│   ├── vacinacao.html         # Controle vacinal
│   ├── zoonoses.html          # Notificações de zoonoses
│   ├── carteirinhas.html      # Lista para emissão de carteirinhas
│   ├── carteirinha.html       # Carteirinha individual com QR Code
│   ├── consulta.html          # Página pública para QR Code
│   ├── relatorios.html        # Geração de relatórios
│   ├── usuarios.html          # Admin: usuários e auditoria
│   ├── css/
│   │   ├── app.css            # Design system institucional
│   │   └── login.css          # Tela de login
│   └── js/
│       └── comum.js           # SDK do frontend (API, modais, toasts)
├── package.json
├── .env.example
└── README.md
```

---

## 🌐 Endpoints da API

Todos os endpoints (exceto `/api/auth/login` e `/api/publico/animal/:codigo`) exigem o cabeçalho `Authorization: Bearer <token>`.

### Autenticação
- `POST /api/auth/login` — login
- `GET  /api/auth/me` — dados do usuário logado
- `POST /api/auth/logout` — encerrar sessão

### Animais
- `GET    /api/animais` — listar com filtros (`busca`, `especie`, `responsavel_id`)
- `GET    /api/animais/:id` — detalhar com histórico completo
- `POST   /api/animais` — criar (gera QR Code automaticamente)
- `PUT    /api/animais/:id` — atualizar
- `DELETE /api/animais/:id` — inativar (soft delete)

### Responsáveis
- `GET    /api/responsaveis`
- `GET    /api/responsaveis/:id`
- `POST   /api/responsaveis`
- `PUT    /api/responsaveis/:id`
- `DELETE /api/responsaveis/:id`

### Sanitário (Vacinas, Vermifugação, Ectoparasitários)
- `GET  /api/sanitario/vacinas` (filtro `vencendo_dias=30`)
- `POST /api/sanitario/vacinas`
- `DELETE /api/sanitario/vacinas/:id`
- Análogos para `/api/sanitario/vermifugacoes` e `/api/sanitario/ectoparasitarios`

### Zoonoses
- `GET    /api/zoonoses` (filtros: `zoonose`, `status`, `bairro`, `animal_id`)
- `GET    /api/zoonoses/:id`
- `POST   /api/zoonoses`
- `PUT    /api/zoonoses/:id`
- `DELETE /api/zoonoses/:id`

### Dashboard e Relatórios
- `GET /api/dashboard` — indicadores e gráficos
- `GET /api/relatorios/animais`
- `GET /api/relatorios/vacinacao`
- `GET /api/relatorios/zoonoses`

### Usuários (somente admin)
- `GET    /api/usuarios`
- `POST   /api/usuarios`
- `PUT    /api/usuarios/:id`
- `DELETE /api/usuarios/:id`
- `GET    /api/usuarios/logs/auditoria`

### Administração — Backup/Restore (somente admin)
- `GET    /api/admin/backup` — Download direto do banco atual
- `POST   /api/admin/backups/criar` — Salva backup no servidor
- `GET    /api/admin/backups` — Lista backups locais
- `GET    /api/admin/backups/:arquivo/download` — Baixa backup específico
- `DELETE /api/admin/backups/:arquivo` — Remove backup local
- `POST   /api/admin/restore` — Restaura banco a partir de upload

### Consulta Pública (sem autenticação)
- `GET /api/publico/animal/:codigo` — leitura de QR Code

---

## ⚙️ Configuração

Copie `.env.example` para `.env` e ajuste:

```ini
PORT=3000
JWT_SECRET=mude-esta-chave-em-producao
JWT_EXPIRES_IN=8h
DB_PATH=./backend/db/sigaz.db
```

> ⚠️ **Importante:** Em produção, **troque o `JWT_SECRET`** por uma string longa e aleatória.

---

## 🪟 Rodar como serviço do Windows (recomendado em produção)

Para o SIGAZ subir automaticamente quando a máquina ligar, sem precisar de terminal aberto:

1. Abra o **PowerShell ou CMD como Administrador**
2. Vá até a pasta do projeto:
   ```cmd
   cd C:\caminho\para\sigaz
   ```
3. Execute o arquivo `instalar-servico-windows.bat` (ou rode manualmente):
   ```cmd
   npm install node-windows --no-save
   node servico-windows.js instalar
   ```
4. O sistema agora sobe sozinho. Para gerenciar, abra `services.msc` e procure por **SIGAZ**.

Para **desinstalar o serviço**: execute `desinstalar-servico-windows.bat` (como Admin).

## 🌐 Acesso externo / HTTPS

Por padrão, o SIGAZ roda em HTTP na porta 3000 (uso interno). Para expor na internet com HTTPS, veja o guia detalhado: **PRODUCAO-HTTPS.md**

## 💾 Backup

O banco de dados é um único arquivo: `backend/db/sigaz.db`.

### Pela interface web (recomendado)

Acesse **Usuários → Backup & Restauração** (apenas perfil admin/ti):

- **Baixar Backup Agora**: gera e baixa direto para o seu computador
- **Salvar Backup no Servidor**: mantém cópia datada em `backend/backups/`
- **Restauração**: upload de um `.db` salvo anteriormente, com confirmação dupla
- Antes de qualquer restauração, um backup automático do estado atual é criado como rede de segurança

### Manualmente

Pare o servidor e copie o arquivo:

```bash
cp backend/db/sigaz.db backups/sigaz-$(date +%Y%m%d).db
```

Ou, **sem parar o servidor** (cópia consistente via SQLite):

```bash
sqlite3 backend/db/sigaz.db "VACUUM INTO 'backups/sigaz-20260529.db'"
```

Recomenda-se rotina diária de backup. Pode ser configurado via cron/agendador de tarefas.

---

## 🔒 Perfis de Acesso

| Perfil       | Permissões |
|--------------|-----------|
| `admin`      | Acesso total + gestão de usuários e auditoria |
| `ti`         | Acesso total |
| `veterinario`| Cadastro de animais, vacinação, zoonoses |
| `auxiliar`   | Cadastro de animais e responsáveis |
| `endemias`   | Zoonoses |
| `secretaria` | Consulta e relatórios |

---

## 📲 QR Code da Carteirinha

A cada animal cadastrado é gerado automaticamente um QR Code apontando para a página pública de consulta:

```
http://<servidor>/consulta.html?codigo=ANI-2026-0001
```

Esse QR Code é embutido na carteirinha digital, que pode ser impressa ou salva como PDF pelo botão de impressão.

---

## 🛠️ Comandos úteis

```bash
npm start              # Inicia servidor em produção
npm run dev            # Inicia com auto-reload (nodemon)
npm run init-db        # Recria o banco e popula dados de exemplo
```

---

## 🆘 Solução de Problemas

**Erro: "Banco de dados não inicializado"**
Execute `npm run init-db` antes de iniciar o servidor.

**Erro: "Cannot find module 'node:sqlite'"**
Sua versão do Node é anterior à 22. Atualize para o Node 22 LTS ou superior em https://nodejs.org

**Porta 3000 já em uso**
Mude a porta no `.env`:
```ini
PORT=3001
```

---

## 📜 Licença

Sistema desenvolvido para a Prefeitura Municipal de Barão de Cocais. Uso interno e adaptação livres para a administração pública.

---

**SIGAZ v1.0** · Prefeitura Municipal de Barão de Cocais · 2026
