# Manual do Usuário — SIGTRANS Saúde

Guia rápido para a rotina de transporte de pacientes. Serve também como material de
treinamento das equipes.

## Acesso

1. Abra o endereço do sistema no navegador.
2. Informe **usuário** e **senha** (fornecidos pelo administrador).
3. Por segurança, a sessão é encerrada após 30 minutos de inatividade.

## Perfis

| Perfil | O que pode fazer |
|--------|------------------|
| Administrador | Tudo, incluindo usuários e auditoria |
| Atendente | Cadastrar pacientes e agendamentos, emitir cartão e senhas |
| Coordenação | Consultar, gerenciar e emitir relatórios |
| Consulta | Somente leitura |

## Fluxo do atendimento

```
Senha → Cadastro do paciente → Agendamento → Cartão de embarque → Embarque → Relatório BPA
```

### 1. Senha (recepção)

- Há **duas filas/salas** de atendimento, cada uma com sua numeração própria:
  - **Sala 01 — Marcação de Consultas e Exames** (senhas `MC-01`…);
  - **Sala 02 — Marcação de Transporte** (senhas `MT-01`…).
- O paciente retira a senha no **Kiosque** (`/senhas/emitir/`), escolhendo o serviço.
- **Senhas → Painel de Senhas**: o operador seleciona a sala na aba e clica em
  **Chamar próximo**. Também há **Repetir**, **Voltar** e **Avançar**.
- A **TV da recepção** (`/senhas/painel/`) exibe as duas salas lado a lado.
- As senhas vão de 01 a 50 e reiniciam automaticamente a cada dia, por fila.
- As filas/salas são configuráveis em `SIGTRANS["SENHA_FILAS"]` (settings).

### 2. Cadastro do paciente

- **Pacientes → Novo**. Preencha os dados; ao menos **CPF ou Cartão SUS (CNS)** é
  obrigatório. O sistema evita duplicidade e calcula a idade automaticamente.
- Os campos seguem o que o BPA exige (raça/cor, município com código IBGE, etc.).

### 3. Agendamento

- **Agenda → Novo agendamento**. Escolha o paciente, a data e o **horário** (das 05:00
  às 18:00, de segunda a sexta), o destino e o procedimento.
- **Tipo de veículo** e **local de embarque** são de preenchimento livre (podem mudar
  na hora da viagem).
- Não há limite diário de agendamentos.

### 4. Cartão de embarque

- Na agenda ou no agendamento, clique em **Cartão** para gerar o **PDF** pronto para
  impressão, no modelo da Prefeitura.

### 5. Confirmação e embarque

- **Confirmar viagem**: registra o contato feito no dia anterior.
- **Registrar embarque**: marque *Embarcou* ou *Não embarcou* e os horários.

### 6. Relatórios e BPA

- **Relatórios → Agendamentos**: filtre por dia, mês, nome, município, procedimento e
  status; exporte em **PDF** ou **Excel**.
- **Relatórios → BPA**: reúne os campos para digitação no BPA.
- **Relatórios → Indicadores**: totais do dia/mês, faltas e distribuição por município,
  destino e status.

## Dúvidas e suporte

Departamento de Informática e Tecnologia — Aristides Ferreira Junior — (31) 3837-7661.
