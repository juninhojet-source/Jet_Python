# 05 — Segurança e LGPD

O sistema trata **dados pessoais e sensíveis** (CPF, renda, endereço, laudos de deficiência)
sob a Administração Pública. Requisitos abaixo são **de projeto**, não opcionais.

## Controle de acesso
- Autenticação individual (sem login compartilhado); senha com **hash** (Django PBKDF2/argon2).
- Autorização por **perfil** (ver [02-especificacao-funcional](02-especificacao-funcional.md)).
- Sessão com **expiração** por inatividade; proteção contra **força bruta** (lockout/rate-limit).
- Proteções web padrão do Django habilitadas: **CSRF**, ORM contra **SQL Injection**,
  escaping de template contra **XSS**, `SECURE_*`/HSTS, cookies `Secure`/`HttpOnly`.

## Guarda de documentos
- Binários **fora da raiz web** (nunca em `/var/www/html/...` acessível por URL direta).
- Servidos **apenas** por *view* autenticada que checa permissão e **registra o acesso**.
- `documento.arquivo_ref` guarda só a referência; download controlado e logado.

## Auditoria (rastreabilidade administrativa)
Tabela `auditoria` **append-only** (sem update/delete). Cada alteração registra: usuário,
data/hora, IP, operação, tabela, registro, campo, **valor anterior → novo**, justificativa.
Cobre especialmente: alterações de renda/pontuação, mudanças de situação, conferência de
documentos e **qualquer edição após a finalização** da inscrição.

## Imutabilidade após finalização (Anexo II)
Finalizada a inscrição, o cadastro é **bloqueado**. Correções posteriores só via procedimento
administrativo autorizado, com justificativa obrigatória e registro em auditoria. O sistema
não permite edição "silenciosa" pós-bloqueio.

## LGPD — princípios aplicados
- **Finalidade e minimização:** coletar só o necessário ao processo seletivo.
- **Transparência:** ficha individual mostra quais dados/documentos embasaram cada decisão.
- **Segurança:** criptografia em trânsito (**HTTPS**) e **backups criptografados**.
- **Retenção/temporalidade:** definir prazo de guarda e descarte pós-processo (decisão D-6).
- **Registro de tratamento:** o log de acesso a documentos serve de evidência de tratamento.

## Ambiente
- Desenvolvimento em **SQLite**; produção em **PostgreSQL** no servidor municipal, atrás de
  HTTPS, com backup automático criptografado e restauração testada.
