# Segurança da Informação e LGPD — SIGTRANS Saúde

O sistema trata dados pessoais sensíveis de saúde e foi desenvolvido em conformidade
com a Lei nº 13.709/2018 (LGPD). Este documento resume os controles implementados.

## Controle de acesso

- **Autenticação individual** com contas próprias do sistema (sem compartilhamento).
- **Perfis de acesso** (menor privilégio): Administrador, Atendente, Coordenação, Consulta.
- **Bloqueio por tentativas**: após 5 tentativas de login malsucedidas, o acesso é
  temporariamente bloqueado (parametrizável em `LOGIN_MAX_TENTATIVAS`).
- **Logout automático por inatividade** após 30 minutos (`IDLE_TIMEOUT_SECONDS`).

## Senhas

- Armazenadas com **hash seguro** (PBKDF2), nunca em texto puro.
- **Política de senha forte**: mínimo de 8 caracteres, com letras e números, evitando
  senhas comuns e apenas numéricas.

## Trilha de auditoria

- **Alterações de dados** (inclusão, alteração, exclusão) registradas com valor
  anterior e novo, autor e data (django-simple-history).
- **Eventos de acesso e operações** registrados na trilha de auditoria: login, logout,
  tentativas falhas, bloqueios, exportações e impressões — com usuário, data/hora e IP.
- A trilha é **imutável**: não pode ser alterada nem excluída pela interface.

## Proteção da aplicação

- Proteções nativas do framework contra **CSRF, XSS e injeção de SQL**.
- **HTTPS/TLS** no ambiente de produção (via proxy reverso).
- Cookies de sessão seguros e cabeçalhos de segurança em produção.

## Hospedagem e dados

- Hospedagem **exclusivamente no servidor local da Prefeitura** (sem nuvem pública
  para dados de pacientes).
- Banco de dados de **propriedade exclusiva da Prefeitura**.

## Direitos do titular

O sistema permite atender às solicitações da LGPD:

- **Consulta** dos dados cadastrados;
- **Correção** e **atualização** cadastral;
- **Registro das datas** das alterações (histórico).

## Backup

- Backups completos e rotina de restauração — ver [MANUAL_BACKUP.md](./MANUAL_BACKUP.md).
