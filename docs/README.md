# Documentação — SIGTRANS Saúde

Sistema de Gestão de Transporte de Pacientes — Secretaria Municipal de Saúde de Barão de Cocais/MG.

## Documentos

- **[SIGTRANS_Saude_Escopo_Arquitetura.docx](./SIGTRANS_Saude_Escopo_Arquitetura.docx)** — Documento de Escopo e Arquitetura Técnica (v1.0).
  Consolida a análise técnica anterior ao desenvolvimento: situação atual, escopo funcional,
  arquitetura, modelo de dados (MER), requisitos derivados dos formulários reais, LGPD,
  ambiente e plano de implementação em fases.

## Premissas técnicas confirmadas

- Desenvolvimento e manutenção pela própria TI da Prefeitura.
- Hospedagem em servidor local **Windows Server** (sem nuvem pública para dados de pacientes).
- Banco de dados **PostgreSQL**, de propriedade da Prefeitura.
- Backend **Python + Django + Django REST Framework**.
- Autenticação com **contas próprias do sistema** (arquitetura preparada para futura integração LDAP/AD).
- BPA atendido por **relatório em PDF** para digitação manual (sem arquivo magnético).

## Plano de implementação (resumo)

| Fase | Entrega |
|------|---------|
| 1 | Fundação, cadastros (Paciente/Veículo/Motorista/Destino), login/perfis, auditoria |
| 2 | Viagem + Agendamento com controle de lotação, Cartão de Embarque (PDF), Mapa de Viagem |
| 3 | Painel de Senhas (MT-01..50, painel de TV) |
| 4 | Relatório BPA, pesquisa e dashboard |
| 5 | Endurecimento LGPD, backup/restore, documentação e treinamento |
