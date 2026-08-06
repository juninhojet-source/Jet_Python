# Documentação — SIGTRANS Saúde

Sistema de Gestão de Transporte de Pacientes — Secretaria Municipal de Saúde de Barão de Cocais/MG.

## Documentos

- **[SIGTRANS_Saude_Escopo_Arquitetura.docx](./SIGTRANS_Saude_Escopo_Arquitetura.docx)** — Documento de Escopo e Arquitetura Técnica (v1.1).
  Consolida a análise técnica anterior ao desenvolvimento: situação atual, escopo funcional,
  arquitetura, modelo de dados (MER), requisitos derivados dos formulários reais, LGPD,
  ambiente e plano de implementação em fases.
- **[SIGTRANS_Saude_Apresentacao.pptx](./SIGTRANS_Saude_Apresentacao.pptx)** — Apresentação institucional
  do projeto (10 slides) para a Secretaria de Saúde, focada em benefícios.

## Premissas técnicas confirmadas

- Desenvolvimento e manutenção pela própria TI da Prefeitura.
- Hospedagem em servidor local **Windows Server** (sem nuvem pública para dados de pacientes).
- Banco de dados **PostgreSQL**, de propriedade da Prefeitura.
- Backend **Python + Django + Django REST Framework**.
- Autenticação com **contas próprias do sistema** (arquitetura preparada para futura integração LDAP/AD).
- BPA atendido por **relatório em PDF** para digitação manual (sem arquivo magnético).

## Ajustes da revisão v1.1 (solicitados pela Secretaria)

- **Removidos** os cadastros de Veículos e de Motoristas.
- Agenda organizada **por horário**, em ordem de agendamento, das **06:00 às 16:30, segunda a sexta**.
- Relatórios com consultas **por agendamento, dia, mês, nome** do paciente e demais filtros.
- Premissas a confirmar: capacidade por horário (parametrizável); granularidade dos horários
  (fixos de 30 min ou livres); e o campo "tipo de veículo" mantido apenas como seleção no agendamento.

## Plano de implementação (resumo)

| Fase | Entrega |
|------|---------|
| 1 | Fundação, cadastros (Paciente/Destino), login/perfis, auditoria |
| 2 | Agenda + Agendamento por horário, Cartão de Embarque (PDF), Lista do Dia |
| 3 | Painel de Senhas (MT-01..50, painel de TV) |
| 4 | Relatórios (por agendamento/dia/mês/nome...), BPA, pesquisa e dashboard |
| 5 | Endurecimento LGPD, backup/restore, documentação e treinamento |
