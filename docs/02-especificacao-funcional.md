# 02 — Especificação Funcional

Descreve **o que cada módulo/tela faz**. Base para as telas Django (templates + Bootstrap).

## Perfis de acesso

| Perfil | Pode |
|--------|------|
| **Administrador** | Tudo, incluindo gestão de usuários e parâmetros do edital |
| **Atendente** | Criar/editar inscrições (enquanto em rascunho), anexar documentos |
| **Analista** | Analisar documentação, validar critérios, aprovar/rejeitar documentos |
| **Comissão** | Homologar, revisar, validar classificação, registrar sorteio |
| **Consulta** | Somente leitura e relatórios |

Toda ação que cria/altera dado é **registrada em auditoria** com usuário, data/hora e IP.

## Módulos

### M1 — Dashboard
Indicadores para a Comissão: total de inscrições; por situação (rascunho, recebida, em
análise, apta, indeferida, pendente, homologada); nº com deficiência; nº de idosos; nº de
núcleos com crianças; nº em situação de risco; nº com mulher responsável; inscrições por dia;
distribuição por faixa de pontuação.

### M2 — Cadastro do Requerente / Inscrição
Campos de identificação (nome, CPF, nascimento, sexo, estado civil, contato, endereço
completo) + dados da inscrição (número **gerado automaticamente**, data/hora, situação).
Campos derivados **calculados e exibidos** (não digitados): idade, "≥ 18?", "reside há
≥ 5 anos?", "renda na faixa?", "possui imóvel?", "já beneficiado?". Estes alimentam a
validação de requisitos (M6).

### M3 — Composição do Núcleo Familiar
Cadastro **individual** de cada integrante: nome, CPF, nascimento, sexo, parentesco
(Requerente, Cônjuge, Companheiro(a), Filho(a), Enteado(a), Pai, Mãe, Padrasto, Madrasta,
Irmão(ã), Menor sob tutela, Outro), flags (dependente, PcD, arrimo). O sistema **conta
automaticamente**: integrantes, crianças ≤ 12, idosos, PcD, dependentes.

### M4 — Controle de Renda
Cada integrante pode ter uma ou mais fontes de renda (emprego formal, informal, autônomo,
aposentadoria, pensão, benefício, outra), com valor e marcação **computável/não computável**.
O sistema calcula: renda bruta familiar computável → renda per capita. Rendas do
[catálogo de exclusões](../regras/parametros_edital.yaml) entram como não computáveis por padrão.

### M5 — Documentação
Checklist eletrônica de documentos **obrigatórios** e **condicionais** (ver
[04-regras](04-regras-de-negocio.md)), cada um com: tipo, pessoa relacionada, data de
emissão, arquivo (armazenado com acesso controlado), situação (Pendente/Recebido/Em
análise/Aprovado/Rejeitado/Substituição solicitada), observação, servidor responsável e data
de conferência. Não permite marcar "documentação OK" em bloco — a conferência é item a item.

### M6 — Análise / Validação de Requisitos e Homologação
Tela que mostra cada **requisito eliminatório** (M2) com status 🟢/🔴. Quando há requisito não
atendido, o sistema **sinaliza "NÃO APTO" mas não indefere sozinho** (D-5): exige confirmação
do analista/comissão, com justificativa registrada. Fluxo de homologação: Atendente →
Analista → Comissão.

### M7 — Pontuação
Exibe o cálculo transparente e **rastreável** por inscrição: cada Critério Legal (I–IV) com
sim/não e pontos; cada Complementar (per capita, aluguel) com o valor apurado, a faixa e os
pontos; e `P = CL + CC`. Deve mostrar **qual documento comprova cada critério** (auditoria de
pontuação). Cálculo automático a partir dos dados de M3/M4/M5 e dos parâmetros do edital.

### M8 — Classificação e Empates
Gera a lista em ordem decrescente de pontuação. Aplica automaticamente os dois primeiros
critérios de desempate (filhos ≤ 12, depois idosos). Empates remanescentes ficam **marcados
para sorteio público**; após o sorteio, o operador registra ata (data, hora, procedimento,
participantes, resultado, responsável, documento anexo).

### M9 — Relatórios e Exportação
Ficha individual (PDF); classificação geral (PDF/Excel); documentação pendente; indeferidos
(com motivo); aptos; encaminhados à CAIXA; empates; auditoria. Botão **Exportar Excel** com
filtros (situação, faixa de pontuação, PcD, idosos, crianças, risco).

### M10 — Auditoria e Controle de Usuários
Log imutável de toda alteração (ver [05-seguranca-lgpd](05-seguranca-lgpd.md)); gestão de
usuários e perfis; **bloqueio do cadastro após finalização** da inscrição (Anexo II).

## Fluxo de situações da inscrição

```
RASCUNHO → INSCRIÇÃO RECEBIDA → EM ANÁLISE → DOCUMENTAÇÃO VALIDADA
        → APTO → HOMOLOGADO → CLASSIFICADO → ENCAMINHADO À CAIXA
```
Ramos: `EM ANÁLISE → PENDÊNCIA → REGULARIZADO → EM ANÁLISE`; `EM ANÁLISE → INDEFERIDO`.
Após **FINALIZAR INSCRIÇÃO**, o registro é 🔒 **bloqueado**; correções só por procedimento
administrativo autorizado, sempre logadas.
