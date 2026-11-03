# 09 — LGPD e Segurança da Informação

Documento de governança do **Sistema MCMV — Cadastro Habitacional** (Edital
001/2026, Barão de Cocais/MG) quanto à **Lei nº 13.709/2018 (LGPD)** e às
medidas de segurança. Complementa a **Política de Privacidade** exibida no
sistema em `/privacidade/` (pública) e vinculada no rodapé e na tela de login.

## 1. Papéis

- **Controlador:** Prefeitura Municipal de Barão de Cocais/MG.
- **Encarregado (DPO) / contato:** Departamento de Informática e Tecnologia —
  Aristides Ferreira Junior — (31) 3837-7661.
- **Operadores:** servidores autorizados, segmentados por perfil.

## 2. Base legal (LGPD)

- Art. 7º, II — obrigação legal/regulatória;
- Art. 7º, III — execução de políticas públicas (PMCMV / Edital 001/2026);
- Art. 23 — tratamento por ente público para finalidade pública;
- Art. 11, II — dado sensível (indicação de deficiência) para política pública.

## 3. Dados tratados e finalidade

| Categoria | Exemplos | Finalidade |
|---|---|---|
| Identificação | nome, CPF, RG, nascimento | cadastro e identificação |
| Contato | telefone, e-mail, endereço | comunicação/comprovação |
| Núcleo familiar | composição, parentesco | pontuação/classificação |
| Socioeconômico | renda, aluguel, situação habitacional | critérios do edital |
| Sensível | pessoa com deficiência | critério de pontuação |
| Documentos | anexos comprobatórios | comprovação |
| Auditoria | usuário, IP, data/hora, ações | segurança/prestação de contas |

## 4. Medidas de segurança implementadas

### Infraestrutura (ambiente da Prefeitura)
- Servidor municipal próprio em **local seguro, climatizado e de acesso restrito**,
  disponível somente ao responsável pela TI.
- **Firewall Fortinet (FortiGate)** protegendo a rede (filtragem + IPS).
- **Active Directory (AD)** e domínio corporativo (identidades centralizadas).

### Aplicação (implementado neste sistema)
- **Acesso somente a pessoas autorizadas**, com autenticação individual.
- **Perfis de usuário** segmentados: Administrador, Atendente, Analista,
  Comissão, Consulta (controle por grupo + `perfil_requerido`).
- **Log de acesso e trilha de auditoria** somente-adição (app `auditoria`:
  quem, quando, o quê, IP).
- **HTTPS/TLS** no acesso (IIS como proxy reverso; ver `docs/08`).
- **Senha forte** (validadores do Django) e **expiração de sessão** por
  inatividade (`SESSION_COOKIE_AGE`, expira ao fechar o navegador).
- Cabeçalhos de segurança (nosniff, X-Frame-Options DENY, referrer-policy);
  cookies `Secure`/`HttpOnly` sob HTTPS.
- **Documentos** guardados fora da raiz web (`MEDIA_ROOT`), servidos apenas por
  view autenticada/autorizada.
- **Registro de ciência (LGPD)** do requerente na inscrição
  (`ciencia_lgpd` + data), com link para a Política de Privacidade.
- **Backup automático diário** com retenção e **restauração testada**
  (ver `docs/10-backup-restauracao.md`).

## 5. Direitos do titular (art. 18) e prazo

Confirmação/acesso, correção, anonimização/bloqueio/eliminação, informação sobre
compartilhamento, revogação de consentimento e petição à ANPD. **Prazo: 15 dias**
(art. 19). Solicitações pelo contato do DPO acima.

## 6. Retenção e descarte

- Cadastros/documentos: durante o processo + prazo legal de guarda/prestação de contas.
- Logs de auditoria: enquanto necessários à fiscalização.
- Backups: conforme retenção configurada (padrão 30 dias).
- Servidores desligados: conta inativada imediatamente.
- Ao fim dos prazos: anonimização ou eliminação.

## 7. Boas práticas operacionais

- Conceder o **menor perfil** necessário a cada servidor; revisar acessos periodicamente.
- Inativar imediatamente contas de quem sai da função.
- Manter o servidor atualizado e o FortiGate com regras mínimas necessárias.
- Guardar os backups **fora do servidor** e **testar a restauração** regularmente.
- Só publicar dados reais após o **HTTPS** ativo (já configurado).

## 8. Incidentes

Em caso de incidente de segurança com risco a titulares, o DPO avalia e, quando
cabível, comunica os titulares e a **ANPD** (art. 48 da LGPD), registrando o
ocorrido e as medidas adotadas.
